# Repository Guidelines

## Project Structure

- `magnetic_treasure_crab_ears_v3/` contains the earlier crab design with its own receivers, generator, exports and validation scripts. Its mounts are a separate kit from the approved Sorcerer NX3 interface.
- `sorcerer_ears_CAD_STL_v2/` contains Python generators and STEP files in `CAD/`, printable parts in `STL/`, and source meshes in `Reference_files/`. Read `READ_ME_FIRST.txt` before choosing the NX3 or TimJ mounting family.
- `polymaker-refill-spool/` and the root-level STL and 3MF are standalone print assets.

## Build and Preview

Use [CAD and Print Workflow](PRINT_WORKFLOW.md) to select CadQuery or Autodesk Fusion MCP, validate the geometry, render a Blender preview when useful, and slice for the Voron 2 in PrusaSlicer.

Run commands from the corresponding project folder.

- **Crab ears.** With CadQuery 2.7 and SciPy installed, run `python cad/build_crab_v3.py` to regenerate the models, then `python analysis/validate_v3.py` to check them.
- **Sorcerer ears.** With Python 3.12, install dependencies using `python -m pip install -r CAD/requirements.txt`. Run `python CAD/build_reference_mounts.py` to rebuild both variants and `python CAD/check_and_position.py` to validate them. Run `blender --background --python CAD/render_reference_previews.py` to render the exported STLs.

For reference-led redesigns, capture the visual features to preserve and the exact approved mating files before modeling. Check the silhouette and front view alongside an assembly view that shows the mount. Treat Blender as optional for this check. A render from the generated geometry can establish appearance and placement while slicer toolpaths establish which features survive slicing.

## Editing and Naming

Use four-space indentation in Python and keep dimensions in millimeters. Follow existing descriptive filenames such as `left_face_gold.stl` and `ear_adapter_W10_R65_print_two.stl`. Update the generator and its inputs when changing generated geometry, then regenerate the matching exports. Preserve reference meshes and attribution files. Keep NX3 and TimJ parts in their respective folders and preserve shared coordinates for multipart color exports.

Reuse approved mating geometry at its original scale. Preserve the pocket pattern, axes and depth. When adapting a visual design, place changes in the decorative body or its attachment to the carrier where possible. Check the nominal assembly after adding the artwork, including clearance around the center mount. Compare mating interference with the source pair so inherited tessellation overlap and new collisions are distinguishable.

## Skills and Agents

Use [$fusion-print-design](.agents/skills/fusion-print-design/SKILL.md) for Fusion CAD authoring and export checks. Use [$voron-print-preflight](.agents/skills/voron-print-preflight/SKILL.md) for geometry, Voron presets and layer review. Invoke either by name in a Codex prompt. Blender previews are optional.

Use `print3d` for a bounded CAD or fit assignment, `automation` for repeatable checks, `computer_use` for a supported slicer UI session, and `reviewer` for consequential independent review. Verify worker tools and apply the current global routing and coordination policy. Give each worker exclusive file or app ownership and serialize Fusion and PrusaSlicer edits. If a required coordination reservation fails, report the limitation and continue locally where possible. See [README usage examples](README.md#codex-skills-and-agent-operations).

## Validation and Review

Reload the exported STLs and check units, dimensions, watertightness, winding and expected solid counts. Inspect `validation_report.json` or `validation_results.json` after regenerating models. Review orientation, first-layer contact, thin relief, bridges, supports and multipart alignment in the slicer.

When a saved print preset fails in the CLI, isolate which preset causes the failure. Preserve installed profiles. If a scratch profile allows a geometry check, record the slicer version, settings used, differences from the original preset and observed layer results. Keep geometry checks, slicer evidence and physical fit as separate results. If the user requests digital files or documentation only, record physical fit as pending. Before an eventual full print of a revised mount, test its coupon or strip with the actual mating parts.

If submitting a change for review, use a short, action-oriented summary such as “Adjust crab-ear receiver clearance.” Identify the affected variant and dimensions, link any relevant issue, and include a CAD or slicer preview for visible changes.

Before publishing a model, verify the asset-specific notices and rights for the source geometry and artwork. Stage only the authorized files. Keep local studies, generated archives, machine-specific slicer files and unrelated edits out of documentation-only pushes.
