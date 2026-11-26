"""Check delivered STL topology and measure the card path and screw motion."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import manifold3d as md
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import cadquery as cq
import trimesh
from build_wand import ORIGIN, Y_AXIS, slab, tube_y

from build_wand import ART, DEFAULT_DONOR, HERE, PLUG_X, assembly_xy, sha


def mesh_solid(mesh):
    m = md.Mesh(np.ascontiguousarray(mesh.vertices, dtype=np.float32),
                np.ascontiguousarray(mesh.faces, dtype=np.uint32))
    body = md.Manifold(m)
    assert body.status() == md.Error.NoError, body.status()
    return body


def cuboid(lo, hi):
    return md.Manifold.cube([b-a for a,b in zip(lo,hi)]).translate(lo)


def mm3(a, b):
    return round(abs((a ^ b).volume()), 5)


def collect():
    records, meshes, bodies = {}, {}, {}
    for directory in ["print_parts", "fit_coupon"]:
        for path in sorted((HERE/directory).glob("*.stl")):
            mesh = trimesh.load_mesh(path, process=True)
            solids = mesh.split(only_watertight=False)
            name = path.stem
            records[name] = {
                "file": str(path.relative_to(HERE).as_posix()), "sha256": sha(path),
                "bbox_mm": mesh.bounds.round(4).tolist(), "size_mm": mesh.extents.round(4).tolist(),
                "shell_count": len(solids), "watertight": bool(mesh.is_watertight),
                "consistent_winding": bool(mesh.is_winding_consistent),
                "all_components_positive_volume": all(p.volume>0 for p in solids),
            }
            expected = 14 if name=="bow_dots_white" else 2 if name=="coupon_spacer_black" else 1
            assert len(solids)==expected and all(p.is_volume for p in solids), (name, records[name])
            if directory == "print_parts":
                meshes[name] = mesh
                bodies[name] = mesh_solid(mesh)
    return records, meshes, bodies


def card_checks(bodies, meshes):
    # A sharp-cornered rectangular gauge contains a rounded CR80. This verifies
    # the full continuous translation interval, including card entry from free air.
    low = -48.40
    high = 37.20
    seated = cuboid([-26.99, low, -.38], [26.99, high, .38])
    sweep = cuboid([-26.99, -175, -.38], [26.99, high, .38])
    with_handle_removed = {k:mm3(v,sweep) for k,v in bodies.items() if k!="handle_cuff_pink"}
    assert max(with_handle_removed.values())<=.001, with_handle_removed
    handle=bodies["handle_cuff_pink"]
    assert mm3(seated,handle)==0
    pull_with_handle={str(d):mm3(handle,seated.translate((0,-d,0))) for d in (.50,.65,.75,1.5,3.0,8.0)}
    push_top={str(d):mm3(bodies["spacer_black"],seated.translate((0,d,0))) for d in (0,.025,.075,.30,1.0)}
    assert pull_with_handle["0.5"]==0 and pull_with_handle["0.65"]>0
    assert push_top["0.025"]==0 and push_top["0.075"]>0
    card_footprint = md.CrossSection.square((53.98,85.60)).translate((-26.99,low))
    exposed={side:round((card_footprint - bodies[side].project()).area(),6)
             for side in ("front_black","rear_black")}
    assert max(exposed.values())<.001, exposed
    return {"simulated_card_mm":[53.98,85.60,.76],"card_y_mm":[low,high],
            "groove_width_mm":55.0,"groove_thickness_mm":1.50,"positive_y_hard_stop_mm":37.25,
            "width_clearance_per_side_mm":.51,"thickness_clearance_per_face_mm":.37,
            "continuous_sweep_limits_y_mm":[-175,high],
            "continuous_sweep_overlap_mm3":with_handle_removed,
            "installed_handle_overlap_by_card_pull_mm":pull_with_handle,
            "spacer_overlap_by_card_push_mm":push_top,
            "front_back_card_exposed_area_mm2":exposed}


def thread_checks(bodies):
    handle=bodies["handle_cuff_pink"]
    neck_clip=cuboid([-8.2,-70.0,-8.2],[8.2,-37.8,8.2])
    female=(bodies["front_black"]^neck_clip)+(bodies["rear_black"]^neck_clip)
    connector=handle^cuboid([-9,-78,-9],[9,-48,9])
    # Check both helical directions and select the mating path from the mesh.
    check=[]
    for sign in (-1,1):
        samples=[]
        for angle in (30,60,90,120,150,180):
            moved=connector.rotate([0,sign*angle,0]).translate([0,-3*angle/360,0])
            samples.append(mm3(moved,female))
        check.append((max(samples),sign,samples))
    _, direction, coarse=min(check)
    samples=[]
    for angle in range(0,2521,15):
        moved=connector.rotate((0,direction*angle,0)).translate((0,-3*angle/360,0))
        samples.append((angle,mm3(moved,female)))
    return {"pitch_mm":3,"rotation_sign_about_positive_y_for_removal":direction,
            "opposite_rotation_sweep_at_first_half_turn":{str(s):v for _,s,v in check},
            "rotation_step_deg":15,"total_rotation_deg":2520,"total_travel_mm":21,
            "peak_interference_mm3":max(v for _,v in samples),
            "peak_at_deg":max(samples,key=lambda row:row[1])[0],
            "peak_first_turn_mm3":max(v for a,v in samples if a<=360),
            "positive_overlap_samples":[p for p in samples if p[1]>.01]}


def artwork_checks(bodies):
    def polygon(key):
        start,segments=ART[key]
        xy=[assembly_xy(*start)]
        for ax,ay,bx,by,cx,cy in segments:
            for t in np.linspace(0,1,101)[1:]:
                u=1-t
                xy.append(assembly_xy(u**3*start[0]+3*u*u*t*ax+3*u*t*t*bx+t**3*cx,
                                      u**3*start[1]+3*u*u*t*ay+3*u*t*t*by+t**3*cy))
            start=(cx,cy)
        return Polygon(xy)

    def outer(body):
        return max([Polygon(s) for s in body.project().to_polygons()],key=lambda p:p.area)

    original=polygon("HEAD")
    case=box(-29.65+1.65,-50+1.65,29.65-1.65,39.5-1.65).buffer(1.65,quad_segs=32)
    region=box(-85,-49.9,85,90)
    nominal_head=original.union(case).intersection(region)
    delivered_head=outer(bodies["front_black"]).intersection(region)
    nominal_bow=unary_union([polygon(s) for s in ("LEFT_BOW","RIGHT_BOW","KNOT")])
    delivered_bow=outer(bodies["bow_pink"]+bodies["bow_dots_white"])
    head_error=nominal_head.exterior.hausdorff_distance(delivered_head.exterior)
    bow_error=nominal_bow.exterior.hausdorff_distance(delivered_bow.exterior)
    assert max(head_error,bow_error)<.06,(head_error,bow_error)
    front=bodies["front_black"]
    for x in (-20,20):
        below=cuboid([x-.05,-46.05,2.47],[x+.05,-45.95,2.49])
        above=cuboid([x-.05,-46.05,2.51],[x+.05,-45.95,2.53])
        assert abs((front^below).volume()-below.volume())<1e-6
        assert (front^above).volume()==0
    for x in (-10,10):
        raised=cuboid([x-.05,-40.05,3.11],[x+.05,-39.95,3.13])
        assert abs((front^raised).volume()-raised.volume())<1e-6
    return {"scale_mm_per_photo_pixel":ART["mm_per_pixel"],"roll_deg":ART["roll_degrees"],
            "ear_span_trace_mm":round(original.bounds[2]-original.bounds[0],5),
            "delivered_head_span_mm":round(delivered_head.bounds[2]-delivered_head.bounds[0],5),
            "max_contour_deviation_mm":{"head_and_case_above_neck":round(head_error,5),"bow":round(bow_error,5)},
            "chin_relief_mm":.65,"front_pocket_shoulder_skin_mm":1.75,
            "measured_chin_probes_xy_mm":[[-10,-40],[10,-40]],
            "measured_shoulder_probes_xy_mm":[[-20,-46],[20,-46]]}

def precise_motion(donor):
    raw=cq.importers.importStep(str(donor)).solids().vals()
    final=cq.importers.importStep(str(HERE/"minnie_card_wand.step")).solids().vals()
    assert len(final)==21 and all(s.isValid() for s in final)
    donor_front=raw[0].translate((-175.816693734826,0,1.5))
    donor_rear=raw[2].translate((171.331443746177,0,0)).rotate(ORIGIN,Y_AXIS,180).translate((0,0,-1.5))
    probe_neck=slab(-8.25,8.25,-70,-37.8,-8.25,8.25)
    probe_plug=slab(-9,9,-79,-48,-10,10)
    result={}
    for label,front,rear,handle in [
        ("source",donor_front,donor_rear,raw[1].rotate(ORIGIN,Y_AXIS,180)),
        ("exported_step",final[0],final[2],final[4]),
    ]:
        front,rear=front.intersect(probe_neck),rear.intersect(probe_neck)
        plug=handle.intersect(probe_plug)
        poses={}
        for angle in (0,75,180,450,1080,2160,2520):
            moved=plug.rotate(ORIGIN,Y_AXIS,-angle).translate((0,-3*angle/360,0))
            poses[str(angle)]=[round(side.intersect(moved).Volume(),7) for side in (front,rear)]
        assert all(max(v)==0 for v in poses.values()),poses
        result[label]=poses
    # All touching components checked as exact solids after STEP import,
    # including individual white inlays and each pin in its final position.
    matrix={}
    for i,a in enumerate(final):
        for j,b in enumerate(final[i+1:],i+1):
            if a.distance(b)<1e-5:
                volume=a.intersect(b).Volume()
                matrix[f"{i}/{j}"]=round(abs(volume),7)
    assert max(matrix.values(),default=0)<.00001,matrix
    result["closed_assembly_intersections_mm3"]=matrix
    cuff_ring=tube_y(7.35,-69.24,-59.62).cut(tube_y(6.55,-70,-59))
    cuff_material=final[4].intersect(cuff_ring).Volume()
    assert abs(cuff_ring.Volume()-cuff_material)<1e-5
    result["continuous_cuff_wall"]={
        "radii_mm":[6.55,7.35],"y_limits_mm":[-69.24,-59.62],
        "expected_annulus_mm3":round(cuff_ring.Volume(),6),
        "measured_handle_material_mm3":round(cuff_material,6)}
    result["step_solid_count"]=len(final)
    result["all_step_solids_valid"]=True
    return result

def run(donor):
    records, meshes, bodies=collect()
    parts=dict(bodies,alignment_pin_black_right=bodies["alignment_pin_black_print_two"].translate((2*PLUG_X,0,0)))
    contacts={f"{k0}/{k1}":mm3(a,b) for (k0,a),(k1,b) in itertools.combinations(parts.items(),2)}
    print("pairs",max(contacts.values()),flush=True)
    checks=card_checks(parts,meshes)
    print("card",checks,flush=True)
    motion=thread_checks(parts)
    print("motion peak mm3",motion["peak_interference_mm3"],flush=True)
    report={"units":"mm","source_donor_step_sha256":sha(donor),"artwork":artwork_checks(parts),"exact_step":precise_motion(donor),
            "photo_trace_script_sha256":ART["source_sha256"],
            "artwork_json_sha256":sha(HERE/"artwork.json"),
            "assembly_step_sha256":sha(HERE/"minnie_card_wand.step"),
            "stls":records,"assembled_pair_intersections_mm3":contacts,
            "card":checks,"screw_motion":motion,"physical_fit":"Pending"}
    (HERE/"validation_report.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donor",type=Path,default=DEFAULT_DONOR)
    run(parser.parse_args().donor)
