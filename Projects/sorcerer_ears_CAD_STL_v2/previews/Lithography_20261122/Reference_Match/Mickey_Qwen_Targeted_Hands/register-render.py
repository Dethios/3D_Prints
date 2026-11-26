from pathlib import Path
import json

import numpy as np
from PIL import Image
from scipy import ndimage, optimize

out = Path(__file__).resolve().parent
src = Image.open(out/"full-enamel-art-input.png").convert("RGB")
render = Image.open(out/"qwen-full-art-raw.png").convert("RGB")
resized = render.resize(src.size,Image.Resampling.LANCZOS)
target = np.asarray(src).astype(float)
generated = np.asarray(resized).astype(float)

def motifs(array):
    r,g,b = np.moveaxis(array,-1,0)
    return np.stack((np.clip((r-1.4*g-18)/65,0,1),
                     np.clip((b-2.3*r-75)/65,0,1),
                     np.clip((r+g-b-195)/180,0,1)),axis=2)

old = motifs(target)
new = motifs(generated)
h,w = old.shape[:2]
yc,xc = np.mgrid[315:806:3,307:767:3].astype(float)
# Lock registration to the hat, face, skirt, and belt rather than the new hands.
safe = ~((xc<469)&(yc>517)&(yc<672))
safe &= ~((xc>630)&(yc<365))
xx,yy=xc[safe],yc[safe]
reference = old[yy.astype(int),xx.astype(int)]

def loss(v):
    sx,sy,dx,dy=v
    xx1=(xx-w/2)*sx+w/2+dx
    yy1=(yy-h/2)*sy+h/2+dy
    aligned=np.stack([ndimage.map_coordinates(new[:,:,i],[yy1,xx1],order=1,
                                             mode="constant") for i in range(3)],axis=-1)
    return float(np.minimum(np.abs(aligned-reference),.55).mean())

first=optimize.minimize(loss,[1.,1.,0.,0.],method="Powell",
                        bounds=[(.93,1.07),(.93,1.07),(-40,40),(-40,40)],
                        options={"maxiter":10,"xtol":.08})
sx,sy,dx,dy=first.x
transform=(sx,0,(1-sx)*w/2+dx,0,sy,(1-sy)*h/2+dy)
registered=resized.transform(src.size,Image.Transform.AFFINE,transform,
                             Image.Resampling.BICUBIC)
registered.save(out/"qwen-full-art-registered.png")
(out/"registration.json").write_text(json.dumps({"input_resolution":list(render.size),
    "output_to_resized_affine":transform,"source_error":loss([1,1,0,0]),
    "registered_error":loss(first.x)},indent=2)+"\n")
print((sx,sy,dx,dy),loss(first.x))
