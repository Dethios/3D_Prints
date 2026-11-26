"""Render the frozen STL set, actual keeper poses and a removable reference card."""
from pathlib import Path

import numpy as np
import trimesh
import vtk
from PIL import Image, ImageDraw, ImageFont
from vtk.util.numpy_support import numpy_to_vtk,vtk_to_numpy

from build_wand import CAD,COLORS
from validate_wand import card_local,world_card

PAPER=(247,245,242)
INK="#332b37"


def font(size,bold=False):
    path=Path("C:/Windows/Fonts")/("segoeuib.ttf" if bold else "segoeui.ttf")
    return ImageFont.truetype(str(path),size) if path.exists() else ImageFont.load_default()


def actor(mesh,color):
    pts=vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(mesh.vertices),deep=True))
    faces=vtk.vtkCellArray()
    for_vtk=lambda a:numpy_to_vtk(np.ascontiguousarray(a,dtype=np.int64),deep=True,array_type=vtk.VTK_ID_TYPE)
    faces.SetData(for_vtk(np.arange(0,3*len(mesh.faces)+1,3)),for_vtk(mesh.faces.ravel()))
    poly=vtk.vtkPolyData()
    poly.SetPoints(pts)
    poly.SetPolys(faces)
    normals=vtk.vtkPolyDataNormals()
    normals.SetInputData(poly)
    normals.SetFeatureAngle(48)
    mapper=vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    item=vtk.vtkActor()
    item.SetMapper(mapper)
    rgb=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
    prop=item.GetProperty()
    prop.SetColor(*rgb)
    prop.SetAmbient(.32)
    prop.SetDiffuse(.76)
    prop.SetSpecular(.16)
    prop.SetSpecularPower(24)
    return item


def view(meshes,target,direction,span,size,card=None,keeper_angle=0):
    engine=vtk.vtkRenderer()
    engine.UseSSAOOn()
    engine.SetSSAORadius(3.5)
    engine.SetSSAOBias(.38)
    engine.SetSSAOKernelSize(160)
    engine.SSAOBlurOn()
    engine.SetBackground(*(x/255 for x in PAPER))
    for name,mesh in meshes.items():
        item=actor(mesh,COLORS[name.split("_")[-1]])
        if name=="keeper_purple":
            item.SetOrigin(16,16,0)
            item.RotateZ(keeper_angle)
        engine.AddActor(item)
    if card is not None:
        m=world_card(card_local(),*card).to_mesh()
        mesh=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False)
        engine.AddActor(actor(mesh,"#91bfc4"))
    position=np.array(target)+np.asarray(direction)/np.linalg.norm(direction)*450
    camera=engine.GetActiveCamera()
    camera.SetFocalPoint(*target)
    camera.SetPosition(*position)
    camera.SetViewUp(0,1,0)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(span/2)
    camera.SetClippingRange(350,550)
    engine.AutomaticLightCreationOff()
    for pos,energy in [((-170,140,200),.80),((130,110,170),.28),((100,60,-210),.75),((-110,60,-165),.20)]:
        light=vtk.vtkLight()
        light.SetPosition(*pos)
        light.SetFocalPoint(*target)
        light.SetIntensity(energy)
        engine.AddLight(light)
    w=vtk.vtkRenderWindow()
    w.SetOffScreenRendering(1)
    w.SetSize(size[0]*2,size[1]*2)
    w.SetMultiSamples(0)
    w.AddRenderer(engine)
    w.Render()
    grab=vtk.vtkWindowToImageFilter()
    grab.SetInput(w)
    grab.ReadFrontBufferOff()
    grab.Update()
    data=grab.GetOutput()
    width,height,_=data.GetDimensions()
    array=vtk_to_numpy(data.GetPointData().GetScalars()).reshape(height,width,-1)[::-1]
    img=Image.fromarray(array.copy()).convert("RGB").resize(size,Image.Resampling.LANCZOS)
    w.Finalize()
    return img


def main():
    meshes={p.stem:trimesh.load_mesh(p) for p in (CAD/"print_parts").glob("*.stl")}
    board=Image.new("RGB",(1640,1050),PAPER)
    draw=ImageDraw.Draw(board)
    draw.text((35,16),"Castle card wand",fill=INK,font=font(42,True))
    draw.text((38,78),"R2 prototype   /   Rendered from the printable meshes",fill="#675f67",font=font(19))
    def panel(x,y,title,caption,params):
        draw.text((x,y),title,fill=INK,font=font(24,True))
        draw.text((x,y+34),caption,fill="#675f67",font=font(16))
        board.paste(view(meshes,**params),(x,y+62))
    panel(30,129,"Assembled wand","140 mm across the star",
          dict(direction=(.045,.025,1),target=(0,-117.,0),span=379,size=(360,857)))
    panel(415,129,"Castle and rose","Four head colors with a separate pink bow",
          dict(direction=(.09,.08,1),target=(0,-13,3),span=166,size=(590,637)))
    panel(415,841,"Bow clearance","Side view of fixed bow, socket and removable grip",
          dict(direction=(.94,.07,.35),target=(0,-67,0),span=70,size=(590,145)))
    panel(1030,129,"Keeper closed","The lower tabs and upper keeper capture the card",
          dict(direction=(.26,.15,-1),target=(0,-8,0),span=92,size=(570,350),card=(-42.5,0,0)))
    panel(1030,575,"Keeper open","Lift the card at the thumb scoop, then slide it free",
          dict(direction=(.45,.34,-1),target=(0,-8,0),span=96,size=(570,350),card=(-42.5,.12,15),keeper_angle=-80))
    board.save(CAD/"wand_assembly.png")

if __name__=="__main__":
    main()


