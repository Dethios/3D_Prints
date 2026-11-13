"""Build the image-traced crab faces on the approved, unscaled NX3 mounts."""
from pathlib import Path
import hashlib
import json
import math
import sys

import manifold3d as md
import numpy as np
from PIL import Image, ImageColor
from shapely import constrained_delaunay_triangles
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
CARRIER_DEPTH = 10.0
RIM_WIDTH = 4.6
CENTER_FACE_THICKNESS = 4.6
CENTER_MATE_GAP = .15
POCKET_DIAMETER = 6.25
POCKET_DEPTH = 3.15
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
    (230, 313, 26, 13, -10, 2.0),
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
# Edge coins touch the inside of the rim. The taller foreground coins
# cover the lower girdle and tip of each gemstone.
LEFT_EDGE_COINS = [
    (64, 278, 27, 15, 31, 2.2), (62, 318, 29, 16, 25, 2.43),
    (359, 253, 28, 16, -49, 2.38), (352, 290, 29, 16, -32, 2.6),
]
RIGHT_EDGE_COINS = [
    (65, 279, 30, 16, 28, 2.34), (67, 318, 29, 16, 31, 2.52),
    (354, 256, 28, 15, -35, 2.45), (350, 295, 31, 16, -37, 2.68),
]
LEFT_FOREGROUND_COINS = [(203, 338, 33, 15, 16, 2.98),
                         (250, 330, 29, 15, -27, 3.21)]
RIGHT_FOREGROUND_COINS = [(202, 345, 29, 16, 23, 2.91),
                          (251, 337, 30, 15, -25, 3.06)]
SPOTS = [(112, 161, 3), (131, 126, 3.4), (145, 113, 2.9), (165, 91, 3.2),
         (177, 100, 2.8), (184, 116, 3.8), (162, 134, 2.7), (135, 153, 2.8),
         (205, 91, 2.9), (120, 184, 3.5), (146, 178, 2.7)]


def cut_gem(outline, table_center, table_scale, table_height):
    """Build a solid with a flat table and planar facets down to the girdle."""
    girdle = np.asarray(list(orient(outline).exterior.coords)[:-1])
    center = np.array([table_center.x, table_center.y])
    table = center + (girdle - center) * table_scale
    count = len(girdle)
    vertices = [(x, y, z) for loop, z in
                [(girdle, 1.68), (girdle, 2.64), (table, table_height)]
                for x, y in loop]
    faces = []
    for i in range(count):
        j = (i + 1) % count
        for offset in (0, count):
            faces.extend([(offset + i, offset + j, offset + j + count),
                          (offset + i, offset + j + count, offset + i + count)])
    for i in range(1, count - 1):
        faces.extend([(0, i + 1, i), (2 * count, 2 * count + i, 2 * count + i + 1)])
    return solid(trimesh.Trimesh(vertices, faces, process=False))


def rounded_relief(outline, levels):
    """Join inset contours with sloped faces and keep a flat print surface."""
    profiles = [(outline.buffer(-inset), height) for inset, height in levels]
    vertices, faces = [], []

    def add_face(coords):
        faces.append(tuple(range(len(vertices), len(vertices) + len(coords))))
        vertices.extend(coords)

    for (outer, lower), (inner, upper) in zip(profiles, profiles[1:]):
        for tri in constrained_delaunay_triangles(outer.difference(inner)).geoms:
            coords = list(orient(tri).exterior.coords)[:-1]
            add_face([(x, y, upper if inner.boundary.distance(Point(x, y)) < 1e-7
                       else lower) for x, y in coords])
    top, height = profiles[-1]
    for tri in constrained_delaunay_triangles(top).geoms:
        add_face([(x, y, height) for x, y in list(orient(tri).exterior.coords)[:-1]])
    for poly in polygons(outline):
        for ring in [poly.exterior, *poly.interiors]:
            for (x, y), (u, v) in zip(ring.coords, list(ring.coords)[1:]):
                add_face([(x, y, 0), (u, v, 0), (u, v, levels[0][1])])
                add_face([(x, y, 0), (u, v, levels[0][1]), (x, y, levels[0][1])])
    for tri in constrained_delaunay_triangles(outline).geoms:
        add_face([(x, y, 0) for x, y in list(orient(tri, sign=-1).exterior.coords)[:-1]])
    return solid(trimesh.Trimesh(vertices, faces, process=True))


