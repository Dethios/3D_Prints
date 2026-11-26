"""Render the delivered meshes and register them against the original photograph."""
from __future__ import annotations

import argparse
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from build_wand import ART, HERE, assembly_xy, sha
from validate_wand import mesh_solid

BACKGROUND = (248,246,243)
COLORS = {"black": (.145,.140,.165), "pink": (.965,.49,.665), "white": (1,.996,.985)}
GEOMETRY = {}


def mesh(name):
    if name not in GEOMETRY:
        GEOMETRY[name] = trimesh.load_mesh(HERE/"print_parts"/f"{name}.stl")
    return GEOMETRY[name]


def actor(name, delta):
    shape = mesh(name)
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(shape.vertices),deep=True))
    faces=vtk.vtkCellArray()

    # Uniform triangle width, using VTK's native offsets/connectivity API.
    offsets=np.arange(0,3*len(shape.faces)+1,3,dtype=np.int64)
    faces.SetData(numpy_to_vtk(offsets,deep=True,array_type=vtk.VTK_ID_TYPE),
                  numpy_to_vtk(np.ascontiguousarray(shape.faces.ravel(),dtype=np.int64),deep=True,array_type=vtk.VTK_ID_TYPE))
    poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(faces)
    normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(42)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
    item=vtk.vtkActor();item.SetMapper(mapper);item.SetPosition(*delta)
    color=next(c for c in COLORS if c in name)
    style=item.GetProperty();style.SetColor(*COLORS[color]);style.SetAmbient(.38);style.SetDiffuse(.72)
    style.SetSpecular(.16 if color=="black" else .20);style.SetSpecularPower(34)
    return item


def view(names, direction=(0,0,1), target=(0,-51,0), span=254, size=(490,850), card=False):
    engine=vtk.vtkRenderer();engine.SetBackground(*(v/255 for v in BACKGROUND))
    for name,delta in names.items():
        engine.AddActor(actor(name,delta))
    if card:
        # The drawing card is intentionally diagrammatic and is excluded from the CAD.
        block=vtk.vtkCubeSource();block.SetCenter(0,-5.60,.05)
        block.SetXLength(53.98);block.SetYLength(85.6);block.SetZLength(.76)
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(block.GetOutputPort())
        item=vtk.vtkActor();item.SetMapper(mapper);item.GetProperty().SetColor(.91,.73,.50)
        item.GetProperty().SetAmbient(.46);engine.AddActor(item)
    engine.AutomaticLightCreationOff()
    for position,intensity in [((-160,180,260),.83),((160,55,140),.30),((50,40,-200),.65)]:
        light=vtk.vtkLight();light.SetPosition(*position);light.SetFocalPoint(0,0,0)
        light.SetIntensity(intensity);engine.AddLight(light)
    camera=engine.GetActiveCamera()
    vector=np.asarray(direction,dtype=float);vector/=np.linalg.norm(vector)
    camera.SetFocalPoint(*target);camera.SetPosition(*(np.asarray(target)+400*vector));camera.SetViewUp(0,1,0)
    camera.ParallelProjectionOn();camera.SetParallelScale(span/2)
    camera.SetClippingRange(50,850)
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetMultiSamples(4)
    win.SetSize(size[0]*2,size[1]*2);win.AddRenderer(engine);win.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(win);capture.ReadFrontBufferOff();capture.Update()
    data=capture.GetOutput();width,height,_=data.GetDimensions()
    pixels=vtk_to_numpy(data.GetPointData().GetScalars()).reshape(height,width,-1)[::-1]
    img=Image.fromarray(pixels.copy()).convert("RGB").resize(size,Image.Resampling.LANCZOS)
    win.Finalize()
    return img


def font(size, bold=False):
    name="segoeuib.ttf" if bold else "segoeui.ttf"
    for directory in (Path("C:/Windows/Fonts"),Path("/usr/share/fonts/truetype/dejavu")):
        for path in (directory/name,directory/("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")):
            if path.is_file():return ImageFont.truetype(str(path),size)
    return ImageFont.load_default()


def headings(draw, x, title, subtitle):
    draw.text((x,28),title,fill="#29232d",font=font(29,True))
    draw.text((x,69),subtitle,fill="#615963",font=font(18))


def make_views():
    positions={key:(0,0,0) for key in (
        "front_black","rear_black","spacer_black","handle_cuff_pink","bow_pink","bow_dots_white")}
    front=view(positions,direction=(.095,.11,1))
    rear=view(positions,direction=(.17,.055,-1))
    # Leave the rear half, spacer and card in place to expose the actual
    # pocket and visible handle tip with the front shell lifted away.
    open_view=view({"rear_black":(0,0,0),"spacer_black":(0,0,0),
                    "handle_cuff_pink":(0,-26,0)},
                   direction=(.36,.08,1),target=(0,-61,0),span=283,card=True)
    canvas=Image.new("RGB",(1494,981),BACKGROUND);draw=ImageDraw.Draw(canvas)
    for i,(pic,title,description) in enumerate([
        (front,"Front","Closed assembly"),
        (rear,"Rear","Card enclosed"),
        (open_view,"Inside","Front cover lifted, handle withdrawn"),
    ]):
        x=8+494*i
        headings(draw,x+21,title,description);canvas.paste(pic,(x,108))
    canvas.save(HERE/"wand_assembly.png")


def photo_xy(x,y):
    cx,cy=ART["reference_axis"];angle=math.radians(ART["roll_degrees"])
    c,s=math.cos(angle),math.sin(angle);unit=ART["mm_per_pixel"]
    bx,by=ART["case_bottom_photo_xy"];bottom=(bx-cx)*s+(by-cy)*c
    dx=x/unit;dy=bottom-(y-ART["assembly_case_bottom_y"])/unit
    return (cx+c*dx+s*dy,cy-s*dx+c*dy)


def trace_overlay(photo):
    assert sha(photo)==ART["photo_sha256"]
    original=Image.open(photo).convert("RGB")
    crop=(477,123,837,483)
    zoom=2
    plain=original.crop(crop).resize((720,720),Image.Resampling.LANCZOS)
    overlay=plain.copy()
    ink=ImageDraw.Draw(overlay)
    def pixel(x,y):
        u,v=photo_xy(x,y)
        return ((u-crop[0])*zoom,(v-crop[1])*zoom)
    for name,color in [("front_black","#19f2cb"),("bow_pink","#ffda66")]:
        solid=mesh_solid(mesh(name))
        if name=="bow_pink": solid=solid+mesh_solid(mesh("bow_dots_white"))
        for loop in solid.project().to_polygons():
            if len(loop)<4:continue
            pts=[pixel(x,y) for x,y in loop]
            ink.line(pts+[pts[0]],fill=color,width=3,joint="curve")
    pair=Image.new("RGB",(1490,856),BACKGROUND)
    draw=ImageDraw.Draw(pair)
    headings(draw,22,"Photograph","Unrotated source crop")
    headings(draw,763,"Export contours","Cyan head and neck, gold bow")
    pair.paste(plain,(14,115));pair.paste(overlay,(756,115))
    pair.save(HERE/"source_overlay.png")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--photo",type=Path)
    args=cli.parse_args()
    make_views()
    if args.photo:
        trace_overlay(args.photo)
