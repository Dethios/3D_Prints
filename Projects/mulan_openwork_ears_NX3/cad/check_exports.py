"""Check the two one-piece print exports at the approved NX3 envelope."""
from pathlib import Path
import sys

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
errors = []
for side in ("left_fan_trio", "right_mulan"):
    path = ROOT / "stl" / f"{side}_integrated_NX3.stl"
    if not path.is_file():
        errors.append(f"Missing print export: {path.name}")
        continue
    part = trimesh.load_mesh(path)
    if not (part.is_volume and len(part.split()) == 1 and part.is_winding_consistent):
        errors.append(f"{path.name}: expected one watertight solid")
    if not (99.9 < part.extents[0] < 100.1 and np.isclose(part.extents[2], 10.0)
            and np.isclose(part.bounds[0, 2], 0)):
        errors.append(f"{path.name}: wrong ring width, depth or print plane")
if errors:
    sys.exit("\n".join(errors))
print("Both ears reload as one watertight solid and retain the NX3 shell envelope.")
