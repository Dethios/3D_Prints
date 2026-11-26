from pathlib import Path
from PIL import Image
from scipy import ndimage
import numpy as np

out=Path(__file__).resolve().parent
original=Image.open(out/"mickey-sticker-qwen-isolated.png").convert("RGBA")
a=np.asarray(original).copy()
r,g,b,alpha=np.moveaxis(a,-1,0)
bright=(alpha>127)&(r>192)&(g>180)&(b>170)
labels,_=ndimage.label(bright)
subject=(labels==labels[658,29])
assert 140<subject.sum()<350
other=bright&~subject
my=ndimage.distance_transform_edt(~subject)
rest=ndimage.distance_transform_edt(~other)
star=(my<2.6)&(my<rest)
stamped=np.zeros_like(a)
stamped[star]=a[star]
a[star]=0
art=Image.fromarray(a)
art.alpha_composite(Image.fromarray(stamped),(4,7))
art.save(out/"mickey-sticker-isolated-star-clearance.png")
