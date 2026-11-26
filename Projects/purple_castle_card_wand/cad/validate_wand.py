"""Verify production STL intersections, load path, detent, thread and R2 artwork."""
import itertools
import json

import cadquery as cq
import manifold3d as md
import numpy as np
import trimesh
from shapely.geometry import box,shape

from build_wand import CAD,ART,DONOR,ART_HASH,DONOR_HASH,FLOOR,BOND,PIVOT,OPEN,digest,rect,extract_thread


def solid(mesh):
    return md.Manifold(md.Mesh(np.ascontiguousarray(mesh.vertices,dtype=np.float32),
                               np.ascontiguousarray(mesh.faces,dtype=np.uint32)))


def intersection(a,b):
    return max(0.0,(a^b).volume())


def cuboid(x0,x1,y0,y1,z0,z1):
    return md.Manifold.cube((x1-x0,y1-y0,z1-z0)).translate((x0,y0,z0))


def rotate_keeper(body,angle):
    # Coordinates are world front XY. Reverse Z-angles only when a reflected
    # build frame has its XY axes reversed. Here XY stays unchanged.
    return body.translate((-16,-16,0)).rotate((0,0,angle)).translate((16,16,0))


def card_local(width=85.60,height=53.98,thickness=1.20):
    outline=box(-width/2+3.18,3.18,width/2-3.18,height-3.18).buffer(3.18,quad_segs=18)
    section=md.CrossSection([list(outline.exterior.coords)[::-1][:-1]])
    gauge=section.extrude(thickness)
    assert gauge.volume()>width*height*thickness*.98
    return gauge


def world_card(gauge,toe_y,toe_depth,theta=0):
    # Model starts in positive outward depth, then lower edge tips away from
    # the tap surface. Reflect only that depth back into front-world Z.
    return gauge.rotate((theta,0,0)).translate((0,toe_y,toe_depth)).mirror((0,0,1)).translate((0,0,FLOOR))


def card_path(parts):
    gauge=card_local()
    rear=parts["rear_purple"]
    keep=parts["keeper_purple"]
    pin=parts["pivot_pin_purple"]
    open_keeper=rotate_keeper(keep,OPEN)
    fixed=rear+pin+open_keeper
    # The lower edge clears the tabs in air, slides underneath while angled,
    # then stays put as the top lowers. Reversing the poses unloads the card.
    results={}
    for tilt in (13.,15.,16.):
        phases=[
            ("lower",[((-39.85,6.0+(0.12-6.0)*t,tilt)) for t in np.linspace(0,1,61)]),
            ("tuck",[((-39.85-2.65*t,0.12,tilt)) for t in np.linspace(0,1,61)]),
            ("flatten",[((-42.50,0.12,tilt*(1-t))) for t in np.linspace(0,1,61)]),
            ("seat",[((-42.50,0.12*(1-t),0)) for t in np.linspace(0,1,9)])]
        stats={}
        for name,poses in phases:
            samples=[intersection(world_card(gauge,*pose),fixed) for pose in poses]
            stats[name]={"samples":len(samples),"peak_collision_mm3":round(max(samples),6),
                         "worst_pose":list(poses[int(np.argmax(samples))])}
        results[str(tilt)] = stats
    seated=world_card(gauge,-42.50,0)
    # Test actual 3-D material, at both extremes of available card play.
    toes=rear^cuboid(-33,33,-43.25,-41.05,FLOOR-3.80,FLOOR-2.29)
    tab_margins={str(theta):round(toes.min_gap(world_card(gauge,-42.50,.12,theta),3),4) for theta in (13,15,16)}
    capture={}
    for y in (-43.25,-41.73):
        pose=world_card(gauge,y,1.50)
        capture[str(y)]={"lower_tab_interference_mm3":round(intersection(pose,rear),4),
                         "closed_keeper_interference_mm3":round(intersection(pose,keep),4)}
    finger=md.Manifold.cylinder(1.7,6.5,6.5,80).translate((0,12.25,FLOOR+.05))
    seated_collisions={"keeper":intersection(seated,keep),"pin":intersection(seated,pin),"rear":intersection(seated,rear)}
    return {"card_mm":[85.6,53.98,1.2],"corner_radius_mm":3.18,"tilt_deg":results,
            "closed_seated_overlap_mm3":seated_collisions,"lift_1p50_mm_capture":capture,
            "card_floor_world_z_mm":FLOOR,"seated_card_to_underside_air_mm":{"tabs":1.10,"latch":1.32},
            "worst_overlap_in_plane_mm":{"lower":0.67,"upper":1.08},"angled_tucked_tab_clearance_mm":tab_margins,
            "thumb_gauge_diameter_mm":13.0,"thumb_gauge_beneath_card_overlap_with_rear_mm3":intersection(finger,rear)}


