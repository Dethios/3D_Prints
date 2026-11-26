from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage,optimize

out=Path(__file__).resolve().parent
src=Image.open(out/"lower-glove-context.png").convert("RGB").resize((192,192),Image.Resampling.LANCZOS)
raw=Image.open(out/"qwen-four-digit-anatomy-corrected.png").convert("RGB")
generated=raw.resize((192,192),Image.Resampling.LANCZOS)
a=np.asarray(src).astype(float)
b=np.asarray(generated).astype(float)
h,w=a.shape[:2]
y,x=np.mgrid[:h:2,:w:2].astype(float)
frozen=(x>28)&(y>31)&(x<174)&(y<173)
frozen &= ~((x<150)&(y>115))
x,y=x[frozen],y[frozen]
truth=a[y.astype(int),x.astype(int)]

def loss(v):
    sx,sy,dx,dy=v
    X=(x-w/2)*sx+w/2+dx
    Y=(y-h/2)*sy+h/2+dy
    guess=np.stack([ndimage.map_coordinates(b[:,:,i],(Y,X),order=1,mode="nearest") for i in range(3)],axis=1)
    return np.minimum(np.abs(truth-guess),45).mean()

res=optimize.minimize(loss,[1,1,0,0],method="Powell",bounds=[(.88,1.12),(.88,1.12),(-18,18),(-18,18)],
                      options={"maxiter":16,"xtol":.07})
sx,sy,dx,dy=res.x
matrix=(sx,0,(1-sx)*w/2+dx,0,sy,(1-sy)*h/2+dy)
aligned=generated.transform((w,h),Image.Transform.AFFINE,matrix,Image.Resampling.BICUBIC)
aligned.save(out/"qwen-four-digit-registered-crop.png")
report={"raw_resolution":list(raw.size),"affine":matrix,"before_error":float(loss([1,1,0,0])),"after_error":float(res.fun)}
(out/"lower-registration.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
