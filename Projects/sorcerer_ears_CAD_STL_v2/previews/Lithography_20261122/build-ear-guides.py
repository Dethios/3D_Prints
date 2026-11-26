import json,math,os,sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import trimesh
from shapely import affinity, Polygon, box
from shapely.geometry import shape
from shapely.ops import unary_union

p=Path('Projects/sorcerer_ears_CAD_STL_v2')
sys.path.insert(0,str((p/'CAD').resolve()))
from build_nx3_uniform_rim_ears import rim_profile

out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
refs=Path(os.environ['SORCERER_IMAGE_REFERENCES'])
nx3=p/'STL/NX3'
_,inner,rim=rim_profile(trimesh.load_mesh(nx3/'ear_blue_base.stl'),trimesh.load_mesh(nx3/'glue_on_base_SOURCE_GEOMETRY.stl'))
outer=Polygon(rim.exterior)
safe=inner.buffer(-1.10).intersection(box(-58,15.2,58,100))
arts=json.loads((p/'CAD/artwork.json').read_text())
PX=9.22
CX, bottom = 512.0, 917.0
def coords(ring):
    return [(float(x)*PX+CX,bottom-float(y)*PX) for x,y in ring.coords]
def fill(d,g,val,holes):
    for poly in ([g] if g.geom_type=='Polygon' else list(g.geoms)):
        if poly.geom_type != 'Polygon':
            continue
        d.polygon(coords(poly.exterior),fill=val)
        for h in poly.interiors:
            d.polygon(coords(h),fill=holes)
def stamp_stars(d,placements,fg,bg):
    for x,y,r,n in placements:
        q=[]
        for j in range(n*2):
            a=math.pi/2+j*math.pi/n
            v=r if j%2==0 else r*.49
            q.append((x+v*math.cos(a),y+v*math.sin(a)))
        s=Polygon(q)
        if safe.covers(s):
            fill(d,s,fg,bg)
def mount(g,angle,scale,x,y):
    return affinity.translate(affinity.rotate(affinity.scale(g,scale,scale,origin=(0,0)),angle,origin=(0,0)),x,y)
for filename,geom in [('ear-outer-alpha.png',outer),('ear-interior-alpha.png',inner),('ear-content-safe-alpha.png',safe)]:
    m=Image.new('L',(1024,1024))
    fill(ImageDraw.Draw(m),geom,255,0)
    m.save(out/filename)
bg='#243F79'; gold='#DCAF54'; ink='#97A9C9'; stars='#CCD5E6'
for side in ['mickey','brooms']:
    im=Image.new('RGB',(1024,1024),'#F6F3EC'); d=ImageDraw.Draw(im)
    fill(d,outer,gold,'#F6F3EC'); fill(d,inner,bg,gold)
    if side=='mickey':
        source=shape(arts['mouse'])
        pose=mount(source.geoms[0],40,1.00,0.8,45.55)
        assert safe.covers(pose)
        fill(d,pose,ink,bg)
        stamp_stars(d,[(-25,69,4.5,5),(-7,76,4.3,4),(18,72,5.2,5),(31,57,4.3,4),
                      (34,42,4.0,4),(-33,31,4.8,5),(-18,22,3.4,4),(28,25,4.1,4),
                      (-30,52,2.1,4),(25,48,2.4,4)],stars,bg)
    else:
        source=shape(arts['brooms'])
        for n in (1,3):
            pose=mount(source.geoms[n],-40,1.12,2.1,39.9)
            assert safe.covers(pose)
            fill(d,pose,ink,bg)
        stamp_stars(d,[(-26,68,4.9,5),(-7,75,4.4,4),(25,66,4.8,5),(-30,41,4.2,4),
                      (-17,30,4.8,4),(22,21,4.7,5),(28,38,4.3,4),(-5,18,3.5,4)],stars,bg)
    im.save(out/f'{side}-true-ear-layout.png')
for title,file,maxsize in [
 ('mickey-pose','codex-clipboard-ace22785-6bbc-441e-83f1-712ed49f32a7.png',416),
 ('mickey-enamel','codex-clipboard-255ff44a-6bb1-46ff-ab94-9a26d4bfb4fd.png',576),
 ('broom-enamel','codex-clipboard-6f9715af-3e13-4bc3-9573-f0a0dba28ce6.png',576)
]:
    im=Image.open(refs/file).convert('RGB')
    ww,hh=im.size
    scale=min(maxsize/max(im.size),1.75)
    target=(max(32,round(ww*scale/32)*32),max(32,round(hh*scale/32)*32))
    ImageOps.contain(im,target,Image.Resampling.LANCZOS).save(out/f'{title}-reference.png')
print('Exact CAD rim and safety masks saved. Both pose guides fit in the usable opening.')
