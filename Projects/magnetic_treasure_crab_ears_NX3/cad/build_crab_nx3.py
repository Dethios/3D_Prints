"""Build the image-traced crab faces on the approved, unscaled NX3 mounts."""
from pathlib import Path
import hashlib
import json
import math

import manifold3d as md
import numpy as np
from PIL import Image, ImageColor
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from svgpathtools import parse_path
import trimesh

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT.parent / "sorcerer_ears_CAD_STL_v2"
NX3 = APPROVED / "STL" / "NX3"
STEP = APPROVED / "CAD" / "NX3"
STL = ROOT / "stl"
SEAT_Z = 10.10
PINS = [(-17, 8.8), (17, 8.8)]
CENTER = (0, 38.79776)
PALETTE = {
    "rim": "#572796", "edge": "#9f5ad8", "shadow": "#45216e",
    "claw": "#9d4fc2", "violet": "#7c3abe", "gold": "#eaa222",
    "bright": "#ffd369", "ochre": "#b87618", "pink": "#f3a7c6",
    "purple_gem": "#893bb4", "blue_gem": "#317cca", "sclera": "#fff0cc",
    "iris": "#65338a", "pupil": "#21112d", "shine": "#fff9ea", "band": "#302044",
}


def union(parts):
    return md.Manifold.batch_boolean(parts, md.OpType.Add)


def mesh(solid):
    data = solid.to_mesh64()
    return trimesh.Trimesh(data.vert_properties[:, :3], data.tri_verts, process=False)


def solid(source):
    m = trimesh.load_mesh(source) if isinstance(source, Path) else source
    result = md.Manifold(md.Mesh64(np.array(m.vertices, dtype=np.float64),
                                    np.array(m.faces, dtype=np.uint64)))
    assert result.status() == md.Error.NoError, source
    return result


def polygons(shape):
    if shape.is_empty:
        return
    if shape.geom_type == "Polygon":
        yield orient(shape)
    else:
        for p in shape.geoms:
            if p.geom_type == "Polygon":
                yield orient(p)


def section(shape):
    contours = []
    for p in polygons(shape):
        contours.extend(np.asarray(r.coords)[:-1] for r in [p.exterior, *p.interiors])
    return md.CrossSection(contours)


def extrude(shape, top, bottom=0):
    profile = section(shape)
    if profile.is_empty():
        return md.Manifold()
    return profile.extrude(top - bottom).translate((0, 0, bottom))


def projection(m, flat_top=None):
    triangles = m.triangles
    if flat_top is not None:
        triangles = triangles[np.isclose(triangles[:, :, 2], flat_top).all(axis=1)]
    outlines = [Polygon(t[:, :2]) for t in triangles]
    return unary_union([p for p in outlines if p.area > 1e-9]).buffer(0)


def traced(d):
    coords = []
    for curve in parse_path(d):
        n = max(2, math.ceil(curve.length(error=1e-4) / 1.35))
        coords.extend((curve.point(j / n).real, curve.point(j / n).imag) for j in range(n))
    return Polygon(coords).buffer(0)


def disk(x, y, r, resolution=40):
    return Point(x, y).buffer(r, quad_segs=resolution)


def ellipse(x, y, a, b, angle):
    e = affinity.scale(disk(0, 0, 1, 14), a, b, origin=(0, 0))
    return affinity.translate(affinity.rotate(e, angle, origin=(0, 0)), x, y)


def line(points, width):
    return LineString(points).buffer(width / 2, quad_segs=8)


