from hashlib import sha256
from pathlib import Path
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import fftconvolve

out = Path(__file__).resolve().parent
source = Path(sys.argv[1]).resolve()
deskew = float(sys.argv[2])
tag = sys.argv[3]
os.environ["NX3_MOUNTED_OUT"] = str(out.parent)
reference = out.parent.parent / "Mounted" / "build-mounted-match.py"
exec(reference.read_text(encoding="utf-8-sig").split("\nmounted={}", 1)[0])

angle = ANGLES["brooms"]
opening, outer = rotate_mask(source_inner, angle), rotate_mask(source_outer, angle)
x0, y0, x1, y1 = outer.getbbox()
view = (x0 - 35, y0 - 35, x1 + 35, y1 + 35)
vx, vy = view[:2]
mask = np.asarray(opening.crop(view)) > 136
frame_y, frame_x = np.where(mask)
frame_center = np.array([(frame_x.min()+frame_x.max())/2, (frame_y.min()+frame_y.max())/2])
foot_edge = ndimage.binary_dilation(mask, iterations=2) & ~mask
art = Image.open(source).convert("RGBA").rotate(deskew, Image.Resampling.BICUBIC, expand=True)
art = art.crop(art.getbbox())


def options(heights, x_positions, y_positions):
    results = []
    for h in heights:
        sprite = art.resize((round(art.width*h/art.height),h), Image.Resampling.LANCZOS)
        w = sprite.width
        silhouette = np.asarray(sprite.getchannel("A")) > 100
        ys, xs = np.where(silhouette)
        color = np.asarray(sprite)[ys,xs,:3].astype(np.int16)
        feet = (ys > .70*h) & (color[:,0]>125) & (color[:,1]>93) & (color[:,0]-color[:,1]<93) & (color[:,2]<147)
        sy, sx, foot = ys[::11], xs[::11], feet[::11]
        for x in x_positions:
            for y in y_positions:
                if y + h > mask.shape[0] or x + w > mask.shape[1]:
                    continue
                inside = mask[y+sy, x+sx]
                lost = 1 - inside.mean()
                if not .001 <= lost <= .155 or (1-inside[~foot].mean()) > .006:
                    continue
                ey, ex = sy[foot]+y, sx[foot]+x
                hits = foot_edge[ey, ex] & (ex >= 330) & (ex <= 918)
                if not hits.any():
                    continue
                limits = np.array([x+sx[inside].min(), y+sy[inside].min(),
                                   x+sx[inside].max(), y+sy[inside].max()])
                results.append((x,y,h,sprite,silhouette,limits,lost))
    return results


lower = options((405,425,445,465,485,505,525,545,565), range(110,356,6), range(285,541,7))
upper = options((425,445,465,485,505,525,545,565,585), range(392,606,6), range(95,351,7))
print("before",len(lower),len(upper),flush=True)
assert lower and upper
print("candidates",len(lower),len(upper),flush=True)


collision_maps = {}


def separated(a, b):
    ax,ay,ah,_,aa,_,_ = a
    bx,by,bh,_,bb,_,_ = b
    key = (ah,bh)
    if key not in collision_maps:
        expanded = np.pad(aa,12)
        expanded = ndimage.binary_dilation(expanded,iterations=12)
        overlap = fftconvolve(expanded.astype(np.float32),bb[::-1,::-1].astype(np.float32))
        collision_maps[key] = overlap > .5
    overlap = collision_maps[key]
    i,j = by-ay+12+bb.shape[0]-1,bx-ax+12+bb.shape[1]-1
    return not (0 <= i < overlap.shape[0] and 0 <= j < overlap.shape[1] and overlap[i,j])

left_bounds = np.array([a[5] for a in lower])
right_bounds = np.array([b[5] for b in upper])
lo = np.minimum(left_bounds[:,None,:2],right_bounds[None,:,:2])
hi = np.maximum(left_bounds[:,None,2:],right_bounds[None,:,2:])
mid = (lo+hi)/2
lh = np.array([a[2] for a in lower])[:,None]
rh = np.array([b[2] for b in upper])[None,:]
cuts = np.array([a[6] for a in lower])[:,None] + np.array([b[6] for b in upper])[None,:]
cost = (abs(mid[:,:,0]-frame_center[0])*1.5 + abs(mid[:,:,1]-frame_center[1])*.35
        - (lh+rh)*.34 + cuts*245 + abs(lh/422-rh/460)*70)
for index in np.argsort(cost,axis=None):
    i,j = divmod(index,len(upper))
    if separated(lower[i],upper[j]):
        break
else:
    raise RuntimeError("No pair can fit without overlap")
choices = (lower[i],upper[j])
scene = Image.new("RGBA",size)
details = []
visible_bounds = []
for (x,y,h,sprite,opacity,_,_), previous_height in zip(choices,(422,460)):
    local = mask[y:y+h,x:x+sprite.width]
    visible = opacity & local
    yy,xx = np.where(visible)
    cut = opacity & ~local
    y_foot, x_foot = np.where(opacity & foot_edge[y:y+h,x:x+sprite.width])
    assert np.count_nonzero((x_foot+x >= 330) & (y_foot > .70*h)) > 8
    details.append({"height_px":h,"height_increase_percent":round((h/previous_height-1)*100,1),
                    "visible_bounds_preview_px":[int(x+xx.min()),int(y+yy.min()),int(x+xx.max()),int(y+yy.max())],
                    "cropped_percent":round(100*cut.sum()/opacity.sum(),2)})
    scene.alpha_composite(sprite,(vx+x,vy+y))

scene = clip(scene,opening)
stars, kept = stars_on_mount([],scene,dots("brooms", PRE.parent/"brooms-artwork-transparent.png")[2:],np.asarray(opening)>136)
scene.alpha_composite(stars)
assert kept >= 5
field = solid_canvas(opening,navy)
field.alpha_composite(scene)
frame = solid_canvas(outer,gold)
frame.alpha_composite(field)
mounted = Image.new("RGBA",size,(*paper,255))
mounted.alpha_composite(frame)
preview_path = out/f"brooms-mounted-{tag}.png"
mounted.crop(view).convert("RGB").save(preview_path)
f = scene.rotate(-angle,Image.Resampling.BICUBIC,center=(C,C)).crop((pad,pad,pad+T,pad+T))
f = clip(f,source_inner)
flat = solid_canvas(source_inner,navy)
flat.alpha_composite(f)
flat.putalpha(source_inner)
flat_path = out/f"brooms-flat-{tag}-lithography.png"
flat.save(flat_path)
assert np.array_equal(np.asarray(Image.open(flat_path).getchannel("A")),np.asarray(source_inner))
report={"mounted_rim_degrees":angle,"source_pose_deskew_degrees":deskew,"brooms":details,"stars":kept,
        "sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in (source,preview_path,flat_path)}}
(out/f"verification-{tag}.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
