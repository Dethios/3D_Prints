"""Verify R3 mesh relief elevations, silhouettes, interfaces and STEP transfer."""
import itertools
import json

import cadquery as cq
import numpy as np
import trimesh
from shapely import contains_xy
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

from build_r3 import R2,R3,ART,MAP,STEP,base,inputs,visible_regions
from validate_wand import solid,intersection,thread


def mesh_projection(body):
    rings=body.project().to_polygons()
    region=Polygon()
    for contour in rings:
        region=region.symmetric_difference(Polygon(contour))
    return region


def profile_measurements(packet,profiles,bodies):
    result={}
    for part,datum in [("head",base.FACE),("bow",base.BOW_BASE+1.8)]:
        for f,region in visible_regions(packet,part):
            label=f["id"]
            if label not in profiles and label not in ("mickey","rose-left-petal","rose-outer-petal","rose-spiral-petal"):
                continue
            body=bodies["head_"+f["color"] if part=="head" else "bow_pink"]
            xs,ys,xe,ye=region.bounds
            # Sample within each exact visible region, including slender features.
            xs=np.arange(xs+.073,xe,.25)
            ys=np.arange(ys+.091,ye,.25)
            gx,gy=np.meshgrid(xs,ys)
            inside=contains_xy(region,gx,gy)
            values=[]
            points=[]
            for x,y in zip(gx[inside],gy[inside]):
                hits=body.ray_cast((x,y,25),(x,y,datum-.1))
                if hits:
                    values.append(hits[0].position[2]-datum)
                    points.append([x,y])
            values=np.asarray(values)
            if len(values)==0:
                raise RuntimeError("Feature missing from print mesh: "+label)
            minimum=int(values.argmin())
            maximum=int(values.argmax())
            spec=profiles.get(label,{"edge":f["relief_mm"],"crest":f["relief_mm"]})
            gain=values[maximum]-values[minimum]
            if spec["crest"]-spec["edge"]>.1:
                assert gain>(spec["crest"]-spec["edge"])*.72,(label,gain)
            assert abs(values[maximum]-spec["crest"])<.15,(label,values[maximum])
            result[label]={"local_datum_world_z_mm":datum,"samples":len(values),
                           "target_edge_crest_mm":[spec["edge"],spec["crest"]],
                           "mesh_top_local_height_range_mm":[round(values[minimum],4),round(values[maximum],4)],
                           "sampled_rise_mm":round(gain,4),
                           "min_location_xy_mm":np.round(points[minimum],4).tolist(),
                           "max_location_xy_mm":np.round(points[maximum],4).tolist()}
    return result


def main():
    packet,profiles=inputs()
    bodies={}
    metrics={}
    for path in sorted((R3/"print_parts").glob("*.stl")):
        mesh=trimesh.load_mesh(path)
        assert mesh.is_volume and all(p.is_volume for p in mesh.split(only_watertight=False)),path
        bodies[path.stem]=solid(mesh)
        metrics[path.stem]={"sha256":base.digest(path),"byte_identical_R2":base.digest(path)==base.digest(R2/"print_parts"/path.name),
                "solids":len(mesh.split()),"mesh_is_volume":bool(mesh.is_volume),
                "consistent_winding":bool(mesh.is_winding_consistent),"watertight":bool(mesh.is_watertight),
                "bbox_mm":mesh.bounds.round(4).tolist(),"triangles":len(mesh.faces)}
    assert {k for k,v in metrics.items() if not v["byte_identical_R2"]}=={"head_gold","head_cream","head_blue","bow_pink"}
    pairs={}
    for a,b in itertools.combinations(bodies,2):
        overlap=intersection(bodies[a],bodies[b])
        if overlap>.00001:
            pairs[a+" / "+b]=round(overlap,6)
        if "handle_purple" not in (a,b) or "rear_purple" not in (a,b):
            assert overlap<.002,(a,b,overlap)
    measurement=profile_measurements(packet,profiles,bodies)
    print("Surface rises",[(k,v["sampled_rise_mm"]) for k,v in measurement.items()],flush=True)
    # Compare the actual XY footprint of each printed color to the fully
    # partitioned, height-priority art input. This includes all window holes.
    error={}
    for part in ("head","bow"):
        by_color={}
        for f,g in visible_regions(packet,part):
            by_color.setdefault(f["color"],[]).append(g)
        for color,regions in by_color.items():
            if color=="purple":
                continue
            target=unary_union(regions)
            if part=="bow":
                target=shape(packet["footprints"]["bow"]["geometry"])
            name="head_"+color if part=="head" else "bow_pink"
            projected=mesh_projection(bodies[name])
            area=target.symmetric_difference(projected).area
            error[name]=round(area,5)
            assert area<.5,(name,area)
    # Spatial coupons: test two bow sockets against R2 geometry through the whole
    # backing, cut by a common slab that excludes the newly shaped decoration.
    from validate_wand import cuboid
    underside=cuboid(-36,36,-100,-40,12.99,14.99)
    before=solid(trimesh.load_mesh(R2/"print_parts/bow_pink.stl"))^underside
    after=bodies["bow_pink"]^underside
    changed=(before-after).volume()+(after-before).volume()
    assert abs(changed)<.0002,changed
    # Mechanical meshes are byte-identical and the R3 front still clears
    # throughout all recorded handle poses. Reuse the original sweep routine.
    screw=thread(bodies)
    assert max(screw["peak_overlap_mm3"][k] for k in ("face","bow"))<.00001
    step=R3/"purple_castle_card_wand_R3.step"
    assembly=cq.Assembly.load(str(step))
    step_parts={k:n.obj for k,n in assembly.objects.items() if n.obj is not None}
    solids=sum(len(b.Solids()) for b in step_parts.values())
    assert len(step_parts)==12 and solids==sum(m["solids"] for m in metrics.values())
    assert all(b.isValid() for b in step_parts.values())
    bsplines={k:sum(f.geomType()=="BSPLINE" for f in step_parts[k].Faces()) for k in ("head_blue","head_gold","head_cream","bow_pink")}
    assert all(bsplines.values()),bsplines
    raw=json.loads((R2/"validation_report.json").read_text())
    result={"units":"mm","profiles_sha256":base.digest(ART),"map_sha256":base.digest(MAP),
            "parent_step_sha256":base.digest(STEP),"step_sha256":base.digest(step),
            "step_named_parts":len(step_parts),"step_valid_solids":solids,"step_bspline_faces_by_group":bsplines,
            "stls":metrics,"surface_measurements":measurement,"projected_symmetric_difference_mm2":error,
            "bow_backing_and_socket_symmetric_difference_mm3":round(abs(changed),8),
            "pair_intersections_over_0p00001_mm3":pairs,"grip_sweep":screw,
            "R2_fixed_card_geometry_unchanged_R2_pose_count":sum(v["samples"] for a in raw["card_path"]["tilt_deg"].values() for v in a.values()),
            "physical_validation":"Pending printed fit, relief finish, bond, durability and reader test."}
    (R3/"validation_report.json").write_text(json.dumps(result,indent=2)+"\n")
    print("STEP, projected errors, backing and sweep",solids,error,changed,screw["min_mesh_bow_clearance_mm"])

if __name__=="__main__":
    main()
