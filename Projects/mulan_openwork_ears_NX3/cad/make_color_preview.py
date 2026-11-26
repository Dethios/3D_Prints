"""Make a separate colored review plate and full-color 3D paint reference."""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely import contains_xy
from shapely.geometry import Polygon
import trimesh

from build_ears import ART_FILES, BG, DRAGON_FILE, ROOT, SHELL_FILE, SLUGS, crab, mount_point
from coin_rim import FLOOR_Z, KEY_Z
from ear_composition import Composition
from make_plate import NS, OUTPUT as PRINT_PLATE

PAINT_PLATE = ROOT / "Mulan_NX3_Color_Review.3mf"
GLB_VIEW = ROOT / "previews" / "mulan_nx3_painted_3d.glb"
PREVIEW = ROOT / "previews" / "mulan_nx3_angled_color.png"
# Group variations of pigment into a practical slicer palette. The
# textured GLB retains source-guide RGB, including intermediate shades.
SWATCHES = (
    ("Gold rim", "#B1853F"), ("Engraving", "#7A582F"),
    ("Navy backing", "#212E6E"), ("Near black", "#150F1A"),
    ("Ivory", "#FCEBCF"), ("Peach", "#F3BC85"),
    ("Mulan skin", "#865348"), ("Carmine", "#DC2845"),
    ("Orange", "#FF851C"), ("Yellow", "#FFDB20"),
    ("Royal blue", "#1441BB"), ("Turquoise", "#5ABFD0"),
    ("Mulan blue", "#326176"), ("Dark red", "#702345"),
    ("Steel", "#8D92A9"), ("Mint", "#D4F5DF"), ("Coin key gold", "#E0B45F"),
)
PALETTE = np.array([[int(code[i:i+2],16) for i in (1,3,5)] for _,code in SWATCHES],dtype=np.uint8)
REGION_SLOTS = np.array([0,1,2,0,len(SWATCHES)-1],dtype=np.uint8)
VENDOR_NS = "http://schemas.slic3r.org/3mf/2017/06"
TRIANGLE_TAG = f"{{{NS}}}triangle"
VERTEX_TAG = f"{{{NS}}}vertex"
EDGE_ORDER = [[0,1],[1,2],[2,0]]
SPLITS = (
    [[0,1,2]], [[0,3,2],[3,1,2]], [[1,4,0],[4,2,0]],
    [[3,1,4],[0,3,4],[0,4,2]], [[2,5,1],[5,0,1]],
    [[5,0,3],[2,5,3],[2,3,1]], [[4,2,5],[1,4,5],[1,5,0]],
    [[0,3,5],[3,1,4],[5,4,2],[3,4,5]],
)


def lab(rgb):
    rgb=np.asarray(rgb,dtype=float)/255
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    xyz=linear @ np.array([[.4124564,.2126729,.0193339],[.3575761,.7151522,.119192],
                           [.1804375,.072175,.9503041]])
    q=xyz/np.array([.95047,1.,1.08883])
    f=np.where(q>(6/29)**3,np.cbrt(q),q/(3*(6/29)**2)+4/29)
    L,a,b=(116*f[:,1]-16),500*(f[:,0]-f[:,1]),200*(f[:,1]-f[:,2])
    return np.column_stack((L,a,b))


def nearest(rgb):
    a,b=lab(rgb),lab(PALETTE)
    distance=np.sum((a[:,None,:]-b[None,:,:])**2,axis=2)
    return np.argmin(distance,axis=1)


def surface_regions(points, interior):
    """0 gold, 1 recessed field, 2 navy underside, 3 art, 4 raised keys."""
    z=points[:,2]
    inset=contains_xy(interior.buffer(.045),points[:,0],points[:,1])
    regions=np.zeros(len(points),dtype=np.uint8)
    regions[inset&(z<=1.91)]=2
    regions[inset&(z>1.91)&(z<6)] = 3
    regions[np.abs(z-FLOOR_Z)<.042]=1
    regions[np.abs(z-KEY_Z)<.042]=4
    return regions


def atlas(art):
    # Reserve five rows on top for the solid-color surfaces. Artwork then
    # fills a 1024 x 1024 tile at 0.10 mm / pixel in part coordinates.
    size=1024
    span=102.0
    x,y=np.meshgrid(np.linspace(-51,51,size),np.linspace(91,-11,size))
    texture=np.empty((size+5,size,3),dtype=np.uint8)
    for i,k in enumerate((0,0,1,2,len(SWATCHES)-1)):
        texture[i]=PALETTE[k]
    texture[5:]=art.color_at(x.ravel(),y.ravel()).reshape((size,size,3)).astype(np.uint8)
    return Image.fromarray(texture),span