def rounded_coin(x, y, a, b, angle, base, crest):
    """Turn a rounded rim and gently crowned face, then ovalize the coin."""
    profile = [(0, 0), (.91, 0), (.981, .19), (1, .45), (.994, .68),
               (.973, .86), (.932, .98), (.893, 1), (.853, .93),
               (.806, .84), (.68, .88), (.48, .93), (.25, .96), (0, .97)]
    curve = md.CrossSection([np.asarray(profile)])
    coin = curve.revolve(circular_segments=72).scale((a, b, crest - base))
    return coin.rotate((0, 0, angle)).translate((x, y, base))


def eye_dome(cx, cy, width, height, equator, rise, outline, floor):
    dome = md.Manifold.sphere(1, 72).scale((width, height, rise))
    return dome.translate((cx, cy, equator)) ^ extrude(outline, equator + rise + .1, floor)


def ear(is_left, source_outline, carrier, keepout):
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
    carrier_outline = projection(mesh(carrier))
    # Follow one perimeter from the round rim through the NX3 seating arc.
    outer_shape = clip.union(carrier_outline).buffer(1.15).buffer(-1.15).simplify(.035)
    rim_inner = outer_shape.buffer(-RIM_WIDTH)
    # Offset back from the inner edge to round the outside of the joins
    # at the same width, including across the convex corners.
    outer_shape = rim_inner.buffer(RIM_WIDTH, quad_segs=32)
    rim = outer_shape.difference(rim_inner)
    treas_clip = clip.intersection(disk(*CENTER, 47.8, 96))
    coin_list = COINS if is_left else RIGHT_COINS
    edge_coins = LEFT_EDGE_COINS if is_left else RIGHT_EDGE_COINS
    foreground_coins = LEFT_FOREGROUND_COINS if is_left else RIGHT_FOREGROUND_COINS
    edge_start = len(coin_list)
    coin_list = coin_list + edge_coins + foreground_coins
    coin_shapes = [artwork(ellipse(x, y, a, b, angle)) for x, y, a, b, angle, _ in coin_list]
    # The treasure web ties the visible coins to the rim and carrier.
    heap = artwork(HEAP).union(unary_union(coin_shapes).buffer(.65)).intersection(treas_clip.buffer(-.06)).simplify(.031)
    parts = [(extrude(heap, 2.1), "ochre")]

    claw = artwork(CLAW).intersection(treas_clip)
    # This flat pad reaches the claw from the rim below the sculpted relief.
    shoulder_pad = artwork(ellipse(206, 67.5, 26, 11.5, 2))
    shoulder_pad = shoulder_pad.intersection(outer_shape.buffer(-.65))
    parts.append((extrude(shoulder_pad, 1.35, .06), "claw"))
    claw_body = rounded_relief(claw, [(0, 2.55), (.22, 3.18), (.68, 3.78),
                                    (1.35, 4.31), (2.25, 4.77), (3.45, 5.11),
                                    (4.9, 5.34), (6.6, 5.48)])
    parts.append((claw_body, "claw"))
    for x, y, r in SPOTS:
        fleck = artwork(disk(x, y, r, 12)).intersection(claw.buffer(-.95))
        if fleck.area > .65:
            # Follow the claw's contour instead of laying dots on one plane.
            spot = claw_body.translate((0, 0, .18)) ^ extrude(fleck, 6, 2.5)
            parts.append((spot, "pink"))

    star = artwork(STAR).buffer(-.22).buffer(.22).intersection(treas_clip)
    star_tail = artwork(line([(306, 229), (306, 274)], 9)).intersection(treas_clip)
    parts.extend([(extrude(star_tail, 1.95), "ochre"),
                  (rounded_relief(star, [(0, 2.15), (.25, 2.87), (.57, 3.57),
                                         (.98, 4.22), (1.45, 4.78),
                                         (2.0, 5.24)]), "bright")])
    coins = []
    for i, (coin_shape, (x, y, a, b, angle, height)) in enumerate(zip(coin_shapes, coin_list)):
        height += i * .0037
        margin = -.70 - i * .019 if i < edge_start else -.08 - (i - edge_start) * .07
        coin = coin_shape.intersection(treas_clip.buffer(margin)).simplify(.009)
        if coin.area < .65:
            continue
        base_z = 1.55 + .011 * i
        center = artwork(Point(x, y))
        coin_solid = rounded_coin(center.x, center.y, a * .267, b * .267,
                                  -sign * (angle + 40), base_z, height + 1.5)
        coins.append((coin_solid ^ extrude(treas_clip.buffer(margin), 6), coin,
                      i >= len(coin_list) - len(foreground_coins), height))

    if is_left:
        # Broad crown and tapered lower point from the diamond reference.
        gem = [(157, 249), (188, 226), (222, 220), (255, 236),
               (274, 268), (230, 342), (148, 282)]
        table_center = (209, 248)
        table_scale, table_height = .49, 5.65
        color = "purple_gem"
    else:
        gem = [(251, 278), (224, 267), (195, 274), (180, 300),
               (213, 347), (265, 321), (272, 298)]
        table_center = (227, 292)
        table_scale, table_height = .48, 5.28
        color = "blue_gem"
    gem_solid = cut_gem(artwork(Polygon(gem)), artwork(Point(*table_center)),
                        table_scale, table_height)
    stone = artwork(Polygon(gem)).intersection(treas_clip.buffer(-.45))
    # Give each silhouette a clear owner. Foreground coins hide the buried
    # edge of the gem. The gem and higher coins hide the coins behind them.
    foreground = sorted((item for item in coins if item[2]), key=lambda item: -item[3])
    background = sorted((item for item in coins if not item[2]), key=lambda item: -item[3])
    occluded = Polygon()
    for body, footprint, _, _ in foreground:
        parts.append((body - extrude(occluded.buffer(.15), 7, 1.4), "gold"))
        occluded = occluded.union(footprint)
    gem_solid = (gem_solid ^ extrude(treas_clip.buffer(-.45), 6))
    parts.append((gem_solid - extrude(occluded.buffer(.12), 7, 2.07), color))
    occluded = occluded.union(stone)
    for body, footprint, _, _ in background:
        parts.append((body - extrude(occluded.buffer(.15), 7, 1.4), "gold"))
        occluded = occluded.union(footprint)

    # Trim the carrier to the rim through its entire depth. Leave a small
    # inset on both sides so the ring defines the final visible walls.
    rim_core = outer_shape.buffer(-.035).difference(rim_inner.buffer(.035))
    carrier_in_rim = carrier ^ extrude(rim_core, CARRIER_DEPTH + .1, -.1)
    assert rim.geom_type == "Polygon" and len(rim.interiors) == 1
    highlight = outer_shape.buffer(-.27).difference(outer_shape.buffer(-1.46))
    assert highlight.geom_type == "Polygon" and len(highlight.interiors) == 1
    ring = [(extrude(rim, CARRIER_DEPTH + .26), "rim"),
            (extrude(highlight, CARRIER_DEPTH + .47, CARRIER_DEPTH + .15), "edge")]
    return [(carrier_in_rim, "rim"), *((p - keepout, color) for p, color in ring + parts)]


