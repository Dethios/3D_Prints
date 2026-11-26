import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


out = Path(__file__).resolve().parent
source = out.parent
master = Image.open(source / "mickey-two-shoes-comfy-master.png").convert("RGB")
inner = Image.open(source / "ear-interior-alpha.png").convert("L")
outer = Image.open(source / "ear-outer-alpha.png").convert("L")
side, pad = 1024, 112
size = (side + 2 * pad,) * 2
center = (size[0] / 2, size[1] / 2)
mount_angle = -40
# Keep the source artwork at native pixel coordinates on the mounted canvas.
# Register the rim so its midpoint meets the rear shoe.
art_origin = (71, 83)
pixel_per_mm = 9.22
resample = Image.Resampling.BICUBIC


def mount(mask):
    padded = Image.new("L", size)
    padded.paste(mask, (pad, pad))
    return padded.rotate(mount_angle, resample, center=center)


def field_terms(x, y):
    return np.stack((np.ones_like(x), x, y, x * x, x * y, y * y), axis=-1)


rgb = np.asarray(master).astype(np.int16)
r, g, b = np.moveaxis(rgb, -1, 0)
blue = (r < 85) & (g >= r + 6) & (b >= r + 35) & (b > 65)
labels, _ = ndimage.label(blue)
counts = np.bincount(labels.ravel())
counts[0] = 0
navy = labels == counts.argmax()
original_field = ndimage.binary_erosion(ndimage.binary_fill_holes(navy), iterations=3)
assert original_field[420, 500] and original_field[780, 367] and original_field[780, 651]
yy, xx = np.indices(rgb.shape[:2], dtype=float)
coords = ((xx - 512) / 512, (yy - 512) / 512)
samples = navy & (xx % 7 == 0) & (yy % 7 == 0)
coefficients = np.linalg.lstsq(
    field_terms(coords[0][samples], coords[1][samples]), rgb[samples], rcond=None
)[0]
my, mx = np.indices(size, dtype=float)
background = field_terms(
    (mx - art_origin[0] - 512) / 512, (my - art_origin[1] - 512) / 512
) @ coefficients
mounted_rgb = Image.fromarray(np.clip(np.rint(background), 0, 255).astype(np.uint8))
source_rgb = field_terms(*coords) @ coefficients
foreground = original_field & (np.linalg.norm(rgb - source_rgb, axis=2) > 19)
labels, _ = ndimage.label(ndimage.binary_closing(foreground, iterations=2))
areas = np.bincount(labels.ravel())
areas[0] = 0
figure = ndimage.binary_fill_holes(labels == areas.argmax())
star_labels, _ = ndimage.label(foreground & ~ndimage.binary_dilation(figure, iterations=9))
moved_star = ndimage.binary_fill_holes(star_labels == star_labels[474, 742])
assert 300 < moved_star.sum() < 1500
figure_shift = (60, 64)
star_shift = (13, 104)

def soft_edge(mask):
    edge = ndimage.binary_dilation(mask, iterations=2).astype(float)
    alpha = np.rint(ndimage.gaussian_filter(edge, .8) * 255).astype(np.uint8)
    alpha[mask] = 255
    return Image.fromarray(alpha)

stationary = soft_edge((star_labels != 0) & ~moved_star)
mounted_rgb.paste(master, art_origin, stationary)
mounted_rgb.paste(master, tuple(a + b for a, b in zip(art_origin, star_shift)), soft_edge(moved_star))
mounted_rgb.paste(master, tuple(a + b for a, b in zip(art_origin, figure_shift)), soft_edge(figure))

mounted_inner = mount(inner)
mounted_outer = mount(outer)
fill = mounted_rgb.convert("RGBA")
fill.putalpha(mounted_inner)
rim = Image.new("RGBA", size, (218, 173, 85, 0))
rim.putalpha(mounted_outer)
rim.alpha_composite(fill)
paper = Image.new("RGBA", size, (249, 239, 222, 255))
paper.alpha_composite(rim)
extents = mounted_outer.getbbox()
view_box = (extents[0] - 35, extents[1] - 35, extents[2] + 35, extents[3] + 35)
paper.crop(view_box).convert("RGB").save(out / "mickey-mounted-lowered.png")

flat = mounted_rgb.rotate(-mount_angle, resample, center=center).crop(
    (pad, pad, pad + side, pad + side)
).convert("RGBA")
flat.paste((0, 0, 0, 0), (0, 0, side, side), inner.point(lambda a: 255 if a == 0 else 0))
flat.putalpha(inner)
flat.save(out / "mickey-flat-lowered-lithography.png")
flat_check = Image.open(out / "mickey-flat-lowered-lithography.png")
assert flat_check.size == master.size
assert np.array_equal(np.asarray(flat_check.getchannel("A")), np.asarray(inner))

inner_px = np.asarray(mounted_inner) > 127
outer_px = np.asarray(mounted_outer) > 127
x0, y0 = (a + b for a, b in zip(art_origin, figure_shift))
source_inner = inner_px[y0:y0 + side, x0:x0 + side]
source_outer = outer_px[y0:y0 + side, x0:x0 + side]
shoe_colors = (r > 100) & (r > g + 24) & (g > b + 20) & (g > 54)
rear = shoe_colors & (xx >= 305) & (xx < 443) & (yy >= 746) & (yy < 818)
forward = shoe_colors & (xx >= 565) & (xx < 716) & (yy >= 746) & (yy < 818)
assert np.count_nonzero(forward) > 3000 and np.count_nonzero(rear) > 3000
assert source_inner[forward].mean() > .99
assert .35 < source_inner[rear].mean() < .70
copied = np.asarray(mounted_rgb)[y0:y0 + side, x0:x0 + side]
visible = figure & source_inner
assert np.array_equal(copied[visible], rgb[visible])
art_y, art_x = np.where(visible)
opening_y, _ = np.where(inner_px)
upper_margin = int(art_y.min() + y0 - opening_y.min())
lower_margin = int(opening_y.max() - art_y.max() - y0)
assert abs(upper_margin - lower_margin) <= 5
contact = rear & source_outer & ~source_inner
cy, cx = np.where(contact)
assert cx.size > 100
inner_y = np.flatnonzero(np.asarray(inner)[:, side // 2] > 127)[-1] + pad
a = math.radians(mount_angle)
midpoint = np.array([center[0] + math.sin(a) * (inner_y - center[1]),
                     center[1] + math.cos(a) * (inner_y - center[1])])
offset_mm = np.linalg.norm(np.array([cx.mean() + x0, cy.mean() + y0]) - midpoint) / pixel_per_mm
report = {
    "mounted_rim_degrees": mount_angle,
    "mounted_art_rotation_degrees": 0,
    "mounted_art_scale": 1.0,
    "mounted_art_origin_px": [x0, y0],
    "full_figure_upper_and_lower_margins_px": [upper_margin, lower_margin],
    "rim_midpoint_to_overlap_center_mm": round(float(offset_mm), 2),
    "rear_shoe_in_opening_percent": round(float(source_inner[rear].mean() * 100), 1),
    "forward_shoe_in_opening_percent": round(float(source_inner[forward].mean() * 100), 1),
    "visible_mickey_pixels_unchanged": True,
    "flat_export_alpha_matches_cad_opening": True,
}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
