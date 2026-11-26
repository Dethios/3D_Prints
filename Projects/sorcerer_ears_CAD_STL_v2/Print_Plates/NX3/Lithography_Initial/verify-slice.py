from pathlib import Path
import json,re
import xml.etree.ElementTree as ET
from hashlib import sha256
from zipfile import ZipFile

import numpy as np
import shapely as sp

out=Path(__file__).resolve().parent
top=next(p for p in out.parents if (p/".coordination").is_dir())
scratch=top/".coordination/k2-lithography-preflight"
file=scratch/"final-slice-validation.gcode"
lines=file.read_text(encoding="utf-8").splitlines()
plate=out/"Sorcerer_NX3_Artwork_K2_0p4_4Color_Initial.3mf"
find=lambda prefix: [i for i,text in enumerate(lines) if text.startswith(prefix)]

init,=find("START_PRINT ")
purge,=find("LINE_PURGE")
end,=find("END_PRINT")
start_t=lines.index("T1",init,purge)
temp=next(i for i in find("M109 ") if i>init)
assert max(find("EXCLUDE_OBJECT_DEFINE ")) < init < start_t < temp < purge < end
assert "G92 E0" in lines[purge+1:purge+4]

current=None
z=0
tool=None
settings={}
marks=[]
first={}
tools={}
for line in lines[init:end+1]:
    if line.startswith(";Z:"):
        z=round(float(line[3:]),2)
    elif line.startswith("EXCLUDE_OBJECT_START NAME='"):
        current=line.split("'")[1]
    elif line.startswith("EXCLUDE_OBJECT_END"):
        current=None
    elif re.fullmatch(r"T[0-3]",line):
        tool=line;marks.append(tool)
    elif current and tool and (line.startswith("G1 ") or line.startswith("G2 ") or line.startswith("G3 ")):
        vals=dict((k,float(v)) for k,v in re.findall(r"([XYE])(-?[\d.]+)",line.partition(";")[0]))
        if vals.get("E",0)>0 and "X" in vals and "Y" in vals:
            tools.setdefault(current,{}).setdefault(z,set()).add(tool)
            if z==.12:
                first.setdefault(current,[]).append((vals["X"],vals["Y"]))
assert set(tools)=={"Brooms_artwork","Mickey_artwork"}
assert all(set(rows)=={round(i*.12,2) for i in range(1,11)} for rows in tools.values())
assert all(slots=={"T1"} for slots in tools["Brooms_artwork"].values())
assert all(slots==({"T1"} if z<=.36 else {"T0","T1","T2","T3"}) for z,slots in tools["Mickey_artwork"].items())

with ZipFile(plate) as zf:
    doc=ET.fromstring(zf.read("3D/3dmodel.model"))
    meta=ET.fromstring(zf.read("Metadata/Slic3r_PE_model.config"))
    assert zf.testzip() is None
    for line in zf.read("Metadata/Slic3r_PE.config").decode().splitlines():
        if line.startswith("; ") and " = " in line:
            k,v=line[2:].split(" = ",1)
            settings[k]=v
    assert settings["layer_height"]==settings["first_layer_height"]=="0.12"
    assert all(settings[key]=="0" for key in ("brim_width","skirts","wipe_tower","support_material","single_extruder_multi_material_priming"))
    assert settings["brim_type"]=="no_brim"
    ns={"m":doc.tag.split("}")[0][1:]}
    island_report={}
    for el,m in zip(doc.findall("m:resources/m:object",ns),meta.findall("object")):
        xy=np.array([[float(v.get(k)) for k in ("x","y","z")] for v in el.findall("m:mesh/m:vertices/m:vertex",ns)])
        face=np.array([[int(t.get(k)) for k in ("v1","v2","v3")] for t in el.findall("m:mesh/m:triangles/m:triangle",ns)])
        firstvol=m.find("volume")
        face=face[int(firstvol.get("firstid")):int(firstvol.get("lastid"))+1]
        bottom=xy[face[(xy[face,2]==0).all(axis=1)],:2]
        item=next(i for i in doc.findall("m:build/m:item",ns) if i.get("objectid")==el.get("id"))
        dx,dy=map(float,item.get("transform").split()[9:11])
        pieces=sp.get_parts(sp.union_all(sp.polygons(bottom+[dx,dy])))
        name=next(t.get("value") for t in m.findall("metadata") if t.get("key")=="name").replace(" ","_")
        x,y=np.asarray(first[name]).T
        misses=[round(float(poly.area),3) for poly in pieces if not sp.contains_xy(sp.buffer(poly,.035),x,y).any()]
        island_report[name]={"geometry_islands":len(pieces),"with_detected_first_layer_extrusion":len(pieces)-len(misses),
                             "missed_island_areas_mm2":misses}

report={"prusaslicer":"2.9.7","layers":10,"tool_selection_sequence":marks,
        "tools_by_object_and_z":{k:{z:sorted(v) for z,v in p.items()} for k,p in tools.items()},
        "first_layer_islands":island_report,
        "estimated_time":next(i.split(" = ")[-1] for i in lines if i.startswith("; estimated printing time (normal mode)")),
        "filament_g_by_slot":next(i.split(" = ")[-1] for i in lines if i.startswith("; filament used [g]")),
        "low_bed_adhesion_warning":"Low bed adhesion" in (scratch/"prusaslicer.log").read_text(),
        "plate_sha256":sha256(plate.read_bytes()).hexdigest()}
(out/"slicing-verification.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="tools_by_object_and_z"},indent=2))
