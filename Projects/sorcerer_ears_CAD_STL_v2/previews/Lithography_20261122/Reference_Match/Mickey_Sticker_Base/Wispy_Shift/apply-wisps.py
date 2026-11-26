from pathlib import Path
from hashlib import sha256
import json

import numpy as np
from scipy import ndimage
from PIL import Image

out=Path(__file__).resolve().parent
source=out.parent/"mickey-sticker-isolated-star-clearance.png"
original=Image.open(source).convert("RGBA")
raw=np.asarray(original).copy()
ox,oy=222,168
box=(ox,oy,ox+original.width,oy+original.height)
deleted=np.asarray(Image.open(out/"magic-source-matte.png").crop(box))>0
original_magic=np.asarray(Image.open(out/"magic-source-core.png").crop(box))>0
hands=np.asarray(Image.open(out/"glove-protection-matte.png").crop(box))>0

labels,_=ndimage.label(raw[:,:,3]>110)
area=np.bincount(labels.ravel())
star_ids=np.flatnonzero((area>=150)&(area<=600))
star_ids=star_ids[star_ids!=0]
assert len(star_ids)==10
star_pixels=np.isin(labels,star_ids)
deleted &= ~ndimage.binary_dilation(star_pixels,iterations=3)
removed=raw.copy()
removed[deleted]=0
original_remaining=removed[:,:,3]>70

donor_path=out/"qwen-wisps-registered.png"
rgb=np.asarray(Image.open(donor_path).convert("RGB").crop(box)).astype(float)
r,g,b=np.moveaxis(rgb,-1,0)
h,w=original_magic.shape
y,x=np.indices((h,w))
near = ndimage.distance_transform_edt(~original_magic) <= 25
pale=(r>28)&(r-g<34)&(g-b<22)&(b-r<64)&(b>81)
coverage=np.clip((r-25)/145,0,1)*pale
# The new tendrils may run outside the old ribbon by a few pixels. They
# must stay behind the original exact character, gloves and ten stars.
star_keepout=ndimage.binary_dilation(star_pixels,iterations=4)
donor_bright=(r>159)&(g>146)&(b>133)
l,_=ndimage.label(donor_bright)
nc=np.bincount(l.ravel());nc[0]=0
star_locs=[(np.mean(np.where(labels==i)[1]),np.mean(np.where(labels==i)[0])) for i in star_ids]
star_locs.append((24,661))
for xx,yy in star_locs:
    border=(x-xx)**2+(y-yy)**2<15**2
    choice=np.unique(l[border])
    isolated=choice[(nc[choice]>=20)&(nc[choice]<700)]
    star_keepout |= ndimage.binary_dilation(np.isin(l,isolated),iterations=3)
donor_hand_edge = ((x+ox>705)&(x+ox<745)&(y+oy>272)&(y+oy<335))
donor_hand_edge |= ((x+ox>608)&(x+ox<714)&(y+oy>233)&(y+oy<347)&(y+oy>390-.215*(x+ox)))
safe = near & ~hands & ~original_remaining & ~star_keepout & ~donor_hand_edge
coverage*=safe
cc,_=ndimage.label(coverage>.085)
sizes=np.bincount(cc.ravel());sizes[0]=0
supported=ndimage.binary_dilation(sizes[cc]>46,iterations=2)
coverage=ndimage.gaussian_filter(coverage*supported,.88)
coverage[coverage<.055]=0
coverage[~safe]=0
top_falloff = np.clip(y/8,0,1)
coverage *= top_falloff*top_falloff*(3-2*top_falloff)
shaded=np.clip((r-38)/190,0,1)
color=np.rint(np.array([232,224,222]) + shaded[:,:,None]*np.array([19,16,8])).astype(np.uint8)
wisps=Image.fromarray(np.dstack((color,np.rint(coverage*255).astype(np.uint8))))
wisps.alpha_composite(Image.fromarray(removed))
target=out/"isolated-sticker-wispy.png"
wisps.save(target)
updated=np.asarray(wisps)
assert np.array_equal(updated[original_remaining],raw[original_remaining])
count=int((coverage>.40).sum())
assert 2500<count<44000
proof=Image.new("RGBA",original.size,(28,51,99,255))
proof.alpha_composite(wisps)
proof.convert("RGB").save(out/"isolated-wispy-proof.png")
record={"strong_donor_wisp_pixels":count,"removed_original_ribbon_pixels":int(deleted.sum()),
        "reference_crop_origin":[ox,oy],"shaft_and_figure_preserved":True,
        "sha256":{file.name:sha256(file.read_bytes()).hexdigest() for file in (source,donor_path,target)}}
(out/"swirl-composite-proof.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record,indent=2))
