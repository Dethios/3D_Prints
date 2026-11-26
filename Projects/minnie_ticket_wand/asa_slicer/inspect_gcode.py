"""Read the emitted K2 G-code and audit material paths in the packaged 3MF coordinates."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union
import trimesh


MODEL_NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
TOOL = re.compile(r"^T(\d+)$")
AXES = re.compile(r"([XYEF])(-?(?:\d*\.)?\d+)")
OBJECT_START = re.compile(r"^EXCLUDE_OBJECT_START NAME='([^']+)'$")
REPORTED_KEYS = (
    "filament used [g]", "total filament used [g]", "total toolchanges",
    "estimated printing time (normal mode)", "nozzle_diameter", "layer_height",
    "first_layer_height", "temperature", "first_layer_temperature", "bed_temperature",
    "first_layer_bed_temperature", "chamber_temperature", "max_volumetric_speed",
    "extrusion_multiplier", "first_layer_speed", "first_layer_infill_speed", "max_print_speed", "brim_width",
    "brim_separation", "fill_density", "fill_pattern", "bridge_angle", "support_material",
    "support_material_buildplate_only", "wipe_tower", "single_extruder_multi_material_priming",
    "physical_printer_settings_id", "post_process",
)


@dataclass(frozen=True)
class Extrusion:
    a: tuple[float, float]
    b: tuple[float, float]
    tool: int
    role: str
    width: float
    speed: float
    item: str | None

    def line(self):
        return LineString((self.a, self.b))


def parse_gcode(path):
    records = defaultdict(list)
    heights, commands, settings = {}, [], {}
    z, width, feed = None, None, None
    x, y = None, None
    tool, role, item = None, "Custom", None
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith(";Z:"):
            z = float(line.removeprefix(";Z:"))
        elif line.startswith(";HEIGHT:"):
            heights[z] = float(line.removeprefix(";HEIGHT:"))
        elif line.startswith(";TYPE:"):
            role = line.removeprefix(";TYPE:")
        elif line.startswith(";WIDTH:"):
            width = float(line.removeprefix(";WIDTH:"))
        elif line.startswith("; ") and " = " in line:
            key, value = line[2:].split(" = ", 1)
            if key in REPORTED_KEYS:
                settings[key] = value
        elif not line.startswith(";"):
            command = line.split(";", 1)[0].strip()
            if not command:
                continue
            if match := TOOL.fullmatch(command):
                tool = int(match.group(1))
                commands.append((index, command))
            elif command.startswith(("G0 ", "G1 ")):
                axes = {name: float(value) for name, value in AXES.findall(command)}
                new_x, new_y = axes.get("X", x), axes.get("Y", y)
                feed = axes.get("F", feed)
                if (z is not None and axes.get("E", 0) > 0 and role != "Custom"
                        and x is not None and y is not None and (new_x, new_y) != (x, y)):
                    records[z].append(Extrusion((x, y), (new_x, new_y), tool, role, width, feed / 60, item))
                x, y = new_x, new_y
            elif match := OBJECT_START.fullmatch(command):
                item = match.group(1)
            elif command.startswith("EXCLUDE_OBJECT_END "):
                item = None
            elif command.startswith(("G2 ", "G3 ", "G91", "M82")):
                raise ValueError(f"Unsupported G-code at line {index}: {command}")
            else:
                commands.append((index, command))
    return records, heights, commands, settings


def read_project(path):
    with ZipFile(path) as archive:
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
        settings = ET.fromstring(archive.read("Metadata/Slic3r_PE_model.config"))
        recipe_file = "Metadata/Prusa_Slicer_full_spectrum.json"
        mixes = json.loads(archive.read(recipe_file)) if recipe_file in archive.namelist() else None
    geometries = {node.get("id"): node for node in model.findall(f".//{MODEL_NS}object")}
    parts_by_item = {}
    for item in model.findall(f".//{MODEL_NS}item"):
        item_id = item.get("objectid")
        item_settings = settings.find(f"./object[@id='{item_id}']")
        item_name = item_settings.find("./metadata[@key='name']").get("value")
        transform = np.fromstring(item.get("transform"), sep=" ").reshape(4, 3)
        model_part = geometries[item_id]
        points = np.array([
            [float(vertex.get(axis)) for axis in "xyz"]
            for vertex in model_part.findall(f".//{MODEL_NS}vertex")
        ])
        points = points @ transform[:3] + transform[3]
        faces = np.array([
            [int(triangle.get(f"v{i}")) for i in range(1, 4)]
            for triangle in model_part.findall(f".//{MODEL_NS}triangle")
        ])
        parts = {}
        for volume in item_settings.findall("volume"):
            start, end = (int(volume.get(key)) for key in ("firstid", "lastid"))
            local_faces = faces[start:end + 1]
            used, local_faces = np.unique(local_faces, return_inverse=True)
            mesh = trimesh.Trimesh(points[used], local_faces.reshape(-1, 3), process=False)
            name = volume.find("./metadata[@key='name']").get("value")
            extruder = int(volume.find("./metadata[@key='extruder']").get("value"))
            parts[name] = extruder, mesh
        parts_by_item[item_name] = parts
    return parts_by_item, mixes


def find_markers(commands):
    def first(prefix, after=0):
        return next(index for index, command in commands if index > after and command.startswith(prefix))

    polygons = [index for index, command in commands if command.startswith("EXCLUDE_OBJECT_DEFINE ")]
    start = first("START_PRINT ")
    selection = next(index for index, command in commands if TOOL.fullmatch(command))
    temp_wait = first("M109 ")
    purge = first("LINE_PURGE")
    reset = first("G92 E0", after=purge)
    end = first("END_PRINT")
    if not max(polygons) < start < selection < temp_wait < purge < reset < end:
        raise ValueError("K2 polygons, startup, tool selection, temperature wait, purge, reset and shutdown are misordered.")
    return dict(object_polygons=polygons, start=start, initial_tool=selection, hotend_wait=temp_wait,
                purge=purge, extrusion_reset=reset, end=end)


def dot_footprint(component, slice_z):
    segments = trimesh.intersections.mesh_plane(component, (0, 0, 1), (0, 0, slice_z))
    return unary_union(list(polygonize(np.round(segments[:, :, :2], 6)))) if len(segments) else None


def object_label(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def audit_white_dots(project, records, heights):
    results = {}
    for item, parts in project.items():
        label = object_label(item)
        model_layers = sorted(
            z for z, moves in records.items()
            if any(move.item == label and "support" not in move.role.lower() and move.role != "Skirt/Brim" for move in moves)
        )
        results[item] = []
        for name, (extruder, mesh) in parts.items():
            if extruder != 3:
                continue
            for number, dot in enumerate(mesh.split(), 1):
                layers = []
                for index, z in enumerate(model_layers):
                    slice_z = z - heights[z] / 2
                    if not dot.bounds[0, 2] < slice_z < dot.bounds[1, 2]:
                        continue
                    outline = dot_footprint(dot, slice_z)
                    if outline is None or outline.is_empty:
                        raise ValueError(f"{item} / {name} dot {number}: missing section at {slice_z} mm.")
                    center_region = outline.buffer(-0.035)
                    min_width = min(np.subtract(outline.bounds[2:], outline.bounds[:2]))
                    if center_region.is_empty:
                        continue
                    x0, y0, x1, y1 = outline.bounds
                    layer = {
                        "z_mm": z, "minimum_section_side_mm": round(min_width, 4),
                        "centerline_mm_by_tool": {}, "unsupported_centerline_mm": 0.0,
                    }
                    prior = []
                    if index > 0:
                        for move in records[model_layers[index - 1]]:
                            if (
                                min(move.a[0], move.b[0]) <= x1 + 0.65 and max(move.a[0], move.b[0]) >= x0 - 0.65
                                and min(move.a[1], move.b[1]) <= y1 + 0.65 and max(move.a[1], move.b[1]) >= y0 - 0.65
                            ):
                                prior.append(move.line().buffer(move.width / 2))
                    prior_coverage = unary_union(prior)
                    for move in records[z]:
                        if (
                            "support" in move.role.lower() or move.role == "Skirt/Brim"
                            or min(move.a[0], move.b[0]) > x1 or max(move.a[0], move.b[0]) < x0
                            or min(move.a[1], move.b[1]) > y1 or max(move.a[1], move.b[1]) < y0
                        ):
                            continue
                        clipped = move.line().intersection(center_region)
                        if clipped.length == 0:
                            continue
                        key = f"T{move.tool}"
                        layer["centerline_mm_by_tool"][key] = layer["centerline_mm_by_tool"].get(key, 0) + clipped.length
                        if move.tool == 2 and index > 0:
                            overhang = clipped.difference(prior_coverage.buffer(move.width / 2 + 0.02))
                            layer["unsupported_centerline_mm"] += overhang.length
                    layers.append(layer)
                required = [entry for entry in layers if entry["minimum_section_side_mm"] > 0.5]
                wrong_tool = [
                    entry["z_mm"] for entry in required
                    if sum(mm for tool, mm in entry["centerline_mm_by_tool"].items() if tool != "T2") > 0.1
                ]
                empty = [entry["z_mm"] for entry in required if entry["centerline_mm_by_tool"].get("T2", 0) < 0.05]
                missing_support = [
                    entry["z_mm"] for entry in layers if entry["unsupported_centerline_mm"] > 0.1
                ]
                results[item].append({
                    "part": name, "component": number, "bounds_mm": dot.bounds.round(5).tolist(),
                    "checked_layers": len(layers), "layers_with_printable_width": len(required),
                    "layers_with_white_paths": sum(entry["centerline_mm_by_tool"].get("T2", 0) > 0.05 for entry in layers),
                    "wrong_material_layers": wrong_tool, "missing_white_layers": empty,
                    "unsupported_white_layers": missing_support,
                })
    return {item: dots for item, dots in results.items() if dots}


def audit_item_paths(project, records):
    results = {}
    first = min(records)
    for item, parts in project.items():
        all_meshes = [mesh for _, mesh in parts.values()]
        low = np.min([mesh.bounds[0] for mesh in all_meshes], axis=0)
        high = np.max([mesh.bounds[1] for mesh in all_meshes], axis=0)
        label = object_label(item)
        layer_tools = {}
        first_layer_area = 0.0
        for z, moves in records.items():
            distance = Counter()
            for move in moves:
                if move.item != label or move.role == "Skirt/Brim" or "support" in move.role.lower():
                    continue
                x = (move.a[0] + move.b[0]) / 2
                y = (move.a[1] + move.b[1]) / 2
                if low[0] <= x <= high[0] and low[1] <= y <= high[1]:
                    length = ((move.b[0] - move.a[0]) ** 2 + (move.b[1] - move.a[1]) ** 2) ** 0.5
                    distance[f"T{move.tool}"] += length
                    if z == first:
                        first_layer_area += length * move.width
            if distance:
                layer_tools[z] = distance
        has_blend = any(extruder >= 5 for extruder, _ in parts.values())
        majority_tool = [layer.most_common(1)[0][0] for layer in layer_tools.values()]
        results[item] = {
            "part_extruders": {name: extruder for name, (extruder, _) in parts.items()},
            "bounds_mm": [low.round(5).tolist(), high.round(5).tolist()],
            "first_layer_bead_area_estimate_mm2": round(first_layer_area, 2),
            "geometry_layers": len(layer_tools),
            "model_tools": sorted({tool for layer in layer_tools.values() for tool in layer}),
            "majority_tool_layer_counts": dict(Counter(majority_tool)),
        }
        if has_blend:
            results[item]["first_12_layers_majority_tool"] = majority_tool[:12]
    return results


def summarize(project_path, gcode_path, cli_log):
    records, heights, commands, settings = parse_gcode(gcode_path)
    project, mixes = read_project(project_path)
    start_end = find_markers(commands)
    tools = Counter(f"T{match.group(1)}" for _, command in commands if (match := TOOL.fullmatch(command)))
    if set(tools) - {"T0", "T2", "T3"}:
        raise ValueError(f"Unexpected physical tool selection: {tools}")
    if any(settings.get(key) != "0" for key in ("wipe_tower", "single_extruder_multi_material_priming")):
        raise ValueError("Wipe tower and slicer priming must be disabled.")
    if len(start_end["object_polygons"]) != len(project):
        raise ValueError("G-code object labeling does not match the 3MF plate.")
    roles = defaultdict(Counter)
    special_paths = defaultdict(lambda: {"total_length_mm": 0.0, "max_segment_mm": 0.0, "layers": set()})
    footprint = None
    for z, moves in records.items():
        for move in moves:
            roles[move.role][f"T{move.tool}"] += 1
            ends = np.array((move.a, move.b))
            box = np.array((ends.min(axis=0), ends.max(axis=0)))
            if footprint is None:
                footprint = box
            else:
                footprint[0] = np.minimum(footprint[0], box[0])
                footprint[1] = np.maximum(footprint[1], box[1])
            if any(term in move.role.lower() for term in ("bridge", "support", "overhang")):
                section = special_paths[move.role]
                length = move.line().length
                section["total_length_mm"] += length
                section["max_segment_mm"] = max(section["max_segment_mm"], length)
                section["layers"].add(z)
    if footprint.min() < 0 or footprint.max() > 260:
        raise ValueError(f"Extrusion paths extend beyond the K2 bed: {footprint.tolist()}")
    for section in special_paths.values():
        section["total_length_mm"] = round(section["total_length_mm"], 3)
        section["max_segment_mm"] = round(section["max_segment_mm"], 3)
        section["layer_count"] = len(section.pop("layers"))
    temperatures = sorted({command for _, command in commands if command.startswith(("M104 ", "M109 ", "M140 ", "M190 "))})
    first = min(records)
    first_speed = max(move.speed for move in records[first])
    max_speed = max(move.speed for moves in records.values() for move in moves)
    if first_speed > 25.01 or max_speed > 50.01:
        raise ValueError(f"Unexpected print speeds: {first_speed:.2f} mm/s first, {max_speed:.2f} mm/s overall.")
    lines = cli_log.read_text(encoding="utf-8-sig").splitlines()
    items = audit_item_paths(project, records)
    for name, item in items.items():
        expected = {"T0", "T2"} if max(item["part_extruders"].values()) >= 5 else {"T3"}
        if set(item["model_tools"]) != expected or item["first_layer_bead_area_estimate_mm2"] <= 0:
            raise ValueError(f"{name} is missing its first layer or has a wrong assignment: {item!r}")
    return {
        "project_file": project_path.name,
        "project_sha256": hashlib.sha256(project_path.read_bytes()).hexdigest(),
        "gcode_sha256": hashlib.sha256(gcode_path.read_bytes()).hexdigest(),
        "slicer": gcode_path.read_text(encoding="utf-8").splitlines()[0].removeprefix("; generated by "),
        "effective_gcode_settings": settings,
        "physical_tool_selections": dict(sorted(tools.items())),
        "startup_shutdown_lines": start_end,
        "color_mix": mixes,
        "recorded_temperature_commands": temperatures,
        "print_layer_count": len(records),
        "extrusion_roles": {key: dict(value) for key, value in roles.items()},
        "extrusion_xy_bounds_mm": footprint.round(3).tolist(),
        "bridges_overhangs_and_supports": dict(special_paths),
        "first_layer_max_extrusion_speed_mm_s": round(first_speed, 2),
        "maximum_extrusion_speed_mm_s": round(max_speed, 2),
        "items": items,
        "white_dots": audit_white_dots(project, records, heights),
        "slicer_warning_lines": [line for line in lines if re.search(r"\b(warning|floating|error|detached)\b", line, re.I)],
        "slicer_warning_count": sum(line.lower().startswith("print warning:") for line in lines),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("gcode", type=Path)
    parser.add_argument("cli_log", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = summarize(args.project, args.gcode, args.cli_log)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.report)


if __name__ == "__main__":
    main()

