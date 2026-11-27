"""Verify the enclosed channel, grip obstruction, screw movement and visible art."""
import itertools
import json
import math

import cadquery as cq
import manifold3d as md
import numpy as np
import trimesh
from shapely.geometry import Polygon,box,shape
from shapely.ops import unary_union

from build_r6 import R6,CAD,ART,MAP,DONOR,PARENT,INNER,FACE,BOW_BASE,SHIFT,base,inputs,outlines,pads_and_ribs,regions
from validate_r3 import mesh_projection
from validate_wand import solid,intersection,cuboid


def rounded_gauge(x0,y0,x1,y1,r,thickness):
    outline=box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=20)
    wire=list(outline.exterior.coords)[::-1][:-1]
    return md.CrossSection([wire]).extrude(thickness).translate((0,0,-thickness/2))


def card_test(b):
    r=3.18
    fixed=b["head_purple"]+b["rear_purple"]+b["frame_purple"]
    plug=b["handle_purple"]
    swept=rounded_gauge(-26.99,-169.,26.99,27.85,r,1.20)
    continuous={}
    for x in (-.4,0,.4):
        for z in (-.29,0,.29):
            continuous[str((x,z))]=round(intersection(swept.translate((x,0,z)),fixed),7)
    assert max(continuous.values())<.00001,continuous
    cards={t:rounded_gauge(-26.99,-42.80,26.99,42.80,r,t) for t in (.76,1.20)}
    seated=cards[1.2].translate((0,-14.95,0))
    obstruction={str(p):round(intersection(seated.translate((0,-p,0)),plug),7)
                 for p in (0,.50,.59,.60,.61,.70,1.0,2.0,4.0)}
    assert obstruction["0.59"]<.00001 and obstruction["0.7"]>.05,obstruction
    upper={str(p):round(intersection(seated.translate((0,p,0)),fixed),7)
           for p in (0,.04,.05,.08,.15)}
    assert upper["0.04"]<.00001 and upper["0.15"]>.01,upper

    # Occupancy test across the center of the channel, while the opposing
    # skins still constrain both sides of the rigid card at this exact station.
    gate=cuboid(-1.5,1.5,-59.04,-58.88,-.90,.90)
    coverage=intersection(gate,plug)/gate.volume()
    assert coverage>.999999,coverage
    face_patches={}
    for x in (-12,12):
        for name,lo,hi in [("head_purple",.90,2.89),("rear_purple",-2.89,-.90)]:
            patch=cuboid(x-.5,x+.5,-59.04,-58.88,lo,hi)
            fraction=intersection(patch,b[name])/patch.volume()
            assert fraction>.99999,(name,x,fraction)
            face_patches[f"{name} X{x}"]=round(fraction,7)

    # Escape cross-section 3.45 mm below the seated position. Roughly 82 mm
    # of card still occupies the slot. Test skew, pitch, roll and shifts at
    # two card thicknesses; discard poses already disallowed by the skins.
    shifted={}
    for thick,gauge in cards.items():
        feasible=0
        denied=0
        total=0
        smallest=1.e6
        for pitch,roll,skew in itertools.product((-.35,0,.35),(-.60,0,.60),(-.60,0,.60)):
            g=gauge.rotate((pitch,roll,skew))
            for x,z in itertools.product((-.45,0,.45),(-.24,0,.24)):
                pose=g.translate((x,-18.4,z))
                total+=1
                if intersection(pose,fixed)>.00005:
                    continue
                feasible+=1
                v=intersection(pose,plug)
                smallest=min(smallest,v)
                denied+=int(v>.01)
        assert feasible>=10 and denied==feasible,(thick,feasible,denied)
        shifted[str(thick)]={"poses":total,"within_shell":feasible,"blocked_by_grip":denied,
                             "least_intersection_mm3":round(smallest,5)}
    projected=seated.project()
    exposed={n:round((projected-b[n].project()).area(),6) for n in ("head_purple","rear_purple")}
    print("Card",continuous,obstruction,upper,coverage,shifted,flush=True)
    return {"card_gauge_mm":[53.98,85.60,1.20],"rounded_corner_radius_mm":r,
        "slot_width_thickness_mm":[55.,1.8],"continuous_sweep_bottom_top_y_mm":[-169.,27.85],
        "swept_load_interference_mm3":continuous,"withdrawal_distance_to_grip_contact_mm":.60,
        "withdrawal_interference_mm3":obstruction,"upper_stop_interference_mm3":upper,
        "positive_gate_xyz_mm":[[-1.5,-59.04,-.9],[1.5,-58.88,.9]],"gate_filled_fraction":round(coverage,7),
        "opposing_skin_patch_filled_fractions":face_patches,"shifted_tilted_escape_challenge":shifted,
        "open_front_or_back_projected_card_area_mm2":exposed}