def center_mount(source_base, carrier):
    # Preserve the footprint at the band. Extend the crown-facing edge
    # to carry the same three centers on a common front-facing plane.
    footprint = projection(mesh(source_base))
    base_pad = box(-17.35, 3.1, 17.35, 12.4).buffer(.65)
    eye_pad = box(-18.7, 2.95, 18.7, 13.65).buffer(1.05)
    carrier_mesh = mesh(carrier)
    # Project the source pocket-floor centers back to the original openings.
    centers = []
    for ids, area, normal in zip(carrier_mesh.facets, carrier_mesh.facets_area,
                                 carrier_mesh.facets_normal):
        if 26 < area < 29 and abs(normal[2]) < .03 and len(ids) >= 17:
            center = np.average(carrier_mesh.triangles_center[ids], axis=0,
                                weights=carrier_mesh.area_faces[ids])
            if abs(center[0]) < 16:
                mouth = center + 3.25 * normal
                centers.append((round(float(mouth[0]), 3), round(float(mouth[1]), 3)))
    centers.sort()
    assert len(centers) == 3
    # Both faces use the same centers so magnet disks line up without
    # forcing the base or the eye stalks into the headband.
    base_blank = extrude(footprint.union(base_pad).simplify(.02), CENTER_FACE_THICKNESS)
    eye_blank = extrude(eye_pad, CENTER_FACE_THICKNESS)
    pockets = union([extrude(disk(x, y, POCKET_DIAMETER / 2), POCKET_DEPTH, -.04)
                     for x, y in centers])
    rear_pockets = pockets
    front_pockets = pockets.mirror((0, 0, 1)).translate((0, 0, CENTER_FACE_THICKNESS))
    assert abs((base_blank ^ front_pockets).volume() - (eye_blank ^ rear_pockets).volume()) < .05
    return base_blank - front_pockets, eye_blank, rear_pockets, centers


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
        # Trace one aperture from its outer corner toward the nose, then
        # mirror it. The rising lower lid leaves a crescent of visible white.
        aperture = traced(
            "M -12 2.5 C -4 2.7 5 2.1 12 1.2 "
            "L 12 -1.4 C 6 -5.8 -1 -8.5 -12 -8.4 Z"
        )
        aperture = affinity.scale(aperture, -sign, 1, origin=(0, 0))
        whites = opening.intersection(affinity.translate(aperture, cx, cy))
        lids = opening.difference(whites)
        lash = line([(cx + sign * 12, cy + 2.5), (cx + sign * 4, cy + 2.53),
                     (cx - sign * 5, cy + 2.04), (cx - sign * 12, cy + 1.2)], 1.24)
        iris = disk(cx - sign * 3.85, cy + .95, 5.25).intersection(whites)
        pupil = disk(cx - sign * 4.35, cy + .72, 3.4).intersection(iris)
        # Shape the visible eye and both lids over the existing solid globe.
        # Shared curvature keeps the iris and pupil seated in the sclera.
        lid_shape = eye_dome(cx, cy, 12.6, 13.8, 3.63, 3.18, lids.buffer(.11), 3.57)
        sclera = eye_dome(cx, cy, 12.4, 13.3, 3.64, 2.18, whites.buffer(.075), 3.59)
        iris_relief = eye_dome(cx, cy, 12.4, 13.3, 3.78, 2.23, iris.buffer(-.025), 3.71)
        pupil_relief = eye_dome(cx, cy, 12.4, 13.3, 3.87, 2.28, pupil, 3.75)
        lash_relief = eye_dome(cx, cy, 12.6, 13.8, 3.79, 3.18,
                               lash.intersection(opening.buffer(.08)), 3.74)
        parts += [(extrude(globe, 3.8), "rim"),
                  (extrude(globe.buffer(-.4).difference(opening.buffer(-.15)), 4.64, 3.65), "edge"),
                  (sclera, "sclera"), (iris_relief, "iris"), (pupil_relief, "pupil"),
                  (lid_shape, "violet"), (lash_relief, "shadow")]
        for offset, y_offset, radius in [(2.7, .03, 1.14), (5.35, -.15, .67)]:
            glint = disk(cx - sign * offset, cy + y_offset, radius).intersection(pupil)
            parts.append((eye_dome(cx, cy, 12.4, 13.3, 4.04, 2.29, glint, 3.92), "shine"))
    return union([p for p, _ in parts]), parts


