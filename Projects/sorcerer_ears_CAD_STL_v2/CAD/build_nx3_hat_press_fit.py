"""Build the flat-back NX3 hat with separately printable moon and stars."""

import json
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import cadquery as cq
import numpy as np
from shapely.geometry import Point, Polygon
import trimesh

from build_nx3_center_hat_3d import (
    BASE, FLAT_BRIM, NX3, ROOT, flat_back_body, read_base_pockets, validate_exports,
)
from build_reference_mounts import planar_solid


VARIANT = "Center_Hat_3D_Press_Fit_Centered"
CLEARANCE = 0.08  # Per side, before printer/material compensation.
LEAD_IN = 0.22
LEAD_HEIGHT = 0.55
RELIEF = 0.7
PRINT_SPACING = 10.0


def star(x, y, radius, rotation):
    vertices = []
    for index in range(10):
        angle = math.pi / 2 + rotation + index * math.pi / 5
        length = radius * (0.48 if index % 2 else 1)
        vertices.append((x + length * math.cos(angle), y + length * math.sin(angle)))
    return Polygon(vertices)


def artwork():
    moon = Point(-0.85, 39.7).buffer(12.35, quad_segs=32).difference(
        Point(6.2, 45.05).buffer(11.65, quad_segs=32)
    )
    marks = [
        ("crescent", moon, 3.1),
        ("top_star", star(0.0, 63.1, 8.2, -0.15), 2.2),
        ("small_right_star", star(5.6, 49.9, 5.15, 0.05), 3.1),
        ("lower_left_star", star(-10.95, 19.2, 7.9, -0.24), 3.35),
        ("lower_right_star", star(10.0, 19.4, 8.5, -0.14), 3.75),
    ]
    for name, outline, seat in marks:
        # Round the thin points so they survive slicing with the 0.5 mm nozzle.
        outline = outline.buffer(-0.48, quad_segs=5).buffer(0.48, quad_segs=5)
        yield name, outline.simplify(0.035, preserve_topology=True), seat


def insert_blank(outline, floor):
    """Chamfer the entry edge before trimming the cap to the crown."""
    blank = planar_solid(outline, floor, 25)
    return cq.Workplane(obj=blank).edges("<Z").chamfer(LEAD_HEIGHT, LEAD_IN).val()


def create_models(pockets):
    crown, body, _ = flat_back_body(pockets, centered=True)
    cap = crown.translate((0, 0, RELIEF))
    inserts, bed_parts, cutters, fused_caps, dimensions = [], [], [], [], {}
    next_x = 0.0
    for name, outline, floor in artwork():
        socket = outline.buffer(CLEARANCE, quad_segs=5)
        # Ensure every socket has a continuous rim and a flat seat entirely
        # inside the crown, including the most outboard point of each star.
        seat_test = planar_solid(socket.buffer(0.42, quad_segs=5), floor - 0.1, 0.65)
        assert body.intersect(seat_test).Volume() / seat_test.Volume() > 0.9999, name
        cutter = planar_solid(socket, floor, 25)
        blank = insert_blank(outline, floor)
        insert = blank.intersect(cap).clean()
        assert insert.isValid() and len(insert.Solids()) == 1, name
        assert cutter.intersect(insert).Volume() / insert.Volume() > 0.9999, name
        inserts.append(insert)
        bounds = insert.BoundingBox()
        bed_parts.append(insert.translate((next_x - bounds.xmin, -bounds.ymin, -floor)))
        next_x += bounds.xlen + PRINT_SPACING
        cutters.append(cutter)
        fused_caps.append(planar_solid(outline, floor, 25).intersect(cap))
        dimensions[name] = {
            "artwork_area_mm2": round(outline.area, 2),
            "plan_dimensions_mm": [round(bounds.xlen, 2), round(bounds.ylen, 2)],
            "seat_z_mm": floor,
        }
    blue = body.cut(*cutters).clean()
    assembled = body.fuse(*fused_caps).clean()
    count = len(inserts)
    return {
        "center_hat_3d_blue": (blue, 1),
        "center_hat_3d_raised_white": (cq.Compound.makeCompound(inserts), count),
        "center_hat_3d_assembled": (assembled, 1),
        "moon_and_stars_flat_print": (cq.Compound.makeCompound(bed_parts), count),
    }, dimensions


def validate_insert_fit(staging, blue, white):
    overlap = trimesh.boolean.intersection([blue, white], engine="manifold")
    with np.errstate(divide="ignore", invalid="ignore"):
        assert overlap.is_empty or abs(overlap.volume) < 0.02, "Inserted artwork collides with the hat"
    mesh = trimesh.load_mesh(staging / "moon_and_stars_flat_print.stl")
    parts = sorted(mesh.split(), key=lambda part: part.bounds[0, 0])
    assert all(right.bounds[0, 0] - left.bounds[1, 0] >= PRINT_SPACING - 0.01
               for left, right in zip(parts, parts[1:]))
    for insert in parts:
        assert abs(insert.bounds[0, 2]) < 0.001, insert.bounds
        on_bed = np.all(np.isclose(insert.triangles[:, :, 2], 0, atol=0.001), axis=1)
        assert insert.area_faces[on_bed].sum() > 20, "Insert needs a substantial planar print face"


def check_rear_outline(path):
    mesh = trimesh.load_mesh(path)
    on_bed = np.all(np.isclose(mesh.triangles[:, :, 2], 0, atol=0.001), axis=1)
    rear = mesh.submesh([np.flatnonzero(on_bed)], append=True, repair=False)
    heights = np.arange(mesh.bounds[0, 1] + 0.1, mesh.bounds[1, 1] - 0.1, 0.5)
    spans = []
    for height in heights:
        edges = trimesh.intersections.mesh_plane(rear, (0, 1, 0), (0, height, 0))
        xs = edges[:, :, 0]
        spans.append((float(xs.min()), float(xs.max())))
    left, right = np.array(spans).T
    drift = float(np.max(np.abs((left + right) / 2)))
    # Linear interpolation of independently tessellated edges can differ
    # slightly near the rounded tip, even with mirrored CAD sections.
    assert drift < 0.1, f"Rear silhouette deviates {drift:.3f} mm from X=0"
    widths = (right - left)[heights > FLAT_BRIM[-1][0]]
    assert np.max(np.diff(widths)) < 0.05, "Crown width should taper continuously above the brim"
    return round(drift, 4)


def build():
    base = trimesh.load_mesh(BASE)
    face_z, pockets = read_base_pockets(base)
    models, dimensions = create_models(pockets)
    with TemporaryDirectory() as temp:
        staging = Path(temp)
        report = validate_exports(staging, models, base, face_z, pockets, flat_back=True,
                                  insert_fit=validate_insert_fit)
        report["rear_outline_max_center_drift_mm"] = check_rear_outline(
            staging / "center_hat_3d_blue.stl"
        )
        report["press_fit"] = {
            "nominal_clearance_per_side_mm": CLEARANCE,
            "entry_bevel_mm": [LEAD_IN, LEAD_HEIGHT],
            "relief_above_crown_mm": RELIEF,
            "pieces": dimensions,
            "physical_press_fit": "Pending",
        }
        cad_dir = ROOT / "CAD" / "NX3" / VARIANT
        for folder, extension in ((cad_dir, "step"), (NX3 / VARIANT, "stl")):
            folder.mkdir(exist_ok=True)
            for path in staging.glob(f"*.{extension}"):
                shutil.copyfile(path, folder / path.name)
        (cad_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
