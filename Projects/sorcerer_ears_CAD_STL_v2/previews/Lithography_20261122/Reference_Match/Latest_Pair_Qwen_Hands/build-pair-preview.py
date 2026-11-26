from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw
import trimesh

out = Path(__file__).resolve().parent
base = out.parent
project = next(p for p in base.parents if (p / "CAD" / "assembly_positions.json").is_file())
pose_path = project / "CAD" / "assembly_positions.json"
band_path = project / "Reference_files" / "dressyspider_larger_headband_source.stl"
poses = json.loads(pose_path.read_text())["NX3"]
outer_path = base / "ear-outer-alpha.png"
inner_path = base / "ear-interior-alpha.png"
outer = Image.open(outer_path).convert("L")
inner = Image.open(inner_path).convert("L")
sides = [
    ("left_brooms", base / "Broom_Pin_Match/New_Profile/Marked_Stars/brooms-flat-marked-stars-lithography.png",
     base / "Broom_Pin_Match/New_Profile/Marked_Stars/brooms-mounted-marked-stars.png"),
    ("right_mouse", base / "Mickey_Qwen_Targeted_Hands/mickey-flat-qwen-targeted-hands-lithography.png",
     base / "Mickey_Qwen_Targeted_Hands/mickey-mounted-qwen-targeted-hands.png"),
]

paper = (249, 243, 231, 255)
canvas = (3900, 3900)
scale = 14.5
origin = np.array([1950., 2290.])
page = Image.new("RGBA", canvas, paper)
draw = ImageDraw.Draw(page)
band = trimesh.load_mesh(band_path)
for face in band.triangles:
    projected = origin + face[:, :2] * np.array([scale, -scale])
    draw.polygon([tuple(point) for point in projected], fill=(34, 38, 51, 255))

band_visible = np.asarray(page)[:, :, 0] == 34
screen_to_world = np.diag([1/scale, -1/scale])
ear_to_texture = np.diag([9.22, -9.22])
angles = {}
ear_layers = []
for key, artwork, mounted_reference in sides:
    flat = Image.open(artwork).convert("RGBA")
    assert np.array_equal(np.asarray(flat.getchannel("A")), np.asarray(inner))
    rim_color = Image.open(mounted_reference).convert("RGB").getpixel((498, 60))
    ear = Image.new("RGBA", outer.size, (*rim_color, 0))
    ear.putalpha(outer)
    ear.alpha_composite(flat)

    pose = np.asarray(poses[key])
    rotation, offset = pose[:2, :2], pose[:2, 3]
    linear = ear_to_texture @ rotation.T @ screen_to_world
    translation = ear_to_texture @ rotation.T @ (-screen_to_world @ origin - offset) + [512, 917]
    affine = tuple(np.column_stack((linear, translation)).ravel())
    layer = ear.transform(canvas, Image.Transform.AFFINE, affine, Image.Resampling.BICUBIC)
    coverage = np.asarray(layer.getchannel("A")) > 127
    assert np.count_nonzero(coverage & band_visible) > 100
    ear_layers.append(coverage)
    page.alpha_composite(layer)
    angles[key] = round(float(np.degrees(np.arctan2(rotation[1, 0], rotation[0, 0]))), 3)

assert not (ear_layers[0] & ear_layers[1]).any()
bounds = ImageChops.difference(page.convert("RGB"), Image.new("RGB", canvas, paper[:3])).getbbox()
assert min(bounds[:2]) > 92 and bounds[2] < canvas[0]-92 and bounds[3] < canvas[1]-92, bounds
x0, y0, x1, y1 = bounds
frame_margin = 92
preview = page.crop((x0-frame_margin, y0-frame_margin, x1+frame_margin, y1+frame_margin)).convert("RGB")
preview = preview.resize((preview.width//2, preview.height//2), Image.Resampling.LANCZOS)
target = out / "nx3-sorcerer-ears-qwen-hands-and-marked-stars.png"
preview.save(target)
source_files = [pose_path, band_path, outer_path, inner_path, *(art for _, art, _ in sides)]
report = {"mounted_angles_degrees": angles, "image_dimensions": list(preview.size),
          "source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in source_files},
          "preview_sha256": sha256(target.read_bytes()).hexdigest()}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
