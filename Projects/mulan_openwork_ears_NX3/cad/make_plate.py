"""Package the exported ears for PrusaSlicer using the checked Crab NX3 profile."""
from io import BytesIO
import math
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image
import trimesh

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT.parent / "magnetic_treasure_crab_ears_NX3/Crab_NX3_Voron24_45deg.3mf"
OUTPUT = ROOT / "Mulan_NX3_Voron24_025mm_45deg.3mf"
NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", NS)


def xml(node):
    return ET.tostring(node, encoding="utf-8", xml_declaration=True)


def main():
    with ZipFile(PROFILE) as src:
        headers = {key: src.read(key) for key in ("[Content_Types].xml", "_rels/.rels")}
        cfg = src.read("Metadata/Slic3r_PE.config").decode("utf-8")

    options = dict(line[2:].split(" = ", 1) for line in cfg.splitlines()
                   if line.startswith("; ") and " = " in line)
    required = {"nozzle_diameter": "0.5", "layer_height": "0.15",
                "first_layer_height": "0.25", "post_process": "",
                "support_material": "0", "brim_width": "0",
                "bed_shape": "0x0,350x0,350x350,0x350"}
    for k, v in required.items():
        if options[k] != v:
            raise ValueError(f"Review changed profile option: {k}: {options[k]}")
    # Project-local fine-nozzle settings. Keep the Voron bed, printer
    # start/end macros and saved installed presets as they were.
    fine = {
        "print_settings_id": "Mulan NX3 - 0.25 mm nozzle, 0.08 mm layers",
        "printer_settings_id": "VictorCustom - 0.25 mm (Mulan project)",
        "nozzle_diameter": "0.25", "nozzle_high_flow": "0",
        "layer_height": "0.08", "first_layer_height": "0.15",
        "min_layer_height": "0.05", "max_layer_height": "0.18",
        "first_layer_speed": "20", "external_perimeter_speed": "28",
        "perimeter_speed": "45", "solid_infill_speed": "45",
        "top_solid_infill_speed": "28", "bridge_speed": "22",
        "resolution": "0.045", "slice_closing_radius": "0.065",
    }
    for key, value in fine.items():
        cfg = cfg.replace(f"; {key} = {options[key]}", f"; {key} = {value}")

    model = ET.Element("model", {"xmlns": NS, "unit": "millimeter"})
    for k, v in {"slic3rpe:Version3mf": "1", "Title": "Mulan Integrated Ears | NX3",
                 "Description": "0.25 mm nozzle. Stepped paint relief and integrated five-pocket NX3 ears.",
                 "Application": "PrusaSlicer-2.9.7"}.items():
        ET.SubElement(model, "metadata", {"name": k}).text = v
    resources, build = [ET.SubElement(model, x) for x in ("resources", "build")]
    model_cfg = ET.Element("config")
    rotation = math.sqrt(.5)
    ranges = []
    for i, (slug, name, center) in enumerate([
        ("left_fan_trio_integrated_NX3", "Left - Fan Trio", (105., 175.)),
        ("right_mulan_integrated_NX3", "Right - Mulan", (245., 175.)),
    ], start=1):
        ear = trimesh.load_mesh(ROOT / "stl" / f"{slug}.stl")
        obj = ET.SubElement(resources, "object", {"id": str(i), "name": name, "type": "model"})
        mesh = ET.SubElement(obj, "mesh")
        vertices = ET.SubElement(mesh, "vertices")
        for point in ear.vertices:
            ET.SubElement(vertices, "vertex", dict(zip("xyz", (f"{x:.8f}" for x in point))))
        triangles = ET.SubElement(mesh, "triangles")
        for face in ear.faces:
            ET.SubElement(triangles, "triangle", dict(zip(("v1", "v2", "v3"), map(str, face))))

        rot = np.array([[rotation, rotation], [-rotation, rotation]])
        xy = ear.vertices[:, :2] @ rot
        shift = np.array(center) - (xy.max(axis=0) + xy.min(axis=0))/2
        ranges.append((xy.min(axis=0) + shift, xy.max(axis=0) + shift))
        transform = [rotation, rotation, 0, -rotation, rotation, 0, 0, 0, 1, *shift, 0]
        ET.SubElement(build, "item", {"objectid": str(i), "printable": "1",
                                      "transform": " ".join(f"{x:.12f}" for x in transform)})

        settings = ET.SubElement(model_cfg, "object", {"id": str(i), "instances_count": "1"})
        overrides = dict(name=name, perimeters="4", fill_density="100%")
        for k, v in overrides.items():
            ET.SubElement(settings, "metadata", {"type": "object", "key": k, "value": v})
        vol = ET.SubElement(settings, "volume", {"firstid": "0", "lastid": str(len(ear.faces)-1)})
        for k, v in dict(name=name, volume_type="ModelPart", source_file=f"{slug}.stl").items():
            ET.SubElement(vol, "metadata", {"type": "volume", "key": k, "value": v})

    assert min(np.min(r[0]) for r in ranges) > 10 and max(np.max(r[1]) for r in ranges) < 340
    for i, (lo, hi) in enumerate(ranges):
        for other_lo, other_hi in ranges[i+1:]:
            assert max(np.max(other_lo-hi), np.max(lo-other_hi)) > 16
    thumb = Image.open(ROOT / "previews/reference_comparison.png").convert("RGB")
    thumb.thumbnail((256, 256), Image.Resampling.LANCZOS)
    png = BytesIO()
    thumb.save(png, format="PNG")
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as out:
        for name, contents in headers.items():
            out.writestr(name, contents)
        out.writestr("3D/3dmodel.model", xml(model))
        out.writestr("Metadata/Slic3r_PE_model.config", xml(model_cfg))
        out.writestr("Metadata/Slic3r_PE.config", cfg)
        out.writestr("Metadata/thumbnail.png", png.getvalue())
    print(OUTPUT)
    print("Bed bounds:", ranges)


if __name__ == "__main__":
    main()