def record(path, result):
    assert result.status() == md.Error.NoError, (path, result.status())
    components = [p for p in result.simplify(.0001).decompose() if abs(p.volume()) > .002]
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
    original_center = solid(NX3 / "center_hat_glue_base_3_of_5.stl")
    center_base, eye_pad, eye_pockets, centers = center_mount(original_center, source_strip)
    eyes_blank, eye_art = eye_unit(eye_pad)
    eyes = eyes_blank - eye_pockets
    eye_art = [(part - eye_pockets, color) for part, color in eye_art]
    source_outline = projection(trimesh.load_mesh(NX3 / "ear_blue_base.stl"))
    # Protect the original receiver and the openings of the NX3 bores when
    # the bottom of the artwork shares the carrier's print plane.
    mount_edge = projection(mesh(full_base)).buffer(.1).simplify(.016)
    bore_caps = json.loads((APPROVED / "CAD/reference_geometry_report.json").read_text())["NX3"]["bore_caps"]
    keepout = [extrude(mount_edge, CARRIER_DEPTH + .02, -.1)]
    for bore in bore_caps:
        center = np.asarray(bore["center"])
        normal = np.asarray(bore["normal"])
        angle = math.degrees(math.atan2(normal[1], normal[0]))
        bore_void = md.Manifold.cylinder(4.5, 3.18, circular_segments=64)
        keepout.append(bore_void.rotate((0, 90, angle)).translate(tuple(center - normal * .12)))
    keepout = union(keepout)
    poses = json.loads((APPROVED / "CAD/assembly_positions.json").read_text())["NX3"]
    lm, rm, base_pose = [np.asarray(poses[k]) for k in ["left_brooms", "right_mouse", "center_hat"]]
    eye_pose = base_pose.copy()
    eye_pose[2, 3] += CENTER_FACE_THICKNESS + CENTER_MATE_GAP

    left_art = ear(True, source_outline, source_strip, keepout)
    right_art = ear(False, source_outline, source_strip, keepout)
    left, right = [union([p for p, _ in reversed(art)]) for art in (left_art, right_art)]
    source_base_path = NX3 / "glue_on_base_SOURCE_GEOMETRY.stl"
    ear_base_path = STL / source_base_path.name
    ear_base_path.write_bytes(source_base_path.read_bytes())
    (ROOT / "cad/glue_on_base_SOURCE_GEOMETRY.step").write_bytes(
        (STEP / "glue_on_base_SOURCE_GEOMETRY.step").read_bytes()
    )
    m = trimesh.load_mesh(ear_base_path)
    assert m.is_volume and len(m.split()) == 1
    outputs = {ear_base_path.name: {"dimensions_mm": m.extents.round(3).tolist(),
                                    "volume_mm3": round(float(m.volume), 3),
                                    "sha256": hashlib.sha256(ear_base_path.read_bytes()).hexdigest(),
                                    "approved_source_bytes_match": True}}
    for name, part in [
        ("left_crab_face", left), ("right_crab_face", right), ("crab_eyes", eyes),
        ("center_hat_glue_base_3_of_5", center_base), ("ear_magnet_fit_test_strip", source_strip),
    ]:
        print("Checking", name, flush=True)
        outputs[name + ".stl"] = record(STL / (name + ".stl"), part)

    base_overlap = (source_strip ^ full_base).volume()
    for ear_part in (left, right):
        assert (ear_part ^ full_base).volume() <= base_overlap + .005
        for bore in bore_caps:
            center = np.asarray(bore["center"])
            normal = np.asarray(bore["normal"])
            angle = math.degrees(math.atan2(normal[1], normal[0]))
            # Check a nominal magnet in the original pocket and a solid
            # cylinder behind it to confirm the back wall remains intact.
            magnet = md.Manifold.cylinder(3, 2.99, circular_segments=64)
            magnet = magnet.rotate((0, 90, angle)).translate(tuple(center + .04 * normal))
            assert abs(((magnet ^ ear_part) - source_strip).volume()) < .005
            back_wall = md.Manifold.cylinder(1.05, 3, circular_segments=64)
            back_wall = back_wall.rotate((0, 90, angle)).translate(tuple(center - 1.07 * normal))
            assert abs((back_wall - ear_part).volume()) < .005
    assert (transformed(eyes, eye_pose) ^ transformed(center_base, base_pose)).volume() < .005
    for x, y in centers:
        test_magnet = extrude(disk(x, y, 3.0), 3.0)
        assert (eyes ^ test_magnet).volume() < .005
        assert (center_base ^ test_magnet.translate((0, 0, CENTER_FACE_THICKNESS - 3))).volume() < .005

    band = solid(APPROVED / "Reference_files/dressyspider_larger_headband_source.stl")
    assemblies = [
        transformed(union([left, full_base]), lm),
        transformed(union([right, full_base]), rm),
        union([transformed(eyes, eye_pose), transformed(center_base, base_pose)]),
    ]
    overlaps = [round((assemblies[i] ^ assemblies[j]).volume(), 6)
                for i, j in [(0, 1), (0, 2), (1, 2)]]
    assert max(overlaps) < .01, overlaps
    center_band_overlap = (assemblies[2] ^ band).volume()
    assert center_band_overlap < .01
    # Reuse the Sorcerer exporter for the matching faceted center-base STEP.
    import cadquery as cq

    sys.path.insert(0, str(APPROVED / "CAD"))
    from build_reference_mounts import step_from_mesh

    center_stl = trimesh.load_mesh(STL / "center_hat_glue_base_3_of_5.stl")
    center_step = ROOT / "cad/center_hat_glue_base_3_of_5.step"
    cq.exporters.export(step_from_mesh(center_stl), str(center_step))
    step_lines = center_step.read_text(encoding="ascii").splitlines()
    center_step.write_text("\n".join(line.rstrip() for line in step_lines) + "\n", encoding="ascii")
    reloaded_step = cq.importers.importStep(str(center_step)).val()
    assert reloaded_step.isValid() and len(reloaded_step.Solids()) == 1
    assert abs(reloaded_step.Volume() - center_stl.volume) < .01
    report = {
        "status": "PASS", "units": "mm", "magnet_size_diameter_by_thickness_mm": [6, 3],
        "stl_checks": outputs,
        "ear_baseline_base_intersection_mm3": base_overlap,
        "ear_added_mating_interference_mm3": 0,
        "rim_body_depth_mm": CARRIER_DEPTH + .26,
        "rim_width_mm": RIM_WIDTH,
        "magnet_back_wall_verified_mm": 1.05,
        "rim_highlight_depth_mm": CARRIER_DEPTH + .47,
        "ear_artwork_base_z_mm": 0,
        "center_base_step_roundtrip_volume_mm3": round(reloaded_step.Volume(), 3),
        "center_pocket_centers_xy_mm": centers,
        "center_pocket_axes": {"base_opening": "+Z (front)", "eye_opening": "-Z (back)"},
        "center_pocket_diameter_mm": POCKET_DIAMETER,
        "center_pocket_depth_mm": POCKET_DEPTH,
        "center_mating_face_gap_mm": CENTER_MATE_GAP,
        "center_band_overlap_mm3": center_band_overlap,
        "nominal_assembly_accessory_overlaps_mm3": overlaps,
        "fit_evidence": "Digital checks on the approved NX3 nominal band poses. Physical fit pending.",
    }
    (ROOT / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    front = [(band, "band")]
    for pose, art in [(lm, left_art), (rm, right_art)]:
        front.append((transformed(full_base, pose), "shadow"))
        front.extend((transformed(part, pose), color) for part, color in art)
    front.append((transformed(center_base, base_pose), "shadow"))
    front.extend((transformed(part, eye_pose), color) for part, color in eye_art)
    for angle in (False, True):
        filename = "crab_nx3_angle.png" if angle else "crab_nx3_front.png"
        rendered(front, ROOT / "previews" / filename, angled=angle)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()






