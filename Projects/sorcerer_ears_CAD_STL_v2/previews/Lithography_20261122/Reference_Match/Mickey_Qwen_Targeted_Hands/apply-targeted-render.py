from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

out = Path(__file__).resolve().parent
root = out.parent
mounted_path = root/"Mickey_Wrist_Join/mickey-mounted-connected-wrist.png"
flat_path = root/"Mickey_Wrist_Join/mickey-flat-connected-wrist-lithography.png"
target_path = out/"qwen-full-art-registered.png"
old = np.asarray(Image.open(mounted_path).convert("RGB")).copy()
render = np.asarray(Image.open(target_path).convert("RGB")).copy()
flat = Image.open(flat_path).convert("RGBA")
inner,outer = [Image.open(root/name).convert("L") for name in ("ear-interior-alpha.png","ear-outer-alpha.png")]
frame_size, pad, center = (1248,1248),112,(624,624)
bicubic = Image.Resampling.BICUBIC
angle = -40


def mount(mask):
    canvas = Image.new("L",frame_size)
    canvas.paste(mask,(pad,pad))
    return canvas.rotate(angle,bicubic,center=center)


bounds = mount(outer).getbbox()
origin = tuple(v-35 for v in bounds[:2])
opening = np.asarray(mount(inner).crop((*origin, origin[0]+old.shape[1],origin[1]+old.shape[0])))
output = old.copy()
authorized = np.zeros(old.shape[:2],bool)
regions = json.loads((out/"composite-regions.json").read_text())
fit_records = []


def glove_core(rgb):
    r,g,b = np.moveaxis(rgb.astype(float),-1,0)
    white = (r>164)&(g>158)&(b>146)&(r-b<65)
    label,_=ndimage.label(white)
    size=np.bincount(label.ravel())
    size[0]=0
    assert size.max()>2400
    return ndimage.binary_fill_holes(size[label]>.06*size.max())


def patch_glove(parameters):
    ix,iy,ax,ay = parameters["source_box"]
    x0,y0,x1,y1 = parameters["target_area"]
    donor = Image.fromarray(render[iy:ay,ix:ax])
    shift_x,shift_y = parameters.get("source_to_target_in_area",[0,0])
    same_size = (x1-x0,y1-y0)
    if donor.size != same_size:
        donor = donor.resize(same_size,Image.Resampling.LANCZOS)
    donor = np.asarray(donor.transform(same_size,Image.Transform.AFFINE,(1,0,-shift_x,0,1,-shift_y),bicubic))
    prior = old[y0:y1,x0:x1]
    current = output[y0:y1,x0:x1]
    rendered_core = glove_core(donor)
    before_core = glove_core(prior)
    extended = ndimage.distance_transform_edt(~rendered_core)
    blend = np.clip((3.35-extended)/1.5,0,1)
    # Bring over the model-produced glove linework, with a narrow feather only at its edge.
    previous_margin = ndimage.binary_dilation(before_core,iterations=5)
    r,g,b = np.moveaxis(prior.astype(int),-1,0)
    red_sleeve = (r>82)&(r>g+55)&(g<65)
    black_wrist = (r<42)&(g<39)&(b<53)
    background = (r<66)&(g>r+8)&(b>g+20)
    cuff_cleanup = (previous_margin & ~(red_sleeve|black_wrist)) & (blend < .97)
    backdrop = (background|red_sleeve)&~previous_margin
    _,near = ndimage.distance_transform_edt(~backdrop,return_indices=True)
    current[cuff_cleanup] = prior[tuple(near)][cuff_cleanup]

    # The only optional painted region is the generated wrist immediately beneath
    # the raised cuff. Preserve geometry beyond it exactly.
    if "wrist_patch" in parameters:
        wx0,wy0,wx1,wy1 = parameters["wrist_patch"]
        rr,gg,bb = np.moveaxis(donor.astype(int),-1,0)
        hand_black=(rr<50)&(gg<48)&(bb<61)
        generated_wrist=ndimage.binary_dilation(hand_black,iterations=2)
        permitted=np.zeros_like(rendered_core)
        permitted[wy0-y0:wy1-y0,wx0-x0:wx1-x0]=True
        blend=np.maximum(blend,ndimage.gaussian_filter((generated_wrist&permitted).astype(float),.55))

    permitted = opening[y0:y1,x0:x1] > 250
    alpha = blend*permitted
    current[:]=np.rint(current+(donor.astype(float)-current)*alpha[:,:,None]).astype(np.uint8)
    authorized[y0:y1,x0:x1] |= (alpha>0)|cuff_cleanup
    fit_records.append({"source_box":parameters["source_box"],
                        "target_area":parameters["target_area"],
                        "pixels_copied":int((alpha>0).sum())})


for region in regions:
    patch_glove(region)

assert np.array_equal(output[~authorized],old[~authorized])
difference = np.any(output!=old,axis=2)
assert 3000<difference.sum()<39000
mounted_output=out/"mickey-mounted-qwen-targeted-hands.png"
flat_output=out/"mickey-flat-qwen-targeted-hands-lithography.png"
Image.fromarray(output).save(mounted_output)
Image.fromarray(difference).save(out/"actual-mounted-edit-mask.png")
patch=Image.fromarray(output).convert("RGBA")
patch.putalpha(Image.fromarray(difference.astype(np.uint8)*255))
padded=Image.new("RGBA",frame_size)
padded.paste(patch,origin)
inverse=padded.rotate(-angle,bicubic,center=center).crop((pad,pad,pad+1024,pad+1024))
alpha=np.asarray(inverse.getchannel("A")).copy()
alpha[np.asarray(inner)<255]=0
inverse.putalpha(Image.fromarray(alpha))
Image.alpha_composite(flat,inverse).save(flat_output)
readback=np.asarray(Image.open(flat_output))
assert np.array_equal(readback[alpha==0],np.asarray(flat)[alpha==0])
assert np.array_equal(readback[:,:,3],np.asarray(inner))
meta={"restored_hands_source":"Qwen full-art render","fit_regions":fit_records,"changed_pixels_mounted":int(difference.sum()),
      "source_sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in
        (mounted_path,flat_path,target_path,mounted_output,flat_output,out/"animation-pose-reference.png")}}
(out/"verification.json").write_text(json.dumps(meta,indent=2)+"\n")
print(json.dumps(meta,indent=2))
