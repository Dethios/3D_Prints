from pathlib import Path
import json
from hashlib import sha256

import numpy as np
from PIL import Image

out = Path(__file__).resolve().parent
base = out.parent
rev = base / "Mickey_Gloves_Clean"
mounted_path = rev / "mickey-mounted-smooth-gloves.png"
flat_path = rev / "mickey-flat-smooth-gloves-lithography.png"
art = Image.open(mounted_path).convert("RGBA")
flat = Image.open(flat_path).convert("RGBA")
inner = Image.open(base/"ear-interior-alpha.png").convert("L")
outer = Image.open(base/"ear-outer-alpha.png").convert("L")
padded_size, pad, center = (1248,1248),112,(624,624)
bicubic = Image.Resampling.BICUBIC

# Extend the existing wrist edges behind the cuff.
# The cuff's white fill and its brown boundary stay in front.
before = np.asarray(art).copy()
after = before.copy()
x0,y0,x1,y1 = (666,292,711,331)
old = before[y0:y1,x0:x1,:3].astype(float)
y,x = np.mgrid[y0:y1,x0:x1].astype(float)
left = 670.4 + (330-y)*.27
right = 701.6 + (330-y)*.27
distance = np.minimum(x-left,right-x)
coverage = np.clip(distance+.58,0,1) * np.clip((331-y)/5,0,1)
r,g,b = np.moveaxis(old,-1,0)
navy = (b>65) & (b>r+16) & (g>r+5)
black = (r<40) & (g<34) & (b<48)
dark_inside = (distance>4.5) & (r<80) & (g<68) & (b<60)
coverage *= navy | black | dark_inside
brown = np.array([141,104,40])
sleeve_black = np.array([9,7,9])
stroke = np.clip((1.80-distance)/.8,0,1)
match = sleeve_black + stroke[:,:,None]*(brown-sleeve_black)
after[y0:y1,x0:x1,:3] = np.rint(old+(match-old)*coverage[:,:,None]).astype(np.uint8)
changed = np.any(before!=after,axis=2)
assert 100 < changed.sum() < 1000
patch = Image.fromarray(after)
mounted_output = out/"mickey-mounted-connected-wrist.png"
patch.convert("RGB").save(mounted_output)

perimeter = Image.new("L",padded_size)
perimeter.paste(outer,(pad,pad))
bounds = perimeter.rotate(-40,bicubic,center=center).getbbox()
origin = tuple(v-35 for v in bounds[:2])
patch.putalpha(Image.fromarray(changed.astype(np.uint8)*255))
padded = Image.new("RGBA",padded_size)
padded.paste(patch,origin)
overlay = padded.rotate(40,bicubic,center=center).crop((pad,pad,pad+1024,pad+1024))
alpha=np.asarray(overlay.getchannel("A")).copy()
alpha[np.asarray(inner)<255]=0
overlay.putalpha(Image.fromarray(alpha))
result = Image.alpha_composite(flat,overlay)
flat_output = out/"mickey-flat-connected-wrist-lithography.png"
result.save(flat_output)
saved=np.asarray(Image.open(flat_output))
assert np.array_equal(saved[:,:,3],np.asarray(inner))
assert np.array_equal(saved[alpha==0],np.asarray(flat)[alpha==0])
Image.fromarray(changed).save(out/"wrist-edit-mask.png")
a=Image.open(mounted_output).crop((658,279,724,346))
a.resize((396,402),Image.Resampling.LANCZOS).save(out/"wrist-detail.png")
record={"changed_mounted_pixels":int(changed.sum()),"flat_alpha_matches_cad_opening":True,
        "sha256":{path.name:sha256(path.read_bytes()).hexdigest() for path in (mounted_path,flat_path,mounted_output,flat_output)}}
(out/"verification.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record,indent=2))
