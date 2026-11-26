"""Build native PrusaSlicer 2.9.7 K2 projects from the installed profiles and CAD exports."""

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from shapely.geometry import MultiPoint
import trimesh


ROOT = Path(__file__).resolve().parent
CAD = ROOT.parent / "asa_cad"
SLICER = Path(r"C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe")
PRESET = "Creality K2 (0.4 mm)"
FILAMENT = "Polymaker ASA"
COLORS = ("#BF1A11", "#808080", "#DBD7D6", "#212721")
BLENDS = {
    5: ("#E8A6B1", 0.25),
    6: ("#CF6A75", 0.50),
}
NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>"""
RELATIONS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


@dataclass
class Part:
    name: str
    extruder: int
    mesh: trimesh.Trimesh
    source: str = ""
    source_sha256: str = ""


@dataclass
class Item:
    name: str
    parts: list[Part]
    center: tuple[float, float]
    rotation: np.ndarray | None = None
    overrides: dict[str, str] = field(default_factory=dict)


def load_current_profiles():
    """Resolve full configurations in the CLI without saving to its profile directory."""
    help_text = subprocess.run([SLICER, "--help"], check=True, capture_output=True, text=True).stdout
    if not help_text.startswith("PrusaSlicer-2.9.7 "):
        raise ValueError("Review 3MF ColorMix compatibility for this slicer version.")
    datadir = Path(os.environ["APPDATA"]) / "PrusaSlicer"
    with tempfile.TemporaryDirectory(prefix="minnie-k2-profile-") as temp:
        output = Path(temp) / "resolved.ini"
        arguments = [
            SLICER, "--datadir", datadir, "--printer-profile", PRESET,
            "--print-profile", PRESET,
        ]
        for _ in COLORS:
            arguments += ["--material-profile", FILAMENT]
        subprocess.run([*arguments, "--save", output], check=True)
        config = dict(
            line.split(" = ", 1)
            for line in output.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#") and " = " in line
        )
    required = {
        "printer_settings_id": PRESET,
        "print_settings_id": PRESET,
        "nozzle_diameter": "0.4,0.4,0.4,0.4",
        "filament_type": "ASA;ASA;ASA;ASA",
        "single_extruder_multi_material": "1",
        "single_extruder_multi_material_priming": "0",
        "wipe_tower": "0",
        "binary_gcode": "0",
        "gcode_flavor": "klipper",
        "gcode_label_objects": "firmware",
        "end_gcode": "END_PRINT",
        "post_process": "",
    }
    for key, value in required.items():
        if config.get(key) != value:
            raise ValueError(f"Review the installed {key}: expected {value!r}, found {config.get(key)!r}")
    if "LINE_PURGE" not in config["start_gcode"] or "T{next_extruder}" not in config["toolchange_gcode"]:
        raise ValueError("The installed printer's K2 startup or tool-change macro changed.")
    return config


def effective_config(base, overrides):
    config = base.copy()
    config.update(
        physical_printer_settings_id="",
        print_host="",
        printhost_apikey="",
        printhost_cafile="",
        extruder_colour=";".join(COLORS),
        filament_colour=";".join(COLORS),
        bed_temperature="95,95,95,95",
        first_layer_bed_temperature="95,95,95,95",
        chamber_temperature="0,0,0,0",
        layer_height="0.12",
        first_layer_height="0.20",
        max_print_speed="50",
        max_volumetric_speed="6",
        first_layer_speed="25",
        first_layer_infill_speed="25",
        perimeter_speed="45",
        external_perimeter_speed="35",
        small_perimeter_speed="25",
        infill_speed="50",
        solid_infill_speed="45",
        top_solid_infill_speed="35",
        bridge_speed="22",
        gap_fill_speed="25",
        support_material_speed="35",
        support_material_interface_speed="28",
        default_acceleration="4500",
        travel_acceleration="6500",
        perimeter_acceleration="2200",
        external_perimeter_acceleration="1500",
        first_layer_acceleration="1200",
        min_fan_speed="0,0,0,0",
        max_fan_speed="0,0,0,0",
        bridge_fan_speed="0,0,0,0",
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


def add_metadata(parent, scope, name, value):
    ET.SubElement(parent, "metadata", type=scope, key=name, value=str(value))


def blend_recipe(blends):
    return {
        "version": 1,
        "physical_extruders": [dict(id=number, color=color) for number, color in enumerate(COLORS, 1)],
        "virtual_extruders": [
            dict(id=number, kind="fullspectrum", color=BLENDS[number][0],
                 components=[
                     dict(extruder=1, ratio=BLENDS[number][1]),
                     dict(extruder=3, ratio=1 - BLENDS[number][1]),
                 ])
            for number in sorted(blends)
        ],
    }


def package_project(output, items, config):
    model = ET.Element("model", xmlns=NS, unit="millimeter")
    for name, value in {
        "slic3rpe:Version3mf": "1",
        "Application": "PrusaSlicer-2.9.7",
        "Title": output.stem,
    }.items():
        ET.SubElement(model, "metadata", name=name).text = value
    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")
    settings = ET.Element("config")
    used_blends = set()
    placements = {}
    prior_footprints = {}
    for index, item in enumerate(items, 1):
        object_id = str(index)
        obj = ET.SubElement(resources, "object", id=object_id, type="model")
        mesh = ET.SubElement(obj, "mesh")
        vertices = ET.SubElement(mesh, "vertices")
        triangles = ET.SubElement(mesh, "triangles")
        obj_settings = ET.SubElement(settings, "object", id=object_id, instances_count="1")
        add_metadata(obj_settings, "object", "name", item.name)
        add_metadata(obj_settings, "object", "extruder", item.parts[0].extruder)
        for key, value in item.overrides.items():
            add_metadata(obj_settings, "object", key, value)
        rotation = np.eye(3) if item.rotation is None else item.rotation
        rotated_vertices = np.concatenate([part.mesh.vertices @ rotation.T for part in item.parts])
        low, high = rotated_vertices.min(axis=0), rotated_vertices.max(axis=0)
        offset = np.array([*item.center, 0.0]) - np.array([*((high[:2] + low[:2]) / 2), low[2]])
        placed_low, placed_high = low + offset, high + offset
        if not (np.all(placed_low[:2] >= 1) and np.all(placed_high[:2] <= 259) and placed_high[2] <= 260):
            raise ValueError(f"{item.name} is outside the K2 bed: {placed_low} to {placed_high}")
        footprint = MultiPoint((rotated_vertices + offset)[:, :2]).convex_hull
        brim = float(config["brim_width"])
        for other_name, other in prior_footprints.items():
            if footprint.distance(other) < 2 * brim + 1:
                raise ValueError(f"{item.name} and {other_name} do not leave room for their brims.")
        if not (np.all(placed_low[:2] >= brim) and np.all(placed_high[:2] <= 260 - brim)):
            raise ValueError(f"{item.name} brim may touch the bed edge.")
        prior_footprints[item.name] = footprint
        transform = np.r_[rotation.T.ravel(), offset]
        ET.SubElement(
            build, "item", objectid=object_id, printable="1",
            transform=" ".join(f"{value:.12g}" for value in transform),
        )
        placement = {
            "bounds_mm": [placed_low.round(6).tolist(), placed_high.round(6).tolist()],
            "rotation": rotation.tolist(),
            "translation_mm": offset.round(10).tolist(),
            "print_overrides": item.overrides,
            "parts": {},
        }
        face_start = 0
        vertex_start = 0
        for part in item.parts:
            if part.extruder not in {1, 3, 4, *BLENDS}:
                raise ValueError(f"Invalid production extruder {part.extruder} for {part.name}")
            if part.extruder in BLENDS:
                used_blends.add(part.extruder)
            if not part.mesh.is_volume:
                raise ValueError(f"{part.name} needs a watertight positive solid.")
            for point in part.mesh.vertices:
                ET.SubElement(vertices, "vertex", dict(zip("xyz", (f"{v:.8f}" for v in point))))
            for face in part.mesh.faces + vertex_start:
                ET.SubElement(triangles, "triangle", dict(zip(("v1", "v2", "v3"), map(str, face))))
            next_face = face_start + len(part.mesh.faces)
            volume = ET.SubElement(
                obj_settings, "volume", firstid=str(face_start), lastid=str(next_face - 1),
            )
            for key, value in {
                "name": part.name, "volume_type": "ModelPart", "extruder": part.extruder,
                "source_file": part.source,
            }.items():
                if value != "":
                    add_metadata(volume, "volume", key, value)
            placed_vertices = part.mesh.vertices @ rotation.T + offset
            placement["parts"][part.name] = {
                "extruder": part.extruder,
                "source": part.source,
                "source_sha256": part.source_sha256,
                "bounds_mm": [
                    placed_vertices.min(axis=0).round(6).tolist(),
                    placed_vertices.max(axis=0).round(6).tolist(),
                ],
            }
            vertex_start += len(part.mesh.vertices)
            face_start = next_face
        placements[item.name] = placement

    print_config = "; generated by PrusaSlicer 2.9.7\n\n" + "".join(
        f"; {key} = {value}\n" for key, value in sorted(config.items())
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", RELATIONS)
        archive.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/Slic3r_PE_model.config", ET.tostring(settings, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/Slic3r_PE.config", print_config)
        if used_blends:
            archive.writestr("Metadata/Prusa_Slicer_full_spectrum.json", json.dumps(blend_recipe(used_blends), indent=2))
    return placements


def swatch_items():
    body = trimesh.creation.box(extents=(22.0, 3.2, 5.4))
    # The two swatches place the same flush white dot within the visible side.
    dot = trimesh.creation.cylinder(radius=1.5, height=1.8, sections=64)
    dot.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
    dot.apply_translation((6.6, -1.6, 0.0))
    dot = trimesh.boolean.intersection([dot, body], engine="manifold")
    pink = trimesh.boolean.difference([body, dot], engine="manifold")
    black = trimesh.creation.box(extents=(9.0, 8.0, 2.6))
    return [
        Item("25 red / 75 white", [Part("Mixed pink", 5, pink), Part("Solid white dot", 3, dot)], (105, 130)),
        Item("50 red / 50 white", [Part("Mixed pink", 6, pink), Part("Solid white dot", 3, dot)], (145, 130)),
        Item("Galaxy Black purge witness", [Part("Galaxy Black", 4, black)], (125, 104)),
    ]


def stl(name, stem, extruder, folder="print_parts"):
    path = CAD / folder / f"{stem}.stl"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Part(name, extruder, trimesh.load_mesh(path), path.name, digest)


def rotate(degrees, axis):
    return trimesh.transformations.rotation_matrix(np.deg2rad(degrees), axis)[:3, :3]


def production_items(plate, bow_angle):
    rear_roll = rotate(180, (1, 0, 0))
    if plate == "shells":
        return [
            Item("Front shell - inner face down", [stl("Galaxy Black front shell", "front_black", 4)], (72, 78)),
            Item("Rear shell - inner face down", [stl("Galaxy Black rear shell", "rear_black", 4)],
                 (189, 178), rotate(180, (0, 0, 1)) @ rear_roll),
        ]
    if plate == "spacer":
        spacer = stl("Galaxy Black spacer", "spacer_black", 4)
        pin = stl("Galaxy Black alignment pin", "alignment_pin_black_print_two", 4)
        return [
            Item("Card spacer", [spacer], (118, 132)),
            Item("Alignment pin 1", [pin], (208, 103)),
            Item("Alignment pin 2", [pin], (208, 124)),
        ]
    if plate == "handle":
        return [Item("Handle and cuff - rear chord down", [stl("Mixed pink handle", "handle_cuff_pink", 5)], (130, 128))]
    if plate == "bow":
        return [
            Item("Bow - upright", [
                stl("Mixed pink bow", "bow_pink", 5),
                stl("Solid white bow dots", "bow_dots_white", 3),
            ], (130, 128), rotate(bow_angle, (1, 0, 0)) @ rotate(3, (0, 0, 1))),
        ]
    return [
        Item("Coupon front shell", [stl("Galaxy Black front coupon", "coupon_front_black", 4, "fit_coupon")],
             (87, 102), overrides=SOLID_NO_SUPPORT),
        Item("Coupon rear shell", [stl("Galaxy Black rear coupon", "coupon_rear_black", 4, "fit_coupon")],
             (169, 102), rear_roll, SOLID_NO_SUPPORT),
        Item("Coupon spacer", [stl("Galaxy Black spacer coupon", "coupon_spacer_black", 4, "fit_coupon")],
             (87, 166), overrides=SOLID_NO_SUPPORT),
        Item("Coupon handle and cuff", [stl("Mixed pink handle coupon", "coupon_handle_cuff_pink", 5, "fit_coupon")],
             (169, 166), overrides={"bridge_angle": "180"}),
    ]


SOLID = {"fill_density": "100%", "fill_pattern": "rectilinear"}
SOLID_NO_SUPPORT = dict(SOLID, support_material="0")
SNUG_SUPPORT = {
    "support_material": "1",
    "support_material_buildplate_only": "1",
    "support_material_style": "snug",
    "support_material_spacing": "1.8",
    "support_material_interface_layers": "2",
    "support_material_interface_spacing": "0.25",
    "support_material_xy_spacing": "70%",
}
PROJECTS = {
    "swatches": ("K2_04_ASA_ColorMix_Swatches.3mf", {}),
    "coupon": ("K2_04_ASA_Card_and_Thread_Coupon.3mf", dict(SNUG_SUPPORT, support_material_threshold="30")),
    "shells": ("K2_04_ASA_Black_Shells.3mf", SOLID),
    "spacer": ("K2_04_ASA_Black_Spacer_and_Pins.3mf", SOLID),
    "handle": ("K2_04_ASA_Pink_Handle.3mf", dict(SNUG_SUPPORT, brim_width="6", support_material_threshold="30",
                                              bridge_angle="180")),
    "bow": ("K2_04_ASA_Pink_Bow_White_Dots.3mf", dict(SNUG_SUPPORT, brim_width="8", brim_separation="0")),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT, help="Directory for native 3MF outputs")
    parser.add_argument("--scratch", type=Path, required=True, help="Directory for build evidence")
    parser.add_argument("--plate", choices=PROJECTS, action="append", help="Build only the named plates")
    parser.add_argument("--bow-angle", type=float, default=90, help="Bow face angle to the bed in degrees")
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    base = load_current_profiles()
    for plate in args.plate or PROJECTS:
        filename, overrides = PROJECTS[plate]
        config = effective_config(base, overrides)
        items = swatch_items() if plate == "swatches" else production_items(plate, args.bow_angle)
        placements = package_project(args.out / filename, items, config)
        evidence = {
            "project": filename,
            "placements": placements,
            "installed_profile_overrides": {
                key: value for key, value in config.items() if base.get(key) != value
            },
        }
        (args.scratch / f"{plate}-build.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(args.out / filename)


if __name__ == "__main__":
    main()

