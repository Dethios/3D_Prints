"""Convert the compact front and measure each flag against the actual lip, rim and roof."""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.affinity import scale
from shapely.geometry import LineString, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
R5 = ROOT.parent/"R5"
sys.dont_write_bytecode = True
sys.path.insert(0,str(R5))
import prepare_bow as bow

WIDTH = 130.0
GRID = WIDTH/552
CAMERA = 2.2*.78


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    prior_path = R5/"castle_profiles.json"
    assert digest(prior_path) == "a6031a4b9d68d8ecbbac9994e19b6778341c953fbc49caba2d2faa16387127dd"
    assert digest(R5/"relief_map.json") == digest(ROOT/"relief_map.json")
    prior = json.loads(prior_path.read_text())
    output = ROOT/"castle_profiles.json"
    packet = json.loads(output.read_text())
    packet["revision"] = "R6 provisional · 130 mm head and inset pennants"
    packet["surface_intent"] = prior["surface_intent"]
    output.write_text(json.dumps(packet,separators=(",",":"))+"\n",encoding="utf-8")
    old = {r["id"]:r for r in prior["features"]}
    own = {r["id"]:r for r in packet["features"]}
    assert own.keys() == old.keys()
    g = {k:shape(f["geometry"]) for k,f in own.items()}
    differences = {}
    for k,f in own.items():
        geom = g[k]
        assert geom.is_valid and not geom.is_empty
        assert all(f[t]==old[k][t] for t in ("part","hex","color","relief_mm"))
        expected = scale(shape(old[k]["geometry"]),WIDTH/140,WIDTH/140,origin=(0,0))
        differences[k] = geom.hausdorff_distance(expected)
    changed = {k for k,d in differences.items() if d>.001}
    assert changed == {s+"-"+kind for s in ("left","right","high") for kind in ("flag","roof")}
    head,bow_shape,handle = [shape(packet["footprints"][p]["geometry"]) for p in ("head","bow","handle")]
    assert abs(head.bounds[2]-head.bounds[0]-WIDTH)<.001
    def vals(seq):
        return [round(x,3) for x in seq]
    stats = {
        "mm_per_master_unit":GRID,"xy_scale_from_R5":WIDTH/140,
        "head_xy_bounds_mm":vals(head.bounds),"bow_xy_bounds_mm":vals(bow_shape.bounds),
        "handle_appearance_xy_bounds_mm":vals(handle.bounds),"profiles":len(own),
        "resculpted_beyond_uniform_scale":sorted(changed),
        "largest_profile_deviation_of_other_28_mm":round(max(d for k,d in differences.items() if k not in changed),6),
        "relief_targets_byte_identical_to_R5":True,"flags":{},
        "projected_bow_overlap_with_star_mm2":round(bow_shape.intersection(head).area,2),
        "projected_loop_overlap_with_star_mm2":{s:round(g[s+"-loop"].intersection(head).area,2) for s in ("left","right")},
        "decor_to_bow_min_xy_gap_mm":round(unary_union([g["left-scroll"],g["right-scroll"]]).distance(bow_shape),3),
    }
    for s,row in (("left",248),("high",161),("right",248)):
        flag,roof = g[s+"-flag"],g[s+"-roof"]
        y=(301-row)*GRID
        staff_width = flag.intersection(LineString([(-65,y),(65,y)])).length
        overlap = flag.intersection(roof)
        item = {
            "flag_bounds_mm":vals(flag.bounds),"purple_lip_gap_mm":round(flag.distance(g["inner-lip"]),3),
            "gold_rim_gap_mm":round(flag.distance(g["rim-outer"]),3),
            "staff_width_mm":round(staff_width,3),"staff_section_at_master_y":row,
            "intended_gold_to_blue_overlap_mm2":round(overlap.area,3),
            "overlap_height_mm":round(overlap.bounds[3]-overlap.bounds[1],3),
        }
        assert item["purple_lip_gap_mm"]>=2.5 and g["star-field"].covers(flag)
        assert item["staff_width_mm"]>=2.0 and item["overlap_height_mm"]>=1.2
        stats["flags"][s] = item
    (ROOT/"compact_checks.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats,indent=2))


def previews(features):
    front = bow.soft_bow(bow.rendering.relief_preview(features),features)
    dpi = round(CAMERA/GRID*25.4)
    front.save(ROOT/"castle_front.png",dpi=(dpi,dpi))
    clip = tuple(round((v-off)*CAMERA) for v,off in zip((176,61,449,306),(5,16,5,16)))
    detail = front.crop(clip)
    detail.save(ROOT/"flag_clearance_detail.png",dpi=(dpi,dpi))
    old = Image.open(R5/"castle_front.png").convert("RGBA").crop(clip)
    page = Image.new("RGB",(987,489),"#faf9f7")
    draw = ImageDraw.Draw(page)
    face = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",22)
    for x,label,pic in ((16,"R5 · 140 mm",old),(507,"R6 · 130 mm",detail)):
        draw.text((x,10),label,fill="#30203a",font=face)
        page.paste(pic,(x,52),pic.getchannel("A"))
    page.save(ROOT/"flag_comparison.png")


if __name__=="__main__":
    bow.ROOT = ROOT
    bow.rendering.ROOT = ROOT
    art = bow.rendering.art
    art.SCALE = GRID
    bow.PX_PER_MM = CAMERA/GRID
    art.ROOT,art.MASTER = ROOT,ROOT/"castle_front.svg"
    bits = art.profiles()
    art.export(bits)
    freeze()
    previews(bits)
