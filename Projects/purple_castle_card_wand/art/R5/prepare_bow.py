"""Build and check the bow and paired curls relative to the frozen R4 artwork."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter
from shapely.geometry import Point, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
R4 = ROOT.parent/"R4"
sys.dont_write_bytecode = True
sys.path.insert(0,str(ROOT.parent/"R3"))
import prepare_curls as rendering

CAMERA = 2.2*.78
PX_PER_MM = CAMERA/rendering.art.SCALE
SOURCE_HASH = "97320e79c886e506b5418e60d2dbbe786060c6c2c9db1c81310e0af0a00af00a"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_and_freeze():
    packet_path = ROOT/"castle_profiles.json"
    packet = json.loads(packet_path.read_text())
    prior = json.loads((R4/packet_path.name).read_text())
    assert digest(R4/packet_path.name) == "506a68c9d413922524dd216000a3c26faeefed100b47a954a3bdd5c36c72efdd"
    old = {item["id"]:item for item in prior["features"]}
    new = {item["id"]:item for item in packet["features"]}
    changed = [k for k in old if old[k] != new[k]]
    assert old.keys() == new.keys()
    assert set(changed) == {"left-scroll","right-scroll","left-loop","right-loop","knot","left-fold-floor","right-fold-floor","left-tail","right-tail"}
    for name in ("head","handle"):
        fp = prior["footprints"][name]
        assert shape(fp["geometry"]).equals(shape(packet["footprints"][name]["geometry"]))
        packet["footprints"][name] = fp
    packet["revision"] = "R5 provisional · last-reference bow and paired curls"
    packet["surface_intent"] = {"file":"relief_map.json","sha256":digest(ROOT/"relief_map.json")}
    packet_path.write_text(json.dumps(packet,separators=(",",":"))+"\n",encoding="utf-8")
    g = {k:shape(v["geometry"]) for k,v in new.items()}
    assert all(v.is_valid for v in g.values()) and "mickey" in g and not any(k.startswith("rose-") for k in g)
    bow = shape(packet["footprints"]["bow"]["geometry"])
    curls = unary_union([g["left-scroll"],g["right-scroll"]])
    def bounds_geom(geo):
        return [round(v,3) for v in geo.bounds]
    result = {"changed":changed,"total_profiles":len(g),"identical_retained_profiles":len(g)-len(changed),
        "head_and_handle_footprints_identical":True,
        "bow_bounds_mm":bounds_geom(bow),"curl_bounds_mm":bounds_geom(curls),"loop_bounds_mm":bounds_geom(g["left-loop"]),
        "left_crease_bounds_mm":bounds_geom(g["left-fold-floor"]),"knot_bounds_mm":bounds_geom(g["knot"]),
        "curl_to_curl_mm":round(g["left-scroll"].distance(g["right-scroll"]),3),
        "curls_to_bow_mm":round(curls.distance(bow),3),"curl_to_knot_mm":round(curls.distance(g["knot"]),3),
        "curls_to_inner_lip_mm":round(curls.distance(g["inner-lip"]),3),
        "curls_to_mickey_mm":round(curls.distance(g["mickey"]),3),
        "ring_to_tail_clearance_mm":round(bow.distance(g["top-collar"]),3),
        "mounts":{}}
    for name,x in (("left",-20),("right",20)):
        center = Point(x,-53)
        keepout = center.buffer(3.65,quad_segs=64)
        assert g[name+"-loop"].covers(keepout) and bow.covers(keepout) and curls.disjoint(keepout)
        result["mounts"][name] = {"center_mm":[x,-53],"bow_outer_edge_to_pad_center_mm":round(bow.boundary.distance(center),3),
            "bow_margin_beyond_3_65_mm_keepout_mm":round(bow.boundary.distance(center)-3.65,3),
            "curl_to_3_65_mm_keepout_mm":round(curls.distance(keepout),3)}
    assert result["curl_to_curl_mm"]>1.5 and result["curls_to_bow_mm"]>1.0 and result["curls_to_inner_lip_mm"]>.9
    print(json.dumps(result,indent=2))
    (ROOT/"bow_checks.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


def soft_bow(front,features):
    # Visualize the shallow ribbon depression and padded edge, using the same silhouette and depth targets.
    window = (260,706,787,1045)
    width,height = window[2]-window[0],window[3]-window[1]
    masks = {}
    for feature in features:
        if feature["part"] != "bow":
            continue
        mask = Image.new("L",(width,height))
        draw = ImageDraw.Draw(mask)
        def pointlist(ring):
            return [((x-5)*CAMERA-window[0],(y-16)*CAMERA-window[1]) for x,y in ring.coords]
        for piece in rendering.art.polys(feature["source_geometry"]):
            draw.polygon(pointlist(piece.exterior),255)
            for hole in piece.interiors:
                draw.polygon(pointlist(hole),0)
        masks[feature["id"]] = np.asarray(mask)>0
    union = np.logical_or.reduce(list(masks.values()))
    specs = {k:spec for spec in json.loads((ROOT/"relief_map.json").read_text())["profiles"] for k in spec["ids"]}
    heightmap = np.zeros((height,width),dtype=float)
    occlusion = np.zeros_like(heightmap)
    for key in ("left-tail","right-tail","left-loop","right-loop","knot"):
        region = masks[key].copy()
        if key.endswith("loop"):
            fold = masks[key.replace("loop","fold-floor")]
            region |= fold
        d = distance_transform_edt(region)/PX_PER_MM
        spec = specs[key]
        spread = max(spec["rise_run"],d.max()*.85)
        z = spec["edge"] + (spec["crest"]-spec["edge"])*np.sin(np.pi*.5*np.clip(d/spread,0,1))
        if key.endswith("loop"):
            # Feather the recess locally so its pinched end flows into the knot.
            df = distance_transform_edt(~fold)/PX_PER_MM
            recess = np.exp(-.5*(df/1.35)**2)
            z = z*(1-recess) + specs[key.replace("loop","fold-floor")]["edge"]*recess
        if "tail" not in key:
            contact = gaussian_filter(region.astype(float),sigma=3)
            occlusion = np.maximum(occlusion,contact*.18)
        heightmap[region] = z[region]
        occlusion[region] = 0.
    z = gaussian_filter(heightmap,1.55)
    dy,dx = np.gradient(z,1/PX_PER_MM)
    norm = np.sqrt(1.+dx*dx+dy*dy)
    diffuse = (.42*dx+.47*dy+.77)/norm
    specular = np.maximum(0.,(.24*dx+.28*dy+.93)/norm)**14
    rgb = np.array([231,93,145],dtype=float)[None,None,:]*(.67+.43*diffuse-occlusion)[:,:,None]+18*specular[:,:,None]
    lit = Image.fromarray(np.clip(rgb,0,255).astype(np.uint8),"RGB")
    # A soft perimeter keeps the R3 renderer's subpixel antialiasing.
    creases = masks["left-fold-floor"] | masks["right-fold-floor"]
    from_crease = distance_transform_edt(~creases)/PX_PER_MM
    blend = np.clip((distance_transform_edt(union)-.45)/2.0,0,1)*(.52+.32*np.exp(-.5*(from_crease/1.4)**2))
    result = front.copy()
    result.paste(lit,window[:2],Image.fromarray((blend*255).astype(np.uint8)))
    return result


def previews(features):
    front = soft_bow(rendering.relief_preview(features),features)
    front.save(ROOT/"castle_front.png",dpi=(172,172))
    box = tuple(round((v-offset)*CAMERA) for v,offset in zip((137,351,483,611),(5,16,5,16)))
    close = front.crop(box)
    close.save(ROOT/"bow_and_curls_detail.png",dpi=(172,172))
    source = Path.home()/"Downloads"/"f9a08a26-a8cc-4ed7-9b47-2e09e868a6c1.png"
    if not source.is_file():
        return
    assert digest(source)==SOURCE_HASH
    ref = Image.open(source).convert("RGB").crop((325,413,698,693))
    panel = (553,415)
    sheet = Image.new("RGB",(1154,480),"#faf9f7")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",23)
    sheet.paste(ref.resize(panel,Image.Resampling.LANCZOS),(16,51))
    close = close.resize(panel,Image.Resampling.LANCZOS)
    sheet.paste(close,(585,51),close.getchannel("A"))
    draw.text((17,10),"Latest reference",fill="#30203a",font=font)
    draw.text((585,10),"R5 · fitted bow and curls",fill="#30203a",font=font)
    sheet.save(ROOT/"reference_comparison.png")


if __name__=="__main__":
    rendering.ROOT = ROOT
    rendering.art.ROOT,rendering.art.MASTER = ROOT,ROOT/"castle_front.svg"
    fs = rendering.art.profiles()
    rendering.art.export(fs)
    verify_and_freeze()
    previews(fs)
