"""Sample the hand-drawn SVG in millimeters and light its relief for the fitted front."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter
from shapely import affinity
from shapely.geometry import Polygon, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from svgpathtools import parse_path
from svgpathtools.parser import parse_transform


ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "castle_front.svg"
SCALE = 140.0 / 552.0
NS = "{http://www.w3.org/2000/svg}"
HREF = "{http://www.w3.org/1999/xlink}href"
PALETTE = {
    "#8343a4": "purple",
    "#f4be4e": "gold",
    "#ffefd5": "cream",
    "#55a6de": "blue",
    "#e75d91": "pink",
}


def polygon_from_path(data):
    result = Polygon()
    for contour in parse_path(data).continuous_subpaths():
        if not contour.isclosed():
            raise ValueError("Open contour")
        points = []
        for segment in contour:
            length = segment.length()
            if not length:
                continue
            intervals = max(1, math.ceil(length / 2.1)) if type(segment).__name__ != "Line" else 1
            for i in range(intervals):
                pt = segment.point(i / intervals)
                points.append((pt.real, pt.imag))
        ring = Polygon(points)
        if not ring.is_valid:
            raise ValueError("Invalid drawn contour: " + data[:80])
        result = result.symmetric_difference(ring)
    return result


def profiles():
    root = ET.parse(MASTER).getroot()
    defs = {node.get("id"): node.get("d") for node in root.iter(NS + "path")}
    features = []
    for layer in root.findall(NS + "g"):
        for node in layer:
            name = node.get("id")
            data = node.get("d") or defs[node.get(HREF).lstrip("#")]
            geom = polygon_from_path(data)
            if node.get("data-cut"):
                geom = geom.difference(polygon_from_path(defs[node.get("data-cut")]))
            if node.get("transform"):
                m = parse_transform(node.get("transform"))
                geom = affinity.affine_transform(geom, [m[0, 0], m[0, 1], m[1, 0], m[1, 1], m[0, 2], m[1, 2]])
            if geom.is_empty or not geom.is_valid:
                raise ValueError(name)
            features.append({
                "id": name, "part": layer.get("data-part"), "color": PALETTE[node.get("fill")],
                "hex": node.get("fill"), "relief_mm": float(node.get("data-h")), "source_geometry": geom,
            })
    return features


def in_mm(geom):
    return affinity.affine_transform(geom, [SCALE, 0, 0, -SCALE, -310 * SCALE, 301 * SCALE])


def polys(geom):
    return list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]


def encode_poly(geom):
    def ring(coords):
        return [[round(x, 4), round(y, 4)] for x, y in coords]

    pieces = []
    for piece in polys(geom):
        geo = mapping(orient(piece, sign=1.0))
        pieces.append([ring(loop) for loop in geo["coordinates"]])
    if len(pieces) == 1:
        return {"type": "Polygon", "coordinates": pieces[0]}
    return {"type": "MultiPolygon", "coordinates": pieces}


def export(features):
    by_id = {item["id"]: in_mm(item["source_geometry"]) for item in features}
    footprints = {part: unary_union([by_id[f["id"]] for f in features if f["part"] == part]) for part in ("head", "bow", "handle")}
    packet = {
        "revision": "R1 provisional", "source_svg_sha256": hashlib.sha256(MASTER.read_bytes()).hexdigest(),
        "units": "mm", "axes": "front XY; +X right, +Y toward tip, +Z toward observer",
        "source_pixel_origin": [310, 301], "mm_per_source_px": SCALE,
        "polygon_encoding": "GeoJSON hierarchy. Exterior CCW and hole CW; all rings closed. Transforms already baked.",
        "relief": "Each head height is absolute millimeters above the purple carrier face. Where raised shapes overlap, the highest surface wins; for equal heights later features win. The bow uses a separate local datum and requires a continuous backing. Handle profiles describe the visible envelope, not the thread or card retainer.",
        "palette": {name: color for color, name in PALETTE.items()},
        "footprints": {part: {"bounds_mm": [round(float(x), 4) for x in geo.bounds], "geometry": encode_poly(geo)} for part, geo in footprints.items()},
        "features": [{**{k:v for k,v in feature.items() if k != "source_geometry"}, "geometry": encode_poly(by_id[feature["id"]])} for feature in features],
    }
    (ROOT / "castle_profiles.json").write_text(json.dumps(packet, separators=(",", ":")) + "\n", encoding="utf-8")
    return by_id, footprints


def render(features):
    # A common front orthographic camera. Shading derives only from the supplied color areas and relief.
    factor = 2.2
    u0, v0, u1, v1 = 5, 16, 615, 1516
    size = round((u1 - u0) * factor), round((v1 - v0) * factor)
    canvas = Image.new("RGBA", size)
    for feature in features:
        geom = feature["source_geometry"]
        xmin, ymin, xmax, ymax = geom.bounds
        padding = 17
        width = math.ceil((xmax-xmin+2*padding)*factor)
        height = math.ceil((ymax-ymin+2*padding)*factor)
        mask = Image.new("L", (width, height))
        draw = ImageDraw.Draw(mask)
        def points(ring):
            return [((x-xmin+padding)*factor, (y-ymin+padding)*factor) for x,y in ring.coords]
        for piece in polys(geom):
            draw.polygon(points(piece.exterior), 255)
            for hole in piece.interiors:
                draw.polygon(points(hole), 0)
        name, part = feature["id"], feature["part"]
        distance = distance_transform_edt(np.asarray(mask) > 0) / factor
        bevel = {"carrier": 5, "rim-outer": 9, "inner-lip": 4, "star-field": 4,
                 "grip": 42, "neck": 50, "knot": 19, "mickey": 3}.get(name, 4.5)
        if part == "bow" and "loop" in name:
            bevel = 21
        elif part == "bow" and "tail" in name:
            bevel = 11
        elif part == "handle" and "grip" != name and "neck" != name:
            bevel = 14
        if name in ("left-scroll","right-scroll"):
            bevel = 6.5
        # A rounded leading edge and a broad, continuous plateau.
        ratio = np.clip(distance / bevel, 0, 1)
        plateau = np.sqrt(np.maximum(0.0, 2*ratio-ratio**2)) * bevel * .80
        smooth = gaussian_filter(plateau, 1.35*factor)
        sy, sx = np.gradient(smooth, 1/factor)
        ny, nx, nz = sy, sx, 1.0
        xgrid = np.arange(width)[None,:] / factor + xmin - padding
        ygrid = np.arange(height)[:,None] / factor + ymin - padding
        if name in ("grip", "neck"):
            radius = 47.0 if name == "grip" else 68.0
            u = np.clip((310 - xgrid) / radius, -.97, .97)
            axial = np.clip((ygrid-1441)/52,0,.98) if name == "grip" else np.zeros_like(ygrid)
            nx = u / np.sqrt(np.maximum(.045, 1-u*u))
            ny = -axial / np.sqrt(np.maximum(.045, 1-axial*axial))
        if name.endswith("-roof"):
            center = (xmin+xmax)/2
            width_fraction = np.clip((ygrid-ymin)/(ymax-ymin), 0, 1)
            local_radius = (xmax-xmin)*.5*(.12+.88*width_fraction)
            roll = np.clip((center-xgrid)/local_radius,-.94,.94)
            nx = .65*nx + .38*roll / np.sqrt(1-roll*roll)
        if "fold-floor" in name:
            nx, ny = -sx, -sy
        length = np.sqrt(nx*nx + ny*ny + nz*nz)
        diffuse = (nx*.42 + ny*.59 + nz*.69) / length
        half = (nx*.24 + ny*.36 + nz*.90) / length
        color = np.array([int(feature["hex"][i:i+2],16) for i in (1,3,5)], dtype=float)
        shine = np.clip(half, 0.0, 1.0) ** 19 * (52 if feature["color"] == "gold" else 25)
        shade = .54 + .64 * diffuse
        if name == "star-field":
            shade += .05 - .065*((xgrid-310)/210)**2 - .08*((ygrid-320)/250)**2
        # The lower field and fold hollows sit in the shadow of their same-color raised lips.
        if name in ("star-field","left-fold-floor","right-fold-floor"):
            shade -= (.12 if name == "star-field" else .16) * np.exp(-distance/4.5)
        if "fold-floor" in name:
            shade -= .10
        values = np.clip(shade[:,:,None] * color[None,None,:] + shine[:,:,None],0,255).astype(np.uint8)
        lit = Image.fromarray(values, "RGB").convert("RGBA")
        lit.putalpha(mask)
        loc = round((xmin-u0-padding)*factor), round((ymin-v0-padding)*factor)
        # Shadow is clipped to previously drawn components; the outer background stays transparent.
        if name not in ("carrier","star-field","grip","left-fold-floor","right-fold-floor"):
            depth = feature["relief_mm"]
            if part == "bow" and "tail" in name:
                depth = 3.0
            blur = max(1.0, (1.6+depth*.30)*factor)
            shadow_mask = mask.filter(ImageFilter.GaussianBlur(blur))
            off = (loc[0]+round((1+depth*.35)*factor),loc[1]+round((1.5+depth*.80)*factor))
            backing = canvas.crop((off[0],off[1],off[0]+width,off[1]+height))
            shadow_alpha = np.minimum(np.asarray(backing.getchannel("A")), np.asarray(shadow_mask))*.40
            shadow = Image.new("RGBA",(width,height),(31,14,38,0))
            shadow.putalpha(Image.fromarray(shadow_alpha.astype(np.uint8)))
            canvas.alpha_composite(shadow,off)
        canvas.alpha_composite(lit,loc)
    final = canvas.resize((round(size[0]*.78),round(size[1]*.78)),Image.Resampling.LANCZOS)
    final.save(ROOT / "castle_front.png", dpi=(round(25.4 * factor*.78/SCALE),)*2)
    return final


def comparison(front):
    original = Path.home() / "Downloads" / "Purple Princess Castle Star Card Holder.png"
    if not original.is_file():
        return
    if hashlib.sha256(original.read_bytes()).hexdigest() != "7bc385172dd12f27c5db3c5a4ac074e6180b9d2eaedc718e8975f2fbe632e03e":
        raise ValueError("Comparison source hash changed")
    bounds = (21, 25, 600, 731)
    ref = Image.open(original).convert("RGB").crop(bounds)
    view_scale = 2.2 * .78
    zoom = front.crop(tuple(round((v-offset) * view_scale) for v,offset in zip(bounds, (5,16,5,16)))).resize(ref.size,Image.Resampling.LANCZOS)
    paper = Image.new("RGB",ref.size,"white")
    paper.paste(zoom,mask=zoom.getchannel("A"))
    sheet = Image.new("RGB",(1218,797),"#faf9f7")
    sheet.paste(ref,(20,64))
    sheet.paste(paper,(619,64))
    draw = ImageDraw.Draw(sheet)
    for x,label in ((25,"Original reference"),(624,"Castle wand · R1")):
        draw.text((x,20), label, fill="#2f2039",font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",24))
    bar_end = 626 + round(20 / SCALE)
    draw.line((626,784,bar_end,784), fill="#584d5c",width=2)
    draw.line((626,779,626,787), fill="#584d5c",width=2)
    draw.line((bar_end,779,bar_end,787), fill="#584d5c",width=2)
    draw.text((bar_end+8,774),"20 mm",fill="#584d5c",font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf",14))
    sheet.save(ROOT / "reference_review.png")


def main():
    facets = profiles()
    by_id, footprints = export(facets)
    front = render(facets)
    comparison(front)
    print("Closed SVG profiles", len(facets))
    for part, geo in footprints.items():
        print(part, geo.geom_type, "bounds mm", [round(v,2) for v in geo.bounds])
    print("Mickey width, height mm", [round(a-b,2) for a,b in zip(by_id["mickey"].bounds[2:],by_id["mickey"].bounds[:2])])
    print("Gold scroll separation mm", round(by_id["left-scroll"].distance(by_id["right-scroll"]),3))
    print("Bow, fixed star projected overlap mm²", round(footprints["head"].intersection(footprints["bow"]).area,2))


if __name__ == "__main__":
    main()
