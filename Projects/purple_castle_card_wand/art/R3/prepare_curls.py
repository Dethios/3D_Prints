"""Build the R3 mirrored curl artwork, preview its relief, and check R2 compatibility."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter
from shapely.affinity import scale as reflect
from shapely.geometry import LineString, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
R2 = ROOT.parent / "R2"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT.parent))
import prepare_art as art


def check_packet():
    exchange = ROOT / "castle_profiles.json"
    packet = json.loads(exchange.read_text())
    prior = json.loads((R2 / exchange.name).read_text())
    previous = {f["id"]: f for f in prior["features"]}
    current = {f["id"]: f for f in packet["features"]}
    changed = sorted(k for k in current if current[k] != previous[k])
    assert current.keys() == previous.keys() and changed == ["left-scroll","right-scroll"]
    for name, fp in prior["footprints"].items():
        assert shape(fp["geometry"]).equals(shape(packet["footprints"][name]["geometry"]))
    packet["footprints"] = prior["footprints"]
    packet["revision"] = "R3 provisional · single curled flourishes and soft relief"
    packet["surface_intent"] = {"file":"relief_map.json","sha256":hashlib.sha256((ROOT/"relief_map.json").read_bytes()).hexdigest()}
    exchange.write_text(json.dumps(packet,separators=(",",":"))+"\n",encoding="utf-8")
    geom = {k:shape(f["geometry"]) for k,f in current.items()}
    assert all(g.is_valid for g in geom.values())
    rose = unary_union([g for k,g in geom.items() if k.startswith("rose-")])
    left,right = (geom[k] for k in changed)
    assert reflect(left,xfact=-1,yfact=1,origin=(0,0)).equals(right)
    reference_area = shape(previous["left-scroll"]["geometry"]).area + shape(previous["right-scroll"]["geometry"]).area
    cuts = {}
    # Fixed vertical sections through the crest and the terminal turn. The latter includes two runs.
    for x in (-25., -29., -31.):
        hit = left.intersection(LineString([(x,-50),(x,-15)]))
        parts = list(hit.geoms) if hasattr(hit,"geoms") else [hit]
        cuts[str(x)] = [round(o.length,3) for o in parts]
    checks = {
        "changed_prior_features":changed,"profiles":len(current),"protected_footprints_identical":True,
        "exact_mirror":True, "each_curl_area_mm2":round(left.area,2),
        "gold_area_change_percent":round(100*((left.area+right.area)/reference_area-1),2),
        "left_bounds_mm":[round(v,3) for v in left.bounds], "paired_tip_gap_mm":round(left.distance(right),3),
        "rose_gap_left_right_mm":[round(x.distance(rose),3) for x in (left,right)],
        "purple_lip_gap_mm":round(left.distance(geom["inner-lip"]),3),
        "vertical_material_sections_mm":cuts,
    }
    assert min(checks["rose_gap_left_right_mm"]) > 1.3
    (ROOT/"curl_checks.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(checks,indent=2))


def relief_preview(features):
    image = art.render(features)
    relief = json.loads((ROOT/"relief_map.json").read_text())
    settings = {key:spec for spec in relief["profiles"] for key in spec["ids"]}
    camera = 2.2*.78
    px_per_mm = camera/art.SCALE
    tone = np.ones((image.height,image.width),dtype=np.float32)
    for feature in features:
        g = feature["source_geometry"]
        lo_x,lo_y,hi_x,hi_y = g.bounds
        x0,y0 = max(0,int((lo_x-5)*camera)-4),max(0,int((lo_y-16)*camera)-4)
        x1,y1 = min(image.width,int((hi_x-5)*camera)+6),min(image.height,int((hi_y-16)*camera)+6)
        mask = Image.new("L",(x1-x0,y1-y0))
        draw = ImageDraw.Draw(mask)
        def points(ring):
            return [((x-5)*camera-x0,(y-16)*camera-y0) for x,y in ring.coords]
        for piece in art.polys(g):
            draw.polygon(points(piece.exterior),255)
            for hole in piece.interiors:
                draw.polygon(points(hole),0)
        inside = np.asarray(mask) > 0
        region = tone[y0:y1,x0:x1]
        spec = settings.get(feature["id"])
        if spec is None or spec["edge"] == spec["crest"]:
            region[inside] = 1.
            continue
        distance = distance_transform_edt(inside)/px_per_mm
        t = np.clip(distance/spec["rise_run"],0.,1.)
        roll = np.sin(.5*np.pi*t)
        if feature["id"].endswith(("-tower","-roof")) or feature["id"] == "keep":
            xs = ((np.arange(x0,x1)[None,:]/camera+5)-(lo_x+hi_x)/2)/((hi_x-lo_x)/2)
            roll *= .72 + .28*np.sqrt(np.maximum(0.,1.-xs*xs))
        heights = roll*(spec["crest"]-spec["edge"])
        dy,dx = np.gradient(gaussian_filter(heights,1.05),1/px_per_mm)
        gain = np.clip(1.+.49*dx+.60*dy,.70,1.22)
        region[inside] = gain[inside]
    rgba = np.array(image)
    rgba[:,:,:3] = np.clip(rgba[:,:,:3]*tone[:,:,None],0,255).astype(np.uint8)
    result = Image.fromarray(rgba,"RGBA")
    result.save(ROOT/"castle_front.png",dpi=(172,172))
    return result


def detail(front):
    scale = 2.2*.78
    crop = tuple(round((x-v)*scale) for x,v in zip((140,202,480,680),(5,16,5,16)))
    close = front.crop(crop)
    close.save(ROOT/"castle_and_bow_detail.png",dpi=(172,172))
    ref = Path.home()/"Downloads"/"90eee49b-97de-46a8-a598-33028244eb61.png"
    if not ref.is_file():
        return
    assert hashlib.sha256(ref.read_bytes()).hexdigest() == "3ac6ee50c094525a4e2d040035288a83ba64c01c51663e2ed9b4d908452fc090"
    sheet = Image.new("RGB",(1152,240),"#faf9f7")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",22)
    ref_crop = Image.open(ref).convert("RGB").crop((390,351,692,507))
    artistic_crop = tuple(round((x-v)*scale) for x,v in zip((141,354,479,529),(5,16,5,16)))
    former = Image.open(R2/"castle_front.png").crop(artistic_crop)
    images = [("Curl reference",ref_crop),("R2",former),("R3",front.crop(artistic_crop))]
    for i,(label,panel) in enumerate(images):
        x = 12+i*380
        draw.text((x,9),label,font=font,fill="#30203a")
        panel = panel.resize((368,190),Image.Resampling.LANCZOS)
        sheet.paste(panel,(x,42),panel.getchannel("A") if panel.mode=="RGBA" else None)
    sheet.save(ROOT/"curl_comparison.png")


if __name__ == "__main__":
    art.ROOT,art.MASTER = ROOT,ROOT/"castle_front.svg"
    features = art.profiles()
    art.export(features)
    check_packet()
    detail(relief_preview(features))
