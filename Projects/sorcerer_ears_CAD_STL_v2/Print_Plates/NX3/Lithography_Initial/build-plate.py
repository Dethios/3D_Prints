from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import shapely as sp
from shapely import affinity
from shapely.geometry import Polygon
import trimesh

out=Path(__file__).resolve().parent
project=out.parents[2]
reference=project/"previews/Lithography_20261122/Reference_Match"
assets=reference/"Transparent_Flat_Artwork"
sys.path.insert(0,str(project/"CAD"))
from build_nx3_uniform_rim_ears import rim_profile

pmm=9.22
thickness,back=.12*10,.12*3
nx3=project/"STL/NX3"
_,cavity,_=rim_profile(trimesh.load_mesh(nx3/"ear_blue_base.stl"),
                      trimesh.load_mesh(nx3/"glue_on_base_SOURCE_GEOMETRY.stl"))
safe=sp.set_precision(cavity.buffer(-.121),.001)
spool={1:("Blue","#2446A1"),2:("White","#F4EFEB"),3:("Red","#D52D36"),4:("Black","#20202A")}

ns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
pe="http://schemas.slic3r.org/3mf/2017/06"
model=ET.Element("model",{"unit":"millimeter","xml:lang":"en-US","xmlns":ns,"xmlns:slic3rpe":pe})
ET.SubElement(model,"metadata",name="slic3rpe:Version3mf").text="1"
ET.SubElement(model,"metadata",name="Title").text="Sorcerer NX3 artwork only"
resources=ET.SubElement(model,"resources")
build=ET.SubElement(model,"build")
config=ET.Element("config")
checks={}
thumb=Image.new("RGB",(512,512),(52,58,67))


def polygons(g):
    if g.geom_type=="Polygon":
        if not g.is_empty:
            yield g
    elif hasattr(g,"geoms"):
        for part in g.geoms:
            yield from polygons(part)


def regions(mask):
    rows,cols=np.where(np.diff(np.pad(mask.astype(np.int8),((0,0),(1,1))),axis=1)!=0)
    starts,ends=cols[::2],cols[1::2]
    assert np.array_equal(rows[::2],rows[1::2])
    ys=rows[::2]
    rect=sp.box((starts-512)/pmm,(916-ys)/pmm,(ends-512)/pmm,(917-ys)/pmm)
    return sp.set_precision(sp.union_all(rect).simplify(.065,preserve_topology=True),.001)


def made_mesh(shape,z0,z1):
    solids=[]
    for p in polygons(shape):
        if p.area<1e-5:
            continue
        mesh=None
        for engine in ("manifold","earcut","geos"):
            if engine=="geos":
                tris=sp.orient_polygons(sp.constrained_delaunay_triangles(p))
                xy=np.array([list(t.exterior.coords)[:3] for t in tris.geoms])
                verts,idx=np.unique(xy.reshape((-1,2)),axis=0,return_inverse=True)
                mesh=trimesh.creation.extrude_triangulation(verts,idx.reshape((-1,3)),z1-z0)
            else:
                mesh=trimesh.creation.extrude_polygon(sp.geometry.polygon.orient(p),z1-z0,engine=engine)
            if mesh.is_volume:
                break
        assert mesh.is_volume,(p.area,mesh.euler_number)
        mesh.apply_translation([0,0,z0])
        solids.append(mesh)
    assert solids
    return trimesh.util.concatenate(solids)


def meta(parent,kind,key,value):
    ET.SubElement(parent,"metadata",type=kind,key=key,value=str(value))


def colored_masks(image):
    r,g,b,a=np.moveaxis(image.astype(np.int16),-1,0)
    kept=a>=85
    labels,_=ndimage.label(kept)
    sizes=np.bincount(labels.ravel()); sizes[0]=0
    kept &= sizes[labels]>=12
    # Select only near the filament hues. Everything else defaults to paintable white.
    blue=(b-r>32)&(b-g>20)&(g-r>4)&(b>78)
    red=(r>117)&(r-g>70)&(r-b>63)&(abs(g-b)<41)&(g<111)
    black=(np.maximum(np.maximum(r,g),b)<83)&(abs(r-b)<22)&(abs(g-r)<24)&(abs(g-b)<20)
    return kept,{1:blue,3:red,4:black}


