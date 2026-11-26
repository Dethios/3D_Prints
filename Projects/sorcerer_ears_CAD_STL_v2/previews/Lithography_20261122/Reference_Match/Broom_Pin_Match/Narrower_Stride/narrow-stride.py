from pathlib import Path
from PIL import Image
import numpy as np
from scipy import ndimage
from scipy.interpolate import PchipInterpolator

out = Path(__file__).resolve().parent
base = Image.open(out.parent/"broom-comfy-cutout.png").convert("RGBA")
original = np.asarray(base)
y, x = np.indices(original.shape[:2], dtype=float)

def smoothstep(q):
    t = np.clip(q,0,1)
    return t*t*(3-2*t)

dx = x - 269
window = smoothstep((y-462)/56) * (1-smoothstep((y-591)/39))
inverse = PchipInterpolator([0,124,176,232,269,306,348,382,454],
                            [0,124,166,209,269,329,369,382,454])
sx = x + (inverse(x)-x)*window
local_y = 1-smoothstep(abs(dx)/98)
vertical = smoothstep((y-462)/83) * (1-smoothstep((y-564)/66))
sy = y - 22*vertical*local_y
sample = (sy,sx)
opacity = original[:,:,3].astype(float)/255
image = np.empty_like(original)
warped_alpha = ndimage.map_coordinates(opacity,sample,order=1,mode="constant")
for i in range(3):
    premultiplied = ndimage.map_coordinates(original[:,:,i]*opacity,sample,order=1,mode="constant")
    image[:,:,i] = np.clip(np.rint(premultiplied/np.maximum(warped_alpha,1e-8)),0,255).astype(np.uint8)
image[:,:,3] = np.rint(warped_alpha*255)
unchanged = (abs(sx-x)<1e-8) & (abs(sy-y)<1e-8)
image[unchanged] = original[unchanged]
assert np.array_equal(image[:459],original[:459])
target = Image.fromarray(image)
target.save(out/"broom-narrower-stride.png")
proof = Image.new("RGBA",(980,700),(35,62,114,255))
proof.alpha_composite(base,(20,20))
proof.alpha_composite(target,(502,20))
proof.convert("RGB").save(out/"broom-stride-comparison.png")
for row in (523,540,550,560):
    report=[]
    for candidate in (original,image):
        on=np.flatnonzero(candidate[row,:,3]>127)
        gaps = np.diff(on)
        report.append(int(gaps.max()-1))
    print(row,report)
