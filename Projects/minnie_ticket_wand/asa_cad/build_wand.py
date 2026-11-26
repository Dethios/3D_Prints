"""Build the traced Minnie CR80 case with the original Flat Print thread pair.

All print exports share the closed assembly's Cartesian coordinates in mm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
DONOR_HASH = "1a60c699d2f997dd78d06de0b5be383e92f365ddfa82f84f5fed9889c92fcec3"
DEFAULT_DONOR = Path.home() / "Downloads/minnie-wand-printables-reference/1636752-card-wand-flat.step"
ART = json.loads((HERE / "artwork.json").read_text())
ORIGIN = (0, 0, 0)
Y_AXIS = (0, 1, 0)
FACE = 3.15
BOW_FACE = FACE + 3.15
KNOT_FACE = BOW_FACE + 0.75
BOW_PINS = [(-20.0, 47.0), (20.0, 47.0)]
PLUG_X = 36.884372603746
PLUG_Y = 12.4905120279686
PLUG_R = 2.85753649278404
POCKET_HALF = 27.5
POCKET_TOP = 37.25


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slab(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, (x0, y0, z0))


def tube_y(radius, lo, hi):
    return cq.Solid.makeCylinder(radius, hi - lo, (0, lo, 0), Y_AXIS)


def post_z(x, y, radius, lo, hi):
    return cq.Solid.makeCylinder(radius, hi - lo, (x, y, lo))


def assembly_xy(photo_x, photo_y):
    cx, cy = ART["reference_axis"]
    angle = math.radians(ART["roll_degrees"])
    sine, cosine = math.sin(angle), math.cos(angle)
    dx, dy = photo_x - cx, photo_y - cy
    bx, by = ART["case_bottom_photo_xy"]
    bottom = (bx - cx) * sine + (by - cy) * cosine
    unit = ART["mm_per_pixel"]
    return ((dx*cosine - dy*sine) * unit,
            (bottom - dx*sine - dy*cosine) * unit + ART["assembly_case_bottom_y"])


def wire(key, z):
    origin, segments = ART[key]
    edges = []
    for ax, ay, bx, by, cx, cy in segments:
        controls = [origin, (ax, ay), (bx, by), (cx, cy)]
        points = [cq.Vector(*assembly_xy(x, y), z) for x, y in controls]
        edges.append(cq.Edge.makeBezier(points))
        origin = (cx, cy)
    return cq.Wire.assembleEdges(edges)


def traced(key, lo, hi):
    return cq.Solid.extrudeLinear(wire(key, lo), [], (0, 0, hi - lo))


def exterior_boundary(lo, hi, chin_relief=False):
    head = traced("HEAD", lo, hi)
    # The rail wall outside the original 55 mm pocket is 2.15 mm per side.
    case_top = hi - 0.65 if chin_relief else hi
    case = cq.Workplane("XY").box(59.3, 89.5, case_top - lo).edges("|Z").fillet(1.65).val()
    case = case.translate((0, -5.25, (lo + case_top) / 2))
    if chin_relief:
        # The photo shows the traced round head proud of two pocket corners.
        # Keep both upper edges soft and the entire inside card plane flat.
        head = edge_round(head, hi, 0.35)
        case = edge_round(case, case_top, 0.35)
    return head.fuse(case).clean()


def edge_round(shape, level, radius):
    eligible = [e for e in shape.Edges()
                if abs(e.BoundingBox().zmin - level) < 0.001
                and abs(e.BoundingBox().zmax - level) < 0.001]
    return shape.fillet(radius, eligible)


def shell(donor_cover, front):
    lo, hi = (0.75, FACE) if front else (-FACE, -0.75)
    plate = exterior_boundary(lo, hi, chin_relief=front)
    # The traced bezier joints vary in tangency. The softened perimeter is
    # built on the matching blank before the imported thread is joined.
    if not front:
        plate = edge_round(plate, lo, 0.35)
    # Preserve both complementary original female thread halves throughout
    # their length. An overlap only at the exterior cylinder joins to the skin.
    plate = plate.cut(tube_y(6.70, -70, -36.0))
    actual_neck = donor_cover.intersect(tube_y(7.02, -69.10, -35.99))
    result = plate.fuse(actual_neck).clean()
    # Reproduce the donor blind seats on both inside faces at original depth.
    for x in (-PLUG_X, PLUG_X):
        result = result.cut(post_z(x, PLUG_Y, PLUG_R, -1.80, 1.80))
    if front:
        for x, y in BOW_PINS:
            # Wide root and tapered lead on blind bow-register bosses.
            boss = post_z(x, y, 1.8, FACE - .2, FACE + 1.65)
            lead = cq.Solid.makeCone(1.8, 1.5, .30, (x, y, FACE + 1.65))
            result = result.fuse(boss, lead)
    return result.clean()


def spacer():
    outside = exterior_boundary(-.75, .75)
    window = slab(-POCKET_HALF, POCKET_HALF, -90, POCKET_TOP, -1.0, 1.0)
    part = outside.cut(window)
    for x in (-PLUG_X, PLUG_X):
        part = part.cut(post_z(x, PLUG_Y, PLUG_R, -1.85, 1.85))
    return part.clean()


def collar(source):
    axes = next(f._geomAdaptor().Cylinder().Axis() for f in source.Faces()
                if f.geomType() == "CYLINDER" and abs(f._geomAdaptor().Cylinder().Radius()-7.0)<1e-5)
    donor_basis = cq.Plane(axes.Location().Coord(), (0.9999839805828384, -0.0007476412908312674, 0.005610669318517783), axes.Direction().Coord())
    installed = cq.Plane((0, -59.55, 0), (0, 0, 1), (0, -1, 0))
    cuff = source.moved(installed.location * donor_basis.location.inverse)
    # Open only the Ø12 contact lands; retain the Ø12.4 relief arcs. An
    # extra outer band provides four 0.4 mm nominal extrusion widths.
    cuff = cuff.cut(tube_y(6.18, -71, -58))
    reinforcement = (cq.Workplane("XY").moveTo(6.76, -69.59)
                     .lineTo(7.80, -69.59).lineTo(7.80, -59.97)
                     .threePointArc((7.68, -59.69), (7.40, -59.57))
                     .lineTo(6.76, -59.57).close().revolve(360,(0,0),(0,1)).val())
    finished = cuff.fuse(reinforcement).clean()
    assert finished.isValid() and len(finished.Solids()) == 1
    return finished

def handle(male, cuff):
    grip = (cq.Workplane("XY").moveTo(0, -174)
            .threePointArc((5.55, -171.70), (7.85, -166.15))
            .lineTo(8.08, -150).lineTo(7.80, -104).lineTo(8.10, -76)
            .lineTo(7.8, -70.4).lineTo(7.8, -69.30).lineTo(0, -69.30)
            .close().revolve(360, (0,0), (0,1)).val())
    # The narrow rear chord gives a long printing flat and preserves the collar OD.
    grip = grip.intersect(slab(-12, 12, -180, -68, -7.8, 12))
    tip = male.intersect(slab(-10, 10, -71, -48, -10, 10))
    finished = grip.fuse(tip, cuff).clean()
    assert finished.isValid() and len(finished.Solids()) == 1
    annulus = tube_y(7.35, -69.24, -59.62).cut(tube_y(6.55, -70, -59))
    assert abs(finished.intersect(annulus).Volume() - annulus.Volume()) < 1e-5
    return finished


def bow():
    loops = traced("LEFT_BOW", FACE, BOW_FACE).fuse(traced("RIGHT_BOW", FACE, BOW_FACE))
    knot = traced("KNOT", FACE, KNOT_FACE)
    result = loops.fuse(knot).clean()
    for x, y in BOW_PINS:
        result = result.cut(post_z(x, y, 2.04, FACE - .2, FACE + 2.18))
    # Shallow, tapered crease on each loop beside the raised knot.
    for x1, y1, x2, y2 in ART["fold_strokes"]:
        a = assembly_xy(x1, y1)
        b = assembly_xy(x2, y2)
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy/length, dx/length
        points = [(a[0]-.18*dx/length,a[1]-.18*dy/length),
                  (a[0]+.45*nx+.16*dx, a[1]+.45*ny+.16*dy),
                  (b[0]+.45*nx, b[1]+.45*ny),
                  (b[0]-.45*nx,b[1]-.45*ny),
                  (a[0]-.45*nx+.16*dx, a[1]-.45*ny+.16*dy)]
        cutter = (cq.Workplane("XY",origin=(0,0,BOW_FACE-.5)).polyline(points)
                  .close().extrude(.51).val())
        result = result.cut(cutter)
    dots = []
    for x, y, radius in ART["bow_dots"]:
        wx, wy = assembly_xy(x, y)
        dots.append(post_z(wx, wy, radius * ART["mm_per_pixel"], BOW_FACE-1.05, BOW_FACE))
    white = cq.Compound.makeCompound(dots)
    return result.cut(white).clean(), white


def build(donor_path):
    assert sha(donor_path) == DONOR_HASH, "Unexpected donor revision"
    raw = cq.importers.importStep(str(donor_path)).solids().vals()
    assert len(raw) == 9
    front = raw[0].translate((-175.816693734826, 0, 1.5))
    rear = raw[2].translate((171.331443746177, 0, 0)).rotate(ORIGIN, Y_AXIS, 180).translate((0, 0, -1.5))
    male = raw[1].rotate(ORIGIN, Y_AXIS, 180)
    # Align the chamfered 3.2 mm source plugs to the two donor blind seats.
    plug = raw[4]
    bb = plug.BoundingBox()
    plug = plug.translate((-PLUG_X - (bb.xmin + bb.xmax)/2, PLUG_Y - (bb.ymin+bb.ymax)/2, 0))
    pink, white = bow()
    return {
        "front_black": shell(front, True),
        "spacer_black": spacer(),
        "rear_black": shell(rear, False),
        "alignment_pin_black_print_two": plug,
        "handle_cuff_pink": handle(male, collar(raw[6])),
        "bow_pink": pink,
        "bow_dots_white": white,
    }


def assembly_parts(parts):
    return dict(parts, alignment_pin_black_right=parts["alignment_pin_black_print_two"].translate((2*PLUG_X,0,0)))


def stl_export(part, path):
    cq.exporters.export(part, str(path), tolerance=.025, angularTolerance=.075)
    # OpenCascade can emit a coincident triangle at the revolved grip pole.
    # Remove only facets whose vertices coincide, preserving all real faces.
    import trimesh
    mesh = trimesh.load_mesh(path)
    faces = mesh.faces
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    if not keep.all():
        mesh.update_faces(keep)
        mesh.remove_unreferenced_vertices()
        mesh.export(path)


def bounds(shape):
    b = shape.BoundingBox()
    return [[round(v, 5) for v in (b.xmin, b.ymin, b.zmin)],
            [round(v, 5) for v in (b.xmax, b.ymax, b.zmax)]]


def export(parts):
    print_dir = HERE/"print_parts"
    coupon_dir = HERE/"fit_coupon"
    for path in (print_dir, coupon_dir):
        path.mkdir(exist_ok=True)
    asm = cq.Assembly(name="Minnie_CR80_wand")
    colors = {"black": cq.Color(.095,.088,.103), "pink": cq.Color(.95,.46,.64), "white": cq.Color(.99,.98,.96)}
    for name, part in assembly_parts(parts).items():
        color = next(k for k in colors if k in name)
        assert part.isValid(), name
        expected = 14 if name == "bow_dots_white" else 1
        assert len(part.Solids()) == expected, (name, len(part.Solids()))
        asm.add(part, name=name, color=colors[color])
        if name in parts:
            stl_export(part, print_dir/f"{name}.stl")
        print(name, bounds(part), round(part.Volume(),2), flush=True)
    asm.export(str(HERE/"minnie_card_wand.step"))
    # Retain the full side-to-side card opening and actual complete thread
    # depth. Short shell section can be held together with binder clips.
    rail_test = slab(-29.75, 29.75, -70.0, -32.0, -10, 10)
    for name in ["front_black", "rear_black", "spacer_black"]:
        sample = parts[name].intersect(rail_test)
        stl_export(sample, coupon_dir/f"coupon_{name}.stl")
    sample_handle = parts["handle_cuff_pink"].intersect(slab(-10,10,-85,-48,-10,10))
    stl_export(sample_handle, coupon_dir/"coupon_handle_cuff_pink.stl")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donor", type=Path, default=DEFAULT_DONOR)
    export(build(parser.parse_args().donor))
