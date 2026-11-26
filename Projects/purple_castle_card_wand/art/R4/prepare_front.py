"""Rebuild the R4 doorway and check its geometry and final raster against frozen R3."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
R3 = ROOT.parent / "R3"
sys.dont_write_bytecode = True
sys.path.insert(0,str(R3))
import prepare_curls as rendering


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert digest(R3/"castle_profiles.json") == "88a6f184d527f653d4a63e7e9ba1386a475350a14dbce7817cd2d8bbab21469b"
    assert digest(ROOT/"relief_map.json") == digest(R3/"relief_map.json")
    rendering.ROOT = ROOT
    art = rendering.art
    art.ROOT, art.MASTER = ROOT, ROOT/"castle_front.svg"
    features = art.profiles()
    art.export(features)
    exchange = ROOT/"castle_profiles.json"
    packet = json.loads(exchange.read_text())
    prior = json.loads((R3/"castle_profiles.json").read_text())
    removed = {"rose-left-petal","rose-outer-petal","rose-spiral-petal"}
    assert removed == {f["id"] for f in prior["features"]}-{f["id"] for f in packet["features"]}
    assert packet["features"] == [f for f in prior["features"] if f["id"] not in removed]
    for name,fp in prior["footprints"].items():
        assert shape(fp["geometry"]).equals(shape(packet["footprints"][name]["geometry"]))
    packet.update(revision="R4 provisional · clear doorway",footprints=prior["footprints"],surface_intent=prior["surface_intent"])
    exchange.write_text(json.dumps(packet,separators=(",",":"))+"\n",encoding="utf-8")
    former_rose = unary_union([shape(f["geometry"]) for f in prior["features"] if f["id"] in removed])
    for f in packet["features"]:
        geom = shape(f["geometry"])
        assert geom.is_valid
        if f["id"] == "star-field":
            assert geom.covers(former_rose)
        elif f["part"] == "head" and f["relief_mm"] > 0:
            assert geom.disjoint(former_rose)
    new = rendering.relief_preview(features)
    old = Image.open(R3/"castle_front.png").convert("RGBA")
    current, previous = np.asarray(new), np.asarray(old)
    assert np.array_equal(current[:,:,3],previous[:,:,3])
    ys,xs = np.nonzero(np.any(current != previous,axis=2))
    pixel_box = [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    # Loosely bound the prior ornament and its projected preview shadow.
    assert 450 <= pixel_box[0] and 620 <= pixel_box[1] and pixel_box[2] <= 610 and pixel_box[3] <= 800, pixel_box
    scale = 2.2*.78
    crop = tuple(round((x-v)*scale) for x,v in zip((138,218,482,640),(5,16,5,16)))
    new.crop(crop).save(ROOT/"doorway_detail.png",dpi=(172,172))
    checks = {"removed":sorted(removed),"retained_features_exact":len(packet["features"]),
        "previous_petals_area_mm2":round(former_rose.area,3),"exposed_material":"purple star-field",
        "three_footprints_identical":True,"relief_file_identical":True,"alpha_identical":True,
        "preview_changed_pixels":len(xs),"preview_change_bounds_px":pixel_box}
    (ROOT/"doorway_checks.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
    print(checks)


if __name__=="__main__":
    main()
