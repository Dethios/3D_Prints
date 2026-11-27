"""Render the cut sites, protected thread and physical release coupon from STLs."""
import json
import numpy as np
from PIL import Image,ImageDraw
import trimesh

from build_fixture import HERE,R6,FILE,COLORS as HEAD_COLORS,MATRIX
from render_wand import view,font,PAPER,INK,COLORS

# The shared rendering camera uses +Y as up. Re-express print Z as camera Y.
TO_VIEW=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]])
COLORS["fixture"]="#1988a6"


def read_mesh(file,transform=TO_VIEW):
    mesh=trimesh.load_mesh(file)
    mesh.apply_transform(transform)
    return mesh


def screen(point,target,direction,span,size):
    optical=np.asarray(direction,dtype=float)
    optical/=np.linalg.norm(optical)
    right=np.cross([0,1,0],optical)
    right/=np.linalg.norm(right)
    vertical=np.cross(optical,right)
    d=np.asarray(point)-np.asarray(target)
    return size[0]/2+np.dot(d,right)*size[1]/span,size[1]/2-np.dot(d,vertical)*size[1]/span


def main():
    meshes={"head_"+color:read_mesh(R6/"print_parts"/("head_"+color+".stl"),TO_VIEW@np.array(MATRIX))
            for color in HEAD_COLORS}
    meshes["cradle_fixture"]=read_mesh(HERE/(FILE+".stl"))
    coupon={}
    for path in (HERE/"release_coupon").glob("*.stl"):
        key="sample_fixture" if "cradle" in path.stem else path.stem
        coupon[key]=read_mesh(path)
    board=Image.new("RGB",(1640,1070),PAPER)
    draw=ImageDraw.Draw(board)
    draw.text((36,18),"Upright star cradle",font=font(42,True),fill=INK)
    draw.text((38,77),"R6 front at 90°   /   Sacrificial structure shown in teal",font=font(20),fill="#655c64")
    def heading(x,y,title,sub):
        draw.text((x,y),title,font=font(25,True),fill=INK)
        draw.text((x,y+35),sub,font=font(16),fill="#655c64")
    heading(30,141,"Six cut sites","Three short blue ties meet each side of the purple structural edge")
    target=(0,69,2)
    direction=(.06,.05,1)
    size=(780,807)
    span=160
    full=view(meshes,target,direction,span,size)
    fd=ImageDraw.Draw(full)
    for s in json.loads((HERE/"fixture_layout.json").read_text())["intended_contacts"]:
        if s["kind"].startswith("cuttable"):
            x,y=screen((s["x"],s["z"],2.05),target,direction,span,size)
            fd.ellipse((x-9,y-9,x+9,y+9),outline="#cb583b",width=3)
    board.paste(full,(22,205))
    heading(830,141,"Lower supports","The teeth and front fingers catch the undersides; the thread channel stays accessible")
    board.paste(view(meshes,(1,24,3),(.32,.21,1),74,(766,334)),(828,205))
    heading(830,590,"Release coupon","Actual lower rim, structural edge, fixture teeth and one tie")
    board.paste(view(coupon,(40,15.0,3),(.33,.22,1),43,(425,347)),(820,650))
    draw.text((1260,713),"On the cooled print",fill=INK,font=font(20,True))
    for i,txt in enumerate(("Support the head.","Clip the side ties.","Move the cradle forward","and slightly down.","Check the thread and slot.")):
        draw.text((1260,756+33*i),txt,fill="#57505b",font=font(18))
    board.save(HERE/"upright_fixture_preview.png")

if __name__=="__main__":
    main()
