"""Reopen the released R5 meshes and STEP, and measure the requested changes."""
import itertools
import json

import cadquery as cq
import numpy as np
from shapely import contains_xy
import trimesh
from shapely.geometry import Point,box,shape
from shapely.ops import unary_union

from build_r5 import ART,MAP,STEP,R2,R3,R5,CHANGED,base,inputs,visible_regions
from validate_r3 import mesh_projection
from validate_wand import cuboid,intersection,solid,thread


def measure_relief(packet,specs,bodies):
    measured={}
    for part,datum in (("head",base.FACE),("bow",base.BOW_BASE+1.8)):
        for f,visible in visible_regions(packet,part):
            name=f["id"]
            if name not in specs and name!="mickey":
                continue
            # Exclude rays grazing the 0.001 mm input quantization or a
            # triangulated vertical side. Entire outlines are checked separately.
            interior=visible.buffer(-.02)
            x0,y0,x1,y1=interior.bounds
            xx,yy=np.meshgrid(np.arange(x0+.073,x1,.25),np.arange(y0+.091,y1,.25))
            included=contains_xy(interior,xx,yy)
            surface=bodies["head_"+f["color"] if part=="head" else "bow_pink"]
            heights=[]
            for x,y in zip(xx[included],yy[included]):
                hits=surface.ray_cast((x,y,25),(x,y,datum-.05))
                if not hits:
                    raise ValueError(f"Missing relief at {x}, {y} on {name}")
                heights.append(hits[0].position[2]-datum)
            low,high=min(heights),max(heights)
            spec=specs.get(name,{"edge":f["relief_mm"],"crest":f["relief_mm"]})
            assert abs(high-spec["crest"])<.15 and low>spec["edge"]-.30,(name,low,high)
            if spec["crest"]>spec["edge"]:
                assert high-low>.70*(spec["crest"]-spec["edge"]),(name,low,high)
            measured[name]={"datum_world_z_mm":datum,"samples":len(heights),
                    "mesh_top_local_height_range_mm":[round(low,4),round(high,4)],
                    "measured_rise_mm":round(high-low,4)}
    return measured


