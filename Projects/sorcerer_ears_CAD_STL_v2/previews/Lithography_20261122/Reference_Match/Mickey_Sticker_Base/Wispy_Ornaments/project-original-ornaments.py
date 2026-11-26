from pathlib import Path
import sys, math
from PIL import Image, ImageDraw, ImageFont
import trimesh
import numpy as np
out=Path(sys.argv[1])
proj=next(p for p in out.parents if (p/"CAD/assembly_positions.json").exists())
m=trimesh.load_mesh(proj/"STL/NX3/Uniform_Rim/right_mouse_raised_gold.stl").split(only_watertight=False)
ss=20
angle=np.deg2rad(-40)
R=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
atlas=Image.new("RGB",(1000,520),(28,51,99))
d=ImageDraw.Draw(atlas)
for i in range(1,9):
 face=m[i].triangles[:,:,:2]
 screen=(face@R.T)*[ss,-ss]
 lo=np.floor(screen.min(axis=(0,1)))-6
 hi=np.ceil(screen.max(axis=(0,1)))+6
 silhouette=Image.new("L",tuple(np.rint(hi-lo).astype(int)))
 dd=ImageDraw.Draw(silhouette)
 for t in screen:
  dd.polygon([tuple(z) for z in t-lo],fill=255)
 silhouette=silhouette.crop(silhouette.getbbox())
 silhouette.save(out/f"outline-ornament-{i}.png")
 print(i,silhouette.size)
 im=Image.new("RGB",silhouette.size,(237,195,115))
 im.thumbnail((209,205))
 mask=silhouette.resize(im.size,Image.Resampling.LANCZOS)
 x=15+(i-1)%4*250;y=20+(i-1)//4*260
 atlas.paste(im,(x,y+22),mask)
 d.text((x,y),str(i),fill="white")
atlas.save(out/"original-component-atlas.png")
