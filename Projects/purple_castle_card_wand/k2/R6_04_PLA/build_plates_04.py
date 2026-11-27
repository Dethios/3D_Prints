"""Build gold-free R6 PLA projects for the installed K2 0.4 mm nozzle presets."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "R6_06_PLA"))
import build_plates as common


PRESET = "Creality K2 (0.4 mm)"
PREFIX = "K2_04_PLA_Castle_R6_"
SHELL_SUPPORT = {**common.SHELL_SUPPORT, "support_material_auto": "1"}
PLATES = {
    "ColorMix_Swatches": common.PLATES["ColorMix_Swatches"],
    "Slot_and_Thread_Coupon": {"brim_width": "4", "layer_height": "0.12", **SHELL_SUPPORT},
    "Rear_Shell": {**common.SHELL, **SHELL_SUPPORT},
    "Pocket_Frame": common.PLATES["Pocket_Frame"],
    "Pink_Bow": {},
}
ALTERNATES = {"Rear_Shell", "Pocket_Frame"}


def load_base_profile(scratch):
    help_text = subprocess.run(
        [common.SLICER, "--help"], check=True, capture_output=True, text=True,
    ).stdout
    if not help_text.startswith("PrusaSlicer-2.9.7 "):
        raise ValueError("Review the native 3MF metadata format for this PrusaSlicer version.")
    datadir = Path(os.environ["APPDATA"]) / "PrusaSlicer"
    target = scratch / "resolved_base.ini"
    arguments = [common.SLICER, "--datadir", datadir, "--printer-profile", PRESET, "--print-profile", PRESET]
    for _ in common.PALETTE:
        arguments.extend(["--material-profile", common.PLA_BASE])
    subprocess.run([*arguments, "--save", target], check=True)
    base = dict(
        line.split(" = ", 1)
        for line in target.read_text(encoding="utf-8").splitlines()
        if " = " in line and not line.startswith("#")
    )
    expected = {
        "printer_settings_id": PRESET,
        "print_settings_id": PRESET,
        "nozzle_diameter": "0.4,0.4,0.4,0.4",
        "filament_type": "PLA;PLA;PLA;PLA",
        "single_extruder_multi_material": "1",
        "single_extruder_multi_material_priming": "0",
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
    return common.effective_config(base, {
        "layer_height": "0.10",
        "wipe_tower": "0",
        "support_material_speed": "35",
        "support_material_interface_speed": "28",
        **overrides,
    })


def build_swatches(target, config):
    builder = common.load_minnie_packager()
    flat = (24, 11, 1.4)
    upright = (24, 3.6, 4.4)
    positions = [
        (84, "Purple", common.PURPLE),
        (124, "Pink", common.PINK),
        (164, "Light blue", common.LIGHT_BLUE),
    ]
    descriptions = [
        (f"{name} {pose}", extruder, (x, y), size)
        for x, name, extruder in positions
        for pose, y, size in (("flat", 113, flat), ("upright", 145, upright))
    ]
    items = [
        builder.Item(name, [builder.Part(name, extruder, builder.trimesh.creation.box(extents=size))], center)
        for name, extruder, center, size in descriptions
    ]
    wedge = builder.trimesh.creation.box(extents=(24, 11, 1))
    for vertex in wedge.vertices:
        vertex[2] = 0.84 + (vertex[1] + 5.5) * math.tan(math.radians(18)) if vertex[2] > 0 else 0
    items.append(builder.Item(
        "Purple slope 18 deg", [builder.Part("Purple slope", common.PURPLE, wedge)], (204, 113)
    ))
    builder.package_project(target, items, config)


def configure_grip_stub(project):
    """Use across-neck bridging and removable bed-only support on the small fit stub."""
    with ZipFile(project) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    settings = ET.fromstring(members[common.MODEL_CONFIG])
    stub = next(item for item in settings.findall("object")
                if common.metadata(item, "name").get("value") == "Grip stub coupon")
    common.metadata(stub, "support_material").set("value", "1")
    ET.SubElement(stub, "metadata", type="object", key="bridge_angle", value="180")
    members[common.MODEL_CONFIG] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    with ZipFile(project, "w", ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def build_projects(out, scratch, chosen):
    base = load_base_profile(scratch)
    projects = []
    evidence = {}
    for name in chosen:
        config = effective_config(base, PLATES[name])
        overrides = {key: value for key, value in config.items() if base.get(key) != value}
        target = out / f"{PREFIX}{name}.3mf"
        if name == "ColorMix_Swatches":
            build_swatches(target, config)
            evidence[target.name] = {"profile_overrides": overrides}
        else:
            source = common.ASA / f"K2_04_ASA_Castle_R6_{name}.3mf"
            evidence[target.name] = common.write_native(source, target, config)
            evidence[target.name]["profile_overrides"] = overrides
            if name == "Slot_and_Thread_Coupon":
                configure_grip_stub(target)
                evidence[target.name]["grip_stub_overrides"] = {"support_material": "1", "bridge_angle": "180"}
            if name in ALTERNATES:
                alternate = out / f"{PREFIX}{name}_Solid_Blue.3mf"
                evidence[alternate.name] = common.write_native(source, alternate, config, body_tool=common.BLUE)
                evidence[alternate.name]["profile_overrides"] = overrides
                projects.append(alternate)
        projects.append(target)
    (scratch / "build.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return projects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--plate", choices=PLATES, action="append")
    parser.add_argument("--slice-only", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    (args.scratch / "cli").mkdir(exist_ok=True)
    projects = (sorted(args.out.glob(f"{PREFIX}*.3mf")) if args.slice_only
                else build_projects(args.out, args.scratch, args.plate or PLATES))
    if not projects:
        raise ValueError("No R6 0.4 mm PLA projects to slice.")
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda path: common.slice_plate(path, args.scratch), projects))


if __name__ == "__main__":
    main()
