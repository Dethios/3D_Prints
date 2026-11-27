"""Compare every nominal 0.12 mm layer of R6 with and without the cradle."""
import json
from pathlib import Path

import cadquery as cq
import numpy as np
import shapely
import trimesh
from shapely.geometry import Polygon,box

from build_fixture import HERE,R6,FILE,GAP,base,sources,TAB_Z
from validate_wand import solid,cuboid
from validate_r3 import mesh_projection


def contour(section):
    region=Polygon()
    for ring in section.to_polygons():
        region=region.symmetric_difference(Polygon(ring))
    return region


def pieces(g,limit=.015):
    if g.geom_type=="Polygon":
        if g.area>limit:
            yield g
    elif hasattr(g,"geoms"):
        for child in g.geoms:
            yield from pieces(child,limit)


def dist_sample(piece,supported):
    # Directed distance of the actual projected unsupported material to a
    # previous layer or gapped support, sampled along its boundary.
    xy=shapely.get_coordinates(shapely.segmentize(piece,.60))
    values=shapely.distance(shapely.points(xy[:,0],xy[:,1]),supported)
    idx=int(np.argmax(values))
    return float(values[idx]),xy[idx].round(3).tolist()


def check():
    part=sources()
    model=part["purple"]+part["gold"]+part["cream"]+part["blue"]
    fixture=solid(trimesh.load_mesh(HERE/(FILE+".stl")))
    prior=Polygon()
    fs=[Polygon(),Polygon(),Polygon()]
    audit={"baseline":[],"cradle":[]}
    births=[]
    geom_islands=[]
    max_contact=0
    layer_count=0
    sum_area={"baseline":0.0,"cradle":0.0}
    first=None
    totals={"baseline":0,"cradle":0}
    for i in range(1170):
        z=.10 if i==0 else .14+i*.12
        region=contour(model.slice(z))
        if region.is_empty:
            continue
        layer_count+=1
        fixture_slice=contour(fixture.slice(z))
        if i==0:
            first={"head_area_mm2":round(region.area,3),"cradle_area_mm2":round(fixture_slice.area,3),
                   "cradle_bounds_xy_mm":list(fixture_slice.bounds)}
        else:
            # 0.30 mm lateral reach = half the nominal nozzle diameter. Count
            # the two lower fixture scans as well, to allow the designed gap.
            footprint=prior.buffer(.30,quad_segs=3)
            gapped=fs[0].union(fs[1]).union(fs[2])
            for c in pieces(region):
                if c.distance(prior)>.30:
                    nearest=c.distance(gapped)
                    births.append({"layer":i+1,"z_mm":round(z,3),"area_mm2":round(c.area,4),
                        "bounds_mm":np.round(c.bounds,3).tolist(),"previous_head_distance_mm":round(c.distance(prior),3),
                        "fixture_distance_XY_in_lower_3_scans_mm":round(nearest,3) if not gapped.is_empty else None})
            for piece in pieces(fixture_slice):
                if piece.area>.1 and piece.distance(fs[0].union(prior))>.35:
                    geom_islands.append([i+1,round(z,3),round(piece.area,3),np.round(piece.bounds,3).tolist()])
            for label,anchor in (("baseline",prior),("cradle",prior.union(gapped))):
                unsupported=region.difference(footprint if label=="baseline" else footprint.union(gapped.buffer(.30,quad_segs=3)))
                for p in pieces(unsupported,.07):
                    sum_area[label]+=p.area
                    d,where=dist_sample(p,anchor)
                    if d<.75:
                        continue
                    totals[label]+=1
                    audit[label].append({"layer":i+1,"z_mm":round(z,3),"max_reach_mm":round(d,3),
                        "xy_at_max":where,"area_mm2":round(p.area,3),"bounds_mm":np.round(p.bounds,3).tolist()})
        prior=region
        fs=[fixture_slice,fs[0],fs[1]]
    for key,rows in audit.items():
        # Retain the largest observed excursion per 5 mm of height and X
        # sign, plus the top twelve ranked areas and excursions.
        buckets={}
        for row in rows:
            x,y=row["xy_at_max"]
            token=(int(row["z_mm"]//5),int(x//10))
            if token not in buckets or row["max_reach_mm"]>buckets[token]["max_reach_mm"]:
                buckets[token]=row
        audit[key]={"worst_by_reach":sorted(rows,key=lambda a:a["max_reach_mm"],reverse=True)[:16],
                    "worst_by_area":sorted(rows,key=lambda a:a["area_mm2"],reverse=True)[:8],
                    "severity_above_0p75_by_zone":sorted(buckets.values(),key=lambda r:r["z_mm"]),
                    "nominal_overhang_area_sum_mm2":round(sum_area[key],3),"zones_over_0p75_count":totals[key]}
    model_contact={color:{"overlap_mm3":round((fixture^body).volume(),8),
        "min_mesh_gap_mm_capped_at_10":round(fixture.min_gap(body,10),5)} for color,body in part.items()}
    assert max(x["overlap_mm3"] for x in model_contact.values())<1.e-6
    # Actual skin of the planar card-contact side, including its mating band;
    # and the raised surface and locators that seat against the permanent bow.
    card=part["purple"]^cuboid(-66,66,-.92,-.895,-.1,142)
    bow_joints=part["purple"]^cuboid(-30,30,-8.,-6.885,19.,51.)
    bore=__import__("manifold3d").Manifold.cylinder(21.,6.25,6.25,128)
    protected={"card_contact_and_bond_plane_mm":round(fixture.min_gap(card,10),4),
        "bow_seating_land_and_ribs_mm":round(fixture.min_gap(bow_joints,10),4),
        "thread_keepout_R6p25_z0_to21_mm":round(fixture.min_gap(bore,10),4)}
    assert min(protected.values())>.24,protected
    # After cutting six nibs on the bench, move only the cradle toward
    # the decorated face while lowering it 1 mm per 4 mm of forward travel.
    trimmed=fixture
    sites=json.loads((HERE/"fixture_layout.json").read_text())["intended_contacts"]
    for site in sites:
        if site["kind"].startswith("cuttable"):
            x,z=site["x"],site["z"]
            a,b=sorted([x-.35*np.sign(x),x+np.sign(x)])
            trimmed=trimmed-cuboid(a,b,-2.52,-1.58,z-.90,z+.60)
    sweep=[abs((model^trimmed.translate((0,-d,-d/4))).volume()) for d in np.linspace(0,28,281)]
    assert max(sweep)<1.e-6,max(sweep)
    step=cq.importers.importStep(str(HERE/(FILE+".step"))).solids().vals()
    assert len(step)==1 and step[0].isValid()
    fixture_mesh=trimesh.load_mesh(HERE/(FILE+".stl"))
    assert fixture_mesh.is_volume and len(fixture_mesh.split())==1
    report={"units":"mm","fixture_sha256":base.digest(HERE/(FILE+".stl")),"step_sha256":base.digest(HERE/(FILE+".step")),
            "mesh":{"watertight":fixture_mesh.is_watertight,"positive_volume":fixture_mesh.is_volume,
                "consistent_winding":fixture_mesh.is_winding_consistent,"volume_mm3":round(fixture_mesh.volume,3)},
            "reloaded_STEP_valid_solids":1,"model_layers_sampled":layer_count,"first_layer":first,
            "layer_centers":"0.10 then 0.26 + n×0.12 mm","model_fixture":model_contact,
            "measured_protected_clearance_mm":protected,"unsupported_model_component_births":births,
            "new_unanchored_fixture_islands_over_0p1_mm2":geom_islands,
            "post_trim_removal":{"sites":6,"sampled_poses":281,"cradle_translation_print_XYZ_mm":[0,-28,-7],
             "peak_overlap_mm3":round(max(sweep),8),"trimmed_fixture_solids":len(trimmed.decompose())},"overhang_comparison":audit,
            "assumptions":"Geometric sections only. Adjacent part layers allow 0.30 mm lateral reach. Support is sampled up to three layers below to include the breakaway gap. Compound bridges and relief cantilevers still need toolpath review."}
    (HERE/"validation_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print('Layers, starts, cradle islands',layer_count,births,geom_islands,flush=True)
    for key,v in audit.items():
        print(key,"worst",v["worst_by_reach"][:8],flush=True)
    print("first, protected",first,protected,flush=True)

if __name__=="__main__":
    check()
