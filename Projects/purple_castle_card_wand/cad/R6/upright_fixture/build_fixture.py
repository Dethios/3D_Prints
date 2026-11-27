"""A sacrificial external PLA cradle for the original R6 front at +90 degrees X."""
import argparse
import json
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString,Polygon,box

HERE=Path(__file__).resolve().parent
R6=HERE.parent
sys.path.insert(0,str(R6))
from build_r6 import base,inputs,outlines
from validate_wand import solid

ELEV=78.35
GAP=.12
MATRIX=[[1,0,0,0],[0,0,-1,0],[0,1,0,ELEV],[0,0,0,1]]
FILE="upright_cradle_blue_A"
COLORS=("purple","gold","cream","blue")
LOW_TEETH=(8.9,12.8,16.9,21.0,25.1,29.3,33.4,36.9,40.0,43.1,46.1)
TAB_Z=(30.35,54.35,87.0)


def sources():
    report=json.loads((R6/"validation_report.json").read_text())["mesh_files"]
    bodies={}
    for color in COLORS:
        path=R6/"print_parts"/("head_"+color+".stl")
        if base.digest(path)!=report[path.stem]["sha256"]:
            raise ValueError(f"Unexpected R6 source {path}")
        m=trimesh.load_mesh(path)
        m.apply_transform(np.array(MATRIX,dtype=float))
        bodies[color]=solid(m)
    return bodies


def xz_poly(g,y0,y1):
    items=[]
    for p in base.polygons(g):
        def wire(coords):
            return cq.Wire.makePolygon([cq.Vector(x,y0,z) for x,z in list(coords)[:-1]],close=True)
        items.append(cq.Solid.extrudeLinear(wire(p.exterior.coords),[wire(r.coords) for r in p.interiors],(0,y1-y0,0)))
    if len(items)==1:
        return items[0]
    return cq.Compound.makeCompound(items)


def rectwire(x,y,z,wx,wy):
    return cq.Wire.makePolygon([cq.Vector(x+dx*wx/2,y+dy*wy/2,z) for dx,dy in
                               ((-1,-1),(1,-1),(1,1),(-1,1))],close=True)


def beam(stations):
    return cq.Solid.makeLoft([rectwire(*s) for s in stations],ruled=True)


def first_z(body,x,y,floor_z=-.1):
    hits=body.ray_cast((x,y,floor_z),(x,y,145))
    return hits[0].position[2] if hits else None


def underside(body,xs,y0,y1,floor_z=-.1):
    pts=[]
    for x in xs:
        heights=[first_z(body,x+dx,y,floor_z) for dx in (-.26,0,.26) for y in np.linspace(y0,y1,11)]
        heights=[v for v in heights if v is not None]
        if not heights:
            raise ValueError(f"No exterior underside at {x}, {y0}, {y1}")
        pts.append((float(x),min(heights)))
    return pts


def roof_profile(body,x0,x1,y0,y1,depth):
    line=underside(body,np.linspace(x0,x1,max(5,int((x1-x0)/.22)+2)),y0,y1)
    return Polygon([(x0,.65),(x1,.65)]+[(x,z-depth) for x,z in line[::-1]])


