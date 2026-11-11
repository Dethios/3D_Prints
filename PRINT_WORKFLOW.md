# CAD and Print Workflow

## Choose the source of truth

| Work | Design pathway |
| --- | --- |
| Existing crab or sorcerer ears, parameter changes, repeated variants | Edit the CadQuery generator and its inputs. Rebuild the matching STEP/STL set and run its validator. Preserve the reference meshes, mounting family and multipart coordinates. |
| New mechanical parts, interactive assembly or imported STEP inspection | Use Autodesk Fusion MCP. Start by listing open documents and confirm the target design and units. Use read-only inspection for dimensions and fit. For authorized edits, use a dedicated design, check the resulting features and bodies, and save when requested. Retain the editable Fusion design reference alongside the STEP exchange and print exports. |
| Standalone STL or 3MF with no planned geometry change | Inspect dimensions and mesh in PrusaSlicer and proceed to layer preview. For fit-critical changes, obtain the editable source or rebuild the affected feature in CAD. |

For Fusion-owned designs, verify the exported mesh independently. Use a project validator only when its geometry assumptions match the part. Check units, overall dimensions, expected body count and manifoldness. Keep intentional multipart bodies aligned. Record the target fit and critical dimensions in millimeters.

## Rebuild and preview

Blender is optional and currently uninstalled. Use Fusion for CAD and assembly inspection and PrusaSlicer for layer review. Install Blender when rendered assembly images or the existing automated preview scripts are needed. The Blender commands below require that installation.

Use Python 3.12 and a dedicated virtual environment. From the workspace root, `uv venv --python 3.12 .venv` and `uv pip install --python .venv/Scripts/python.exe -r Projects/sorcerer_ears_CAD_STL_v2/CAD/requirements.txt` prepare the pinned sorcerer environment. The requirements also include the crab project's documented CadQuery 2.7 and SciPy dependencies. Activate the environment or use its Python by absolute path. If the configured uv cache is inaccessible, use `uv --no-cache`.

Run each row from its project directory. Builds, validators and preview scripts can update files in that project. Use a scratch copy for comparisons or trial runs.

| Project | Build and validate in order | Render the exported geometry |
| --- | --- | --- |
| Earlier crab ears (`magnetic_treasure_crab_ears_v3/`) | `python cad/build_crab_v3.py`, then `python analysis/validate_v3.py` | `blender --background --python-exit-code 1 --python analysis/render_v3.py` |
| NX3 crab ears (`Projects/magnetic_treasure_crab_ears_NX3/`, local kit) | `python cad/build_crab_nx3.py` with the approved Sorcerer project beside it. Review `validation_report.json` and `slicer_preflight.json`. | Review the supplied previews and the assembly together. |
| Sorcerer ears (`Projects/sorcerer_ears_CAD_STL_v2/`) | `python CAD/build_reference_mounts.py`, then `python CAD/check_and_position.py` | `blender --background --python-exit-code 1 --python CAD/render_reference_previews.py` |

For printer rewiring, choose the PUG gland and mount independently for the intended location and hardware. The [rewiring index](Printer/rewiring/README.md) records the local options and maker pages.

Use the full path to `blender.exe` if it is outside PATH. For a new Fusion design, import the exported print mesh in Blender when a visual review would help. Review decorative silhouettes, assembly clearances and orientation. Use the slicer for actual toolpaths.

## Slice for the Voron 2

Open `C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe`. Read the installed presets from `C:\Users\vic-l\AppData\Roaming\PrusaSlicer`. The saved physical printer selection is `Voron2.4 * VictorCustom`. The `VictorCustom` printer preset specifies Klipper, a 0.5 mm nozzle and a 350 × 350 × 320 mm configured envelope. Confirm the installed nozzle and usable volume before relying on these values.

1. Load the intended model. When using a third-party 3MF, import geometry only or explicitly reselect and check the Voron settings, including custom G-code.
2. Select `VictorCustom` and a compatible preset for the actual filament. Local examples include `Polymaker PolyChroma Matte` (PLA) and `Polymaker ASA`. Start with `Functional Parts` for mounts and `Cosmetic Parts` for visual pieces, then tune for the part. The ear documentation's 0.4 mm starting settings need review against the 0.5 mm profile, especially at narrow reliefs, stems and magnet-pocket bridges.
3. Inspect the first layer, wall continuity, islands, bridges and supports. Keep support material out of blind magnet bores. Preserve shared coordinates in multicolor parts and verify the machine's available color-change method. Adjust fit in CAD or on a test coupon.
4. For tolerance-critical parts, slice the magnet coupon or mount test strip with the same nozzle, material, orientation and settings as the intended print. Confirm mating fit and magnet polarity before producing the full set.
5. Save a project 3MF with the selected presets and record the CAD revision and any fit results. Export local G-code only after reviewing the layers. Treat transfer or print start as separate actions.

The printer's SSH endpoint is `192.168.1.37`. Use the `voron` alias when `ssh -G voron` resolves it to that address. Verify any changed host key through a trusted path. SSH is for printer diagnostics and is independent of local slicing. Keep private keys, physical-printer credentials and host settings out of design bundles.

References: [PrusaSlicer 2.9 print and preview workflow](https://help.prusa3d.com/article/first-print-with-prusaslicer-2-9_1753) and [Saving projects as 3MF](https://help.prusa3d.com/article/saving-projects-as-3mf_1773).

### Ellis 45° Voron layout

Ellis rotates parts 45° in the bed plane mainly to make rear seam placement more predictable across a plate. A straight move at 45° on a CoreXY printer uses one motor, which can improve the finish of some straight walls. Use the angle as a starting point and judge it against the actual seam preview, part shape and available bed space. [Ellis's 45° profile notes](https://github.com/AndrewEllis93/Ellis-SuperSlicer-Profiles/blob/master/README.md#45-degree-profile-vs-standard-profile)

1. Choose the print face for strength, surface finish, overhangs and magnet-pocket access. Apply +45° around Z in the slicer with the part flat on its chosen face and at 100% scale.
2. Arrange the rotated parts with room for brims and airflow. After auto-arranging, recheck rotations, spacing and bed bounds. [Ellis's part spacing notes](https://github.com/AndrewEllis93/Ellis-SuperSlicer-Profiles/blob/master/README.md#part-spacing--plating)
3. Check seam locations and layer paths. If using rear seams, aim a suitable edge toward the back of the plate and check where the slicer actually places the seam. Keep the tuned printer and filament settings. Treat the infill angle as a separate setting and review the resulting solid fill and bridges.
4. Save the 3MF with the selected settings. Reopen and slice it to confirm the final layout, first-layer adhesion features and pocket bridges.

The NX3 crab plate used +45° on all eight parts, 0° base infill angle, and 4 mm outer brims on the five mount pieces. Those settings were checked together in PrusaSlicer. Choose brim and infill settings for each future plate.
