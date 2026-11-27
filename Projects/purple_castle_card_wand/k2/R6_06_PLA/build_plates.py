"""Build private K2 0.6 mm PLA ColorMix projects from the frozen R6 placements."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
ASSET_ROOT = PROJECT.parents[1]
ASA = HERE.parent / "R6"
MINNIE_PACKAGER = ASSET_ROOT / "Projects/minnie_ticket_wand/asa_slicer/build_plates.py"
SLICER = Path(r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe")
PRESET = "Creality K2 (0.6 mm)"
PLA_BASE = "Polymaker PolyChroma Matte"
PALETTE = ("#174FBA", "#CF201B", "#F3F3F1", "#C59B4F")
BLUE, RED, WHITE, GOLD = range(1, 5)
PURPLE, PINK, LIGHT_BLUE = range(5, 8)
MIXES = {
    PURPLE: ("#8053A3", {RED: 0.50, BLUE: 0.50}),
    PINK: ("#E6AAB6", {RED: 0.25, WHITE: 0.75}),
    LIGHT_BLUE: ("#9EBDEB", {BLUE: 0.25, WHITE: 0.75}),
}
ASSIGN = {
    "head_purple": PURPLE,
    "head_gold": GOLD,
    "head_cream": WHITE,
    "head_blue": LIGHT_BLUE,
    "rear_purple": PURPLE,
    "frame_purple": PURPLE,
    "handle_purple": PURPLE,
    "handle_gold": GOLD,
    "bow_pink": PINK,
    "front_coupon_purple": PURPLE,
    "rear_coupon_purple": PURPLE,
    "frame_coupon_purple": PURPLE,
    "grip_stub_purple": PURPLE,
}
SHELL = {"fill_density": "100%", "fill_pattern": "rectilinear", "bridge_angle": "180"}
SHELL_SUPPORT = {
    "support_material": "1",
    "support_material_buildplate_only": "1",
    "support_material_style": "snug",
    "support_material_threshold": "12",
    "support_material_spacing": "1.8",
    "support_material_interface_layers": "2",
    "support_material_interface_spacing": "0.25",
    "support_material_xy_spacing": "70%",
}
PLATES = {
    "Slot_and_Thread_Coupon": {"brim_width": "4", **SHELL_SUPPORT},
    "Star_Face": {**SHELL, **SHELL_SUPPORT},
    "Rear_Shell": {**SHELL, **SHELL_SUPPORT},
    "Pocket_Frame": {"fill_density": "100%", "fill_pattern": "rectilinear"},
    "Threaded_Grip": {"brim_width": "6"},
    "Pink_Bow": {},
    "ColorMix_Swatches": {"brim_width": "3", "fill_density": "100%", "fill_pattern": "rectilinear"},
}
PREFIX = "K2_06_PLA_Castle_R6_"
CONFIG = "Metadata/Slic3r_PE.config"
MODEL_CONFIG = "Metadata/Slic3r_PE_model.config"
COLOR_MIX = "Metadata/Prusa_Slicer_full_spectrum.json"
GEOMETRY = "3D/3dmodel.model"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_base_profile(scratch):
    help_text = subprocess.run([SLICER, "--help"], check=True, capture_output=True, text=True).stdout
    if not help_text.startswith("PrusaSlicer-2.9.7 "):
        raise ValueError("This packager expects PrusaSlicer 2.9.7.")
    datadir = Path(os.environ["APPDATA"]) / "PrusaSlicer"
    target = scratch / "resolved_base.ini"
    arguments = [SLICER, "--datadir", datadir, "--printer-profile", PRESET, "--print-profile", PRESET]
    for _ in PALETTE:
        arguments.extend(["--material-profile", PLA_BASE])
    subprocess.run([*arguments, "--save", target], check=True)
    base = dict(
        line.split(" = ", 1)
        for line in target.read_text(encoding="utf-8").splitlines()
        if " = " in line and not line.startswith("#")
    )
    expected = {
        "printer_settings_id": PRESET,
        "print_settings_id": PRESET,
        "nozzle_diameter": "0.6,0.6,0.6,0.6",
        "filament_type": "PLA;PLA;PLA;PLA",
        "single_extruder_multi_material": "1",
        "single_extruder_multi_material_priming": "0",
        "wipe_tower": "0",
        "binary_gcode": "0",
        "gcode_flavor": "klipper",
        "gcode_label_objects": "firmware",
        "post_process": "",
        "end_gcode": "END_PRINT",
    }
    for key, value in expected.items():
        if base.get(key) != value:
            raise ValueError(f"Installed {key} changed. Expected {value!r}, got {base.get(key)!r}.")
    if "LINE_PURGE" not in base["start_gcode"] or "T{next_extruder}" not in base["toolchange_gcode"]:
        raise ValueError("Review the installed K2 start and toolchange macros.")
    return base


def effective_config(base, overrides):
    config = base.copy()
    config.update(
        physical_printer_settings_id="",
        print_host="",
        printhost_apikey="",
        printhost_cafile="",
        extruder_colour=";".join(PALETTE),
        filament_colour=";".join(PALETTE),
        filament_settings_id='"Hyper PLA Blue (R6 trial)";"Hyper PLA Red (R6 trial)";'
                             '"Hyper PLA White (R6 trial)";"PolyLite PLA Pro Metallic Gold (R6 trial)"',
        filament_density="1.24,1.24,1.24,1.24",
        extrusion_multiplier="1,1,1,1",
        filament_max_volumetric_speed="6,6,6,6",
        first_layer_temperature="215,215,215,215",
        temperature="210,210,210,210",
        first_layer_bed_temperature="60,60,60,60",
        bed_temperature="55,55,55,55",
        min_fan_speed="65,65,65,65",
        max_fan_speed="100,100,100,100",
        bridge_fan_speed="100,100,100,100",
        full_fan_speed_layer="4,4,4,4",
        layer_height="0.12",
        first_layer_height="0.20",
        max_print_speed="60",
        max_volumetric_speed="6",
        first_layer_speed="25",
        first_layer_infill_speed="25",
        perimeter_speed="45",
        external_perimeter_speed="35",
        small_perimeter_speed="25",
        infill_speed="60",
        solid_infill_speed="50",
        top_solid_infill_speed="35",
        gap_fill_speed="25",
        bridge_speed="24",
        first_layer_acceleration="1200",
        brim_type="outer_only",
        brim_width="4",
        brim_separation="0.10",
        seam_position="rear",
        support_material="0",
        support_material_extruder="0",
        support_material_interface_extruder="0",
    )
    config.update(overrides)
    return config


def recipe(ids):
    return {
        "version": 1,
        "physical_extruders": [
            {"id": slot, "color": color} for slot, color in enumerate(PALETTE, 1)
        ],
        "virtual_extruders": [
            {"id": index, "kind": "fullspectrum", "color": MIXES[index][0],
             "components": [
                 {"extruder": slot, "ratio": ratio}
                 for slot, ratio in sorted(MIXES[index][1].items())
             ]}
            for index in sorted(ids)
        ],
    }


def metadata(node, key):
    return node.find(f"./metadata[@key='{key}']")


def write_native(source, target, config, *, body_tool=PURPLE):
    with ZipFile(source) as archive:
        members = {item: archive.read(item) for item in archive.namelist()}
    settings = ET.fromstring(members[MODEL_CONFIG])
    used_mixes = set()
    for item in settings.findall("object"):
        # Use the tuned PLA support policy. The stub matches the unsupported full grip.
        for setting in list(item.findall("metadata")):
            if setting.get("key").startswith("support_material"):
                item.remove(setting)
        slots = []
        for volume in item.findall("volume"):
            name = metadata(volume, "name").get("value")
            if name == "grip_stub_purple":
                ET.SubElement(item, "metadata", type="object", key="support_material", value="0")
            assigned = ASSIGN[name]
            if assigned == PURPLE:
                assigned = body_tool
            metadata(volume, "extruder").set("value", str(assigned))
            slots.append(assigned)
        if not slots:
            raise ValueError("Model object lacks printable volumes.")
        metadata(item, "extruder").set("value", str(slots[0]))
        used_mixes.update(slot for slot in slots if slot in MIXES)

    members[MODEL_CONFIG] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    members[CONFIG] = "; generated by PrusaSlicer 2.9.7\n\n" + "".join(
        f"; {key} = {value}\n" for key, value in sorted(config.items())
    )
    members.pop(COLOR_MIX, None)
    if used_mixes:
        members[COLOR_MIX] = json.dumps(recipe(used_mixes), indent=2)
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return {"source_plate": source.name, "source_3mf_sha256": digest(source.read_bytes()),
            "geometry_xml_sha256": digest(members[GEOMETRY])}


def load_minnie_packager():
    spec = importlib.util.spec_from_file_location("r6_native_3mf_packager", MINNIE_PACKAGER)
    builder = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = builder
    spec.loader.exec_module(builder)
    builder.COLORS = PALETTE
    builder.BLENDS = MIXES
    builder.blend_recipe = recipe
    return builder


def build_swatches(target, config, *, control=None):
    builder = load_minnie_packager()
    flat = (24, 11, 1.4)
    upright = (24, 3.6, 4.4)
    if control is None:
        descriptions = [
            (f"{name} {pose}", extruder, (x, y), size)
            for x, name, extruder in ((84, "Purple", PURPLE), (124, "Pink", PINK), (164, "Light blue", LIGHT_BLUE))
            for pose, y, size in (("flat", 113, flat), ("upright", 145, upright))
        ]
        descriptions.append(("Metallic Gold", GOLD, (124, 84), flat))
    else:
        name, extruder = control
        descriptions = [(name, extruder, (124, 84), flat)]
    items = [
        builder.Item(name, [builder.Part(name, extruder, builder.trimesh.creation.box(extents=size))], center)
        for name, extruder, center, size in descriptions
    ]
    if control is None:
        wedge = builder.trimesh.creation.box(extents=(24, 11, 1))
        for vertex in wedge.vertices:
            vertex[2] = 0.84 + (vertex[1] + 5.5) * math.tan(math.radians(18)) if vertex[2] > 0 else 0
        items.append(builder.Item(
            "Purple slope 18 deg", [builder.Part("Purple slope", PURPLE, wedge)], (204, 113)
        ))
    builder.package_project(target, items, config)


def slice_plate(project, scratch):
    gcode = scratch / project.with_suffix(".gcode").name
    invocation = subprocess.run(
        [SLICER, "--datadir", scratch / "cli", "--export-gcode", "--output", gcode, project],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    log = gcode.with_suffix(".log")
    log.write_text(invocation.stdout + "\n" + invocation.stderr, encoding="utf-8")
    print(f"{project.name}: exit {invocation.returncode}", flush=True)
    if invocation.returncode:
        raise RuntimeError(f"Check {log}")
    return gcode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--plate", choices=PLATES, action="append")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--slice-only", action="store_true")
    parser.add_argument("--verify-end-slots", action="store_true",
                        help="Also slice temporary calibration bodies from A and D alone.")
    parser.add_argument("--solid-blue-alternates", action="store_true",
                        help="Also generate blue rear and frame and blue-and-gold grip alternatives.")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    (args.scratch / "cli").mkdir(exist_ok=True)
    chosen = args.plate or PLATES
    projects = []
    evidence = {}
    if not args.slice_only:
        base = load_base_profile(args.scratch)
    for name in chosen:
        project = args.out / f"{PREFIX}{name}.3mf"
        projects.append(project)
        if args.slice_only:
            continue
        config = effective_config(base, PLATES[name])
        overrides = {key: value for key, value in config.items() if base.get(key) != value}
        if name == "ColorMix_Swatches":
            build_swatches(project, config)
            evidence[project.name] = {}
        else:
            source = ASA / f"K2_04_ASA_Castle_R6_{name}.3mf"
            evidence[project.name] = write_native(source, project, config)
            if args.solid_blue_alternates and name in {"Rear_Shell", "Pocket_Frame", "Threaded_Grip"}:
                alternate = args.out / f"{PREFIX}{name}_Solid_Blue.3mf"
                evidence[alternate.name] = write_native(source, alternate, config, body_tool=BLUE)
                evidence[alternate.name]["profile_overrides"] = overrides
                projects.append(alternate)
        evidence[project.name]["profile_overrides"] = overrides
    if args.verify_end_slots and not args.slice_only:
        for name, control_slot in [
            ("A_Blue", ("Hyper PLA Blue", BLUE)), ("D_Gold", ("Metallic Gold", GOLD))
        ]:
            control = args.scratch / f"Control_{name}.3mf"
            build_swatches(control, effective_config(base, PLATES["ColorMix_Swatches"]), control=control_slot)
            projects.append(control)
    if evidence:
        (args.scratch / "build.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if not args.build_only:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda path: slice_plate(path, args.scratch), projects))


if __name__ == "__main__":
    main()
