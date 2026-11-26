import json
from hashlib import sha256
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

out=Path(__file__).resolve().parent
base=out.parent.parent
source_path=out.parent/"mickey-sticker-isolated-star-clearance.png"
art=Image.open(source_path).convert("RGBA")
inner,outer=[Image.open(base/n).convert("L") for n in ("ear-interior-alpha.png","ear-outer-alpha.png")]
canvas,pad,center=(1248,1248),112,(624,624)
mounted_angle=-40
bicubic=Image.Resampling.BICUBIC
navy,gold,paper=(28,51,99),(218,173,85),(249,239,222)

def mount(mask):
    image=Image.new("L",canvas)
    image.paste(mask,(pad,pad))
    return image.rotate(mounted_angle,bicubic,center=center)


def fill(mask,color):
    layer=Image.new("RGBA",mask.size,(*color,0))
    layer.putalpha(mask)
    return layer


def clip(layer,mask):
    rgb=layer.copy()
    a=np.asarray(layer.getchannel("A")).astype(np.uint16)
    b=np.asarray(mask).astype(np.uint16)
    rgb.putalpha(Image.fromarray(((a*b+127)//255).astype(np.uint8)))
    return rgb


opening,perimeter=mount(inner),mount(outer)
x0,y0,x1,y1=perimeter.getbbox()
view=x0-35,y0-35,x1+35,y1+35
inside=np.asarray(opening.crop(view))>127
clear=ndimage.distance_transform_edt(inside)
distance=clear-ndimage.distance_transform_edt(~inside)
r,g,b,alpha=np.moveaxis(np.asarray(art).astype(np.int16),-1,0)
mask=alpha>110
Y,X=np.indices(alpha.shape)
labels,_=ndimage.label(mask)
areas=np.bincount(labels.ravel())
main_label=areas[1:].argmax()+1
stars=np.flatnonzero((areas>=150)&(areas<=600))
stars=stars[stars!=0]
assert len(stars)==10
main=labels==main_label
shoe_colors=(r>151)&(g>103)&(r-g<98)&(g-b>16)&(b<170)
rear=main&shoe_colors&(X>177)&(X<318)&(Y>590)&(Y<666)
front=main&shoe_colors&(X>324)&(X<481)&(Y>574)
assert rear.sum()>1800 and front.sum()>2800
allowed_crop=(X<329)&(Y>499)


def points(mask,stride=1):
    y,x=np.where(mask)
    return np.column_stack((x,y))[::stride]


edge=main&~ndimage.binary_erosion(main,iterations=2)
protected=points(edge&~allowed_crop,5)
outline=points(edge,5)
rear_xy=points(rear,7)
front_xy=points(front,9)
star_xy=[points(labels==i,5) for i in stars]
candidates=[]
for scale in np.arange(.865,1.031,.012):
    features=[np.rint(p*scale).astype(int) for p in (protected,outline,rear_xy,front_xy,*star_xy)]
    hard,whole,back,fore,*twinkles=features
    for x in range(155,286,5):
        for y in range(126,251,4):
            shift=np.array([x,y])
            if np.any(hard+shift<0) or np.any(whole+shift>=inside.shape[0]):
                continue
            def depth(v):
                z=v+shift
                return distance[z[:,1],z[:,0]]
            if depth(hard).min()<5 or depth(fore).min()<7:
                continue
            shoe_depth=depth(back)
            cut=(shoe_depth<0).mean()
            if not .006<cut<.21:
                continue
            crop=(depth(whole)<0).mean()
            if crop>.205:
                continue
            moved=[max(0.,8-depth(star).min()) for star in twinkles]
            if sum(v>0 for v in moved)>2 or max(moved)>177:
                continue
            # Keep emphasis on the body rather than the midpoints of the long spiral.
            body_x=x+scale*335
            cost=(1.025-scale)*205 + abs(body_x-525)*.40 + 70*crop + 47*cut + .25*sum(moved)
            candidates.append((cost,scale,x,y,float(cut),float(crop)))
assert candidates,"No enlarged fit met the rear-shoe contact criteria"
_,scale,x,y,rough_shoe_crop,_=min(candidates)
print("placement",x,y,scale,rough_shoe_crop,flush=True)

# Isolate only the separate stars that need new positions after the composition is lowered.
sprite_pixels=np.asarray(art).copy()
ink_pixels=sprite_pixels.copy()
star_layers=[]
for index, star in enumerate(stars):
    component=labels==star
    yy,xx=np.where(component)
    foreground=ndimage.binary_dilation(component,iterations=2)&(alpha>0)&~main
    xx1,yy1=round(x+xx.mean()*scale),round(y+yy.mean()*scale)
    stamp=Image.fromarray(np.where(foreground[:,:,None],sprite_pixels,0).astype(np.uint8))
    stamp=stamp.resize((round(art.width*scale),round(art.height*scale)),Image.Resampling.LANCZOS)
    raster=np.asarray(stamp.getchannel("A"))>100
    oy,ox=np.where(raster)
    ink_pixels[foreground]=0
    star_layers.append((index,stamp,np.column_stack((ox,oy)),(xx1,yy1)))

ink=Image.fromarray(ink_pixels).resize((round(art.width*scale),round(art.height*scale)),Image.Resampling.LANCZOS)
scene=Image.new("RGBA",inside.shape[::-1])
scene.alpha_composite(ink,(x,y))
occupied=np.asarray(scene.getchannel("A"))>100
star_moves=[]
offsets=sorted((dx*dx+dy*dy,dx,dy) for dy in range(-165,166,3) for dx in range(-150,151,3))
# Prioritize stars that already fit, preserving the original relative placement wherever possible.
for index, star, coordinates, loc in sorted(star_layers,key=lambda v:clear[v[3][1],v[3][0]],reverse=True):
    free=ndimage.distance_transform_edt(~occupied)
    ranked = offsets
    if loc[1] > 690 and clear[loc[1],loc[0]] == 0:
        preferred = np.array([249, 590]) - loc
        ranked = sorted(offsets, key=lambda v:(v[1]-preferred[0])**2 + (v[2]-preferred[1])**2)
    for _,dx,dy in ranked:
        locs=coordinates+[x+dx,y+dy]
        xx,yy=locs.T
        if np.any(locs<0) or np.any(locs>=inside.shape[0]):
            continue
        gap=7 if dx==dy==0 else 10
        if clear[yy,xx].min()<gap or free[yy,xx].min()<(2 if dx==dy==0 else 9):
            continue
        scene.alpha_composite(star,(x+dx,y+dy))
        occupied[yy,xx]=True
        if (dx,dy)!=(0,0):
            star_moves.append({"source_star":index+1,"mounted_shift_px":[dx,dy]})
        break
    else:
        raise RuntimeError("Could not place a sticker twinkle inside the opening")

w,h=ink.size
shoe_alpha=Image.fromarray((rear*255).astype(np.uint8)).resize((w,h),Image.Resampling.BILINEAR)
shoe_native=np.asarray(shoe_alpha)>127
shoe_inside=inside[y:y+h,x:x+w]
contact=int((shoe_native&(~shoe_inside)&(np.abs(distance[y:y+h,x:x+w])<=3)).sum())
assert contact>7
pct=100*(shoe_native&shoe_inside).sum()/shoe_native.sum()
assert pct>78
print("rear shoe visible percent",pct,"contact pixels",contact,"star moves",star_moves)
padded=Image.new("RGBA",canvas)
padded.alpha_composite(scene,view[:2])
mounted_ink=clip(padded,opening)
field=fill(opening,navy)
field.alpha_composite(mounted_ink)
rim=fill(perimeter,gold)
rim.alpha_composite(field)
review=Image.new("RGBA",canvas,(*paper,255))
review.alpha_composite(rim)
mounted_path=out/"mickey-mounted-sticker-larger.png"
review.crop(view).convert("RGB").save(mounted_path)
flat_ink=mounted_ink.rotate(-mounted_angle,bicubic,center=center).crop((pad,pad,pad+1024,pad+1024))
flat=fill(inner,navy)
flat.alpha_composite(clip(flat_ink,inner))
flat.putalpha(inner)
flat_path=out/"mickey-flat-sticker-larger-lithography.png"
flat.save(flat_path)
assert np.array_equal(np.asarray(Image.open(flat_path).getchannel("A")),np.asarray(inner))
meta={"scale":round(float(scale),3),"scale_change_percent":round((scale/.739-1)*100,1),
      "position_mounted_px":[x,y],"rear_shoe_visible_percent":round(float(pct),1),
      "rear_shoe_contact_sample_pixels":contact,"stars_visible":len(stars),"relocated_stars":star_moves,
      "sha256":{file.name:sha256(file.read_bytes()).hexdigest() for file in (source_path,mounted_path,flat_path)}}
(out/"verification.json").write_text(json.dumps(meta,indent=2)+"\n")