# The left ear artwork is traced in the supplied image coordinates. The right
# ear mirrors the claw and has its own smaller gem and arrangement of coins.
CLAW = traced(
    "M 80 268 C 74 245 75 213 83 184 C 99 119 154 77 207 70 "
    "C 242 65 269 75 283 101 C 259 98 248 105 238 117 "
    "C 232 114 229 120 233 125 C 223 132 220 138 221 144 "
    "C 213 143 209 150 210 155 C 200 164 193 170 182 178 "
    "C 192 190 220 178 236 167 C 232 186 219 202 201 213 "
    "C 176 233 156 236 132 230 C 116 236 103 247 93 272 Z"
)
HEAP = traced(
    "M 49 281 C 73 268 90 288 112 291 C 133 272 154 274 174 284 "
    "C 192 276 208 264 234 272 C 257 249 281 238 311 255 "
    "C 328 252 346 232 374 244 L 396 427 L 43 427 Z"
)
STAR = traced(
    "M 305 146 C 308 145 308 149 309 153 L 316 185 "
    "Q 317 189 322 189 L 346 194 Q 351 196 346 199 L 320 206 "
    "Q 317 207 316 213 L 309 245 Q 306 254 303 245 L 295 213 "
    "Q 294 208 289 206 L 263 199 Q 258 196 264 194 L 291 188 "
    "Q 296 187 296 183 Z"
)
COINS = [
    (89, 282, 30, 17, 27, 2.0), (95, 321, 30, 19, 19, 2.35),
    (130, 306, 26, 15, -20, 1.85), (131, 355, 32, 19, -29, 2.55),
    (102, 361, 27, 14, -44, 1.65), (161, 388, 33, 21, -15, 2.65),
    (201, 371, 22, 13, 18, 1.9), (218, 405, 33, 23, 8, 2.65),
    (244, 353, 34, 17, -31, 2.9), (278, 320, 32, 19, -29, 2.6),
    (270, 288, 32, 14, -19, 2.1), (301, 269, 31, 13, -14, 2.6),
    (340, 250, 24, 13, -55, 2.1), (270, 246, 24, 13, 20, 1.95),
    (311, 300, 22, 14, -20, 2.15), (325, 325, 30, 15, -32, 1.9),
    (194, 335, 21, 14, -4, 1.7), (230, 313, 26, 13, -10, 2.0),
]
RIGHT_COINS = [
    (85, 282, 30, 16, 24, 2.3), (92, 324, 29, 16, 13, 1.9),
    (128, 306, 25, 15, -29, 2.25), (124, 352, 29, 17, 29, 2.55),
    (154, 365, 34, 20, 25, 2.6), (137, 279, 24, 14, 22, 2.0),
    (191, 381, 30, 17, -22, 2.0), (189, 414, 32, 22, -8, 2.65),
    (230, 403, 34, 22, 17, 2.65), (238, 368, 27, 20, 32, 2.4),
    (267, 345, 29, 17, 29, 2.6), (295, 323, 30, 19, -12, 2.3),
    (282, 275, 32, 16, -18, 2.45), (323, 280, 25, 14, -12, 2.0),
    (323, 248, 24, 15, -43, 2.25), (244, 254, 25, 12, 33, 2.35),
    (166, 333, 22, 14, 17, 2.05), (200, 355, 26, 15, -16, 2.0),
]
SPOTS = [(112, 161, 3), (131, 126, 3.4), (145, 113, 2.9), (165, 91, 3.2),
         (177, 100, 2.8), (184, 116, 3.8), (162, 134, 2.7), (135, 153, 2.8),
         (205, 91, 2.9), (120, 184, 3.5), (146, 178, 2.7)]


