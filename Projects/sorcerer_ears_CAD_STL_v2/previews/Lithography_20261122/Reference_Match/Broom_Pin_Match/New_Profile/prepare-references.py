from pathlib import Path
from PIL import Image
import numpy as np
from scipy import ndimage
import os

out=Path(os.environ["SORCERER_LITHO_OUTPUT"])
page=Image.open(out/"new-reference.png").convert("RGB")
print(page.size, flush=True)
im=page.crop((358,28,576,266))
a=np.asarray(im).astype(float)
reference=np.median(a[:4,:4],axis=(0,1))
d=np.linalg.norm(a-reference,axis=2)
alpha=np.clip((d-8)/65,0,1)
labels,_=ndimage.label(alpha>.09)
areas=np.bincount(labels.ravel())
areas[0]=0
alpha[(areas[labels]<18) & (alpha>.09)]=0
alpha[alpha<.09]=0
sprite=im.convert("RGBA")
sprite.putalpha(Image.fromarray(np.rint(alpha*255).astype(np.uint8)))
sprite=sprite.crop(sprite.getbbox())
sprite.save(out/"reference-profile-cutout.png")
size=896
height=639
resized=sprite.resize((round(sprite.width*height/sprite.height),height),Image.Resampling.LANCZOS)
guide=Image.new("RGBA",(size,size),(20,47,91,255))
guide.alpha_composite(resized,((size-resized.width)//2,(size-height)//2))
guide.convert("RGB").save(out/"new-profile-guide.png")
page.crop((16,14,297,335)).save(out/"new-pin-finish-reference.png")
