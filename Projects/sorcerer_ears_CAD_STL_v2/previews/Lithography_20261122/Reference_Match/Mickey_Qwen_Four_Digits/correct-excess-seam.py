from pathlib import Path
import json

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.interpolate import CubicHermiteSpline, PchipInterpolator

out=Path(__file__).resolve().parent
raw=Image.open(out/"qwen-four-digit-raw.png").convert("RGB")
source=np.asarray(raw).astype(float)
result=source.copy()
y,x=np.indices(source.shape[:2],dtype=float)

def smoothstep(v):
    u=np.clip(v,0,1)
    return u*u*(3-2*u)

# Keep the Qwen glove and remove only the first underside separator.
# Bring the donor's own enamel colors across that line at matching height.
crease=PchipInterpolator([558,566,580,600,622,644,652],[273,275,278,285,298,315,324])
seam=crease(np.clip(y,558,652))
seam_weight=(1-smoothstep((abs(x-seam)-6)/7))*smoothstep((y-559)/7)*(1-smoothstep((y-632)/14))
seam_pixel_a=np.clip(seam-15,0,799)
seam_pixel_b=np.clip(seam+17,0,799)
left=np.stack([ndimage.map_coordinates(source[:,:,c],(y,seam_pixel_a),order=1)
               for c in range(3)],axis=-1)
right=np.stack([ndimage.map_coordinates(source[:,:,c],(y,seam_pixel_b),order=1)
                for c in range(3)],axis=-1)
seam_target=.35*left+.65*right
result+=(seam_target-result)*seam_weight[:,:,None]

# Bridge the scallop using the neighboring Qwen contour and its existing color profile.
curve=CubicHermiteSpline([289,339],[634.5,650.7],[.32,.43])
edge=curve(np.clip(x,289,339))
d=y-edge
profile_a=np.stack([ndimage.map_coordinates(source[:,:,c],(632+d,np.full_like(x,283)),order=1,mode="nearest")
                    for c in range(3)],axis=-1)
profile_b=np.stack([ndimage.map_coordinates(source[:,:,c],(651+d,np.full_like(x,340)),order=1,mode="nearest")
                    for c in range(3)],axis=-1)
mix=np.clip((x-292)/44,0,1)
profile=profile_a*(1-mix[:,:,None])+profile_b*mix[:,:,None]
outer_feather=smoothstep((x-290)/11)*(1-smoothstep((x-332)/10))
edge_weight=outer_feather*smoothstep((d+21)/12)*(1-smoothstep((d-10)/11))
result+=(profile-result)*edge_weight[:,:,None]
updated=np.rint(np.clip(result,0,255)).astype(np.uint8)
changed=np.any(updated!=source,axis=2)
assert 500<changed.sum()<4000
Image.fromarray(updated).save(out/"qwen-four-digit-anatomy-corrected.png")
Image.fromarray(changed).save(out/"excess-seam-edit-mask.png")
(out/"digit-correction.json").write_text(json.dumps({"reason":"Qwen retained three underside separation marks. First excess mark and scallop were corrected locally.","changed_pixels":int(changed.sum())},indent=2)+"\n")
