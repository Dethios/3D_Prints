from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

out=Path(__file__).resolve().parent
base=out.parent.parent
previous=out.parent/"Wispy_Shift"
mounted_path=previous/"mickey-mounted-sticker-wispy-shift.png"
flat_path=previous/"mickey-flat-sticker-wispy-shift-lithography.png"
mounted=Image.open(mounted_path).convert("RGBA")
flat=Image.open(flat_path).convert("RGBA")
outer,inner=[Image.open(base/n).convert("L") for n in ("ear-outer-alpha.png","ear-interior-alpha.png")]
canvas,pad,center,angle=(1248,1248),112,(624,624),-40
bicubic=Image.Resampling.BICUBIC

def mask_to_mount(mask):
    full=Image.new("L",canvas)
    full.paste(mask,(pad,pad))
    return full.rotate(angle,bicubic,center=center)

origin=tuple(v-35 for v in mask_to_mount(outer).getbbox()[:2])
opening=np.asarray(mask_to_mount(inner).crop((*origin,origin[0]+mounted.width,origin[1]+mounted.height)))
clearance=ndimage.distance_transform_edt(opening==255)
baseline=np.asarray(mounted)
navy=np.array([28,51,99])
orig_art=(np.linalg.norm(baseline[:,:,:3].astype(float)-navy,axis=2)>14)
occupied=orig_art.copy()
gold=(227,186,112)
overlay=Image.new("RGBA",mounted.size)

# Blend a tapered thread into the existing wisp at the fingertip.
zoom=8
area=(626,205,671,256)
w,h=area[2]-area[0],area[3]-area[1]
bridge=Image.new("RGBA",(w*zoom,h*zoom))
draw=ImageDraw.Draw(bridge)
controls=np.array([[635.8,246.3],[637.2,236.8],[645.5,223.0],[657.5,213.0]])
for t in np.linspace(0,1,230):
    p=(1-t)**3*controls[0]+3*t*(1-t)**2*controls[1]+3*t*t*(1-t)*controls[2]+t**3*controls[3]
    radius=1.25 - .32*np.sin(t*np.pi) + .6*t**3
    color=tuple(np.rint(np.array([246,235,226])*(1-t)+np.array([143,152,180])*t).astype(int))
    opacity=round(236-75*np.sin(t*np.pi/2))
    q=(p-area[:2])*zoom
    rr=radius*zoom
    draw.ellipse((q[0]-rr,q[1]-rr,q[0]+rr,q[1]+rr),fill=(*color,opacity))
bridge=bridge.resize((w,h),Image.Resampling.LANCZOS)
alpha=np.asarray(bridge.getchannel("A")).copy()
# The fingertip stays in front of the new wisp.
protect=baseline[area[1]:area[3],area[0]:area[2],0]>165
alpha[protect]=0
bridge.putalpha(Image.fromarray(alpha))
overlay.alpha_composite(bridge,area[:2])
occupied |= np.asarray(overlay.getchannel("A"))>24

# The two curves and six starbursts are the exact original mesh silhouettes.
records=[]
ornaments=[
    (7,(447,198),(262,69)),
    (3,(821,445),(83,151)),
    (5,(748,432),(66,66)),
    (1,(513,266),(49,49)),
    (4,(214,325),(38,38)),
    (6,(390,135),(25,25)),
    (8,(428,233),(31,31)),
    (2,(871,528),(20,20)),
]
for ident,target,sprite_size in ornaments:
    mask_source=Image.open(out/f"outline-ornament-{ident}.png").convert("L")
    mask=np.asarray(mask_source.resize(sprite_size,Image.Resampling.LANCZOS)).copy()
    mask[mask<8]=0
    sprite=Image.new("RGBA",sprite_size,(*gold,0))
    sprite.putalpha(Image.fromarray(mask))
    ys,xs=np.where(mask>0)
    distance_to_art=ndimage.distance_transform_edt(~occupied)
    attempts=sorted((dx*dx+dy*dy,dx,dy) for dx in range(-60,61,4) for dy in range(-52,53,4))
    for _,dx,dy in attempts:
        px=target[0]+dx-sprite.width//2
        py=target[1]+dy-sprite.height//2
        X,Y=xs+px,ys+py
        if np.any(X<0) or np.any(Y<0) or np.any(X>=mounted.width) or np.any(Y>=mounted.height):
            continue
        if clearance[Y,X].min()<11 or distance_to_art[Y,X].min()<14:
            continue
        assert not orig_art[Y,X].any()
        overlay.alpha_composite(sprite,(px,py))
        occupied[Y,X]=True
        records.append({"original_mesh_component":ident,"mounted_center_px":[target[0]+dx,target[1]+dy],"size_px":sprite_size})
        break
    else:
        raise RuntimeError(f"Could not fit original ornament {ident}")

assert len(records)==8
out_mounted=out/"mickey-mounted-wispy-original-ornaments.png"
out_flat=out/"mickey-flat-wispy-original-ornaments-lithography.png"
final_mounted=Image.alpha_composite(mounted,overlay)
final_mounted.convert("RGB").save(out_mounted)
unchanged=np.asarray(overlay.getchannel("A"))==0
assert np.array_equal(np.asarray(Image.open(out_mounted).convert("RGBA"))[unchanged],baseline[unchanged])
assert np.all(opening[np.asarray(overlay.getchannel("A"))>0] == 255)
overlay.save(out/"mounted-ornament-and-bridge-layer.png")
show=Image.new("RGBA",canvas)
show.paste(overlay,origin)
patch=show.rotate(-angle,bicubic,center=center).crop((pad,pad,pad+1024,pad+1024))
a=np.asarray(patch.getchannel("A")).copy()
a[np.asarray(inner)!=255]=0
patch.putalpha(Image.fromarray(a))
Image.alpha_composite(flat,patch).save(out_flat)
readback=np.asarray(Image.open(out_flat))
assert np.array_equal(readback[:,:,3],np.asarray(inner))
assert np.array_equal(readback[a==0],np.asarray(flat)[a==0])
final_mounted.crop((598,183,724,278)).convert("RGB").resize((504,380),Image.Resampling.LANCZOS).save(out/"connected-fingertip-detail.png")
record={"exact_gold_mesh_ornaments":records,"original_art_placement_unchanged":True,
        "sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in (mounted_path,flat_path,out_mounted,out_flat,out/"original-outline-reference.png")}}
(out/"verification.json").write_text(json.dumps(record,indent=2)+"\n")
print(records)
