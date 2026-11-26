"""Build and check R2 from its editable SVG with the same projection used for R1."""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT.parent))
import prepare_art as art


def save_closeup(front):
    blueprint = Path.home() / "Downloads" / "Purple Castle Star Card Wand Blueprint.png"
    if not blueprint.is_file():
        return
    digest = hashlib.sha256(blueprint.read_bytes()).hexdigest()
    if digest != "7c4202584515bbf4c98f5578b08741578a1eb9dc0a10efa11c703502ac942650":
        raise ValueError("The supplied blueprint has changed")
    blue = Image.open(blueprint).convert("RGB").crop((574,938,885,1181))
    # At these relative magnifications Mickey has the same width in both panels.
    bounds = (222,331,399,469)
    scale = 2.2 * .78
    crop = tuple(round((v-o)*scale) for v,o in zip(bounds,(5,16,5,16)))
    panel_size = (528,412)
    detail = front.crop(crop).resize(panel_size, Image.Resampling.LANCZOS)
    sheet = Image.new("RGB",(1104,477),"#faf9f7")
    sheet.paste(blue.resize(panel_size,Image.Resampling.LANCZOS),(16,55))
    sheet.paste(detail,(560,55),detail.getchannel("A"))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",23)
    draw.text((18,12),"Blueprint detail",fill="#30203a",font=font)
    draw.text((562,12),"Purple castle wand · R2",fill="#30203a",font=font)
    sheet.save(ROOT/"rose_reference_detail.png")


def main():
    art.ROOT = ROOT
    art.MASTER = ROOT / "castle_front.svg"
    features = art.profiles()
    art.export(features)
    exchange = ROOT / "castle_profiles.json"
    packet = json.loads(exchange.read_text())
    packet["revision"] = "R2 provisional · enchanted rose"
    first = json.loads((ROOT.parent / "castle_profiles.json").read_text())
    for name, prior in first["footprints"].items():
        assert shape(prior["geometry"]).equals(shape(packet["footprints"][name]["geometry"])), name
    # A union can rotate the starting vertex; preserve the original serial representation.
    packet["footprints"] = first["footprints"]
    exchange.write_text(json.dumps(packet,separators=(",",":"))+"\n",encoding="utf-8")
    former = {f["id"]:f for f in first["features"]}
    current = {f["id"]:f for f in packet["features"]}
    changed = sorted(k for k in former if former[k] != current[k])
    assert changed == ["left-scroll","right-scroll"], changed
    new = sorted(set(current)-set(former))
    assert new == ["rose-left-petal","rose-outer-petal","rose-spiral-petal"]
    geo = {k:shape(v["geometry"]) for k,v in current.items()}
    assert all(g.is_valid for g in geo.values())
    rose = unary_union([geo[k] for k in new])
    assert shape(packet["footprints"]["head"]["geometry"]).covers(rose)
    controls = ["mickey","left-scroll","right-scroll","gatehouse","inner-lip"]
    clearances = {k:round(rose.distance(geo[k]),3) for k in controls}
    assert all(v > .65 for v in clearances.values()), clearances
    report = {
        "changed_prior_features":changed, "added_features":new, "profiles":len(current),
        "protected_footprints_identical":True,
        "rose_bounds_mm":[round(v,3) for v in rose.bounds],
        "rose_width_height_mm":[round(rose.bounds[i+2]-rose.bounds[i],3) for i in (0,1)],
        "petal_areas_mm2":{k:round(geo[k].area,2) for k in new},
        "petal_minimum_separations_mm":{a+" to "+b:round(geo[a].distance(geo[b]),3) for i,a in enumerate(new) for b in new[i+1:]},
        "rose_edge_separations_mm":clearances,
        "rose_center_x_offset_from_mickey_mm":round((rose.bounds[0]+rose.bounds[2]-geo["mickey"].bounds[0]-geo["mickey"].bounds[2])/2,3),
    }
    print(json.dumps(report,indent=2))
    (ROOT/"rose_checks.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    front = art.render(features)
    save_closeup(front)


if __name__ == "__main__":
    main()