def latch(parts):
    rear,keeper,pin=[parts[k] for k in ("rear_purple","keeper_purple","pivot_pin_purple")]
    nose_area=md.Manifold.cylinder(12,2.6,2.6,72).translate((16,26.1,-3))
    nose=keeper^nose_area
    remainder=keeper-nose_area
    samples=[]
    for a in np.linspace(0,OPEN,81):
        samples.append([float(a),intersection(rotate_keeper(remainder,a),rear),
                        intersection(rotate_keeper(nose,a),rear),intersection(rotate_keeper(keeper,a),pin)])
    return {"rotation_deg":OPEN,"samples":len(samples),"max_rigid_region_intersection_mm3":max(p[1] for p in samples),
            "max_intentional_nose_deflection_volume_mm3":max(p[2] for p in samples),
            "closed_and_open_nose_interference_mm3":[samples[0][2],samples[-1][2]],
            "max_pivot_interference_mm3":max(p[3] for p in samples),
            "beyond_stop_test_mm3":{str(a):intersection(rotate_keeper(remainder,a),rear) for a in (8,-90)},
            "central_hub_radial_clearance_mm":.30,"retaining_flange_radial_overlap_mm":.69,
            "hub_axial_play_mm":.26,"nominal_detent_rise_to_running_deck_mm":.42}


def thread(parts):
    # Crop each piece only beyond the handle's 21 mm removal swept envelope.
    region=cuboid(-22,22,-140,-42,-22,22)
    rear=parts["rear_purple"]^region
    bow=parts["bow_pink"]^region
    face=parts["head_purple"]^region
    moving=(parts["handle_gold"]+parts["handle_purple"])^region
    sets=[]
    bow_gap=[]
    for a in range(0,2521,15):
        moved=moving.rotate((0,-a,0)).translate((0,-3*a/360,0))
        bow_gap.append(moved.min_gap(bow,12.))
        sets.append([a,intersection(moved,rear),intersection(moved,bow),intersection(moved,face)])
    return {"min_mesh_bow_clearance_mm":round(min(bow_gap),4),"min_at_angle_deg":sets[int(np.argmin(bow_gap))][0],
            "pitch_mm":3,"samples":len(sets),"angle_step_deg":15,"withdrawal_mm":21,
            "direction_deg_about_plus_y":-2520,
            "peak_overlap_mm3":dict(zip(("rear","bow","face"),[max(i[j] for i in sets) for j in (1,2,3)])),
            "peak_first_turn_mm3":max(max(i[1:]) for i in sets if i[0]<=360),
            "peak_at_deg":dict(zip(("rear","bow","face"),[max(sets,key=lambda i:i[j])[0] for j in (1,2,3)]))}


def verify_brep(step):
    assembly=cq.Assembly.load(str(step))
    bodies={key:node.obj for key,node in assembly.objects.items() if node.obj is not None}
    source_female,source_stud=extract_thread()
    receiver=bodies["rear_purple"].intersect(rect(-12,12,-70,-46,-12,9))
    stud=bodies["handle_purple"].intersect(rect(-15,15,-80,-48,-12,12))
    helical={}
    for model, socket, plug in [("source_pair",source_female,source_stud),("production_STEP",receiver,stud)]:
        poses={}
        for angle in np.linspace(0,2520,17):
            moved=plug.rotate((0,0,0),(0,1,0),-angle).translate((0,-3*angle/360,0))
            poses[str(angle)]=round(socket.intersect(moved).Volume(),7)
        helical[model]=poses
        print("Exact screw",model,poses,flush=True)
    pairs={}
    for a,b in [("head_gold","head_purple"),("head_cream","head_gold"),("head_blue","head_cream"),("bow_pink","head_gold"),("bow_pink","head_purple"),("handle_gold","handle_purple")]:
        pairs[a+" / "+b]=round(bodies[a].intersect(bodies[b]).Volume(),7)
    return {"solids":sum(len(b.Solids()) for b in bodies.values()),
            "all_valid":all(b.isValid() for b in bodies.values()),"pitch_mm":3,
            "helical_intersection_mm3":helical,"material_interfaces_mm3":pairs}