def build(out):
    packet,_=inputs()
    _,outer,_=outlines(packet)
    projected=affinity.translate(outer,yoff=ELEV)
    # R6 carrier only: the model contact tips are restricted to structural
    # surfaces, with all colored relief crowns and card faces outside reach.
    parts=sources()
    body=parts["purple"]
    gold=parts["gold"]
    items=[base.rect(-71.8,71.8,9.0,13.4,0,1.52),
           base.rect(-9,9,-13.2,-9.7,0,1.52)]
    contacts=[]
    for sign in (-1,1):
        def xshape(g):
            return g if sign==1 else affinity.scale(g,xfact=-1,yfact=1,origin=(0,0))
        def xblock(x0,x1,y0,y1,z0,z1):
            a,b=sorted([sign*x0,sign*x1])
            return base.rect(a,b,y0,y1,z0,z1)
        def bar(stations):
            return beam([(sign*x,y,z,wx,wy) for x,y,z,wx,wy in stations])
        # Feet join at the back, beyond the card-contact plane. The space
        # directly below the female half-thread is left completely open.
        items.extend([xblock(7.7,53.0,-13.2,-9.7,0,1.52),
                      xblock(49.8,54.2,-19.0,15.,0,1.80),
                      xblock(60.1,64.9,-15.,18.,0,1.80),
                      xblock(51,64,-15.0,-11.5,0,1.52)])
        for x in (10.4,23.3,36.0,45.0):
            items.append(xblock(x-1.5,x+1.5,-12.0,10.8,0,1.25))
        # A toothed low wall follows the measured underside of the carrier.
        y0,y1=-2.70,-1.38
        lowwall=roof_profile(body,8.01,47.18,y0,y1,GAP+1.50)
        for x,h in [(16.5,5.2),(26.3,6.2),(36.2,5.0)]:
            lowwall=lowwall.difference(Polygon([(x-3.4,2.8),(x+3.4,2.8),(x,2.8+h)]))
        items.append(xz_poly(xshape(lowwall),y0,y1))
        for x in LOW_TEETH:
            width=2.05 if x<35 else 1.86
            tooth=roof_profile(body,x-width/2,x+width/2,y0,y1,GAP)
            items.append(xz_poly(xshape(tooth),y0,y1))
            contacts.append({"kind":"lower-edge gap","x":round(sign*x,2),"y_range":[y0,y1],
                             "top_z":round(first_z(body,x,(y0+y1)/2)-GAP,4),"gap_mm":GAP})
        for x in (13.1,27.2,42.0):
            items.append(bar([(x,3.2,.8,1.75,10.70),(x,-.30,8.0,1.75,3.90),
                              (x,-1.53,10.0,1.75,1.70)]))
        # Two pads normally hidden beneath the pink bow cantilever forward
        # when printed upright. Catch only their downward exterior edges.
        for x in (16.6,22.5):
            py0,py1=-5.95,-4.99
            items.append(xblock(x-1.55,x+1.55,-12.2,-4.85,0,1.25))
            p=roof_profile(body,x-1.05,x+1.05,py0,py1,GAP)
            items.append(xz_poly(xshape(p),py0,py1))
            items.append(bar([(x,-8.2,.8,2.1,7.4),(x,-6.15,13.,2.1,2.85),
                              (x,-5.52,18.0,2.1,1.0)]))
            contacts.append({"kind":"bow-land lower edge gap","x":sign*x,"y_range":[py0,py1],
                             "top_z":round(first_z(body,x,(py0+py1)/2)-GAP,4),"gap_mm":GAP})
        # The lower gold rim starts alongside the purple tip. This shelf
        # reaches its downward edge, stopping 0.55 mm behind the gold face.
        rim=roof_profile(gold,38.05,40.9,-4.15,-2.92,.24)
        items.append(xz_poly(xshape(rim),-4.15,-2.92))
        items.append(xblock(38.1,40.9,-4.2,-2.20,0,2.20))
        contacts.append({"kind":"lower gold rim edge; gapped","x":sign*39.475,"y_range":[-4.15,-2.92],
                         "top_z":round(first_z(gold,39.475,-3.55)-.24,4),"gap_mm":.24})
        # Separate front-facing prongs approach the underside of each curled
        # ribbon from free space. No prong passes through a thread or a pad.
        for x,half_width,height in [(2.50,.85,42.15),(27.25,1.40,46.0)]:
            py0,py1=-5.52,-4.82
            grid=np.linspace(x-half_width,x+half_width,13)
            line=underside(gold,grid,py0,py1,height-1.0)
            curve=Polygon([(x-half_width,height-2.5),(x+half_width,height-2.5)]+
                          [(tx,tz-.24) for tx,tz in line[::-1]])
            items.append(xz_poly(xshape(curve),py0,py1))
            mid_x=x+2.4 if x>20 else x
            items.append(bar([(mid_x,-10.95,.7,half_width*2+.45,2.14),
                              (mid_x,-9.50,height-11.,half_width*2+.45,1.85),
                              (x,-5.25,height-2.1,half_width*2+.18,1.28),
                              (x,-5.17,height-1.4,half_width*2,.70)]))
            contacts.append({"kind":"gold curl underside; gapped","x":sign*x,"y_range":[py0,py1],
                             "top_z":round(first_z(gold,x,-4.9)-.24,4),"gap_mm":.24})
        # A triangulated side pier keeps the edge ties short. Its wide feet
        # resist out-of-plane movement without attachment to the back face.
        items.append(bar([(52,-2.05,.75,3.5,5.0),(52,-2.05,35.,3.4,4.4),
                          (69.2,-2.05,88.,3.2,4.1)]))
        items.append(bar([(52,-15.5,.75,3.3,4.5),(52,-2.05,35.,3.0,3.8)]))
        items.append(bar([(62.5,14.5,.75,3.2,4.5),(69.2,-2.05,88.,3.0,3.8)]))
        for z in TAB_Z:
            edge=projected.intersection(LineString([(0,z),(80,z)])).bounds[2]
            pier=lambda h:52.0 if h<=35 else 52+(h-35)*17.2/53
            # Ramp toward the silhouette at a printable angle, then narrow to
            # a single 0.80 mm wide nib at the structural perimeter.
            start_z=z-max(5.0,1.14*(pier(z)-edge)+2.0)
            start_x=pier(start_z)
            branch=Polygon([(start_x+1.1,start_z-.7),(start_x-1.2,start_z-1.8),
                            (edge+1.5,z-.15),(edge+1.6,z+.32),
                            (start_x+1.25,start_z+4.1)])
            branch=branch.difference(projected.buffer(.65))
            items.append(xz_poly(xshape(branch),-3.00,-1.25))
            nib=Polygon([(edge-1,z-.33),(edge+.42,z-.43),(edge+2.8,z-2.52),
                         (edge+3.3,z+.31),(edge-1,z+.31)]).difference(projected)
            items.append(xz_poly(xshape(nib),-2.45,-1.65))
            contacts.append({"kind":"cuttable structural edge tie","x":round(sign*edge,4),
                             "y_range":[-2.45,-1.65],"z":z,"nominal_z_height":.64})
    print("Fusing external cradle",len(items),"components",flush=True)
    cradle=base.combine(items)
    print("CAD",len(cradle.Solids()),cradle.isValid(),flush=True)
    assert cradle.isValid() and len(cradle.Solids())==1
    out.mkdir(parents=True,exist_ok=True)
    mesh=base.save_stl(cradle,out/(FILE+".stl"))
    assert mesh.is_volume and len(mesh.split(only_watertight=False))==1
    cq.exporters.export(cradle,str(out/(FILE+".step")))
    layout={"units":"mm","fixture":FILE+".stl","fixture_extruder":"physical blue A",
        "fixture_sha256":base.digest(out/(FILE+".stl")),"head_transform_row_major":MATRIX,
        "fixture_transform_row_major":np.eye(4,dtype=int).tolist(),
        "unchanged_R6_parts":{"../print_parts/head_"+c+".stl":base.digest(R6/"print_parts"/("head_"+c+".stl")) for c in COLORS},
        "fixture_bounds_mm":mesh.bounds.round(4).tolist(),"part_bounds_mm":[[-65,-7.60,0],[65,-.90,140.288]],
        "connected_fixture_solids":1,"nominal_lower_support_gap_mm":GAP,"intended_contacts":contacts,
        "lower_contact_strategy":"Purple edge and hidden bow-pad undersides have 0.12 mm nominal air gap. Six exterior rim/curl undersides have a 0.24 mm nominal air gap. Six zero-gap, cuttable purple perimeter ties brace the print.",
        "bed_placement":"Add the four transformed head parts and the already-upright blue fixture as one multipart group. Translate the group together; use the fixture bounds for group XY centering."}
    (out/"fixture_layout.json").write_text(json.dumps(layout,indent=2)+"\n")
    print("Released",layout["fixture_sha256"],layout["fixture_bounds_mm"],flush=True)


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--out",type=Path,default=HERE)
    build(cli.parse_args().out)
