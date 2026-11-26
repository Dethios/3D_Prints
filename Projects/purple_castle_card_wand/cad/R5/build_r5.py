"""Build the reference-fitted R5 castle card wand from the frozen R3 assembly."""
import argparse
import json
import shutil
import sys
from pathlib import Path

import cadquery as cq
from shapely.geometry import shape

R5 = Path(__file__).resolve().parent
R2 = R5.parent
R3 = R2/"R3"
sys.path.insert(0,str(R3))
from build_r3 import base,curved_region,visible_regions

ART = R2.parent/"art/R5/castle_profiles.json"
MAP = ART.with_name("relief_map.json")
STEP = R3/"purple_castle_card_wand_R3.step"
CHANGED = {"head_gold","head_cream","bow_pink"}
HASHES = {ART:"a6031a4b9d68d8ecbbac9994e19b6778341c953fbc49caba2d2faa16387127dd",
          MAP:"0a73df176ea6965100df1e30e2ab8e6ef9c29b43f17cfa8f05a5e893c9331611",
          STEP:"47154aecf3b182cc2261b42a7a764e737d8904dda519b5dac8431cb806119264"}


def inputs():
    for path,expected in HASHES.items():
        if base.digest(path)!=expected:
            raise ValueError(f"Unexpected revision of {path.name}")
    packet=json.loads(ART.read_text())
    specs={name:spec for spec in json.loads(MAP.read_text())["profiles"] for name in spec["ids"]}
    return packet,specs


def sculpt(packet,specs,part,datum,colors):
    result={color:[] for color in colors}
    regions=list(visible_regions(packet,part))
    # Independent 0.001 mm polygon rounding gives two cream pieces a
    # nonmanifold point at the end of their 16 mm shared border. Relieve only
    # the tower side of this seam by 0.009 mm, below one printed line width.
    gatehouse=next((g for f,g in regions if f["id"]=="gatehouse"),None)
    for f,visible in regions:
        if f["id"]=="right-tower" and gatehouse is not None:
            visible=visible.difference(gatehouse.buffer(.009,quad_segs=4))
        color=f["color"]
        if color not in colors:
            continue
        spec=specs.get(f["id"])
        for poly in base.polygons(visible):
            if spec:
                body=curved_region(poly,datum,spec)
            else:
                body=base.prism(poly,datum,datum+f["relief_mm"])
            result[color].extend(body.Solids())
    return result


def build(out):
    packet,specs=inputs()
    parent=cq.Assembly.load(str(STEP))
    bodies={name:n.obj for name,n in parent.objects.items() if n.obj is not None}
    for color,parts in sculpt(packet,specs,"head",base.FACE,("cream","gold")).items():
        bodies["head_"+color]=base.combine(parts)
    datum=base.BOW_BASE+1.8
    footprint=base.clean2(shape(packet["footprints"]["bow"]["geometry"]))
    backing=base.prism(footprint,base.BOW_BASE,datum)
    pink=sculpt(packet,specs,"bow",datum,("pink",))["pink"]
    bow=base.combine([backing]+pink)
    for x,y in base.BOW_MOUNTS:
        bow=bow.cut(base.circle(x,y,1.65,base.BOW_BASE-.1,base.BOW_BASE+1.45))
    bodies["bow_pink"]=bow.clean()

    assembly=cq.Assembly(name="purple_castle_card_wand_R5")
    directory=out/"print_parts"
    directory.mkdir(parents=True,exist_ok=True)
    for name,body in bodies.items():
        if not body.isValid():
            raise ValueError("Invalid B-rep "+name)
        path=directory/(name+".stl")
        if name in CHANGED:
            mesh=base.save_stl(body,path)
            if not mesh.is_volume:
                raise ValueError("Invalid mesh "+name)
            print(name,base.digest(path),len(body.Solids()),mesh.bounds.round(4).tolist(),flush=True)
        else:
            shutil.copyfile(R3/"print_parts"/path.name,path)
        assembly.add(body,name=name,color=cq.Color(base.COLORS[name.split("_")[-1]]))
    assembly.save(str(out/"purple_castle_card_wand_R5.step"))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=R5)
    build(parser.parse_args().out)