def stats():
    packet,specs=inputs()
    bodies={}
    files={}
    for path in sorted((R5/"print_parts").glob("*.stl")):
        mesh=trimesh.load_mesh(path)
        pieces=mesh.split(only_watertight=False)
        assert mesh.is_volume and all(piece.is_volume for piece in pieces),path
        bodies[path.stem]=solid(mesh)
        files[path.stem]={"sha256":base.digest(path),"identical_R3":base.digest(path)==base.digest(R3/"print_parts"/path.name),
          "connected_solids":len(pieces),"watertight":bool(mesh.is_watertight),
          "consistent_winding":bool(mesh.is_winding_consistent),"all_positive_volume":all(piece.volume>0 for piece in pieces),
          "bbox_mm":mesh.bounds.round(4).tolist(),"triangles":len(mesh.faces)}
    assert {name for name,f in files.items() if not f["identical_R3"]}==CHANGED
    assert len(bodies)==12
    overlaps={}
    for a,b in itertools.combinations(bodies,2):
        v=intersection(bodies[a],bodies[b])
        if v>.00001:
            overlaps[a+" / "+b]=round(v,6)
        if {a,b}!={"handle_purple","rear_purple"}:
            assert v<.002,(a,b,v)

    layers={f["id"]:g for f,g in visible_regions(packet,"head")}
    source={f["id"]:shape(f["geometry"]) for f in packet["features"]}
    old_packet=json.loads((R2.parent/"art/R3/castle_profiles.json").read_text())
    old_petals=unary_union([shape(f["geometry"]) for f in old_packet["features"] if f["id"].startswith("rose-")])
    assert all(not f["id"].startswith("rose-") for f in packet["features"])
    projections={name:mesh_projection(bodies[name]) for name in ("head_cream","head_gold","head_blue","bow_pink")}
    old_rose_in_cream=old_petals.intersection(projections["head_cream"]).area
    assert old_rose_in_cream<.02,old_rose_in_cream
    mickey=source["mickey"]
    surroundings=mickey.buffer(.20)
    mickey_error=mickey.symmetric_difference(surroundings.intersection(projections["head_cream"])).area
    assert mickey_error<.015,mickey_error
    errors={}
    for color in ("cream","gold","blue"):
        spec=unary_union([regions for f,regions in visible_regions(packet,"head") if f["color"]==color])
        errors["head_"+color]=spec.symmetric_difference(projections["head_"+color]).area
    expected_bow=shape(packet["footprints"]["bow"]["geometry"])
    errors["bow_pink"]=expected_bow.symmetric_difference(projections["bow_pink"]).area
    assert max(errors.values())<.2,errors

    # Select the actual disjoint ribbons independently of the rim and flags.
    scrolls=[]
    for name in ("left-scroll","right-scroll"):
        contour=source[name]
        scrolls.append(projections["head_gold"].intersection(contour.buffer(.05)))
    scrolls_combined=unary_union(scrolls)
    span=scrolls_combined.bounds[2]-scrolls_combined.bounds[0]
    separation=scrolls[0].distance(scrolls[1])
    bow_clearance=scrolls_combined.distance(projections["bow_pink"])
    assert 75.1<span<75.4 and 1.55<separation<1.8 and 1.15<bow_clearance<1.4
    gold_mesh=trimesh.load_mesh(R5/"print_parts/head_gold.stl")
    rim=solid(max(gold_mesh.split(),key=lambda m:m.extents[0]))
    rim_overlap=mesh_projection(rim).intersection(projections["bow_pink"]).area
    rim_gap=bodies["bow_pink"].min_gap(rim,5.)
    gold_gap=bodies["bow_pink"].min_gap(bodies["head_gold"],5.)
    assert rim_overlap>0 and 1.58<rim_gap<1.62 and gold_gap>1.20
    # Restrict fit comparison to the sleeves and their full bonding pads.
    previous=solid(trimesh.load_mesh(R3/"print_parts/bow_pink.stl"))
    sockets={}
    for x,y in base.BOW_MOUNTS:
        pad=cuboid(x-3.65,x+3.65,y-3.65,y+3.65,13.19,14.99)
        a=previous^pad
        b=bodies["bow_pink"]^pad
        difference=(a-b).volume()+(b-a).volume()
        assert abs(difference)<.00001,difference
        sockets[str(x)]=round(abs(difference),8)
    peaks=measure_relief(packet,specs,bodies)
    assert 2.398<peaks["left-fold-floor"]["mesh_top_local_height_range_mm"][0]<2.402
    print("Rose, Mickey, curls width/gap/bow, bow socket",old_rose_in_cream,mickey_error,span,separation,bow_clearance,sockets,flush=True)
    movement=thread(bodies)
    assert movement["peak_overlap_mm3"]["bow"]<.00001 and movement["peak_overlap_mm3"]["face"]<.00001
    step=R5/"purple_castle_card_wand_R5.step"
    assembly=cq.Assembly.load(str(step))
    breps={k:n.obj for k,n in assembly.objects.items() if n.obj is not None}
    assert set(breps)==set(bodies)
    assert all(s.isValid() for s in breps.values())
    assert all(len(breps[k].Solids())==item["connected_solids"] for k,item in files.items())
    curves={k:sum(f.geomType()=="BSPLINE" for f in breps[k].Faces()) for k in ("head_blue","head_cream","head_gold","bow_pink")}
    assert all(curves.values())
    report={"units":"mm","art_sha256":base.digest(ART),"relief_map_sha256":base.digest(MAP),
        "parent_step_sha256":base.digest(STEP),"step_sha256":base.digest(step),
        "STEP_valid_solid_count":sum(len(s.Solids()) for s in breps.values()),"STEP_parts":len(breps),
        "STEP_bspline_faces":curves,"meshes":files,"surface_measurements":peaks,
        "art_mesh_symmetric_difference_mm2":errors,"former_rose_remaining_cream_area_mm2":round(old_rose_in_cream,8),
        "mickey_symmetric_difference_mm2":round(mickey_error,6),
        "actual_curl_pair_width_mm":round(span,4),"actual_curl_tip_separation_mm":round(separation,4),
        "actual_curl_to_bow_min_XY_gap_mm":round(bow_clearance,4),
        "rim_bow_XY_overlap_mm2":round(rim_overlap,4),"bow_underside_to_gold_rim_gap_mm":round(rim_gap,4),
        "bow_to_all_gold_min_3d_gap_mm":round(gold_gap,4),"bow_mount_material_difference_mm3":sockets,"assembly_overlaps_over_0p00001_mm3":overlaps,
        "grip_sweep":movement,"physical_status":"Physical print, actual fit, finish, bond and reader performance pending."}
    (R5/"validation_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Passed",report["STEP_valid_solid_count"],movement["min_mesh_bow_clearance_mm"],flush=True)

if __name__=="__main__":
    stats()