for object_id,(name,dx,dy) in enumerate((("brooms",72,83),("mickey",188,83)),1):
    path=assets/f"{name}-flat-decorations-transparent.png"
    pic=np.asarray(Image.open(path).convert("RGBA"))
    visible,colors=colored_masks(pic)
    raw=regions(ndimage.binary_closing(visible,iterations=1))
    footprint=sp.union_all([p for p in polygons(raw.intersection(safe)) if p.area>=.13])
    assert footprint.is_valid and cavity.buffer(-.119).covers(footprint)
    before=footprint.area
    parts=[(2,"White backing under artwork",made_mesh(footprint,0,back))]
    remaining=footprint
    ink={}
    top_regions=[]
    for tool,c in colors.items():
        mask=visible & c
        # Remove one-pixel color flecks but retain connected printed details.
        mask=ndimage.binary_opening(mask,iterations=1)
        solid=regions(mask).intersection(remaining.buffer(-.018,quad_segs=2))
        solid=sp.set_precision(solid.buffer(-.024,quad_segs=2).buffer(.024,quad_segs=2),.001)
        solid=sp.union_all([p for p in polygons(solid) if p.area>=.15])
        if not solid.is_empty:
            parts.append((tool,spool[tool][0],made_mesh(solid,back,thickness)))
            remaining=remaining.difference(solid)
            ink[tool]=round(solid.area,3)
            top_regions.append((tool,solid))
    parts.append((2,"White finish and paint areas",made_mesh(remaining,back,thickness)))
    assert abs(remaining.area+sum(ink.values())-before)<.005
    for slot, region in [(2,remaining),*top_regions]:
        bitmap=Image.new("L",thumb.size)
        painter=ImageDraw.Draw(bitmap)
        def thumb_coords(ring):
            return [(34+2.15*(x+dx-25),73+2.15*(169-y-dy)) for x,y in ring.coords]
        for p in polygons(region):
            painter.polygon(thumb_coords(p.exterior),fill=255)
            for hole in p.interiors:
                painter.polygon(thumb_coords(hole),fill=0)
        thumb.paste(spool[slot][1],(0,0,*thumb.size),bitmap)
    m=ET.SubElement(ET.SubElement(resources,"object",id=str(object_id),type="model"),"mesh")
    vertices=ET.SubElement(m,"vertices")
    triangles=ET.SubElement(m,"triangles")
    o=ET.SubElement(config,"object",id=str(object_id),instances_count="1")
    meta(o,"object","name",f"{name.title()} artwork")
    meta(o,"object","extruder",2)
    vertex_offset=0
    face_offset=0
    for slot,title,mesh in parts:
        for x,y,z in mesh.vertices:
            ET.SubElement(vertices,"vertex",x=f"{x:.7f}",y=f"{y:.7f}",z=f"{z:.5f}")
        for i,j,k in mesh.faces+vertex_offset:
            ET.SubElement(triangles,"triangle",v1=str(i),v2=str(j),v3=str(k))
        vol=ET.SubElement(o,"volume",firstid=str(face_offset),lastid=str(face_offset+len(mesh.faces)-1))
        meta(vol,"volume","name",title)
        meta(vol,"volume","volume_type","ModelPart")
        meta(vol,"volume","extruder",slot)
        vertex_offset+=len(mesh.vertices)
        face_offset+=len(mesh.faces)
    transform=f"1 0 0 0 1 0 0 0 1 {dx} {dy} 0"
    ET.SubElement(build,"item",objectid=str(object_id),transform=transform)
    minx,miny,maxx,maxy=footprint.bounds
    assert 0<minx+dx<maxx+dx<260 and 0<miny+dy<maxy+dy<260
    checks[name]={"native_art_sha256":sha256(path.read_bytes()).hexdigest(),
                  "bed_bounds_xy_mm":[round(v,3) for v in (minx+dx,miny+dy,maxx+dx,maxy+dy)],
                  "artwork_area_mm2":round(before,3),"paint_or_white_area_mm2":round(remaining.area,3),
                  "colored_area_mm2_by_slot":ink,"footprint_islands":len(list(polygons(footprint))),
                  "artwork_top_mm":round(thickness,3),"volumes":len(parts),"face_count":face_offset}
    print(name,checks[name],flush=True)

template=project/"Print_Plates/NX3/Sorcerer_NX3_Relief_Interiors_K2_0p4_CFS.3mf"
plate=out/"Sorcerer_NX3_Artwork_K2_0p4_4Color_Initial.3mf"
patch={"layer_height":"0.12","first_layer_height":"0.12","brim_type":"no_brim",
       "brim_width":"0","skirts":"0","support_material":"0","post_process":"",
       "wipe_tower":"0","infill_first":"0"}
with ZipFile(template) as original, ZipFile(plate,"w",compression=ZIP_DEFLATED) as archive:
    for key in ("[Content_Types].xml","_rels/.rels"):
        archive.writestr(key,original.read(key))
    old=original.read("Metadata/Slic3r_PE.config").decode()
    for key,value in patch.items():
        old,n=re.subn(rf"(?m)^; {key} =[^\r\n]*",f"; {key} = {value}",old)
        if not n:
            old+=f"\n; {key} = {value}\n"
    archive.writestr("Metadata/Slic3r_PE.config",old)
    picture=BytesIO()
    thumb.save(picture,format="PNG")
    archive.writestr("Metadata/thumbnail.png",picture.getvalue())
    archive.writestr("3D/3dmodel.model",ET.tostring(model,encoding="utf-8",xml_declaration=True))
    archive.writestr("Metadata/Slic3r_PE_model.config",ET.tostring(config,encoding="utf-8",xml_declaration=True))
with ZipFile(plate) as z:
    assert z.testzip() is None
    spine=ET.fromstring(z.read("Metadata/Slic3r_PE_model.config"))
    slots={int(m.get("value")) for m in spine.findall(".//volume/metadata") if m.get("key")=="extruder"}
    assert slots=={1,2,3,4}
report={"pixels_per_mm":pmm,"nominal_rim_margin_mm":.12,"decoration_thickness_mm":round(thickness,2),
        "four_slots":spool,"parts":checks,"plate_sha256":sha256(plate.read_bytes()).hexdigest()}
(out/"geometry-verification.json").write_text(json.dumps(report,indent=2)+"\n")
