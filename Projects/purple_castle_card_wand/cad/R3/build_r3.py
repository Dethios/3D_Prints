"""Build smooth, vertical-walled relief from the frozen R3 XY regions."""
import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.Geom import Geom_BSplineSurface
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
from OCP.gp import gp_Pnt, gp_Vec
from shapely import contains_xy, distance, points
from shapely.geometry import Point, Polygon, shape

R3 = Path(__file__).resolve().parent
R2 = R3.parent
sys.path.insert(0,str(R2))
import build_wand as base

ART = R2.parent / "art/R3/castle_profiles.json"
MAP = ART.with_name("relief_map.json")
STEP = R2 / "purple_castle_card_wand.step"
HASHES = {ART: "88a6f184d527f653d4a63e7e9ba1386a475350a14dbce7817cd2d8bbab21469b",
          MAP: "7accccd1a3cf7daf40577cce16578f958b45425a6085578119ab02c394c61b40",
          STEP:"ddce0078634cd15a40940c72492b475f91860ae6c70a9a0788230b0b5ae34360"}


def inputs():
    for path,expected in HASHES.items():
        if base.digest(path)!=expected:
            raise ValueError(f"Unexpected revision of {path.name}")
    packet=json.loads(ART.read_text())
    return packet,{label:spec for spec in json.loads(MAP.read_text())["profiles"] for label in spec["ids"]}


def visible_regions(packet,part):
    rows = [(ix,f) for ix,f in enumerate(packet["features"]) if f["part"]==part]
    covered=Polygon()
    for _,f in sorted(rows,key=lambda row:(row[1]["relief_mm"],row[0]),reverse=True):
        g=base.clean2(shape(f["geometry"]))
        region=g.difference(covered)
        covered=base.clean2(covered.union(g))
        if not f["relief_mm"] or region.is_empty:
            continue
        if part=="head":
            for x,y in base.BOW_MOUNTS:
                region=region.difference(Point(x,y).buffer(3.65,quad_segs=24))
        yield f,region


def spline_axis(low,high,spacing):
    # Use Greville abscissae for control X and Y, so spline UV equals XY.
    knots=np.linspace(low-2*spacing,high+2*spacing,max(6,math.ceil((high-low)/spacing)+5))
    mults=np.ones(len(knots),dtype=int)
    mults[[0,-1]]=4
    expanded=np.repeat(knots,mults)
    controls=np.convolve(expanded[1:-1],np.ones(3)/3,mode="valid")
    values=TColStd_Array1OfReal(1,len(knots))
    multiplicities=TColStd_Array1OfInteger(1,len(knots))
    for i,(k,m) in enumerate(zip(knots,mults),1):
        values.SetValue(i,k)
        multiplicities.SetValue(i,int(m))
    return controls,values,multiplicities


def curved_region(p,datum,spec):
    """Clip an analytic bicubic height surface to the approved artwork outline."""
    edge,crest,run=spec["edge"],spec["crest"],spec["rise_run"]
    if edge==crest:
        return base.prism(p,datum,datum+edge)
    xmin,ymin,xmax,ymax=p.bounds
    pitch=.88 if run>=2.5 else .64
    x,ux,um=spline_axis(xmin,xmax,pitch)
    y,vy,vm=spline_axis(ymin,ymax,pitch)
    xx,yy=np.meshgrid(x,y,indexing="ij")
    signed=distance(points(xx,yy),p.boundary)*np.where(contains_xy(p,xx,yy),1,-1)
    # Widen the roll on large padded lobes and keep narrow scrolls convex
    # across their entire width. A short analytic continuation outside the
    # polygon gives the trimmed spline its rounded shoulder at the edge.
    reach=max(.5,min(max(run,.85*signed.max()),signed.max()*.92))
    t=np.clip(signed/reach,-.35,1.)
    heights=datum+edge+(crest-edge)*np.sin(np.pi*t/2)
    poles=TColgp_Array2OfPnt(1,len(x),1,len(y))
    for i in range(len(x)):
        for j in range(len(y)):
            poles.SetValue(i+1,j+1,gp_Pnt(x[i],y[j],heights[i,j]))
    surf=Geom_BSplineSurface(poles,ux,vy,um,vm,3,3)
    face=BRepBuilderAPI_MakeFace(surf,1.e-6).Face()
    cap=cq.Shape.cast(BRepPrimAPI_MakePrism(face,gp_Vec(0,0,-18)).Shape())
    prism=base.prism(p,datum,datum+crest+1.0)
    body=prism.intersect(cap).clean()
    if not body.isValid() or len(body.Solids())!=1:
        raise RuntimeError("Invalid intersection in curved relief")
    return body

def sculpt(packet,profiles,part,datum):
    colors={}
    for f,region in visible_regions(packet,part):
        color,label=f["color"],f["id"]
        if color=="purple":
            continue
        components=[]
        for p in base.polygons(region):
            if label in profiles and profiles[label]["crest"]!=profiles[label]["edge"]:
                body=curved_region(p,datum,profiles[label])
            else:
                height=profiles[label]["edge"] if label in profiles else f["relief_mm"]
                body=base.prism(p,datum,datum+height)
            components.extend(body.Solids())
        if components:
            print(part,label,len(components),flush=True)
            colors.setdefault(color,[]).extend(components)
    return colors


def build(out):
    packet,profiles=inputs()
    source=cq.Assembly.load(str(STEP))
    bodies={key:node.obj for key,node in source.objects.items() if node.obj is not None}
    for color,parts in sculpt(packet,profiles,"head",base.FACE).items():
        bodies["head_"+color]=base.combine(parts)
    datum=base.BOW_BASE+1.8
    outline=base.clean2(shape(packet["footprints"]["bow"]["geometry"]))
    backing=base.prism(outline,base.BOW_BASE,datum)
    relief=sculpt(packet,profiles,"bow",datum)
    bow=base.combine([backing]+relief["pink"])
    for x,y in base.BOW_MOUNTS:
        bow=bow.cut(base.circle(x,y,1.65,base.BOW_BASE-.1,base.BOW_BASE+1.45))
    bodies["bow_pink"]=bow.clean()
    assembly=cq.Assembly(name="purple_castle_card_wand_R3")
    (out/"print_parts").mkdir(parents=True,exist_ok=True)
    for name,body in bodies.items():
        if not body.isValid():
            raise RuntimeError(f"Invalid assembled component {name}")
        path=out/"print_parts"/(name+".stl")
        if name in ("head_cream","head_gold","head_blue","bow_pink"):
            mesh=base.save_stl(body,path)
            print(name,len(body.Solids()),mesh.is_volume,mesh.bounds,flush=True)
            if not mesh.is_volume:
                raise RuntimeError(f"Invalid mesh {name}")
        else:
            shutil.copyfile(R2/"print_parts"/path.name,path)
        assembly.add(body,name=name,color=cq.Color(base.COLORS[name.split("_")[-1]]))
    assembly.save(str(out/"purple_castle_card_wand_R3.step"))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=R3)
    build(parser.parse_args().out)
