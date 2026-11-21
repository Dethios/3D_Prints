"""Build the 3D NX3 hat for the Crab NX3 front-facing three-magnet base.

Assembly coordinates are X across the headband, Y up, and Z toward the viewer.
The hat's Z=0 rear face mates to the supplied adapter's +Z face.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import cadquery as cq
import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import shape

from build_reference_mounts import ROOT, planar_solid
from check_and_position import intersection_volume, transform


NX3 = ROOT / "STL" / "NX3"
BASE = ROOT.parent / "magnetic_treasure_crab_ears_NX3" / "stl" / "center_hat_glue_base_3_of_5.stl"
FULL_VARIANT = "Center_Hat_3D"
FLAT_VARIANT = "Center_Hat_3D_Flat_Back"
MATE_GAP = 0.15
PLATE_THICKNESS = 4.6
MAGNET_RADIUS = 3.0
MAGNET_THICKNESS = 3.0
FLAT_SCALE = 1.5
FLAT_BRIM_BOTTOM = 0.9

# Each section is (height, X center, Z center, X radius, Z radius) in mm.
CROWN = [
    (18.0, -0.5, 13.7, 16.2, 9.6),
    (33.0, -1.5, 13.2, 12.5, 7.9),
    (43.0, -2.3, 12.6, 10.1, 6.6),
    (53.0, -3.0, 11.6, 7.5, 5.1),
    (64.4, -3.8, 10.0, 3.8, 2.9),
    (67.45, -3.9, 9.6, 0.3, 0.23),
]
BRIM = [
    (15.4, 0.0, 13.7, 17.4, 11.2),
    (16.1, 0.0, 13.7, 19.0, 12.4),
    (17.2, 0.0, 13.7, 19.5, 12.8),
    (18.4, 0.0, 13.7, 19.2, 12.5),
    (19.5, -0.15, 13.7, 18.2, 11.5),
    (20.0, -0.25, 13.7, 16.9, 10.0),
]
# A deeper lower brim encloses the original three pockets. Each section lies
# on the same vertical centre plane before the rear half is removed.
FLAT_BRIM = [
    (FLAT_BRIM_BOTTOM, 0.0, 0.0, 24.0, 14.5),
    (2.3, 0.0, 0.0, 27.6, 17.4),
    (4.8, 0.0, 0.0, 29.25, 19.2),
    (7.5, -0.1, 0.0, 28.1, 17.9),
    (10.6, -0.3, 0.0, 24.0, 14.0),
]


def ellipse_loft(sections):
    wires = []
    for y, x, z, x_radius, z_radius in sections:
        plane = cq.Plane(origin=(x, y, z), xDir=(1, 0, 0), normal=(0, -1, 0))
        wires.append(cq.Workplane(plane).ellipse(x_radius, z_radius).val())
    return cq.Solid.makeLoft(wires)


def read_base_pockets(base):
    """Measure the three polygonal pocket floors on the actual STL."""
    assert base.is_volume and len(base.split()) == 1
    face_z = float(base.bounds[1, 2])
    pockets = []
    for faces, area, normal in zip(base.facets, base.facets_area, base.facets_normal):
        if normal[2] < 0.999 or not 28 < area < 34:
            continue
        vertices = base.vertices[base.faces[faces]].reshape(-1, 3)
        center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
        radii = np.linalg.norm(vertices[:, :2] - center[:2], axis=1)
        assert np.ptp(radii) < 0.005, (center, radii)
        pockets.append((*np.round(center[:2], 4),
                        round(float(radii.mean()), 4), round(face_z - center[2], 4)))
    assert len(pockets) == 3, f"Expected three front-facing pockets, found {len(pockets)}"
    for _, _, radius, depth in pockets:
        assert MAGNET_RADIUS < radius < 3.35
        assert MAGNET_THICKNESS <= depth <= PLATE_THICKNESS - 1.2
    return face_z, sorted(pockets)


def mount_plate(pockets):
    # The rear pad overlaps the brim from below. Its face is perpendicular to
    # the old under-hat interface and parallel to the supplied base face.
    right_edge = [(11.5, 1.65), (18.0, 1.4), (18.0, 10.7), (11.5, 11.7),
                  (8.5, 14.2), (7.0, 18.7)]
    outline = [(0, 2.2), *right_edge, *((-x, y) for x, y in reversed(right_edge))]
    plate = (cq.Workplane("XY").polyline(outline).close()
             .extrude(PLATE_THICKNESS).edges("|Z").fillet(0.8).val())
    return cut_pockets(plate, pockets)


def cut_pockets(body, pockets):
    tools = [
        cq.Solid.makeCylinder(radius, depth + 0.1, cq.Vector(x, y, -0.1))
        for x, y, radius, depth in pockets
    ]
    return body.cut(*tools)


def flat_back_body(pockets, *, centered=False):
    y_shift = FLAT_BRIM_BOTTOM - FLAT_SCALE * BRIM[0][0]
    crown = ellipse_loft([
        (y * FLAT_SCALE + y_shift, 0.0 if centered else x * FLAT_SCALE, 0.0,
         x_radius * FLAT_SCALE, z_radius * FLAT_SCALE)
        for y, x, _, x_radius, z_radius in CROWN
    ])
    brim = ellipse_loft([
        (y, 0.0 if centered else x, z, x_radius, z_radius)
        for y, x, z, x_radius, z_radius in FLAT_BRIM
    ])
    front_half = cq.Solid.makeBox(100, 120, 40, cq.Vector(-50, -5, 0))
    return crown, cut_pockets(crown.fuse(brim).intersect(front_half), pockets), y_shift


def create_hat(pockets, flat_back):
    if flat_back:
        crown, body, y_shift = flat_back_body(pockets)
        scale, art_z = FLAT_SCALE, 1.5
    else:
        crown = ellipse_loft(CROWN)
        brim = ellipse_loft(BRIM)
        body = crown.fuse(brim, mount_plate(pockets))
        scale, y_shift, art_z = 1.0, 0.0, 12.0

    artwork = shape(json.loads((ROOT / "CAD" / "artwork.json").read_text())["hat"])
    # Keep the original marks, with the top star and crescent nudged toward
    # the centre so the edges remain on the front of the rounded crown.
    marks = []
    for polygon in artwork.geoms:
        center = polygon.centroid
        shift = -2.0 if center.y > 15 else 1.2 if center.x < -3 and center.y > 0 else 0.0
        reduced = affinity.scale(polygon, xfact=0.87 * scale, yfact=0.94 * scale, origin=(0, 0))
        marks.append(affinity.translate(reduced, xoff=shift * scale, yoff=33.0 * scale + y_shift))
    # Trim each extruded mark between two translated copies of the same
    # crown surface. Its exposed face follows the crown's actual curvature.
    front_skin = crown.translate((0, 0, 0.95 * scale)).cut(crown.translate((0, 0, -0.35 * scale)))
    accents = [planar_solid(mark, art_z, 15.0 * scale).intersect(front_skin) for mark in marks]
    white = cq.Compound.makeCompound(accents)
    blue = body.cut(white).clean()
    assembled = body.fuse(*accents).clean()
    return {
        "center_hat_3d_blue": (blue, 1),
        "center_hat_3d_raised_white": (white, 4),
        "center_hat_3d_assembled": (assembled, 1),
    }


def validate_exports(staging, models, base, face_z, pockets, flat_back, insert_fit=None):
    checks = {}
    for name, (solid, count) in models.items():
        assert solid.isValid() and len(solid.Solids()) == count, name
        cq.exporters.export(solid, str(staging / f"{name}.step"))
        # Fresh tessellation at each STL export uses the same chord and angular tolerance.
        cq.exporters.export(solid, str(staging / f"{name}.stl"), tolerance=0.025,
                            angularTolerance=0.10)
        mesh = trimesh.load_mesh(staging / f"{name}.stl")
        step = cq.importers.importStep(str(staging / f"{name}.step")).val()
        assert mesh.is_volume and len(mesh.split()) == count, name
        assert step.isValid() and len(step.Solids()) == count, name
        assert abs(mesh.volume - step.Volume()) < max(0.5, step.Volume() * 0.005), name
        checks[name] = {
            "dimensions_xyz_mm": mesh.extents.round(3).tolist(),
            "mesh_volume_mm3": round(float(mesh.volume), 3),
            "solid_count": count,
        }

    hat = trimesh.load_mesh(staging / "center_hat_3d_assembled.stl")
    blue = trimesh.load_mesh(staging / "center_hat_3d_blue.stl")
    white = trimesh.load_mesh(staging / "center_hat_3d_raised_white.stl")
    assert math.isclose(hat.bounds[0, 2], 0.0, abs_tol=0.001)
    print_face = np.all(np.isclose(hat.triangles[:, :, 2], 0.0, atol=0.001), axis=1)
    if flat_back:
        expected_height = (CROWN[-1][0] - BRIM[0][0]) * FLAT_SCALE
        assert math.isclose(hat.extents[1], expected_height, abs_tol=0.01)
        assert math.isclose(hat.extents[0], 2 * FLAT_BRIM[2][3], abs_tol=0.4)
        assert hat.triangles[print_face, :, 1].max() >= hat.bounds[1, 1] - 0.01
    else:
        assert hat.extents[2] >= 20
    if insert_fit is None:
        assert intersection_volume(blue, white) < 0.5
        assert abs(blue.volume + white.volume - hat.volume) < 1.0
    else:
        insert_fit(staging, blue, white)
    for x, y, radius, depth in pockets:
        # The 6 x 3 mm magnet must fit, and a plug extending through the
        # measured pocket floor must meet solid material.
        for mesh, z in ((hat, MAGNET_THICKNESS / 2),
                        (base, face_z - MAGNET_THICKNESS / 2)):
            magnet = trimesh.creation.cylinder(radius=MAGNET_RADIUS, height=MAGNET_THICKNESS,
                                               sections=96)
            magnet.apply_translation((x, y, z))
            assert intersection_volume(mesh, magnet) < 0.005, (x, y, z)
        depth_probe = trimesh.creation.cylinder(radius=radius - 0.03, height=0.1, sections=96)
        depth_probe.apply_translation((x, y, depth))
        assert 0.45 < intersection_volume(hat, depth_probe) / depth_probe.volume < 0.55
        if flat_back:
            # Each brim pocket is enclosed by at least one 0.5 mm extrusion
            # across its full depth. Exclude the central bore from the probe.
            wall_probe = trimesh.creation.annulus(r_min=radius + 0.03, r_max=radius + 0.6,
                                                  height=depth - 0.1, sections=96)
            wall_probe.apply_translation((x, y, depth / 2))
            assert intersection_volume(hat, wall_probe) / wall_probe.volume > 0.999

    hat_in_base_frame = hat.copy()
    hat_in_base_frame.apply_translation((0, 0, face_z + MATE_GAP))
    poses = json.loads((ROOT / "CAD" / "assembly_positions.json").read_text())["NX3"]
    posed_hat = transform(hat_in_base_frame, poses["center_hat"])
    posed_base = transform(base, poses["center_hat"])
    band = trimesh.load_mesh(ROOT / "Reference_files" / "dressyspider_larger_headband_source.stl")
    # The source headband is an open mesh. The Z bounds alone prove separation.
    band_gap = posed_hat.bounds[0, 2] - band.bounds[1, 2]
    assert band_gap > 0.0, band_gap
    clearances = {
        "supplied_center_base": intersection_volume(posed_hat, posed_base),
    }
    for side in ("left_brooms", "right_mouse"):
        for part, name in (("ear", f"{side}_assembled"), ("base", "glue_on_base_SOURCE_GEOMETRY")):
            posed = transform(trimesh.load_mesh(NX3 / f"{name}.stl"), poses[side])
            clearances[f"{side}_{part}"] = intersection_volume(posed_hat, posed)
    assert max(clearances.values()) < 0.005, clearances
    return {
        "status": "PASS",
        "mating_base": BASE.relative_to(ROOT.parent).as_posix(),
        "mating_base_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "mount_normal": "-Z (rear), 90 degrees from the under-hat mount",
        "nominal_mating_gap_mm": MATE_GAP,
        "crown_scale": FLAT_SCALE if flat_back else 1.0,
        "vertical_bisection": flat_back,
        "print_face_area_mm2": round(float(hat.area_faces[print_face].sum()), 3),
        "hat_offset_from_base_mm": [0.0, 0.0, round(face_z + MATE_GAP, 3)],
        "matching_pockets": [
            {"center_xy_mm": [x, y], "diameter_mm": 2 * radius, "depth_mm": depth}
            for x, y, radius, depth in pockets
        ],
        "nominal_assembly_intersections_mm3": clearances,
        "headband_front_clearance_lower_bound_mm": round(float(band_gap), 3),
        "exports": checks,
        "physical_fit": "Pending",
    }


def build(flat_back=False):
    variant = FLAT_VARIANT if flat_back else FULL_VARIANT
    base = trimesh.load_mesh(BASE)
    face_z, pockets = read_base_pockets(base)
    models = create_hat(pockets, flat_back)
    with TemporaryDirectory() as temporary:
        staging = Path(temporary)
        report = validate_exports(staging, models, base, face_z, pockets, flat_back)
        cad_dir = ROOT / "CAD" / "NX3" / variant
        stl_dir = NX3 / variant
        for folder, extension in ((cad_dir, "step"), (stl_dir, "stl")):
            folder.mkdir(exist_ok=True)
            for path in staging.glob(f"*.{extension}"):
                shutil.copyfile(path, folder / path.name)
        (cad_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flat-back", action="store_true", help="Build the enlarged bisected hat.")
    build(flat_back=parser.parse_args().flat_back)
