from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

out=Path(__file__).resolve().parent
source=Image.open(out/"selected-broom-clean-lines.png").convert("RGBA")
rgba=np.asarray(source).copy()
rgb=rgba[:,:,:3].astype(float)
r,g,b=np.moveaxis(rgb,-1,0)
luma=.22*r+.69*g+.09*b
# Use the Mickey glove's brown internal ink and antique-gold edge colors.
warm_ink=np.array([98,68,34])
brown_coverage=np.clip((86-luma)/41,0,1)
brown_coverage=ndimage.gaussian_filter(brown_coverage,.8)
color=rgb+brown_coverage[:,:,None]*(warm_ink-rgb)
opaque=rgba[:,:,3]>127
dist=ndimage.distance_transform_edt(opaque)-ndimage.distance_transform_edt(~opaque)
distance=ndimage.gaussian_filter(dist,1.3)
gold=np.array([166,118,57])
# A two-pixel band at source resolution becomes a narrow outline on each mounted broom.
gold_coverage=np.clip((3.50-distance)/2.5,0,1)*.93
color+=gold_coverage[:,:,None]*(gold-color)
rgba[:,:,:3]=np.rint(np.clip(color,0,255)).astype(np.uint8)
result=Image.fromarray(rgba)
assert np.array_equal(np.asarray(result.getchannel("A")),np.asarray(source.getchannel("A")))
result.save(out/"selected-broom-mickey-linework.png")
