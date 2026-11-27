"""Render the release meshes and an X=0 section through the installed grip."""
import numpy as np
from PIL import Image,ImageDraw
import trimesh
from shapely.geometry import Polygon,box

from build_r6 import R6,base
from validate_r6 import rounded_gauge
from validate_wand import solid
from render_wand import view,font,PAPER,INK,COLORS

TEAL="#88bdc9"
VIOLET="#5d387c"


def mesh_from_solid(s):
    data=s.to_mesh()
    return trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts,process=False)


def section_view(meshes,card):
    # Rotate the STL stack so X=0 is the slicing plane. The section returns
    # (assembly Z, assembly Y); draw Y horizontally to put the grip at left.
    start,end=-85.,-40.
    width,height=940,276
    scale=13.0
    left=76
    zero=139
    img=Image.new("RGB",(width,height),PAPER)
    draw=ImageDraw.Draw(img)
    def pixel(y,z):
        return left+(y-start)*scale,zero-z*scale
    def draw_part(body,color):
        region=Polygon()
        for ring in body.rotate((0,90,0)).slice(0).to_polygons():
            region=region.symmetric_difference(Polygon(ring))
        region=region.intersection(box(-9.5,start,9.5,end))
        for p in base.polygons(region):
            draw.polygon([pixel(y,z) for z,y in p.exterior.coords],fill=color)
            for hole in p.interiors:
                draw.polygon([pixel(y,z) for z,y in hole.coords],fill=PAPER)
    for key in ("head_purple","rear_purple"):
        draw_part(solid(meshes[key]),"#945aa6")
    draw_part(solid(meshes["handle_purple"]),VIOLET)
    draw_part(card,TEAL)
    for y,z,tx,ty,label in [(-72.5,3.5,49,15,"Grip and cuff"),
                            (-58.04,0.0,503,22,"0.60 mm seated gap"),
                            (-44.7,0,692,140,"1.20 mm card")]:
        tip=pixel(y,z)
        draw.line([tip,(tx+8,ty+15)],fill="#46384a",width=2)
        draw.ellipse((tip[0]-2,tip[1]-2,tip[0]+2,tip[1]+2),fill="#46384a")
        bounds=draw.textbbox((tx,ty),label,font=font(18,True))
        draw.rectangle((bounds[0]-2,bounds[1]-2,bounds[2]+2,bounds[3]+2),fill=PAPER)
        draw.text((tx,ty),label,font=font(18,True),fill=INK)
    return img


def main():
    meshes={p.stem:trimesh.load_mesh(p) for p in (R6/"print_parts").glob("*.stl")}
    COLORS["gauge"]=TEAL
    card=rounded_gauge(-26.99,-57.75,26.99,27.85,3.18,1.2)
    canvas=Image.new("RGB",(1700,1100),PAPER)
    d=ImageDraw.Draw(canvas)
    d.text((32,22),"Castle card wand  /  R6",font=font(41,True),fill=INK)
    d.text((34,76),"130 mm star   /   enclosed portrait card",font=font(20),fill="#635b66")
    def header(x,y,title,sub):
        d.text((x,y),title,font=font(24,True),fill=INK)
        d.text((x,y+36),sub,font=font(16),fill="#635b66")
    header(32,135,"Front","The three pennants clear the raised purple lip")
    canvas.paste(view(meshes,(0,-10,4),(.06,.05,1),176,(678,840)),(22,198))
    header(741,135,"Loading from below","Grip removed and rear cover hidden to show the channel")
    loading={k:v for k,v in meshes.items() if k not in ("rear_purple","handle_purple","handle_gold")}
    loading["card_gauge"]=mesh_from_solid(card.translate((0,-29,0)))
    canvas.paste(view(loading,(0,-18,0),(.08,.06,-1),163,(455,533)),(738,198))
    header(1212,135,"Closed rear","The assembled grip blocks the lower opening")
    canvas.paste(view(meshes,(0,-18,0),(.08,.06,-1),163,(455,533)),(1210,198))
    header(741,750,"How the grip retains the card","Center section from the meshes, colored to distinguish the grip and card")
    canvas.paste(section_view(meshes,card),(732,813))
    canvas.save(R6/"castle_wand_R6_preview.png")

if __name__=="__main__":
    main()
