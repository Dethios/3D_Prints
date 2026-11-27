"""Audit all R6 0.4 mm PLA projects and check the three active 0.6 mm gold plates."""

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import numpy as np

from build_plates_04 import HERE, PREFIX, PRESET, common
import audit_plates as shared


AUDIT_06 = HERE.parent / "R6_06_PLA" / "preflight.json"
GOLD_PLATES = (
    "K2_06_PLA_Castle_R6_Star_Face.3mf",
    "K2_06_PLA_Castle_R6_Threaded_Grip.3mf",
    "K2_06_PLA_Castle_R6_Threaded_Grip_Solid_Blue.3mf",
)
COMMON_REQUIRED = shared.REQUIRED.copy()
COMMON_BRIDGES = shared.report_bridges_and_supports


def audit_bridges(records, transforms, inspector):
    stub_label = "Grip_stub_coupon"
    supports = defaultdict(list)
    remaining = {}
    for z, moves in records.items():
        remaining[z] = []
        for move in moves:
            if "support" in move.role.lower():
                supports[move.item, move.role].append((z, move))
            else:
                remaining[z].append(move)
    result = COMMON_BRIDGES(remaining, transforms, inspector)
    if "Grip stub coupon" not in transforms:
        assert not supports
        return result
    assert any(label == stub_label for label, _ in supports)
    assert result[stub_label]["Bridge infill"]["longest_centerline_move_mm"] < 8.7
    transform_by_label = {
        inspector.object_label(name): np.array(values).reshape(4, 3)
        for name, values in transforms.items()
    }
    for (label, role), paths in supports.items():
        assert all(move.tool in range(3) for _, move in paths)
        bed_points = np.array([(x, y, z) for z, move in paths for x, y in (move.a, move.b)])
        assert np.all((bed_points[:, :2] >= 0) & (bed_points[:, :2] <= 260))
        transform = transform_by_label[label]
        local_points = (bed_points - transform[3]) @ transform[:3].T
        bead_radius = max(move.width for _, move in paths) / 2
        x_distance = np.abs(local_points[:, 0]).max() + bead_radius
        max_y = local_points[:, 1].max() + bead_radius
        if label == stub_label:
            assert x_distance < 6.3
            assert -71 < local_points[:, 1].min() - bead_radius and max_y < -55
            assert local_points[:, 2].max() < -3.7
        else:
            assert label in {"Front_shell_coupon", "Rear_shell_coupon"}
            assert x_distance < 2.2 and max_y < -57.75
        result[label][role] = {
            "segments": len(paths),
            "tool_set": sorted({f"T{move.tool}" for _, move in paths}),
            "longest_centerline_move_mm": round(max(math.dist(move.a, move.b) for _, move in paths), 3),
            "max_mm_from_thread_axis_x": round(x_distance, 3),
            "max_assembly_y_mm": round(max_y, 3),
            "assembly_xyz_centerline_bounds_mm": [
                local_points.min(axis=0).round(3).tolist(), local_points.max(axis=0).round(3).tolist(),
            ],
        }
    return result


def validate_gold_plate_archive():
    previous = json.loads(AUDIT_06.read_text(encoding="utf-8"))["plates"]
    receipts = {}
    for name in GOLD_PLATES:
        saved = previous[name]
        assert shared.sha((AUDIT_06.parent / name).read_bytes()) == saved["project_sha256"]
        assert saved["effective_settings"]["nozzle_diameter"] == "0.6,0.6,0.6,0.6"
        assert "T3" in saved["physical_tool_commands_in_order"]
        assert not saved["warnings"]
        receipts[name] = {
            "sha256_matches_existing_preflight": saved["project_sha256"],
            "slicer": saved["slicer"],
            "filaments": sorted(set(saved["physical_tool_commands_in_order"])),
            "material_and_time": saved["material_and_time"],
        }
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plates", type=Path, default=HERE)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    shared.PREFIX = PREFIX
    shared.report_bridges_and_supports = audit_bridges
    inspector = shared.load_inspector()
    paths = sorted(args.plates.glob(f"{PREFIX}*.3mf"))
    assert len(paths) == 7, "Expected five gold-free plates and two solid-blue alternates."
    results = {}
    for path in paths:
        shared.REQUIRED = {
            **COMMON_REQUIRED,
            "printer_settings_id": PRESET,
            "print_settings_id": PRESET,
            "nozzle_diameter": "0.4,0.4,0.4,0.4",
            "layer_height": "0.12" if "Coupon" in path.name else "0.1",
        }
        receipt = shared.audit_plate(path, args.scratch, inspector)
        assert set(receipt["physical_tool_commands_in_order"]) <= {"T0", "T1", "T2"}, path.name
        assert all(4 not in row["part_extruders"].values() for row in receipt["items"].values())
        if "Swatches" in path.name:
            assert len(receipt["items"]) == 7 and "Metallic Gold" not in receipt["items"]
        results[path.name] = receipt
        print(path.name, receipt["material_and_time"], flush=True)

    build_record = args.scratch / "build.json"
    report = {
        "r6_art_sha256": shared.sha(shared.ART.read_bytes()),
        "embedded_profile_overrides_and_source_records": json.loads(build_record.read_text(encoding="utf-8")),
        "plates": results,
        "active_gold_plates_from_prior_06_preflight": validate_gold_plate_archive(),
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
