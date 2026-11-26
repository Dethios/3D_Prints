from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

out = Path(__file__).resolve().parent
root = out.parent
previous = root/"Mickey_Star_Spacing"
mounted_path = previous/"mickey-mounted-more-stars.png"
flat_path = previous/"mickey-flat-more-stars-lithography.png"
ref_path = out/"glove-cleanup-comfy-render.png"
mounted = Image.open(mounted_path).convert("RGBA")
old = np.asarray(mounted).copy()
ref = Image.open(ref_path).convert("RGB")
flat_before = Image.open(flat_path).convert("RGBA")
inner = Image.open(root/"ear-interior-alpha.png").convert("L")
outer = Image.open(root/"ear-outer-alpha.png").convert("L")
canvas = (1248,1248)
pad = 112
center = (624,624)
angle = -40
resample = Image.Resampling.BICUBIC


def mounted_mask(mask):
    padded = Image.new("L", canvas)
    padded.paste(mask, (pad,pad))
    return padded.rotate(angle,resample,center=center)


bounds = mounted_mask(outer).getbbox()
view_origin = tuple(v-35 for v in bounds[:2])
opening = np.asarray(mounted_mask(inner).crop(
    (*view_origin, view_origin[0]+mounted.width,view_origin[1]+mounted.height)
))
allowed = np.zeros(old.shape[:2], dtype=bool)
data = old.copy()
donors = []


def largest(mask):
    labels,n = ndimage.label(mask)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    assert n and counts.max()
    return labels == counts.argmax()


def donor_from_render(box):
    crop = ref.crop(box).convert("RGBA")
    pixels = np.asarray(crop).astype(np.int16)
    r,g,b = np.moveaxis(pixels[:,:,:3],-1,0)
    mask = (r>161)&(g>154)&(b>138)&((r-b)<68)
    labels, _ = ndimage.label(mask)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    assert sizes.max() > 10000
    pieces = sizes[labels] > sizes.max()*.04
    pieces = ndimage.binary_fill_holes(ndimage.binary_closing(pieces,iterations=3))
    distance = ndimage.distance_transform_edt(pieces) - ndimage.distance_transform_edt(~pieces)
    alpha = np.clip((ndimage.gaussian_filter(distance,.65)+2.4)/1.55,0,1)
    crop.putalpha(Image.fromarray(np.rint(255*alpha).astype(np.uint8)))
    return crop.crop(crop.getbbox())


def replace_glove(ref_box, dest_box, old_box, mid):
    donor = donor_from_render(ref_box)
    ox,oy,width,height = dest_box
    rs = donor.resize((width,height),Image.Resampling.LANCZOS)
    layer = Image.new("RGBA",mounted.size)
    layer.alpha_composite(rs,(ox,oy))
    x0,y0,x1,y1 = old_box
    local = old[y0:y1,x0:x1,:3].astype(int)
    r,g,b = np.moveaxis(local,-1,0)
    white = (r>178)&(g>176)&(b>168)&(np.abs(r-g)<25)
    labels,_ = ndimage.label(white)
    k = labels[mid[1]-y0,mid[0]-x0]
    assert k and (labels==k).sum()>3000
    region = ndimage.binary_fill_holes(labels==k)
    # Include the old cuff as well as its gold outline.
    for j in np.unique(labels[ndimage.binary_dilation(region,iterations=6)]):
        if j and (labels==j).sum()>40:
            region |= labels==j
    region = ndimage.binary_dilation(region,iterations=9)
    # The unedited black wrist is the registration surface for the new cuff.
    region &= ~((r<47)&(g<39)&(b<65)) & ~((r>85)&(r>g+67)&(g<62))
    navy = (r<62)&(g>r+9)&(b>g+28)
    red_cloth = (r>77)&(r>g+35)&(g<74)&(b<62)
    keep_color = (navy | red_cloth) & ~region
    _,indices = ndimage.distance_transform_edt(~keep_color,return_indices=True)
    canvas_px = data[y0:y1,x0:x1]
    canvas_px[region] = canvas_px[tuple(indices)][region]
    allowed[y0:y1,x0:x1] |= region
    # Clip the antialiased outer fringe to the already verified CAD opening.
    layer_alpha = np.asarray(layer.getchannel("A")).copy()
    layer_alpha[opening < 245] = 0
    layer.putalpha(Image.fromarray(layer_alpha))
    layer_mask = layer_alpha>0
    allowed[:] |= layer_mask
    data[:] = np.asarray(Image.alpha_composite(Image.fromarray(data),layer))
    donors.append({"render_crop":ref_box,"destination_box":dest_box,
                   "changed_mask_pixels":int(layer_mask.sum())})


replace_glove((97,182,504,445),(648,210,167,108),(631,191,820,328),(719,252))
replace_glove((697,197,923,451),(366,547,91,102),(347,533,475,666),(409,610))
assert np.array_equal(data[~allowed],old[~allowed])
mounted_output = out/"mickey-mounted-clean-gloves.png"
Image.fromarray(data).convert("RGB").save(mounted_output)
Image.fromarray(allowed).save(out/"actual-mounted-glove-edit-mask.png")

# Transfer only the edit region to the print orientation.
new_patch = Image.fromarray(data)
new_patch.putalpha(Image.fromarray(allowed.astype(np.uint8)*255))
padded = Image.new("RGBA",canvas)
padded.paste(new_patch,view_origin)
patch = padded.rotate(-angle,resample,center=center).crop((pad,pad,pad+1024,pad+1024))
pa = np.asarray(patch.getchannel("A")).copy()
original_alpha = np.asarray(inner)
pa[original_alpha < 255] = 0
patch.putalpha(Image.fromarray(pa))
revised_flat = Image.alpha_composite(flat_before,patch)
flat_output = out/"mickey-flat-clean-gloves-lithography.png"
revised_flat.save(flat_output)
readback = np.asarray(Image.open(flat_output))
assert np.array_equal(readback[pa==0],np.asarray(flat_before)[pa==0])
assert np.array_equal(readback[:,:,3],original_alpha)
report={"edit":"Two Qwen-restored gloves composited locally over the source artwork",
        "donors":donors,"outside_mask_pixel_match":True,"flat_alpha_matches_cad_opening":True,
        "sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in (ref_path,mounted_path,flat_path,mounted_output,flat_output)}}
(out/"verification-clean-gloves.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