def screw_test(b,step):
    clip=cuboid(-21,21,-104,-54,-20,20)
    grip=(b["handle_purple"]+b["handle_gold"])^clip
    rear=b["rear_purple"]^clip
    front=b["head_purple"]^clip
    bow=b["bow_pink"]^clip
    values=[]
    for angle in range(0,2521,15):
        moved=grip.rotate((0,-angle,0)).translate((0,-3*angle/360,0))
        values.append([angle,intersection(front,moved),intersection(rear,moved),intersection(bow,moved),
                       moved.min_gap(bow,12)])
    assert max(row[3] for row in values)<.00001
    # Exact shape comparisons isolate the faceting residual in the STL threads.
    region=base.rect(-10,10,-80,-55,-10,10)
    handles=step["handle_purple"].intersect(region)
    females=[step[name].intersect(region) for name in ("head_purple","rear_purple")]
    exact={}
    for angle in (0,75,180,450,1080,2160,2520):
        moved=handles.rotate((0,0,0),(0,1,0),-angle).translate((0,-3*angle/360,0))
        exact[str(angle)]=[round(f.intersect(moved).Volume(),7) for f in females]
    assert max(v for pair in exact.values() for v in pair)<.00001,exact
    return {"pitch_mm":3.0,"axial_travel_mm":21,"mesh_poses":len(values),"angle_step_deg":15,
            "mesh_max_overlap_mm3":{"front":max(v[1] for v in values),"rear":max(v[2] for v in values),
                                    "bow":max(v[3] for v in values)},
            "minimum_bow_to_rotating_grip_mm":min(v[4] for v in values),"exact_STEP_pose_overlap_mm3":exact}


def details(packet,b,meshes):
    art={f["id"]:shape(f["geometry"]) for f in packet["features"]}
    gold_parts=[mesh_projection(solid(m)) for m in meshes["head_gold"].split()]
    lip=mesh_projection(b["head_purple"]^cuboid(-67,67,-62,64,FACE+.1,FACE+.7))
    rim=unary_union([p for p in gold_parts if p.intersection(art["rim-outer"]).area>2])
    flags={}
    for label in ("left-flag","high-flag","right-flag"):
        flag=max(gold_parts,key=lambda p:p.intersection(art[label]).area)
        flags[label]={"min_to_purple_lip_mm":round(flag.distance(lip),4),
                      "min_to_gold_rim_mm":round(flag.distance(rim),4)}
    assert min(v["min_to_purple_lip_mm"] for v in flags.values())>2.94,flags
    assert min(v["min_to_gold_rim_mm"] for v in flags.values())>5.45,flags
    anchor_ids={"left-flag","high-flag","right-flag","left-star","right-star","mickey"}
    anchors={}
    for f,shape2 in regions(packet,"head"):
        if f["id"] not in anchor_ids:
            continue
        body=b["head_"+f["color"]]
        rings=[]
        for depth in (.60,.22):
            layer=body ^ cuboid(-67,67,-63,64,FACE-depth-.01,FACE-depth+.01)
            rings.append(round(mesh_projection(layer).intersection(shape2).area,3))
        assert rings[0]>rings[1]>5,(f["id"],rings)
        anchors[f["id"]]={"embedded_foot_mm2":rings[0],"embedded_stem_mm2":rings[1]}
    lands,ribs=pads_and_ribs(packet)
    joint=lands.difference(unary_union([r.buffer(.20) for r in ribs]))
    # Slice the actual meshes across the planar joint. The head also has
    # neck geometry outside this area, so intersect with the actual bow.
    head=mesh_projection(b["head_purple"] ^ cuboid(-31,31,-63,-28,BOW_BASE-.025,BOW_BASE-.010))
    underside=mesh_projection(b["bow_pink"] ^ cuboid(-31,31,-73,-28,BOW_BASE+.010,BOW_BASE+.025))
    contact=head.intersection(underside).area
    assert abs(contact-joint.area)<.15,(contact,joint.area)
    return {"measured_flags":flags,"bow_planar_bond_area_mm2":round(contact,3),
            "measured_motif_root_sections":anchors,"integral_bow_ribs":2,"bow_rib_height_mm":.70,"bow_rib_slot_depth_mm":.93,
            "bow_rib_lateral_clearance_per_side_mm":.20,
            "bow_backing_thickness_mm":2.30,"face_motif_stepped_root_depth_mm":.80}


