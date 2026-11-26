import json
from hashlib import sha256
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

out=Path(__file__).resolve().parent
root=out.parent
raw_path=Path(sys.argv[1]).resolve()
label=sys.argv[2]
outer_path=root/"ear-outer-alpha.png"
inner_path=root/"ear-interior-alpha.png"
inner,outer=[Image.open(p).convert("L") for p in (inner_path,outer_path)]
pad, size, center, angle=112,(1248,1248),(624,624),-40
navy,gold,paper=(28,51,99),(218,173,85),(249,239,222)
bicubic=Image.Resampling.BICUBIC


def mount(mask):
    full=Image.new("L",size)
    full.paste(mask,(pad,pad))
    return full.rotate(angle,bicubic,center=center)


def color_base(image,rgb):
    layer=Image.new("RGBA",image.size,(*rgb,0))
    layer.putalpha(image)
    return layer


def fit_selected(source, candidates=54):
    im=Image.open(source).convert("RGBA")
    pix=np.asarray(im).astype(float)[:,:,:3]
    r,g,b=np.moveaxis(pix,-1,0)
    blue=(r<100)&(b>r+26)&(g>r+5)&(b>60)
    components,n=ndimage.label(blue)
    count=np.bincount(components.ravel())
    count[0]=0
    assert count.max() > 30000
    field=ndimage.binary_fill_holes(components==count.argmax())
    inside=ndimage.binary_erosion(field,iterations=7)
    if inside.sum()<150000:
        raise ValueError("Cannot isolate the navy ear interior")
    iy,ix=np.indices(inside.shape,dtype=float)
    X=(ix-im.width/2)/im.width
    Y=(iy-im.height/2)/im.height
    reg=np.stack((np.ones_like(X),X,Y,X*X,X*Y,Y*Y),axis=-1)
    background=blue&inside&(ix%5==0)&(iy%5==0)
    coefficients=np.linalg.lstsq(reg[background],pix[background],rcond=None)[0]
    for _ in range(2):
        err=np.linalg.norm(pix-reg@coefficients,axis=2)
        use=background&(err<24)
        coefficients=np.linalg.lstsq(reg[use],pix[use],rcond=None)[0]
    diff=np.linalg.norm(pix-reg@coefficients,axis=2)
    f=inside&(diff>25)
    f=ndimage.binary_closing(f,iterations=1)
    cc,_=ndimage.label(f)
    area=np.bincount(cc.ravel())
    area[0]=0
    keep=area[cc]>=max(22,round(im.width*im.height*.000026))
    alpha=np.clip((diff-7)/28,0,1)*ndimage.binary_dilation(keep,iterations=1)
    alpha[alpha<.035]=0
    im.putalpha(Image.fromarray(np.rint(alpha*255).astype(np.uint8)))
    im=im.crop(im.getbbox())
    assert im.width>400 and im.height>400
    return im


art = Image.open(raw_path).convert("RGBA") if "--isolated" in sys.argv else fit_selected(raw_path)
art.save(out/f"mickey-sticker-{label}-isolated.png")
opening,perimeter=mount(inner),mount(outer)
frame=np.asarray(opening)>180
distance=ndimage.distance_transform_edt(frame)
yy,xx=np.where(np.asarray(art.getchannel("A"))>100)
selection=np.column_stack((xx,yy))
sharp=ndimage.binary_erosion(np.asarray(art.getchannel("A"))>100,iterations=2)
yy2,xx2=np.where((np.asarray(art.getchannel("A"))>100)&~sharp)
edges=np.column_stack((xx2,yy2))[::5]
art_center=np.array([(art.width-1)/2,(art.height-1)/2])
frame_y,frame_x=np.where(frame)
frame_center=np.array([(frame_x.min()+frame_x.max())/2,(frame_y.min()+frame_y.max())/2])
max_scale=min((frame_x.max()-frame_x.min())/art.width,(frame_y.max()-frame_y.min())/art.height)
solutions=[]
for scale in np.arange(max_scale*.995,max_scale*.48,-.009):
    offset=np.rint((edges-art_center)*scale).astype(int)
    for dx in range(-140,141,7):
        for dy in range(-133,134,7):
            center_at=np.rint(frame_center+[dx,dy]).astype(int)
            co=offset+center_at
            if np.any(co<0) or np.any(co>=size[0]):
                continue
            gap=distance[co[:,1],co[:,0]].min()
            if gap<8:
                continue
            score=(max_scale-scale)*440 + abs(dx)*.32 + abs(dy-18)*.11
            solutions.append((score,scale,center_at))
if not solutions:
    raise ValueError("The full sticker artwork does not fit the ear opening")
_,scale,place=min(solutions,key=lambda row:row[0])
sprite=art.resize((round(art.width*scale),round(art.height*scale)),Image.Resampling.LANCZOS)
x,y=np.rint(place-np.array(sprite.size)/2).astype(int)
scene=Image.new("RGBA",size)
scene.alpha_composite(sprite,(x,y))
a=np.asarray(scene.getchannel("A"))
assert np.all(distance[a>100]>3)

def clip(layer,mask):
    p=np.asarray(layer.getchannel("A")).astype(np.uint16)
    q=np.asarray(mask).astype(np.uint16)
    result=layer.copy()
    result.putalpha(Image.fromarray(((p*q+127)//255).astype(np.uint8)))
    return result

ink=clip(scene,opening)
field=color_base(opening,navy)
field.alpha_composite(ink)
rim=color_base(perimeter,gold)
rim.alpha_composite(field)
review=Image.new("RGBA",size,(*paper,255))
review.alpha_composite(rim)
lx,ly,rx,ry=perimeter.getbbox()
preview_path=out/f"mickey-mounted-sticker-{label}.png"
review.crop((lx-35,ly-35,rx+35,ry+35)).convert("RGB").save(preview_path)
flat_ink=ink.rotate(-angle,bicubic,center=center).crop((pad,pad,pad+1024,pad+1024))
fl=color_base(inner,navy)
fl.alpha_composite(clip(flat_ink,inner))
fl.putalpha(inner)
flat_path=out/f"mickey-flat-sticker-{label}-lithography.png"
fl.save(flat_path)
assert np.array_equal(np.asarray(Image.open(flat_path).getchannel("A")),np.asarray(inner))
files=(raw_path,inner_path,outer_path,preview_path,flat_path,out/"sticker-reference.png")
report={"scale":round(float(scale),3),"relative_max_scale":round(float(scale/max_scale),3),
        "mounted_rim_degrees":angle,"minimum_perimeter_clearance_px":float(distance[a>100].min()),
        "sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in files}}
(out/f"verification-{label}.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