def textured(mesh, art, interior):
    # Share vertices within each UV region but separate them where a rim
    # or engraving face meets the textured insert.
    face_regions=surface_regions(mesh.triangles_center,interior)
    key=mesh.faces*5+face_regions[:,None]
    unique,ids=np.unique(key,return_inverse=True)
    vertices=mesh.vertices[unique//5]
    material_region=unique%5
    image,span=atlas(art)
    w,h=image.size
    ui=(vertices[:,0]+51.)/span
    vi=(91.-vertices[:,1])/span
    uv=np.column_stack(((.5+ui*(w-1))/w,1.-(5.5+vi*(w-1))/h))
    for region,row in ((0,1),(1,2),(2,3),(4,4)):
        uv[material_region==region]=(.5,1.-(row+.5)/h)
    mat=trimesh.visual.material.PBRMaterial(baseColorTexture=image,metallicFactor=0.,roughnessFactor=.78,
                                          doubleSided=False)
    uv_colors=trimesh.visual.TextureVisuals(uv=uv,material=mat)
    painted=trimesh.Trimesh(vertices=vertices,faces=ids.reshape(mesh.faces.shape),
                          visual=uv_colors,process=False)
    return painted


def tessellate(mesh, art, interior):
    """Split shared edges so triangular paint cells follow the artwork.

    Midpoints lie exactly on the original surface. Uncolored neighbors
    receive the same edge split, keeping the preview mesh watertight.
    """
    v,f=mesh.vertices.copy(),mesh.faces.copy()
    safe=interior.buffer(.07)
    for _ in range(9):
        tri=v[f]
        cent=tri.mean(axis=1)
        facing=contains_xy(safe,cent[:,0],cent[:,1])&(cent[:,2]>1.91)&(cent[:,2]<6)
        indices=np.flatnonzero(facing)
        labels=nearest(art.color_at(v[:,0],v[:,1]))
        colors=labels[f[indices]]
        means=nearest(art.color_at(cent[indices,0],cent[indices,1]))
        varying=np.any(colors!=means[:,None],axis=1)
        limits=np.where(varying,.42,1.02)
        length=np.linalg.norm(tri[indices][:,[1,2,0]]-tri[indices],axis=-1)
        split=length>limits[:,None]
        if not np.any(split):
            break
        edges=f[:,EDGE_ORDER]
        unique,cells=np.unique(np.sort(edges.reshape(-1,2),axis=1),axis=0,return_inverse=True)
        cells=cells.reshape((-1,3))
        marked=np.unique(cells[indices][split])
        mids=np.full(len(unique),-1,dtype=np.int64)
        mids[marked]=np.arange(len(v),len(v)+len(marked))
        midpoint=mids[cells]
        code=(midpoint>=0) @ np.array([1,2,4])
        extended=np.concatenate((f,midpoint),axis=1)
        f=np.concatenate([extended[code==k][:,pattern].reshape((-1,3))
                          for k,pattern in enumerate(SPLITS)],axis=0)
        v=np.vstack((v,v[unique[marked]].mean(axis=1)))
    colored=trimesh.Trimesh(vertices=v,faces=f,process=False)
    assert colored.is_volume and abs(colored.volume-mesh.volume)<.001
    field=colored.triangles_center
    regions=surface_regions(field,interior)
    slots=REGION_SLOTS[regions].copy()
    field_points=field[regions==3]
    slots[regions==3]=nearest(art.color_at(field_points[:,0],field_points[:,1]))
    return colored,slots


def prepare():
    stock=crab.projection(trimesh.load_mesh(SHELL_FILE),flat_top=10.)
    interior=Polygon(stock.interiors[0])
    pose=mount_point()
    pose=[np.asarray(pose[key]) for key in ('left_brooms','right_mouse')]
    dragon=Image.open(ROOT/'artwork'/DRAGON_FILE)
    assets=[]
    for i,(name,position) in enumerate(zip(SLUGS,pose)):
        original=trimesh.load_mesh(ROOT/'stl'/f'{name}.stl')
        picture=Image.open(ROOT/'artwork'/ART_FILES[i])
        art=Composition(picture,interior,i,dragon)
        assets.append((original,art,position,picture))
    return assets,interior


def make_visuals(assets,interior):
    from render_review import render_mesh

    scene=trimesh.Scene()
    canvas=Image.new('RGB',(1360,745),BG)
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',36)
    label=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
    draw.text((28,18),'Mulan NX3  |  Painted 3D preview',font=font,fill='#f1d795')
    poses=[pose for _,_,pose,_ in assets]
    cx=np.mean([p[0,3] for p in poses])
    cy=np.mean([p[1,3] for p in poses])+24.
    for i,(mesh,art,pose,picture) in enumerate(assets):
        name=('Left fan trio','Right Mulan and dragon')[i]
        paint=textured(mesh,art,interior)
        paint.apply_transform(pose)
        paint.apply_translation((-cx,-cy,0))
        paint.apply_scale(.001)
        scene.add_geometry(paint,node_name=name,geom_name=name)
        frame=render_mesh((crab.solid(mesh),art,pose,picture),angle=22,use_paint=True)
        frame.thumbnail((654,630),Image.Resampling.LANCZOS)
        x=22+i*674+(654-frame.width)//2
        canvas.paste(frame,(x,73))
        draw.text((48+i*674,709),name,font=label,fill='#d4bfd7')
    scene.export(GLB_VIEW,file_type='glb')
    canvas.save(PREVIEW)
    print(GLB_VIEW)


def encode_slot(index):
    """PrusaSlicer 2.9 whole-triangle paint encoding, with 1-based states."""
    number = int(index)+1
    if number <= 2:
        return f"{4*number:X}"
    if number >= 17:
        return f"{number-17:02X}EC"
    return f"{number-3:X}C".rjust(2,"0")


def plate_settings(source):
    options = dict(line[2:].split(" = ",1) for line in source.splitlines()
                   if line.startswith("; ") and " = " in line)
    count = len(SWATCHES)
    colors = ";".join(code for _,code in SWATCHES)
    names = ";".join(f'"{label}"' for label,_ in SWATCHES)
    option_overrides = {
        "extruder_colour": colors,
        "filament_colour": colors,
        "filament_settings_id": names,
        "nozzle_diameter": ",".join(["0.25"]*count),
        "filament_diameter": ",".join([options["filament_diameter"]]*count),
        "single_extruder_multi_material": "1",
        "wipe_tower": "0",
        "printer_settings_id": "NX3 virtual color review",
        "print_settings_id": "Mulan NX3 color review",
        "physical_printer_settings_id": "",
        "print_host": "",
        "printhost_apikey": "",
    }
    options.update(option_overrides)
    return "\n".join(f"; {key} = {value}" for key,value in options.items())+"\n"


def color_plate(assets,interior):
    with ZipFile(PRINT_PLATE) as original:
        package={name:original.read(name) for name in original.namelist()}
    model=ET.fromstring(package["3D/3dmodel.model"])
    ET.register_namespace("slic3rpe",VENDOR_NS)
    resources=model.find(f"{{{NS}}}resources")
    model_config=ET.fromstring(package["Metadata/Slic3r_PE_model.config"])
    model.insert(1,ET.Element(f"{{{NS}}}metadata",{"name":"slic3rpe:MmPaintingVersion"}))
    model[1].text="2" if len(SWATCHES)>16 else "1"
    for label,value in {
        "Title":"Mulan NX3 — Color review",
        "Description":"Virtual filament colors for reviewing the paint scheme in 3D.",
    }.items():
        model.find(f'{{{NS}}}metadata[@name="{label}"]').text=value
    for ((mesh,art,_,_),obj,cfg) in zip(assets,list(resources),list(model_config)):
        local,slots=tessellate(mesh,art,interior)
        mesh_node=obj.find(f"{{{NS}}}mesh")
        points=mesh_node.find(f"{{{NS}}}vertices")
        triangles=mesh_node.find(f"{{{NS}}}triangles")
        points.clear()
        triangles.clear()
        for point in local.vertices:
            ET.SubElement(points,VERTEX_TAG,dict(zip("xyz",(f"{n:.8f}" for n in point))))
        for face,slot in zip(local.faces,slots):
            attrs=dict(zip(("v1","v2","v3"),map(str,face)))
            attrs[f"{{{VENDOR_NS}}}mmu_segmentation"]=encode_slot(slot)
            ET.SubElement(triangles,TRIANGLE_TAG,attrs)
        cfg.find("volume").set("lastid",str(len(local.faces)-1))
        used=np.unique(slots)
        print(obj.get("name"),len(local.faces),"paint cells,",len(used),"colors")
        assert len(used)>=11
    package["3D/3dmodel.model"]=ET.tostring(model,encoding="utf-8",xml_declaration=True)
    package["Metadata/Slic3r_PE_model.config"]=ET.tostring(model_config,encoding="utf-8",xml_declaration=True)
    package["Metadata/Slic3r_PE.config"]=plate_settings(package["Metadata/Slic3r_PE.config"].decode("utf-8")).encode("utf-8")
    thumbnail=Image.open(PREVIEW)
    thumbnail.thumbnail((256,256),Image.Resampling.LANCZOS)
    slot=BytesIO()
    thumbnail.save(slot,format="PNG")
    package["Metadata/thumbnail.png"]=slot.getvalue()
    with ZipFile(PAINT_PLATE,"w",ZIP_DEFLATED) as out:
        for name,data in package.items():
            out.writestr(name,data)
    print(PAINT_PLATE)


if __name__ == '__main__':
    assets,interior=prepare()
    make_visuals(assets,interior)
    color_plate(assets,interior)
