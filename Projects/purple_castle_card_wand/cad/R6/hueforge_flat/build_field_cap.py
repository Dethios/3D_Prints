"""Split the frozen R6 front carrier into a base and a one-layer field cap."""

import argparse
import json
import math
import sys
from pathlib import Path

import cadquery as cq
import trimesh
from shapely import MultiPolygon
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
R6 = HERE.parent
sys.path.insert(0, str(R6.parent))
from build_wand import digest, polygons, prism, save_stl

ART = R6.parents[1] / "art/R6/castle_profiles.json"
STEP = R6 / "purple_castle_card_wand_R6.step"
SOURCE_HASHES = {
    ART: "ff1b7d81a01e941be9c393d3b716d585c54cd923cb2af1f61c3441d363779094",
    STEP: "a82407cd00a1db9faeb40fd8c2b01c9a81352e0b157cbc0662e062f34d2f612b",
}
DATUM = 0.90
CAP_BOTTOM = 2.78
CAP_TOP = 2.90
FIELD_MARGIN = 0.23
ART_MARGIN = 0.28
OPENING_RADIUS = 0.46
CONTOUR_TOLERANCE = 0.06
MIN_REGION_AREA = 25.0
VOLUME_TOLERANCE = 1e-5
INTEGRATION_TOLERANCE = 1e-11
INTEGRATED_PARTITION_TOLERANCE = 0.01


def field_mask(art):
    """Reserve the original lip and the full projected ornament and bow footprints."""
    features = art["features"]
    field = next(shape(f["geometry"]) for f in features if f["id"] == "star-field")
    decorations = [
        shape(f["geometry"]) for f in features
        if f["part"] == "head" and f["relief_mm"] > 0
    ]
    bow = shape(art["footprints"]["bow"]["geometry"])
    keepouts = unary_union([bow, *decorations])
    exposed = field.difference(keepouts)

    # Reserve enough extra space for the contour simplification to stay inside
    # the nominal keepouts while eliminating tiny chamfers and stepped segments.
    window = field.buffer(-FIELD_MARGIN - CONTOUR_TOLERANCE, quad_segs=4)
    window = window.difference(keepouts.buffer(ART_MARGIN + CONTOUR_TOLERANCE + 0.01, quad_segs=4))
    opened = window.buffer(-OPENING_RADIUS, quad_segs=4).buffer(OPENING_RADIUS, quad_segs=4)
    simplified = opened.simplify(CONTOUR_TOLERANCE, preserve_topology=True)
    selected = MultiPolygon([p for p in polygons(simplified) if p.area >= MIN_REGION_AREA])
    assert selected.is_valid and not selected.is_empty
    assert all(p.buffer(-OPENING_RADIUS, quad_segs=4).area > 0 for p in selected.geoms)
    assert selected.distance(keepouts) >= ART_MARGIN
    assert field.contains(selected) and selected.distance(field.boundary) >= FIELD_MARGIN
    return selected, exposed.area, selected.distance(keepouts), selected.distance(field.boundary)


def solid_volume(body):
    return sum(solid.Volume(tol=INTEGRATION_TOLERANCE) for solid in body.Solids())


def bounds(body):
    box = body.BoundingBox()
    return [[box.xmin, box.ymin, box.zmin], [box.xmax, box.ymax, box.zmax]]


def export_mesh(body, path):
    exact_bounds = bounds(body)
    save_stl(body, path)
    mesh = trimesh.load_mesh(path)
    assert mesh.is_volume and mesh.is_watertight and mesh.is_winding_consistent, path
    assert len(mesh.split(only_watertight=False)) == len(body.Solids()), path
    for actual, exact in zip(mesh.bounds, exact_bounds, strict=True):
        assert all(abs(m - b) < 0.005 for m, b in zip(actual, exact, strict=True)), path
    return {
        "sha256": digest(path),
        "solid_count": len(body.Solids()),
        "watertight": mesh.is_watertight,
        "consistent_winding": mesh.is_winding_consistent,
        "bounds_mm": mesh.bounds.tolist(),
        "stl_volume_mm3": mesh.volume,
        "exact_volume_mm3": solid_volume(body),
    }