def ear(is_left, source_outline, contact):
    sign = 1 if is_left else -1
    # Counter-rotate graphics so the treasure reads level on the headband.
    def artwork(g):
        g = affinity.affine_transform(g, [sign * .267, 0, 0, -.267,
                                           -sign * .267 * 204, .267 * 237])
        g = affinity.rotate(g, -sign * 40, origin=(0, 0))
        return affinity.translate(g, *CENTER)

    c = disk(*CENTER, 49.9, 96)
    # Retain the circle above the NX3 seat. Below the seam follow the approved
    # perimeter so the face cannot project into the mating edge.
    clip = c.intersection(source_outline.buffer(-.4).union(box(-51, 14.5, 51, 91)))
    inner = disk(*CENTER, 46.1, 96)
    rim = clip.difference(inner)
    treas_clip = clip.intersection(disk(*CENTER, 47.8, 96))
    frame = [
        (extrude(rim, 3.45), "rim"),
        (extrude(rim.intersection(c.buffer(-.65).difference(c.buffer(-1.7))),
                 3.85, 3.32), "edge"),
    ]
    coin_list = COINS if is_left else RIGHT_COINS
    coin_shapes = [artwork(ellipse(x, y, a, b, angle)) for x, y, a, b, angle, _ in coin_list]
    # The flat treasure web ties the visible coins to the rim and covers the
    # two locating pins. Its top edge follows the coin pile.
    heap = artwork(HEAP).union(unary_union(coin_shapes)).intersection(treas_clip)
    foot = contact.buffer(.14).intersection(clip.buffer(-.24)).simplify(.026)
    parts = frame + [(extrude(foot, 2.2), "shadow"), (extrude(heap, 2.1), "ochre")]

    # Add a broad, recessed web at the outer edge of the claw where its
    # traced silhouette meets the inside of the ring.
    claw = artwork(CLAW).intersection(treas_clip)
    claw_link = claw.buffer(1.65).intersection(c.difference(c.buffer(-5.45))).intersection(clip)
    parts.extend([(extrude(claw_link, 2.3), "shadow"), (extrude(claw, 2.85), "violet"),
                  (extrude(claw.buffer(-.72), 3.45, 2.7), "claw")])
    for x, y, r in SPOTS:
        fleck = artwork(disk(x, y, r, 12)).intersection(claw.buffer(-.95))
        if fleck.area > .65:
            parts.append((extrude(fleck, 3.76, 3.4), "pink"))

    star = artwork(STAR).intersection(treas_clip)
    star_tail = artwork(line([(306, 228), (306, 270)], 8)).intersection(treas_clip)
    parts.extend([(extrude(star.union(star_tail), 2.65), "gold"),
                  (extrude(star.buffer(-.48), 3.7, 2.45), "bright")])
    for i, (coin_shape, (_, _, _, _, _, height)) in enumerate(zip(coin_shapes, coin_list)):
        height += i * .0037
        coin = coin_shape.intersection(treas_clip.buffer(-.70 - i * .019)).simplify(.009)
        if coin.area < .65:
            continue
        # Alternating heights show overlapping coin edges. The smaller,
        # recessed inner face gives each oval a readable raised lip.
        inset = coin.buffer(-.65)
        parts.append((extrude(coin, height + .95, 1.72), "gold"))
        lip = coin.difference(inset)
        parts.append((extrude(lip, height + 1.32, height + .79), "bright"))

    gem = [(156, 246), (216, 219), (271, 246), (274, 291),
           (247, 345), (199, 336), (151, 299)]
    nodes = [(186, 267), (228, 255), (253, 267), (181, 294), (232, 316)]
    if not is_left:
        gem = [(150, 282), (192, 263), (230, 283), (234, 326),
               (204, 357), (168, 349), (143, 322)]
        nodes = [(166, 295), (199, 289), (216, 300), (169, 325), (195, 337)]
    edges = [(gem[0], nodes[0]), (gem[1], nodes[1]), (gem[2], nodes[2]),
             (gem[4], nodes[4]), (gem[6], nodes[3]), (nodes[0], nodes[1]),
             (nodes[1], nodes[2]), (nodes[0], nodes[3]), (nodes[3], nodes[4]),
             (nodes[1], nodes[4]), (nodes[2], gem[3]), (nodes[4], gem[5])]
    gem_shift = -12 if is_left else -11
    def gem_art(g):
        return artwork(affinity.translate(g, yoff=gem_shift))

    stone = gem_art(Polygon(gem)).intersection(treas_clip.buffer(-.45))
    interior = stone.buffer(-1.32)
    rails = unary_union([gem_art(line([a, b], 4.3)) for a, b in edges]).intersection(stone.buffer(-.21))
    parts.extend([(extrude(stone, 3.4), "ochre"),
                  (extrude(stone.difference(interior), 4.75, 3.1), "bright"),
                  (extrude(interior, 4.13, 3.1), "purple_gem" if is_left else "blue_gem"),
                  (extrude(rails, 4.59, 3.96), "bright")])
    # Ensure the crown and underside both have a bonded polygon at the seat.
    sockets = [extrude(disk(x, y, 1.95), 1.25, -.05) for x, y in PINS]
    for socket in sockets:
        assert (socket ^ extrude(foot, 1.25)).volume() > 12
    fused = union([p for p, _ in parts]) - union(sockets)
    return fused, parts


