from bridge import *
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation
import sys
sys.path.insert(0,str(KIT/"cad"))
from build_crab_nx3 import solid, rendered, mesh, STL
w=Path(__file__).parent
fontroot=Path("C:/Windows/Fonts")
title=ImageFont.truetype(str(fontroot/"segoeuib.ttf"),28)
label=ImageFont.truetype(str(fontroot/"segoeui.ttf"),20)
bold=ImageFont.truetype(str(fontroot/"segoeuib.ttf"),20)
a=layers(sys.argv[1])
b=layers(sys.argv[2])
target=max((r for r in a if r[1]=="Bridge infill"),key=lambda r:r[2])
paper=Image.new("RGB",(1450,845),"#f5f2fa")
draw=ImageDraw.Draw(paper)
draw.text((24,13),"Where the 25.2 mm bridge runs",font=title,fill="#241933")
draw.text((24,54),"NX3 left ear   •   PrusaSlicer toolpaths at Z = 1.90 mm",font=label,fill="#56456d")
rot=Rotation.from_euler("z",40,degrees=True).as_matrix()
shape=solid(STL/"left_crab_face.stl").transform(np.column_stack([rot,[0,0,0]]))
preview=w/"left-front.png"
rendered([(shape,"sclera")],preview)
im=Image.open(preview).convert("RGB")
xy=mesh(shape).vertices[:,:2]
lo,hi=xy.min(axis=0),xy.max(axis=0)
scale=1800/(hi[0]-lo[0]+14)*.75
def front(p):
    q=rot[:2,:2]@p
    return ((q[0]-lo[0]+7)*scale,(hi[1]-q[1]+7)*scale)
d=ImageDraw.Draw(im)
p,q=map(front,target[3:])
d.line([p,q],fill="#e64769",width=12)
for x,y in (p,q): d.ellipse((x-12,y-12,x+12,y+12),fill="#ffdee6",outline="#d62851",width=5)
im.thumbnail((444,600),Image.Resampling.LANCZOS)
paper.paste(im,(24,132))
draw.text((24,98),"Projected onto the exported STL",font=bold,fill="#352546")
draw.text((24,654),"The red line marks the former bridge.",font=label,fill="#352546")
draw.text((24,683),"It ran beneath the left gem.",font=label,fill="#352546")
for col,(moves,caption) in enumerate([(a,"Original plate • Z = 1.90 mm"),(b,sys.argv[3])]):
    x0=496+478*col; y0=132; box_w=453; box_h=500
    draw.text((x0,98),caption,font=bold,fill="#352546")
    draw.rounded_rectangle((x0,y0,x0+box_w,y0+box_h),radius=10,fill="white",outline="#ddd5e9")
    lo2=np.array([-48,5]); hi2=np.array([6,57]); s=min((box_w-25)/(hi2[0]-lo2[0]),(box_h-25)/(hi2[1]-lo2[1]))
    def project(pt):
        q=rot[:2,:2]@pt
        return (x0+12+(q[0]-lo2[0])*s,y0+20+(hi2[1]-q[1])*s)
    top=Image.new("RGB",(box_w-4,box_h-4),"white")
    td=ImageDraw.Draw(top)
    def local_panel(pt):
        x,y=project(pt)
        return x-x0-2,y-y0-2
    for z,role,_,p,q in moves:
        if abs(z-1.9)<1e-6:
            color="#f1912c" if role=="Bridge infill" else "#8875a6" if "perimeter" in role.lower() else "#cfc2df"
            td.line([local_panel(p),local_panel(q)],fill=color,width=2 if role=="Bridge infill" else 1)
    if col==0: td.line([local_panel(p) for p in target[3:]],fill="#d62851",width=5)
    paper.paste(top,(x0+2,y0+2))
    bridge=[r[2] for r in moves if abs(r[0]-1.9)<1e-6 and r[1]=="Bridge infill"]
    result=f"Longest bridge on this layer  {max(bridge):.2f} mm" if bridge else "No bridge extrusion on this layer"
    draw.text((x0,654),result,font=label,fill="#352546")
for x,c,t in [(498,"#d62851","25.2 mm segment"),(722,"#f1912c","Bridge infill"),(904,"#a798bc","Other toolpaths")]:
    draw.line((x,723,x+29,723),fill=c,width=4)
    draw.text((x+38,710),t,font=label,fill="#352546")
draw.text((24,789),"Both gem foundations now reach Z = 0. The visible front relief stays the same.",font=label,fill="#56456d")
paper.save(w/"gem-foundation-toolpaths.png")
