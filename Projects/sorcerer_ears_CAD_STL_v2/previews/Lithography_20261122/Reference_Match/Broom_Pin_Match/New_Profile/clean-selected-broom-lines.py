from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image

out = Path(__file__).resolve().parent
source = Image.open(out/"reference-profile-cutout.png").convert("RGBA")
pixels = np.asarray(source).astype(float)
alpha = pixels[:,:,3]/255
solid = alpha > .63
levels, _ = ndimage.label(solid)
counts = np.bincount(levels.ravel())
counts[0] = 0
solid &= counts[levels] >= 3

# Remove the white screenshot matte from the edge colors.
interior = ndimage.distance_transform_edt(solid)
rgb_channels = pixels[:,:,:3]
white_matte = (rgb_channels.min(axis=2)>181) & (np.ptp(rgb_channels,axis=2)<29) & (interior<2.5)
_, nearest = ndimage.distance_transform_edt(~(solid & ~white_matte),return_indices=True)
rgb = rgb_channels[tuple(nearest)]
distance = interior - ndimage.distance_transform_edt(~solid)
# Interpolate a signed-distance field to smooth the contour while keeping the exact pose.
sd = ndimage.zoom(ndimage.gaussian_filter(distance,.73),4,order=3,grid_mode=True,mode="nearest")
new_alpha = np.clip((sd+.32)/.55,0,1)
colors = np.stack([ndimage.zoom(ndimage.gaussian_filter(rgb[:,:,c],.46),4,order=3,
                               grid_mode=True,mode="nearest") for c in range(3)],axis=2)
soft = ndimage.gaussian_filter(colors,(2.0,2.0,0.))
colors = np.clip(colors+.60*(colors-soft),0,255)
# Follow the original silhouette with a thin dark edge to unify pixelated contour fragments.
outline = np.clip((.98-sd)/.82,0,1)*.94
edge_ink = np.array([36,28,24])
colors = colors + outline[:,:,None]*(edge_ink-colors)
rgba = np.dstack([np.rint(colors),np.rint(new_alpha*255)]).astype(np.uint8)
clean = Image.fromarray(rgba)
clean.save(out/"selected-broom-clean-lines.png")
board = Image.new("RGBA",(970,610),(20,47,91,255))
for image,x in ((source,32),(clean,505)):
    render = image.resize((430,504),Image.Resampling.LANCZOS)
    board.alpha_composite(render,(x,53))
board.convert("RGB").save(out/"broom-line-cleanup-comparison.png")
before = source.getchannel("A").point(lambda x: 255 if x>127 else 0)
after = clean.getchannel("A").resize(source.size,Image.Resampling.LANCZOS).point(lambda x: 255 if x>127 else 0)
a,b = np.asarray(before)>0,np.asarray(after)>0
print("outline overlap",round(np.sum(a&b)/np.sum(a|b),4))