def eye_unit(center_strip):
    parts = [(center_strip, "shadow")]
    for sign in (-1, 1):
        def side(points):
            return [(sign * x, y) for x, y in points]
        stalk = traced(
            "M 9 12 C 9 23 7 31 9 40 C 10 48 14 56 17 60 "
            "L 24 59 C 19 52 17 45 16 38 C 14 28 18 21 19 13 Z"
        )
        if sign < 0:
            stalk = affinity.scale(stalk, -1, 1, origin=(0, 0))
        parts += [(extrude(stalk, 3.6), "rim"),
                  (extrude(line(side([(13, 16), (12, 25), (12.2, 37), (14.1, 47), (18.4, 57)]),
                                1.3).intersection(stalk.buffer(-.35)), 4.12, 3.48), "edge")]
        cx, cy = sign * 21.1, 63.25
        globe = ellipse(cx, cy, 13.1, 14.2, 0)
        opening = ellipse(cx, cy, 10.9, 11.9, 0)
        lid = opening.intersection(box(cx - 12, cy + 2.0, cx + 12, cy + 13))
        whites = opening.difference(lid)
        iris = disk(cx - sign * 3.5, cy - 1.1, 6).intersection(whites)
        pupil = disk(cx - sign * 4.6, cy -.2, 3.6).intersection(whites)
        parts += [(extrude(globe, 3.8), "rim"),
                  (extrude(globe.buffer(-.4).difference(opening.buffer(-.15)), 4.64, 3.65), "edge"),
                  (extrude(whites, 4.35, 3.7), "sclera"),
                  (extrude(iris, 4.63, 4.27), "iris"),
                  (extrude(pupil, 4.87, 4.53), "pupil"),
                  (extrude(lid, 4.95, 3.7), "violet"),
                  (extrude(opening.intersection(box(cx - 12, cy + 1.1, cx + 12, cy + 2.6)),
                           5.18, 4.19), "shadow"),
                  (extrude(disk(cx - sign * 3.0, cy + .05, 1.28).intersection(pupil),
                           5.19, 4.78), "shine"),
                  (extrude(disk(cx - sign * 6.2, cy - .55, .70).intersection(pupil),
                           5.13, 4.78), "shine")]
    return union([p for p, _ in parts]), parts