def main():
    packet,specs=inputs()
    b={}
    coupon_bodies={}
    mesh_by_name={}
    records={}
    for directory in ("print_parts","fit_coupon"):
        for path in sorted((R6/directory).glob("*.stl")):
            mesh=trimesh.load_mesh(path)
            children=mesh.split(only_watertight=False)
            assert mesh.is_volume and all(m.is_volume for m in children),path
            records[path.stem]={"sha256":base.digest(path),"shells":len(children),
                "watertight":bool(mesh.is_watertight),"consistent_winding":bool(mesh.is_winding_consistent),
                "all_positive_volume":all(m.volume>0 for m in children),"bbox_mm":mesh.bounds.round(4).tolist(),
                "volume_mm3":round(mesh.volume,3)}
            if directory=="print_parts":
                b[path.stem]=solid(mesh)
                mesh_by_name[path.stem]=mesh
            else:
                assert len(children)==1
                coupon_bodies[path.stem]=solid(mesh)
    assert len(b)==9
    overlaps={}
    for a,c in itertools.combinations(b,2):
        v=intersection(b[a],b[c])
        if v>.00001:
            overlaps[a+" / "+c]=round(v,7)
        if {a,c} not in ({"head_purple","handle_purple"},{"rear_purple","handle_purple"}):
            assert v<.002,(a,c,v)
    card=card_test(b)
    assert max(card["open_front_or_back_projected_card_area_mm2"].values())<.001,card
    coupon_card=card_test({name:coupon_bodies[part] for name,part in {
        "head_purple":"front_coupon_purple","rear_purple":"rear_coupon_purple",
        "frame_purple":"frame_coupon_purple","handle_purple":"grip_stub_purple"}.items()})
    feature=details(packet,b,mesh_by_name)
    print("Details",feature,flush=True)
    file=R6/"purple_castle_card_wand_R6.step"
    assembly=cq.Assembly.load(str(file))
    parts={k:n.obj for k,n in assembly.objects.items() if n.obj is not None}
    assert set(parts)==set(b)
    for name,body in parts.items():
        assert body.isValid() and len(body.Solids())==records[name]["shells"]
    screw=screw_test(b,parts)
    # Separately compare the fixed perimeter bond and the decorative envelope.
    star,outer,frame=outlines(packet)
    upper_arc=base.rounded_box(-27.5,-117,27.5,27.90,3.35).boundary.intersection(box(-33,24.5,33,31))
    top_wall=upper_arc.distance(outer.boundary)
    assert top_wall>2.0
    package={"units":"mm","source_SHA256":{p.name:base.digest(p) for p in (ART,MAP,DONOR,PARENT)},
       "step_sha256":base.digest(file),"mesh_files":records,"step_named_parts":len(parts),
       "step_valid_solids":sum(len(s.Solids()) for s in parts.values()),
       "functional_assemblies":["bonded star head and bow","full-size threaded grip"],
       "head_bond_land_each_side_mm2":round(frame.area,3),"upper_pocket_min_rim_wall_mm":round(top_wall,4),"star_xy_mm":list(star.bounds),
       "assembly_bounds_mm":[np.min([m.bounds[0] for m in mesh_by_name.values()],axis=0).round(3).tolist(),
                             np.max([m.bounds[1] for m in mesh_by_name.values()],axis=0).round(3).tolist()],
       "assembled_intersections_over_0p00001_mm3":overlaps,"card":card,"coupon_card":coupon_card,"screw":screw,
       "art_and_mounts":feature,"physical_status":"Coupon fit, adhesive, drop/pull, fatigue, thread wear, child access and reader operation unverified."}
    (R6/"validation_report.json").write_text(json.dumps(package,indent=2)+"\n")
    print("Verified STEP assemblies, screw poses",package["step_named_parts"],screw,flush=True)

if __name__=="__main__":
    main()
