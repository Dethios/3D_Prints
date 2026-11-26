"""Build illustration reliefs inside the approved engraved NX3 shell."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import manifold3d as md
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, box
import trimesh

from coin_rim import FLOOR_Z, KEY_Z, KEY_STROKE, SHOULDER_Z, coin_rim


ROOT = Path(__file__).resolve().parents[1]
REF = ROOT.parent / "sorcerer_ears_CAD_STL_v2"
NX3 = REF / "STL/NX3"
sys.path.insert(0, str(ROOT.parent / "magnetic_treasure_crab_ears_NX3" / "cad"))
import build_crab_nx3 as crab

crab.PALETTE = {"band": "#40383e", "gold_light": "#f0cc7d"}
NAMES = ("fan-trio", "mulan")
SIDES = ("left", "right")
RIM_DEPTH = 10.0
SHELL_FILE = NX3 / "Uniform_Rim/ear_blue_base.stl"
SLUGS = ("left_fan_trio_integrated_NX3", "right_mulan_integrated_NX3")
ART_FILES = ("fan-trio-hands-corrected.png", "mulan-illustration2.png")
DRAGON_FILE = "Brighter-dragon.jpg"
BG = "#181227"


def record(body, path):
    assert body.status().name == "NoError", (path, body.status())
    solids = sorted(body.simplify(.00013).decompose(), key=lambda s: s.volume(), reverse=True)
    assert len([p for p in solids if p.volume() > .001]) == 1, (path, [s.volume() for s in solids])
    crab.mesh(solids[0]).export(path)
    m = trimesh.load_mesh(path)
    assert m.is_volume and len(m.split()) == 1 and abs(m.bounds[0, 2]) < .001, path
    return crab.solid(m), {
        "extents_mm": m.extents.round(3).tolist(),
        "volume_mm3": round(m.volume, 3), "watertight": True, "solid_count": 1,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def mount_point():
    return json.loads((REF / "CAD/assembly_positions.json").read_text())["NX3"]


def bore_cylinder(center, normal, depth, radius, offset):
    angle = math.degrees(math.atan2(normal[1], normal[0]))
    cylinder = md.Manifold.cylinder(depth, radius, circular_segments=72)
    return cylinder.rotate((0, 90, angle)).translate(tuple(center + offset*normal))


def check_mount(ear, shell, strip, adapter, bores, engraving):
    shell_lost = max(0, (shell - ear).volume())
    mount_lost = max(0, ((strip - engraving) - ear).volume())
    baseline = (strip ^ adapter).volume()
    new_overlap = max(0, (ear ^ adapter).volume() - baseline)
    assert shell_lost < .03 and mount_lost < .015 and new_overlap < .012
    bore_changes = []
    for bore in bores:
        c, n = np.asarray(bore["center"]), np.asarray(bore["normal"])
        clear = bore_cylinder(c, n, 4.5, 3.15, -.04)
        intrusion = max(0, ((clear ^ ear) - strip).volume())
        wall = bore_cylinder(c, n, 1.05, 3., -1.07)
        assert intrusion < .008 and (wall-ear).volume() < .008
        bore_changes.append(round(intrusion, 6))
    return {"source_shell_material_lost_mm3": round(shell_lost, 7),
            "carrier_material_lost_outside_engraving_mm3": round(mount_lost, 7),
            "inherited_adapter_intersection_mm3": round(baseline, 7),
            "added_adapter_intersection_mm3": round(new_overlap, 7),
            "added_pocket_interference_mm3": bore_changes,
            "verified_pocket_back_wall_mm": 1.05}


def main():
    from ear_composition import Composition
    from lithograph import GRID_MM
    from PIL import Image
    from render_review import render

    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-stl-dir", type=Path,
                        help="Optional approved rim and mount reference exports.")
    parser.add_argument("--source-dir", type=Path,
                        help="Optional directory with the original medallion photos for provenance.")
    parser.add_argument("--art-dir", type=Path, default=ROOT / "artwork",
                        help="Directory containing the two new RGBA illustrations.")
    args = parser.parse_args()
    shell_mesh = trimesh.load_mesh(SHELL_FILE)
    shell = crab.solid(shell_mesh)
    strip_path = NX3 / "mount_test_strip.stl"
    base_path = NX3 / "glue_on_base_SOURCE_GEOMETRY.stl"
    strip, adapter = crab.solid(strip_path), crab.solid(base_path)
    band = crab.solid(REF / "Reference_files/dressyspider_larger_headband_source.stl")
    poses = mount_point()
    transforms = [np.asarray(poses[key]) for key in ("left_brooms", "right_mouse")]
    bores = json.loads((REF / "CAD/reference_geometry_report.json").read_text())["NX3"]["bore_caps"]
    pocket_guards = [bore_cylinder(np.asarray(bore["center"]), np.asarray(bore["normal"]),
                                  5.4, 3.26, -.22) for bore in bores]
    relief_keepout = crab.union([adapter, *pocket_guards])
    rim = crab.projection(shell_mesh, flat_top=RIM_DEPTH)
    assert rim.geom_type == "Polygon" and len(rim.interiors) == 1
    interior = Polygon(rim.interiors[0])
    belt,field,keys,tile_count = coin_rim(rim)
    engraving_cut = crab.union([
        crab.extrude(belt,10.15,KEY_Z),
        crab.extrude(belt.difference(keys),KEY_Z+.04,SHOULDER_Z),
        crab.extrude(field.difference(keys),SHOULDER_Z+.04,FLOOR_Z),
    ])
    assert (engraving_cut ^ relief_keepout).volume() < .001
    engraved_shell = shell - engraving_cut
    parts = {}
    preview_inputs = []
    assemblies = []
    dragon = Image.open(args.art_dir / DRAGON_FILE)
    for i, (side, slug, pose) in enumerate(zip(SIDES, SLUGS, transforms)):
        picture = Image.open(args.art_dir / ART_FILES[i])
        art = Composition(picture, interior, i, dragon)
        relief, height = art.mesh()
        relief = relief ^ crab.extrude(art.safe, 6.0, 1.57)
        relief = relief - relief_keepout
        if i == 0:
            wall = art.safe.difference(interior).intersection(box(-45,0,45,21))
            rim_joint = (relief ^ engraved_shell ^ crab.extrude(wall, 5.9, 2.26)).volume()
            assert rim_joint > 1.5, "Trio relief must join the lower ring above the backing"
            side_zone = affinity.rotate(box(-47,-32,-21,-20), -40, origin=(0,0))
            side_zone = affinity.translate(side_zone, yoff=38.79776)
            side_wall = art.safe.difference(interior).intersection(side_zone)
            side_joint = (relief ^ engraved_shell ^ crab.extrude(side_wall, 5.9, 2.26)).volume()
            assert side_joint > .7, "Red robe must join the outboard side of the ring"
        else:
            rocket_wall = art.rocket_zone.difference(interior)
            rocket_joint = (relief ^ engraved_shell ^ crab.extrude(rocket_wall, 5.9, 2.26)).volume()
            assert rocket_joint > .45, "Rocket must overlap the lower rim above the backing"
        design = engraved_shell + relief
        reloaded, info = record(design, ROOT / "stl" / f"{slug}.stl")
        info.update(check_mount(reloaded, engraved_shell, strip, adapter, bores,
                                engraving_cut))
        if i == 0:
            info["trio_overlap_with_lower_rim_mm3"] = round(rim_joint, 3)
            info["red_robe_overlap_with_left_rim_mm3"] = round(side_joint, 3)
        else:
            info["rocket_overlap_with_lower_rim_mm3"] = round(rocket_joint, 3)
        relief_prism = crab.extrude(art.safe, 5.9, 2.22)
        area = (reloaded ^ relief_prism).slice(2.25).area()
        info["artwork_area_at_0_25mm_raise_mm2"] = round(area, 2)
        info["artwork_coverage_percent_of_safe_field"] = round(100*area/art.safe.area, 1)
        if args.previous_stl_dir:
            previous = crab.solid(args.previous_stl_dir / f"{slug}.stl")
            protect = crab.union([crab.extrude(art.safe, 5.9, 1.95),
                                  crab.extrude(rim.buffer(.08),10.08,FLOOR_Z-.07)])
            current_exterior = reloaded - protect
            old_exterior = previous - protect
            removed = max(0., (old_exterior - current_exterior).volume())
            added = max(0., (current_exterior - old_exterior).volume())
            assert max(removed, added) < .015, (slug, removed, added)
            info["outside_artwork_and_rim_change_mm3"] = {
                "removed": round(removed, 7), "added": round(added, 7)
            }
            prior_area = (previous ^ relief_prism).slice(2.25).area()
            info["prior_artwork_area_at_0_25mm_raise_mm2"] = round(prior_area, 2)
            info["artwork_coverage_gain_percent"] = round(100*(area/prior_area-1),1)
        assembly = crab.transformed(reloaded, pose)
        assemblies.append(assembly)
        source_in_place = crab.transformed(shell, pose)
        added_band = max(0., (assembly ^ band).volume() - (source_in_place ^ band).volume())
        assert added_band < .012
        info.update({
            "printed_parts": 1,
            "relief_field_z_mm": 2.0,
            "max_artwork_height_above_backing_mm": round(float(height.max())-.06, 3),
            "photo_relief_grid_mm": GRID_MM,
            "foreground_scale_mm_per_source_px": round(float(art.foreground_scale), 5),
            "added_band_intersection_mm3": round(added_band, 7),
        })
        parts[side] = info
        preview_inputs.append((reloaded, art, pose, picture.copy()))
    pair_overlap = (assemblies[0] ^ assemblies[1]).volume()
    assert pair_overlap < .012
    opposite = [(part ^ crab.transformed(adapter, transforms[1-i])).volume()
                for i, part in enumerate(assemblies)]
    assert max(opposite) < .012
    report = {"status": "PASS", "units": "mm", "ring_depth_equals_carrier_mm": 10.0,
              "nominal_front_view_rim_width_mm": 5.056,
              "coin_rim": {"key_coils_per_ear": tile_count, "nominal_key_stroke_mm": KEY_STROKE,
                           "levels_z_mm": [FLOOR_Z,SHOULDER_Z,KEY_Z,RIM_DEPTH]},
              "magnet_size_mm": [6,3],
              "five_original_pockets_per_ear": True,
              "ear_pair_intersection_mm3": round(max(pair_overlap, 0), 7),
              "opposite_adapter_intersections_mm3": [round(max(v, 0), 7) for v in opposite],
              "parts": parts, "physical_fit": "Pending"}
    report["source_sha256"] = {str(path.name): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (SHELL_FILE, strip_path, base_path)}
    if args.source_dir:
        report["visual_sources_sha256"] = {
            name: hashlib.sha256((args.source_dir / f"source-{name}.png").read_bytes()).hexdigest()
            for name in NAMES
        }
    report["artwork_base_sha256"] = {name: hashlib.sha256((args.art_dir / name).read_bytes()).hexdigest()
                                   for name in (*ART_FILES, DRAGON_FILE)}
    (ROOT / "validation_report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2), flush=True)
    render(preview_inputs, band)


if __name__ == "__main__":
    main()
