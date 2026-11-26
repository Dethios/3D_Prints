from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image

out = Path(__file__).resolve().parent
root = out.parent.parent
review_path = out/"brooms-mounted-selected-original-angle.png"
flat_path = out/"brooms-flat-selected-original-angle-lithography.png"
outer_path = root/"ear-outer-alpha.png"
inner_path = root/"ear-interior-alpha.png"
original_path = out/"reference-profile-cutout.png"
updated_path = out/"selected-broom-clean-lines.png"
outer,inner = [Image.open(p).convert("L") for p in (outer_path,inner_path)]
size, pad, center, angle = (1248,1248),112,(624,624),40
bicubic = Image.Resampling.BICUBIC
navy = (35,62,114)
gold = (220,175,84)
paper = (247,244,237)


def mount(mask):
    full = Image.new("L",size)
    full.paste(mask,(pad,pad))
    return full.rotate(angle,bicubic,center=center)


opening, perimeter = mount(inner), mount(outer)
x0,y0,x1,y1 = perimeter.getbbox()
view = x0-35,y0-35,x1+35,y1+35
raw, modified = [Image.open(p).convert("RGBA") for p in (original_path,updated_path)]
places = [(200,418,round(raw.width*465/raw.height),465),(524,221,round(raw.width*425/raw.height),425)]

def shape_layer(source):
    art = source
    layer = Image.new("RGBA",size)
    for x,y,w,h in places:
        sprite = art.resize((w,h),Image.Resampling.LANCZOS)
        layer.alpha_composite(sprite,(view[0]+x,view[1]+y))
    return layer


before,after = [shape_layer(source) for source in (raw,modified)]


def clip(layer,mask):
    build = np.asarray(layer.getchannel("A")).astype(np.uint16)
    fit = np.asarray(mask).astype(np.uint16)
    clipped = layer.copy()
    clipped.putalpha(Image.fromarray(((build*fit+127)//255).astype(np.uint8)))
    return clipped


def fill(mask,rgb):
    layer = Image.new("RGBA",mask.size,(*rgb,0))
    layer.putalpha(mask)
    return layer


def flatten(layer):
    return layer.rotate(-angle,bicubic,center=center).crop((pad,pad,pad+1024,pad+1024))


def patch(prior_path, old_layer, new_layer, output_path, save_rgb=False):
    frozen = np.asarray(Image.open(prior_path).convert("RGBA")).copy()
    src,dst = np.asarray(old_layer),np.asarray(new_layer)
    change = np.any(src != dst,axis=2)
    # Every masked source pixel must match the old motif-free-of-stars compositing.
    assert np.array_equal(frozen[change],src[change])
    frozen[change] = dst[change]
    saved = Image.fromarray(frozen)
    (saved.convert("RGB") if save_rgb else saved).save(output_path)
    readback = np.asarray(Image.open(output_path).convert("RGBA"))
    previous = np.asarray(Image.open(prior_path).convert("RGBA"))
    assert np.array_equal(readback[~change],previous[~change])
    return int(change.sum())


def mounted(layer):
    canvas = Image.new("RGBA",size,(*paper,255))
    rim = fill(perimeter,gold)
    field = fill(opening,navy)
    field.alpha_composite(clip(layer,opening))
    rim.alpha_composite(field)
    canvas.alpha_composite(rim)
    return canvas.crop(view)


def flat(layer):
    result = fill(inner,navy)
    result.alpha_composite(clip(flatten(clip(layer,opening)),inner))
    result.putalpha(inner)
    return result


mounted_output=out/"brooms-mounted-clean-lines.png"
flat_output=out/"brooms-flat-clean-lines-lithography.png"
mount_changes=patch(review_path,mounted(before),mounted(after),mounted_output,save_rgb=True)
flat_changes=patch(flat_path,flat(before),flat(after),flat_output)
assert np.array_equal(np.asarray(Image.open(flat_output).getchannel("A")),np.asarray(inner))
summary={"mounted_changed_pixels":mount_changes,"flat_changed_pixels":flat_changes,
         "ear_placement_and_star_pixels_preserved":True,
         "sha256":{f.name:sha256(f.read_bytes()).hexdigest() for f in (out/"user-selected-broom.png",
            original_path,updated_path,review_path,flat_path,mounted_output,flat_output)}}
(out/"verification-clean-lines.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
