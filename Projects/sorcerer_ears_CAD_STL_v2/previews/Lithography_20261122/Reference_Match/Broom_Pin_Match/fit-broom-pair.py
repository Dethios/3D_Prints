import json
import os
from hashlib import sha256
from pathlib import Path
import sys

out = Path(__file__).resolve().parent
os.environ["NX3_MOUNTED_OUT"] = str(out)
layout_script = out.parent / "Mounted" / "build-mounted-match.py"
exec(layout_script.read_text(encoding="utf-8-sig").split("\nmounted={}", 1)[0])

source = Path(sys.argv[1]).resolve()
sprite = Image.open(source).convert("RGBA")
angle = ANGLES["brooms"]
card_text = sys.argv[2] if len(sys.argv) > 2 else "review"
imask, omask = rotate_mask(source_inner, angle), rotate_mask(source_outer, angle)
grid = np.asarray(imask) > 136
collar = np.asarray(imask) > 200
boundary = ndimage.binary_dilation(collar, iterations=2) & ~collar


def sprite_asset(height):
    scaled = sprite.resize((round(sprite.width * height / sprite.height), height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (T, T))
    canvas.alpha_composite(scaled, ((T - scaled.width) // 2, (T - scaled.height) // 2))
    canvas.save(out / f"placement-source-{height}.png")
    return pinned_asset(out / f"placement-source-{height}.png")


def rank_options(art, offsets, target, tilts, label):
    options = []
    outline = art["outline"]
    protected = is_protected(outline, label, art)
    anchor = relative_anchor(art, "broom")
    ceiling = np.argmax(grid, axis=0)
    floor = grid.shape[0] - np.argmax(grid[::-1], axis=0) - 1
    supported = grid.any(axis=0)
    for tilt in tilts:
        matrix = turning(tilt)
        for scale in np.arange(1., .46, -.04):
            edge = (outline - anchor) @ matrix * scale
            for rim_x, xy in extent_points(offsets, angle, 0):
                px = np.rint(edge[:,0] + xy[0]).astype(int)
                if np.any((px < 0) | (px >= W)) or not supported[px].all():
                    continue
                bottom_limit = floor[px] - edge[:,1]
                top_limit = ceiling[px] - edge[:,1]
                py = round(float(np.percentile(bottom_limit, 2.6))) + 2
                if py < top_limit.max() or py > bottom_limit[protected].min() or abs(py-xy[1]) > 190:
                    continue
                position = np.array([xy[0], py])
                moved = edge + position
                lost = 1 - mask_hit(grid, (art["sample"] - anchor) @ matrix * scale + position).mean()
                if not .0003 <= lost <= .085:
                    continue
                options.append({"rank": (1-scale)*4 + abs(target-rim_x)*.003
                                + abs(lost-.009)*12 + abs(py-xy[1])*.006,
                                "scale": float(scale), "tilt": tilt,
                                "anchor": anchor, "target": position,
                                "rim_x": rim_x, "cut_fraction": lost,
                                "lo": moved.min(axis=0), "hi": moved.max(axis=0)})
    return sorted(options, key=lambda item: item["rank"])

left_art, right_art = sprite_asset(422), sprite_asset(460)
left = rank_options(left_art, range(215, 501, 5), 357, (16., 23., 29., 34., 39., 44.), "broom-leaning")
right = rank_options(right_art, range(435, 797, 5), 620, (-15., -8., 0., 8., 13., 19., 27.), "broom-upright")
print("feasible positions", len(left), len(right), flush=True)
assert left and right



picked = None
constraints = sorted(((a["rank"] + b["rank"] + abs(a["scale"] - b["scale"]) * 2.5 + abs(a["tilt"] - 27.)*.017 + abs(b["tilt"] - 5.)*.022, i, j)
                      for i, a in enumerate(left[:530]) for j, b in enumerate(right[:530])))
halos = {}
for _, i, j in constraints:
    pair = left[i], right[j]
    if not bbox_overlap(*pair):
        picked = pair
        break
    a_points = placement(left_art, pair[0])
    if i not in halos:
        raster = np.zeros(size, dtype=bool)
        xy = np.rint(a_points).astype(int)
        good = np.all((xy >= 0) & (xy < W), axis=1)
        raster[xy[good, 1], xy[good, 0]] = True
        halos[i] = ndimage.binary_dilation(raster, iterations=10)
    if not mask_hit(halos[i], placement(right_art, pair[1])).any():
        picked = pair
        break
assert picked

scene = Image.new("RGBA", size)
audit = []
stamped = []
for art, choice in zip((left_art, right_art), picked):
    image = stamp(art, choice)
    opacity = np.asarray(image.getchannel("A")) > 100
    contact = int(np.sum(opacity & boundary))
    assert contact > 18
    audit.append({"tilt_degrees": choice["tilt"], "scale": round(choice["scale"], 3),
                  "rim_contact_pixels": contact, "occluded_percent": round(100 * choice["cut_fraction"], 2)})
    stamped.append(opacity & grid)
    scene.alpha_composite(clip(image, imask))

assert not (stamped[0] & stamped[1]).any()
existing_stars = dots("brooms", PRE.parent / "brooms-artwork-transparent.png")[2:]
stars, n_stars = stars_on_mount([], scene, existing_stars, grid)
scene.alpha_composite(stars)
assert n_stars >= 7
field = solid_canvas(imask, navy)
field.alpha_composite(scene)
rim = solid_canvas(omask, gold)
rim.alpha_composite(field)
preview = Image.new("RGBA", size, (*paper, 255))
preview.alpha_composite(rim)
x0, y0, x1, y1 = omask.getbbox()
preview_path = out / f"brooms-mounted-{card_text}.png"
preview.crop((x0-35, y0-35, x1+35, y1+35)).convert("RGB").save(preview_path)
flattened = scene.rotate(-angle, Image.Resampling.BICUBIC, center=(C, C)).crop((pad,pad,pad+T,pad+T))
flattened = clip(flattened, source_inner)
lithography = solid_canvas(source_inner, navy)
lithography.alpha_composite(flattened)
lithography.putalpha(source_inner)
flat_path = out / f"brooms-flat-{card_text}-lithography.png"
lithography.save(flat_path)
assert np.array_equal(np.asarray(Image.open(flat_path).getchannel("A")), np.asarray(source_inner))
report = {"source": source.name, "mount_degrees": angle, "star_count": n_stars, "broom_fit": audit,
          "sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in (source, preview_path, flat_path)}}
(out / f"verification-{card_text}.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
