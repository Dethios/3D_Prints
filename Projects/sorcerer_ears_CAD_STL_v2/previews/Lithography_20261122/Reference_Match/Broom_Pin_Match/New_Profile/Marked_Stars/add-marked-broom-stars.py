from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, label


out = Path(__file__).resolve().parent
root = out.parent.parent.parent
previous = out.parent
sources = [previous / "brooms-mounted-matching-linework.png", previous / "brooms-flat-matching-linework-lithography.png"]
mounted, flat = [Image.open(path).convert("RGBA") for path in sources]
inner = Image.open(root / "ear-interior-alpha.png").convert("L")
outer = Image.open(root / "ear-outer-alpha.png").convert("L")
pad, size = 112, (1248, 1248)
center, angle = (624, 624), 40
rotation_sampling = Image.Resampling.BICUBIC


def mount_mask(mask):
    padded = Image.new("L", size)
    padded.paste(mask, (pad, pad))
    return padded.rotate(angle, rotation_sampling, center=center)


view_origin = tuple(value - 35 for value in mount_mask(outer).getbbox()[:2])
opening = np.asarray(mount_mask(inner))[
    view_origin[1]:view_origin[1] + mounted.height, view_origin[0]:view_origin[0] + mounted.width
]
rgb = np.asarray(mounted).astype(float)[:, :, :3]
red, green, blue = np.moveaxis(rgb, -1, 0)
existing = (red > 65) | (green > 85) | (blue < 65)
clear_distance = distance_transform_edt(~existing)
overlay = Image.new("RGBA", mounted.size)
placements = [(262, 217, 36, 253, 344, 1.37), (412, 320, 34, 537, 286, .74)]
spacing = []

for source_x, source_y, radius, x, y, scale in placements:
    region = mounted.crop((source_x - radius, source_y - radius, source_x + radius, source_y + radius))
    values = np.asarray(region)[:, :, :3].astype(float)
    navy = np.median(values[values[:, :, 0] < 45], axis=0)
    gold = np.median(values[values[:, :, 0] > 180], axis=0)
    tint = gold - navy
    coverage = np.clip((values - navy) @ tint / (tint @ tint), 0, 1)
    components, _ = label(coverage > .055)
    star_component = components[radius, radius]
    assert star_component != 0
    coverage[components != star_component] = 0
    star = Image.new("RGBA", region.size, (*np.rint(gold).astype(int), 255))
    star.putalpha(Image.fromarray(np.rint(coverage * 255).astype(np.uint8)))
    radius = round(radius * scale)
    star = star.resize((2 * radius, 2 * radius), Image.Resampling.LANCZOS)
    box = np.s_[y - radius:y + radius, x - radius:x + radius]
    shape = np.asarray(star.getchannel("A")) > 0
    assert np.all(opening[box][shape] == 255)
    nearest = float(clear_distance[box][shape].min())
    assert nearest >= 15, (x,y,nearest)
    spacing.append({"center_mounted_preview_px": [x, y], "size_multiplier": scale, "nearest_edge_gap_px": round(nearest, 1)})
    overlay.alpha_composite(star, (x - radius, y - radius))

mounted_result = Image.alpha_composite(mounted, overlay)
full_overlay = Image.new("RGBA", size)
full_overlay.paste(overlay, view_origin)
flat_overlay = full_overlay.rotate(-angle, rotation_sampling, center=center).crop(
    (pad, pad, pad + flat.width, pad + flat.height)
)
flat_result = Image.alpha_composite(flat, flat_overlay)
assert np.array_equal(np.asarray(flat_result.getchannel("A")), np.asarray(inner))
outputs = [out / "brooms-mounted-marked-stars.png", out / "brooms-flat-marked-stars-lithography.png"]
for base, layer, result, path in zip((mounted, flat), (overlay, flat_overlay), (mounted_result, flat_result), outputs):
    result.save(path)
    keep = np.asarray(layer.getchannel("A")) == 0
    assert np.array_equal(np.asarray(Image.open(path))[keep], np.asarray(base)[keep])

overlay.save(out / "added-stars-matte.png")
record = {
    "change": "Two stars cloned from the prior approved artwork for the upper and left gaps",
    "mounted_rim_angle_degrees": angle,
    "pixels_per_mm": 9.22,
    "placement": spacing,
    "unchanged_outside_added_stars": True,
    "flat_alpha_matches_cad_opening": True,
    "sha256": {path.name: sha256(path.read_bytes()).hexdigest() for path in sources + outputs},
}
(out / "verification-broom-stars.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record["placement"]))