def build(out, mask_only=False):
    for path, expected in SOURCE_HASHES.items():
        if digest(path) != expected:
            raise ValueError(f"Unexpected frozen source revision for {path}")

    art = json.loads(ART.read_text(encoding="utf-8"))
    assert art["units"] == "mm" and art["axes"] == "front XY; +X right, +Y toward tip, +Z toward observer"
    mask, exposed, decor_gap, rim_gap = field_mask(art)
    print(f"Field mask {mask.area:.3f} mm² in {len(mask.geoms)} regions", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    cap_region = out / "cap_region.json"
    cap_region.write_text(json.dumps(mapping(mask), separators=(",", ":")) + "\n", encoding="utf-8")
    if mask_only:
        return

    source = cq.Assembly.load(str(STEP))
    parts = {name: node.obj for name, node in source.objects.items() if node.obj is not None}
    assert len(parts) == 9 and sum(len(body.Solids()) for body in parts.values()) == 28
    assert all(body.isValid() for body in parts.values())
    original = parts["head_purple"]
    assert len(original.Solids()) == 1
    original_bounds = bounds(original)
    assert math.isclose(original_bounds[0][2], DATUM, abs_tol=VOLUME_TOLERANCE)
    prism_mask = prism(mask, CAP_BOTTOM, CAP_TOP)
    cap = original.intersect(prism_mask).clean()
    assert cap.isValid() and len(cap.Solids()) == len(mask.geoms)
    assert abs(solid_volume(cap) - mask.area * (CAP_TOP - CAP_BOTTOM)) < VOLUME_TOLERANCE
    base = original.cut(cap).clean()
    assert base.isValid() and len(base.Solids()) == 1
    for before, after in zip(original_bounds, bounds(base), strict=True):
        assert all(abs(b - a) < VOLUME_TOLERANCE for b, a in zip(before, after, strict=True))

    bodies = {"head_base": base, "head_field_cap": cap}
    mesh_outputs = {name + ".stl": export_mesh(body, out / (name + ".stl"))
                    for name, body in bodies.items()}
    print("Reloaded watertight base and cap STL files", flush=True)

    # Test the positive-volume intersection and both directions of the true CAD
    # difference against the original carrier, in addition to checking volume.
    overlap = solid_volume(base.intersect(cap))
    assert overlap < VOLUME_TOLERANCE
    fused = base.fuse(*cap.Solids()).clean()
    assert fused.isValid() and len(fused.Solids()) == 1
    missing_solid = original.cut(fused)
    additional_solid = fused.cut(original)
    missing = solid_volume(missing_solid)
    additional = solid_volume(additional_solid)
    volume_residual = solid_volume(base) + solid_volume(cap) - solid_volume(original)
    print(f"CAD differences in mm³: missing {missing:.8g}, added {additional:.8g}, "
          f"partition volume residual {volume_residual:.8g}", flush=True)
    assert not missing_solid.Solids() and not additional_solid.Solids()
    # The Boolean result proves both directional differences are empty.
    # Integrating the curved, trimmed carrier faces has finite numerical error.
    assert abs(volume_residual) < INTEGRATED_PARTITION_TOLERANCE
    ornament_overlaps = {
        name: solid_volume(cap.intersect(parts[name]))
        for name in ("head_gold", "head_cream", "head_blue", "bow_pink")
    }
    assert max(ornament_overlaps.values()) < VOLUME_TOLERANCE
    print("Verified carrier recombination and CAD ornament clearance", flush=True)

    exchange = out / "head_field_split.step"
    assembly = cq.Assembly(name="R6_front_carrier_field_split")
    for name, body in bodies.items():
        assembly.add(body, name=name)
    assembly.export(str(exchange))
    readback = cq.Assembly.load(str(exchange))
    for name, body in bodies.items():
        read = readback.objects[name].obj
        assert read.isValid() and len(read.Solids()) == len(body.Solids())
        assert abs(solid_volume(read) - solid_volume(body)) < VOLUME_TOLERANCE

    results = {
        "units": "mm",
        "axes": art["axes"],
        "art_revision": art["revision"],
        "source_sha256": {path.name: digest(path) for path in SOURCE_HASHES},
        "source_step_valid_solid_count": 28,
        "cadquery_version": cq.__version__,
        "original_carrier_bounds_mm": original_bounds,
        "original_carrier_volume_mm3": solid_volume(original),
        "assembly_print_datum_z_mm": DATUM,
        "cap_assembly_z_mm": [CAP_BOTTOM, CAP_TOP],
        "cap_print_z_mm": [round(z - DATUM, 2) for z in (CAP_BOTTOM, CAP_TOP)],
        "cap_section_area_mm2": mask.area,
        "cap_region_sha256": digest(cap_region),
        "cap_component_areas_mm2": sorted((p.area for p in mask.geoms), reverse=True),
        "projected_exposed_art_field_area_mm2": exposed,
        "cap_fraction_of_projected_exposed_art_field": mask.area / exposed,
        "xy_cap_clearance_from_projected_ornaments_mm": decor_gap,
        "xy_cap_clearance_from_original_field_boundary_mm": rim_gap,
        "exact_base_cap_overlap_mm3": overlap,
        "exact_recombined_geometry_missing_mm3": missing,
        "exact_recombined_geometry_added_mm3": additional,
        "integrated_partition_volume_residual_mm3": volume_residual,
        "exact_cap_ornament_overlap_mm3": ornament_overlaps,
        "mesh_outputs": mesh_outputs,
        "step_output_sha256": digest(exchange),
    }
    (out / "validation_report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Verified cap and base exports in {out}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE, help="export directory")
    parser.add_argument("--mask-only", action="store_true", help="export the 2D cap region only")
    args = parser.parse_args()
    build(args.out, args.mask_only)