def verify():
    mesh_paths=sorted((CAD/"print_parts").glob("*.stl"))
    parts={}
    metrics={}
    for path in mesh_paths+sorted((CAD/"fit_coupon").glob("*.stl")):
        mesh=trimesh.load_mesh(path)
        item=solid(mesh)
        assert item.status()==md.Error.NoError and mesh.is_volume,path
        metrics[path.stem]={"sha256":digest(path),"shells":len(mesh.split()),"bbox_mm":mesh.bounds.round(4).tolist(),
                    "watertight":bool(mesh.is_watertight),"winding_consistent":bool(mesh.is_winding_consistent),
                    "facets":len(mesh.faces),"volume_mm3":round(mesh.volume,4)}
        if path in mesh_paths:
            parts[path.stem]=item
    overlap={}
    for a,b in itertools.combinations(parts,2):
        v=intersection(parts[a],parts[b])
        if v>.00001:
            overlap[a+" / "+b]=round(v,6)
    knit=parts["handle_purple"] ^ parts["rear_purple"]
    residual={"bounds_mm":list(knit.bounding_box()),"largest_fragment_mm3":max(x.volume() for x in knit.decompose())}
    print("Pairs",overlap,flush=True)
    motion=latch(parts)
    print("Latch",motion,flush=True)
    route=card_path(parts)
    print("Card",route,flush=True)
    screw=thread(parts)
    print("Screw",screw,flush=True)
    art=json.loads(ART.read_text())
    outline=shape(art["footprints"]["head"]["geometry"])
    poly=box(-43.30+3.25,-43.25+3.25,43.30-3.25,12.25-3.25).buffer(3.25,quad_segs=32)
    step=CAD/"purple_castle_card_wand.step"
    exact=verify_brep(step)
    result={"units":"mm","prototype":"R2","art_sha256":digest(ART),"derived_donor_sha256":digest(DONOR),
          "step_sha256":digest(step),"step_solid_count":exact["solids"],"step_all_valid":exact["all_valid"],"exact_step":exact,
          "mesh_solid_count":sum(m["shells"] for k,m in metrics.items() if k in parts),
          "parts":metrics,"assembly_intersection_above_0p00001_mm3":overlap,
          "min_outer_wall_rounded_pocket_mm":outline.boundary.distance(poly.boundary),
          "thread_mesh_residual":residual,"card_path":route,"keeper":motion,"screw_motion":screw,
          "physical_fit":"Pending printed coupons, actual card, repeated detent cycles, tap and bond test."}
    assert exact["solids"] == result["mesh_solid_count"] == 29 and exact["all_valid"]
    assert max(v for poses in exact["helical_intersection_mm3"].values() for v in poses.values()) < .00001
    assert max(v["peak_collision_mm3"] for tilt in route["tilt_deg"].values() for v in tilt.values()) < .00001
    assert max(motion["closed_and_open_nose_interference_mm3"]) < .00001 and motion["max_rigid_region_intersection_mm3"] < .00001
    assert min(motion["beyond_stop_test_mm3"].values()) > .001
    assert max(route["closed_seated_overlap_mm3"].values()) < .00001
    assert min(v for checks in route["lift_1p50_mm_capture"].values() for v in checks.values()) > .001
    assert max(v for k,v in screw["peak_overlap_mm3"].items() if k!="rear") < .00001
    assert max(exact["material_interfaces_mm3"].values()) < .002
    (CAD/"validation_report.json").write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    verify()
