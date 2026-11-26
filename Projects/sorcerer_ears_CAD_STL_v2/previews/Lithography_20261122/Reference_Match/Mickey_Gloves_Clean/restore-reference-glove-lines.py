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
ref_path = root/"Mickey_Gloves"/"attached-glove-reference.png"
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


def donor_from_reference(box):
    pixels = np.asarray(ref.crop(box)).astype(float)
    red,green,blue = np.moveaxis(pixels,-1,0)
    glove = largest((green > 113) & (green-red > 10) & (green-blue > -25))
    glove = ndimage.binary_fill_holes(ndimage.binary_closing(glove,iterations=1))
    # Convert the animated blue-lit glove to the plate's ivory and brown line colors.
    # Extract the cuff, palm, and curled-finger marks from the reference pixels.
    _,nearest = ndimage.distance_transform_edt(~glove,return_indices=True)
    smooth = ndimage.gaussian_filter(green[tuple(nearest)], .51)
    lit = ndimage.grey_closing(smooth, size=(9,9))
    transition = np.clip((lit-smooth-10)/22,0,1)
    line = transition*transition*(3-2*transition)
    line = np.where(glove,line,0)
    white = np.array([249,248,244])
    brown = np.array([119,85,42])
    rgb = white + line[:,:,None]*(brown-white)
    interior = ndimage.distance_transform_edt(glove)
    
    # Resize the signed distance field before taking the contour to avoid stair steps.
    signed = ndimage.distance_transform_edt(glove) - ndimage.distance_transform_edt(~glove)
    signed = ndimage.gaussian_filter(signed,.68)
    def magnify(a):
        im = Image.fromarray(a.astype(np.float32))
        return np.asarray(im.resize((im.width*4,im.height*4),Image.Resampling.BICUBIC))
    d = magnify(signed)
    ink = np.stack([magnify(rgb[:,:,i]) for i in range(3)],axis=2)
    stroke = np.clip((1.32-d)/.55,0,1)
    ink += stroke[:,:,None]*(np.array([156,108,49])-ink)
    alpha = np.clip((d+.12)/.46,0,1)
    rgba = np.dstack((np.clip(ink,0,255),np.rint(alpha*255))).astype(np.uint8)
    return Image.fromarray(rgba)


def replace_glove(ref_box, ref_anchor, dest_anchor, scale, old_box, mid):
    donor = donor_from_reference(ref_box)
    rs = donor.resize((round(donor.width*scale/4),round(donor.height*scale/4)),Image.Resampling.LANCZOS)
    ox = round(dest_anchor[0]-scale*(ref_anchor[0]-ref_box[0]))
    oy = round(dest_anchor[1]-scale*(ref_anchor[1]-ref_box[1]))
    layer = Image.new("RGBA",mounted.size)
    layer.alpha_composite(rs,(ox,oy))
    layer_mask = np.asarray(layer.getchannel("A"))>0

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
    donors.append({"reference_box":ref_box,"destination_anchor":dest_anchor,"scale":scale,
                   "reference_anchor":ref_anchor,"changed_mask_pixels":int(layer_mask.sum())})


replace_glove((216,16,335,94),(253,84),(690,308),1.64,(632,194,820,327),(719,252))
replace_glove((63,232,132,299),(99,245),(421,558),1.80,(347,533,475,666),(409,610))
assert np.array_equal(data[~allowed],old[~allowed])
mounted_output = out/"mickey-mounted-sharpened-reference-gloves.png"
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
flat_output = out/"mickey-flat-sharpened-reference-gloves-lithography.png"
revised_flat.save(flat_output)
readback = np.asarray(Image.open(flat_output))
assert np.array_equal(readback[pa==0],np.asarray(flat_before)[pa==0])
assert np.array_equal(readback[:,:,3],original_alpha)
report={"edit":"Two glove shapes and seams extracted from the attached animation frame",
        "donors":donors,"outside_mask_pixel_match":True,"flat_alpha_matches_cad_opening":True,
        "sha256":{p.name:sha256(p.read_bytes()).hexdigest() for p in (ref_path,mounted_path,flat_path,mounted_output,flat_output)}}
(out/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