def record(path, result):
    assert result.status() == md.Error.NoError, (path, result.status())
    components = [p for p in result.simplify(.0001).decompose() if abs(p.volume()) > 1e-6]
    assert len(components) == 1, (path, [p.volume() for p in components])
    mesh(components[0]).export(path)
    reloaded = trimesh.load_mesh(path)
    assert reloaded.is_volume and len(reloaded.split()) == 1, path
    return {"dimensions_mm": reloaded.extents.round(3).tolist(),
            "volume_mm3": round(float(reloaded.volume), 3),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def transformed(p, pose):
    return p.transform(pose[:3].tolist())


def rendered(parts, filename, angled=False):
    """Orthographic triangle rasterizer with a depth buffer, using the CAD surfaces."""
    theta = math.radians(19 if angled else 0)
    phi = math.radians(-15 if angled else 0)
    a = np.array([[math.cos(theta), 0, math.sin(theta)], [0, 1, 0],
                  [-math.sin(theta), 0, math.cos(theta)]])
    b = np.array([[1, 0, 0], [0, math.cos(phi), -math.sin(phi)],
                  [0, math.sin(phi), math.cos(phi)]])
    view = b @ a
    scene = [(mesh(body), color) for body, color in parts]
    all_xy = np.concatenate([m.vertices @ view[:2].T for m, _ in scene])
    lo, hi = all_xy.min(axis=0), all_xy.max(axis=0)
    scale = 1800 / (hi[0] - lo[0] + 14)
    width, height = np.ceil((hi - lo + 14) * scale).astype(int)
    zbuffer = np.full((height, width), -np.inf, np.float32)
    pixels = np.empty((height, width, 3), np.uint8)
    for j in range(height):
        pixels[j] = (24 + j * 10 // height, 18 + j * 6 // height, 39 + j * 10 // height)
    light = np.array([-.35, .5, .79])
    for model, color in scene:
        rgb = np.array(ImageColor.getrgb(PALETTE[color]))
        pts = model.vertices @ view.T
        pts[:, 0] = (pts[:, 0] - lo[0] + 7) * scale
        pts[:, 1] = (hi[1] - pts[:, 1] + 7) * scale
        normals = model.face_normals @ view.T
        for i in np.flatnonzero(normals[:, 2] > 1e-7):
            t = pts[model.faces[i]]
            mn = np.floor(t[:, :2].min(axis=0)).astype(int)
            mx = np.ceil(t[:, :2].max(axis=0)).astype(int)
            yy, xx = np.ogrid[mn[1]:mx[1]+1, mn[0]:mx[0]+1]
            v1, v2 = t[1] - t[0], t[2] - t[0]
            den = v1[0] * v2[1] - v1[1] * v2[0]
            u = ((xx + .5 - t[0, 0]) * v2[1] - (yy + .5 - t[0, 1]) * v2[0]) / den
            v = (v1[0] * (yy + .5 - t[0, 1]) - v1[1] * (xx + .5 - t[0, 0])) / den
            depth = t[0, 2] + u * v1[2] + v * v2[2]
            region = zbuffer[mn[1]:mx[1]+1, mn[0]:mx[0]+1]
            hit = (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1.0000001) & (depth >= region)
            region[hit] = depth[hit]
            shade = .60 + .51 * max(0, normals[i] @ light)
            pixels[mn[1]:mx[1]+1, mn[0]:mx[0]+1][hit] = np.clip(rgb * shade, 0, 255)
    Image.fromarray(pixels).resize((width * 3 // 4, height * 3 // 4),
                                   Image.Resampling.LANCZOS).save(filename)


def main():
    source_strip = solid(NX3 / "mount_test_strip.stl")
    full_base = solid(NX3 / "glue_on_base_SOURCE_GEOMETRY.stl")
    center_base = solid(NX3 / "center_hat_glue_base_3_of_5.stl")
    approved_hat = solid(NX3 / "center_hat_blue_base.stl")
    # The approved center accessory uses the same strip crop as its base,
    # and its added hat art only begins above the original cut at Y=14.45.
    center_strip = source_strip ^ md.Manifold.cube((40, 40, 12)).translate((-20, -20, -1))
    trim = md.Manifold.cube((42, 34.4, 12)).translate((-21, -20, -1))
    assert abs(((center_strip ^ trim) - approved_hat).volume()) < .005
    strip_contact = projection(mesh(source_strip), flat_top=10)
    source_outline = projection(trimesh.load_mesh(NX3 / "ear_blue_base.stl"))
    poses = json.loads((APPROVED / "CAD/assembly_positions.json").read_text())["NX3"]
    lm, rm, em = [np.asarray(poses[k]) for k in ["left_brooms", "right_mouse", "center_hat"]]
    eyes, eye_art = eye_unit(center_strip)

    def clear_center(is_left, pose):
        face, art = ear(is_left, source_outline, strip_contact)
        center_x = em[0, 3]
        # A straight relief along the side of the center shoe keeps the
        # installation gap smooth and gives the print a clean interior edge.
        low = center_x - 20.9
        high = center_x + 20.9
        zone = box(low, 65.0, high, 84.0)
        inverse = np.linalg.inv(pose)
        cut = affinity.affine_transform(zone, [inverse[0, 0], inverse[0, 1],
                                                 inverse[1, 0], inverse[1, 1],
                                                 inverse[0, 3], inverse[1, 3]])
        clearance = extrude(cut, 7, -.5)
        return face - clearance, [(p - clearance, color) for p, color in art]

    left, left_art = clear_center(True, lm)
    right, right_art = clear_center(False, rm)
    shoe = union([source_strip] + [extrude(disk(x, y, 1.6), 11.0, 9.7) for x, y in PINS])
    fit_test = source_strip

    # The bases are byte-for-byte copies of the approved STL and STEP.
    names = ["glue_on_base_SOURCE_GEOMETRY", "center_hat_glue_base_3_of_5"]
    outputs = {}
    for name in names:
        src = NX3 / (name + ".stl")
        dst = STL / src.name
        dst.write_bytes(src.read_bytes())
        (ROOT / "cad" / (name + ".step")).write_bytes((STEP / (name + ".step")).read_bytes())
        m = trimesh.load_mesh(dst)
        assert m.is_volume and len(m.split()) == 1
        outputs[dst.name] = {"dimensions_mm": m.extents.round(3).tolist(),
                             "volume_mm3": round(float(m.volume), 3),
                             "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
                             "approved_source_bytes_match": dst.read_bytes() == src.read_bytes()}
    for name, part in [
        ("left_crab_face", left), ("right_crab_face", right), ("crab_eyes", eyes),
        ("ear_magnet_carrier_print_two", shoe), ("ear_magnet_fit_test_strip", fit_test),
    ]:
        print("Checking", name, flush=True)
        outputs[name + ".stl"] = record(STL / (name + ".stl"), part)

    base_overlap = (source_strip ^ full_base).volume()
    center_overlap = (center_strip ^ center_base).volume()
    assert abs((shoe ^ full_base).volume() - base_overlap) < .005
    assert abs((eyes ^ center_base).volume() - center_overlap) < .005
    keep = md.Manifold.cube((120, 100, 11)).translate((-60, -30, -1))
    assert abs(((shoe ^ keep) - source_strip).volume()) < .005
    protected_center = md.Manifold.cube((120, 42, 11)).translate((-60, -30, -1))
    assert abs(((eyes ^ protected_center) - center_strip).volume()) < .005
    bonding = []
    for face in [left, right]:
        posed = face.translate((0, 0, SEAT_Z))
        assert abs((posed ^ shoe).volume()) < .005
        assert abs((posed ^ full_base).volume()) < .005
        underside = projection(mesh(face), flat_top=0)
        bonding.append(round(underside.intersection(strip_contact).area, 1))
    assert min(bonding) > 220

    band = solid(APPROVED / "Reference_files/dressyspider_larger_headband_source.stl")
    assemblies = [
        transformed(union([left.translate((0, 0, SEAT_Z)), shoe, full_base]), lm),
        transformed(union([right.translate((0, 0, SEAT_Z)), shoe, full_base]), rm),
        transformed(union([eyes, center_base]), em),
    ]
    overlaps = [round((assemblies[i] ^ assemblies[j]).volume(), 6)
                for i, j in [(0, 1), (0, 2), (1, 2)]]
    assert max(overlaps) < .01, overlaps
    report = {
        "status": "PASS", "units": "mm", "magnet_size_diameter_by_thickness_mm": [6, 3],
        "stl_checks": outputs,
        "ear_baseline_base_intersection_mm3": base_overlap,
        "eye_baseline_base_intersection_mm3": center_overlap,
        "added_mating_interference_mm3": 0,
        "nominal_assembly_accessory_overlaps_mm3": overlaps,
        "face_carrier_bonding_projection_mm2_left_right": bonding,
        "face_carrier_nominal_adhesive_gap_mm": SEAT_Z - 10,
        "fit_evidence": "Digital checks on the approved NX3 nominal band poses. Physical fit pending.",
    }
    (ROOT / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    front = [(band, "band")]
    for pose, art in [(lm, left_art), (rm, right_art)]:
        front += [(transformed(shoe, pose), "shadow"), (transformed(full_base, pose), "shadow")]
        front.extend((transformed(p.translate((0, 0, SEAT_Z)), pose), col) for p, col in art)
    front += [(transformed(center_base, em), "shadow")]
    front.extend((transformed(p, em), col) for p, col in eye_art)
    for angle in (False, True):
        filename = "crab_nx3_angle.png" if angle else "crab_nx3_front.png"
        rendered(front, ROOT / "previews" / filename, angled=angle)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()








