"""Audit reopened R6 3MFs against exported physical K2 commands and toolpaths."""

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
from itertools import groupby
import json
import math
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageDraw
from shapely.affinity import affine_transform
from shapely.geometry import MultiPoint, shape
from shapely.ops import unary_union

from build_plates import (
    ASA, ASSIGN, ASSET_ROOT, GEOMETRY, HERE, MIXES, MODEL_CONFIG, PALETTE,
    PROJECT, PREFIX, PRESET, PURPLE, recipe,
)


ART = PROJECT / "art/R6/castle_profiles.json"
INSPECTOR = ASSET_ROOT / "Projects/minnie_ticket_wand/asa_slicer/inspect_gcode.py"
REQUIRED = {
    "printer_settings_id": PRESET,
    "print_settings_id": PRESET,
    "nozzle_diameter": "0.6,0.6,0.6,0.6",
    "layer_height": "0.12",
    "first_layer_height": "0.2",
    "filament_type": "PLA;PLA;PLA;PLA",
    "temperature": "210,210,210,210",
    "first_layer_temperature": "215,215,215,215",
    "bed_temperature": "55,55,55,55",
    "first_layer_bed_temperature": "60,60,60,60",
    "max_volumetric_speed": "6",
    "filament_max_volumetric_speed": "6,6,6,6",
    "single_extruder_multi_material_priming": "0",
    "wipe_tower": "0",
    "post_process": "",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_inspector():
    spec = importlib.util.spec_from_file_location("r6_toolpath_inspector", INSPECTOR)
    inspector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = inspector
    spec.loader.exec_module(inspector)
    return inspector


def expected_tools(extruder, mixes):
    if extruder in mixes:
        return {f"T{slot - 1}" for slot in mixes[extruder]}
    return {f"T{extruder - 1}"}


def read_config(data):
    return dict(line[2:].split(" = ", 1) for line in data.splitlines() if line.startswith("; ") and " = " in line)


def source_transforms(project):
    with ZipFile(project) as archive:
        settings = ET.fromstring(archive.read(MODEL_CONFIG))
        geometry = archive.read(GEOMETRY)
    names = {
        item.get("id"): item.find("./metadata[@key='name']").get("value")
        for item in settings.findall("object")
    }
    transforms = {
        names[item.get("objectid")]: list(map(float, item.get("transform").split()))
        for item in ET.fromstring(geometry).findall("{*}build/{*}item")
    }
    return geometry, transforms


def model_moves(moves, label):
    return (move for move in moves if move.item == label and move.role != "Skirt/Brim"
            and "support" not in move.role.lower())


def layer_breakdown(records, label):
    return {
        z: Counter(move.tool for move in model_moves(moves, label))
        for z, moves in sorted(records.items())
        if any(model_moves(moves, label))
    }


def report_swatches(items, records, inspector):
    result = {}
    for name in items:
        by_layer = layer_breakdown(records, inspector.object_label(name))
        result[name] = {
            "deposited_layers_by_physical_tool": {
                f"T{tool}": count for tool, count in sorted(Counter(
                    tool for tools in by_layer.values() for tool in tools
                ).items())
            },
            "exposed_flat_top_z_mm": max(by_layer),
            "exposed_flat_top_physical_tools": [f"T{tool}" for tool in by_layer[max(by_layer)]],
        }
    return result


def report_bridges_and_supports(records, transform_by_name, inspector):
    roles = defaultdict(list)
    for z, moves in records.items():
        for move in moves:
            assert move.tool in range(4), move
            assert all(0 <= coordinate <= 260 for point in (move.a, move.b) for coordinate in point), move
            if "bridge" in move.role.lower() or "support" in move.role.lower():
                roles[move.item, move.role].append((z, move))
    result = defaultdict(dict)
    translation = {inspector.object_label(name): transform[9:] for name, transform in transform_by_name.items()}
    for (label, role), paths in roles.items():
        coords = np.array([(x, y, z) for z, move in paths for x, y in (move.a, move.b)])
        row = {
            "segments": len(paths),
            "tool_set": sorted({f"T{move.tool}" for _, move in paths}),
            "longest_centerline_move_mm": round(max(math.dist(move.a, move.b) for _, move in paths), 3),
            "bed_bounds_mm": [coords.min(axis=0).round(3).tolist(), coords.max(axis=0).round(3).tolist()],
        }
        if "support" in role.lower():
            # The cover and coupon keep their assembly Y direction in their sourced print pose.
            assert label in {"Castle_star_face", "Rear_shell", "Front_shell_coupon", "Rear_shell_coupon"}
            t_x, t_y, _ = translation[label]
            path_radius = max(move.width for _, move in paths) / 2
            x_distance = max(abs(coords[:, 0] - t_x)) + path_radius
            max_y = coords[:, 1].max() - t_y + path_radius
            assert x_distance < 2.0 and max_y < -57.75, (label, row)
            row.update(max_mm_from_thread_axis_x=round(x_distance, 3), max_assembly_y_mm=round(max_y, 3))
        result[label][role] = row
    return result


def world_to_image(bounds, scale):
    low_x, low_y, high_x, high_y = bounds

    def xy(p):
        return round((p[0] - low_x) * scale), round((high_y - p[1]) * scale)

    return xy, (math.ceil((high_x - low_x) * scale) + 1, math.ceil((high_y - low_y) * scale) + 1)


def draw_beads(draw, moves, xy, scale):
    for move in moves:
        a, b = xy(move.a), xy(move.b)
        radius = move.width * scale / 2
        color = move.tool + 1
        draw.line((a, b), fill=color, width=max(1, round(radius * 2)))
        for x, y in (a, b):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def region_mask(region, xy, image_size):
    image = Image.new("1", image_size)
    draw = ImageDraw.Draw(image)
    geometry = [region] if region.geom_type == "Polygon" else getattr(region, "geoms", [])
    for polygon in geometry:
        if polygon.is_empty or polygon.geom_type != "Polygon":
            continue
        draw.polygon([xy(v) for v in polygon.exterior.coords], fill=255)
        for interior in polygon.interiors:
            draw.polygon([xy(v) for v in interior.coords], fill=0)
    return image


def profiles(transform, element):
    features = [
        row for row in json.loads(ART.read_text(encoding="utf-8"))["features"] if row["part"] == element
    ]
    overlaid = []
    regions = {}
    matrix = [transform[0], transform[3], transform[1], transform[4], *transform[9:11]]
    for row in reversed(sorted(features, key=lambda entry: entry["relief_mm"])):
        name = row["id"]
        uncut = shape(row["geometry"]).buffer(0)
        if row["relief_mm"] or name == "star-field":
            visible = uncut.difference(unary_union(overlaid))
            regions[name] = affine_transform(visible, matrix)
        if row["relief_mm"]:
            overlaid.append(uncut)
    return regions


def audit_feature_projection(records, name, transform, element, output):
    regions = profiles(transform, element)
    low_x, low_y, high_x, high_y = unary_union(list(regions.values())).bounds
    projection, xy = top_projection(records, name, (low_x - 2, low_y - 2, high_x + 2, high_y + 2))
    save_color_projection(projection, output)
    return projected_region_tools(projection, xy, regions), regions


def top_projection(records, name, bounds):
    scale = 15
    xy, size = world_to_image(bounds, scale)
    label = re.sub(r"[^A-Za-z0-9_]", "_", name)
    projection = Image.new("P", size)
    draw = ImageDraw.Draw(projection)
    for moves in (records[z] for z in sorted(records)):
        draw_beads(draw, model_moves(moves, label), xy, scale)
    return projection, xy


def save_color_projection(projection, output):
    colors = [(24, 27, 35), *(ImageColor.getrgb(value) for value in PALETTE)]
    projection.putpalette([channel for color in colors for channel in color])
    projection.save(output)


def projected_region_tools(projection, xy, regions):
    surface = np.asarray(projection)
    result = {}
    for name, region in regions.items():
        if region.area < 1:
            continue
        selected = np.asarray(region_mask(region.buffer(-0.2), xy, projection.size))
        counts = Counter(surface[selected].tolist())
        count = sum(counts.values())
        if count:
            result[name] = {
                ("uncovered" if tool == 0 else f"T{tool - 1}"): round(pixels / count, 4)
                for tool, pixels in sorted(counts.items())
            }
    return result


def audit_sloped_swatch(records, parts, scratch):
    name = "Purple slope 18 deg"
    _, mesh = parts[name]["Purple slope"]
    (low_x, low_y, _), (high_x, high_y, _) = mesh.bounds
    projection, xy = top_projection(records, name, (low_x, low_y, high_x, high_y))
    x, above_y = xy(((low_x + high_x) / 2, high_y - 0.8))
    _, below_y = xy((low_x, low_y + 0.8))
    scan = np.asarray(projection)[above_y:below_y, x]
    runs = [(int(tool), len(list(pixels))) for tool, pixels in groupby(scan) if tool]
    assert set(tool for tool, _ in runs) == {1, 2} and len(runs) >= 12, runs
    save_color_projection(projection, scratch / "projected_purple_slope.png")
    return {
        "alternating_tool_bands_along_central_y_scan": len(runs),
        "median_band_spacing_projected_mm": round(float(np.median([pixels for _, pixels in runs])) / 15, 3),
        "projected_scan_physical_tools": sorted({f"T{tool - 1}" for tool, _ in runs}),
    }


def audit_grip_bands(records, parts):
    name = "Threaded grip"
    _, mesh = parts[name]["handle_gold"]
    components = sorted(mesh.split(), key=lambda part: part.bounds[0, 1])
    assert len(components) == 3
    outlines = {
        label: MultiPoint(part.vertices[:, :2]).convex_hull
        for label, part in zip(("pommel ring", "second collar", "top collar"), components)
    }
    low_x, low_y, high_x, high_y = unary_union(list(outlines.values())).bounds
    projection, xy = top_projection(records, name, (low_x, low_y, high_x, high_y))
    bands = projected_region_tools(projection, xy, outlines)
    assert len(bands) == 3 and all(tools.get("T3", 0) >= 0.95 for tools in bands.values()), bands
    return bands


def flag_layers(records, flag, region):
    low_x, low_y, high_x, high_y = region.bounds
    scale = 30
    xy, size = world_to_image((low_x - 1, low_y - 1, high_x + 1, high_y + 1), scale)
    mask = region_mask(region, xy, size)
    mask_count = mask.histogram()[255]
    previous = Image.new("1", size)
    results = []
    for z, moves in sorted(records.items()):
        local = [
            move for move in model_moves(moves, "Castle_star_face")
            if min(move.a[0], move.b[0]) < high_x + 0.6 and max(move.a[0], move.b[0]) > low_x - 0.6
            and min(move.a[1], move.b[1]) < high_y + 0.6 and max(move.a[1], move.b[1]) > low_y - 0.6
        ]
        # Use a separate monochrome footprint to check the prior layer, regardless of filament.
        all_beads = Image.new("L", size)
        draw_beads(ImageDraw.Draw(all_beads), local, xy, scale)
        gold = all_beads.point(lambda v: 255 if v == 4 else 0, mode="1")
        gold_here = ImageChops.logical_and(gold, mask)
        pixels = gold_here.histogram()[255]
        if pixels > mask_count * 0.01:
            prior_contact = ImageChops.logical_and(gold_here, previous).histogram()[255]
            results.append((z, pixels / mask_count, prior_contact / pixels))
        previous = all_beads.point(lambda v: 255 if v else 0, mode="1")
    assert len(results) >= 3, flag
    assert max(row[1] for row in results) > 0.85, (flag, results)
    assert results[0][2] > 0.8, (flag, results)
    return {
        "first_z_mm": results[0][0], "last_z_mm": results[-1][0], "layers_with_gold": len(results),
        "max_nominal_profile_coverage": round(max(row[1] for row in results), 4),
        "first_gold_bead_coverage_supported_by_prior_deposit": round(results[0][2], 4),
    }


def audit_plate(project, scratch, inspector):
    gcode = scratch / project.with_suffix(".gcode").name
    log = gcode.with_suffix(".log").read_text(encoding="utf-8")
    warnings = [line for line in log.splitlines() if re.search(r"\b(warning|floating|error|detached)\b", line, re.I)]
    assert not warnings, (project.name, warnings)
    records, _, commands, summary = inspector.parse_gcode(gcode)
    config = read_config(gcode.read_text(encoding="utf-8"))
    effective = {key: config[key] for key in REQUIRED}
    assert effective == REQUIRED, (project.name, effective)
    model, attached_recipe = inspector.read_project(project)
    geometry, transforms = source_transforms(project)

    model_audit = inspector.audit_item_paths(model, records)
    mixes = {index: ratio for index, (_, ratio) in MIXES.items()}
    production = project.name.startswith(PREFIX) and "Swatches" not in project.name
    alternate = "Solid_Blue" in project.name
    extruder_uses = {slot for parts in model.values() for slot, _ in parts.values()}
    used_recipe_ids = extruder_uses.intersection(MIXES)
    assert attached_recipe == (recipe(used_recipe_ids) if used_recipe_ids else None)
    expected = set()
    for item, row in model_audit.items():
        wanted = set()
        for name, slot in row["part_extruders"].items():
            if production:
                assert slot == (1 if alternate and ASSIGN[name] == PURPLE else ASSIGN[name]), (name, slot)
            wanted.update(expected_tools(slot, mixes))
        assert wanted == set(row["model_tools"]), (project.name, item, wanted, row)
        assert row["first_layer_bead_area_estimate_mm2"] > 0, (project.name, item)
        expected.update(wanted)
    if project.stem == "Control_A_Blue":
        assert expected == {"T0"}
    if project.stem == "Control_D_Gold":
        assert expected == {"T3"}
    selections = [command for _, command in commands if inspector.TOOL.fullmatch(command)]
    assert set(selections) == expected, (project.name, set(selections))
    markers = inspector.find_markers(commands)
    assert len(markers["object_polygons"]) == len(model), project.name
    assert dict(commands)[markers["start"]] == "START_PRINT EXTRUDER_TEMP=215 BED_TEMP=60"
    assert dict(commands)[markers["hotend_wait"]] == "M109 S215"
    assert sum(command == "LINE_PURGE" for _, command in commands) == 1
    assert any(command == "M140 S55" for _, command in commands)
    assert len(selections) == int(summary.get("total toolchanges", 0)) + 1
    assert max(move.speed for paths in records.values() for move in paths) <= 60.02
    assert max(move.speed for move in records[min(records)]) <= 25.02

    report = {
        "project_sha256": sha(project.read_bytes()),
        "geometry_xml_sha256": sha(geometry),
        "scratch_gcode_sha256": sha(gcode.read_bytes()),
        "slicer": gcode.read_text(encoding="utf-8").splitlines()[0].removeprefix("; generated by "),
        "effective_settings": effective,
        "material_and_time": {key: summary.get(key, "0") for key in (
            "estimated printing time (normal mode)", "total toolchanges", "total filament used [g]", "filament used [g]"
        )},
        "physical_tool_commands_in_order": selections,
        "startup_and_shutdown_lines": markers,
        "color_mix": attached_recipe,
        "items": model_audit,
        "model_build_transforms": transforms,
        "bridges_and_supports": report_bridges_and_supports(records, transforms, inspector),
        "warnings": warnings,
    }
    if production:
        stem = project.stem.removeprefix(PREFIX).removesuffix("_Solid_Blue")
        source = ASA / f"K2_04_ASA_Castle_R6_{stem}.3mf"
        source_geometry, _ = source_transforms(source)
        assert source_geometry == geometry, project.name
        report["same_geometry_and_transforms_as"] = source.name
    if "Swatches" in project.name:
        report["swatches"] = report_swatches(model, records, inspector)
        report["purple_18_degree_swatch_slope"] = audit_sloped_swatch(records, model, scratch)
    if "Threaded_Grip" in project.name:
        report["gold_band_top_projected_tool_area_fraction"] = audit_grip_bands(records, model)
    if "Star_Face" in project.name or "Pink_Bow" in project.name:
        name = next(iter(transforms))
        element = "head" if "Star_Face" in project.name else "bow"
        projection, regions = audit_feature_projection(records, name, transforms[name], element,
                                                     scratch / f"projected_{element}_toolpaths.png")
        report["top_projected_tool_area_fraction"] = projection
        if element == "head":
            report["flags"] = {
                name: flag_layers(records, name, outline)
                for name, outline in regions.items() if name.endswith("-flag")
            }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plates", type=Path, default=HERE)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    inspector = load_inspector()
    paths = sorted(args.plates.glob(f"{PREFIX}*.3mf")) + sorted(args.scratch.glob("Control_*.3mf"))
    if not paths:
        raise ValueError("No native projects to audit.")
    results = {}
    for path in paths:
        results[path.name] = audit_plate(path, args.scratch, inspector)
        print(path.name, results[path.name]["material_and_time"], flush=True)
    build_record = args.scratch / "build.json"
    report = {
        "r6_art_sha256": sha(ART.read_bytes()),
        "embedded_profile_overrides_and_source_records": json.loads(build_record.read_text(encoding="utf-8")),
        "plates": results,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
