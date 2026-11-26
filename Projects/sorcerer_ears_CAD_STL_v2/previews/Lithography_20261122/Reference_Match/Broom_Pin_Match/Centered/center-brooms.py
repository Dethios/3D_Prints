from hashlib import sha256
from pathlib import Path
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

out = Path(__file__).resolve().parent
source = out.parent / "broom-comfy-cutout.png"
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
art = Image.open(source).convert("RGBA").rotate(9, Image.Resampling.BICUBIC, expand=True)
art = art.crop(art.getbbox())


def options(heights, x_positions, y_positions):
    results = []
    for h in heights:
        sprite = art.resize((round(art.width*h/art.height),h), Image.Resampling.LANCZOS)
        w = sprite.width
        silhouette = np.asarray(sprite.getchannel("A")) > 100
        ys, xs = np.where(silhouette)
        feet = ys > .80*h
        sy, sx, foot = ys[::11], xs[::11], feet[::11]
        for x in x_positions:
            for y in y_positions:
                if y + h > mask.shape[0] or x + w > mask.shape[1]:
                    continue
                inside = mask[y+sy, x+sx]
                lost = 1 - inside.mean()
                if not .001 <= lost <= .105 or (1-inside[~foot].mean()) > .025:
                    continue
                ey, ex = sy[foot]+y, sx[foot]+x
                hits = foot_edge[ey, ex] & (ex >= 330) & (ex <= 918)
                if not hits.any():
                    continue
                limits = np.array([x+sx[inside].min(), y+sy[inside].min(),
                                   x+sx[inside].max(), y+sy[inside].max()])
                results.append((x,y,h,sprite,silhouette,limits,lost))
    return results


lower = options((505,525,545,565), range(140,356,5), range(285,471,5))
upper = options((535,555,575,595), range(405,606,5), range(95,295,5))
print("before",len(lower),len(upper),flush=True)
assert lower and upper
print("candidates",len(lower),len(upper),flush=True)


def rate(a, b):
    edges = np.r_[np.minimum(a[5][:2],b[5][:2]), np.maximum(a[5][2:],b[5][2:])]
    center = (edges[:2] + edges[2:])/2
    return (abs(center[0]-frame_center[0])*1.5 + abs(center[1]-frame_center[1])*0.35
            - (a[2]+b[2])*0.34 + (a[6]+b[6])*165
            + abs(a[2]/422 - b[2]/460)*70)


def separated(a, b):
    ax,ay,_,_,aa,_,_ = a
    bx,by,_,_,bb,_,_ = b
    x0,x1=max(ax,bx),min(ax+aa.shape[1],bx+bb.shape[1])
    y0,y1=max(ay,by),min(ay+aa.shape[0],by+bb.shape[0])
    if x1 <= x0 or y1 <= y0:
        return True
    region = aa[y0-ay:y1-ay,x0-ax:x1-ax]
    second = bb[y0-by:y1-by,x0-bx:x1-bx]
    return not (ndimage.binary_dilation(region,iterations=12) & second).any()


pool = sorted((rate(a,b),i,j) for i,a in enumerate(lower) for j,b in enumerate(upper))
_, i, j = next(entry for entry in pool if separated(lower[entry[1]], upper[entry[2]]))
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
    assert np.count_nonzero((x_foot+x >= 330) & (y_foot > .80*h)) > 8
    details.append({"height_px":h,"height_increase_percent":round((h/previous_height-1)*100,1),
                    "visible_bounds_preview_px":[int(x+xx.min()),int(y+yy.min()),int(x+xx.max()),int(y+yy.max())],
                    "cropped_percent":round(100*cut.sum()/opacity.sum(),2)})
    scene.alpha_composite(sprite,(vx+x,vy+y))

scene = clip(scene,opening)
stars, kept = stars_on_mount([],scene,dots("brooms", PRE.parent/"brooms-artwork-transparent.png")[2:],np.asarray(opening)>136)
scene.alpha_composite(stars)
assert kept >= 6
field = solid_canvas(opening,navy)
field.alpha_composite(scene)
frame = solid_canvas(outer,gold)
frame.alpha_composite(field)
mounted = Image.new("RGBA",size,(*paper,255))
mounted.alpha_composite(frame)
preview_path = out/"brooms-mounted-centered.png"
mounted.crop(view).convert("RGB").save(preview_path)
f = scene.rotate(-angle,Image.Resampling.BICUBIC,center=(C,C)).crop((pad,pad,pad+T,pad+T))
f = clip(f,source_inner)
flat = solid_canvas(source_inner,navy)
flat.alpha_composite(f)
flat.putalpha(source_inner)
flat_path = out/"brooms-flat-centered-lithography.png"
flat.save(flat_path)
assert np.array_equal(np.asarray(Image.open(flat_path).getchannel("A")),np.asarray(source_inner))
report={"mounted_rim_degrees":angle,"source_pose_deskew_degrees":9,"brooms":details,"stars":kept,
        "sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in (source,preview_path,flat_path)}}
(out/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
