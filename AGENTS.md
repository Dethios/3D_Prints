# Repository Guidelines

## Project Structure

- `magnetic_treasure_crab_ears_v3/` contains the crab-ear generator and STEP files in `cad/`, printable parts in `stl/`, and validation scripts in `analysis/`. Start with `README.md`.
- `sorcerer_ears_CAD_STL_v2/` contains Python generators and STEP files in `CAD/`, printable parts in `STL/`, and source meshes in `Reference_files/`. Read `READ_ME_FIRST.txt` before choosing the NX3 or TimJ mounting family.
- `polymaker-refill-spool/` and the root-level STL and 3MF are standalone print assets.

## Build and Preview

Use [CAD and Print Workflow](PRINT_WORKFLOW.md) to select CadQuery or Autodesk Fusion MCP, validate the geometry, render a Blender preview when useful, and slice for the Voron 2 in PrusaSlicer.

Run commands from the corresponding project folder.

- **Crab ears.** With CadQuery 2.7 and SciPy installed, run `python cad/build_crab_v3.py` to regenerate the models, then `python analysis/validate_v3.py` to check them.
- **Sorcerer ears.** With Python 3.12, install dependencies using `python -m pip install -r CAD/requirements.txt`. Run `python CAD/build_reference_mounts.py` to rebuild both variants and `python CAD/check_and_position.py` to validate them. Run `blender --background --python CAD/render_reference_previews.py` to render the exported STLs.

## Editing and Naming

Use four-space indentation in Python and keep dimensions in millimeters. Follow existing descriptive filenames such as `left_face_gold.stl` and `ear_adapter_W10_R65_print_two.stl`. Update the generator and its inputs when changing generated geometry, then regenerate the matching exports. Preserve reference meshes and attribution files. Keep NX3 and TimJ parts in their respective folders and preserve shared coordinates for multipart color exports.

## Skills and Agents

Use [$fusion-print-design](.agents/skills/fusion-print-design/SKILL.md) for Fusion CAD authoring and export checks. Use [$voron-print-preflight](.agents/skills/voron-print-preflight/SKILL.md) for geometry, Voron presets and layer review. Invoke either by name in a Codex prompt. Blender previews are optional.

Assign CAD and fit work to `print3d`, repeatable checks to `automation`, slicer UI work to `computer_use`, and consequential independent review to `reviewer`. Verify worker tools, use `agents/*.toml` routing, give exclusive file/app ownership, and serialize Fusion and PrusaSlicer edits. See [README usage examples](README.md#codex-skills-and-agent-operations).

## Validation and Review

Inspect the applicable JSON report, `validation_report.json` or `validation_results.json`, after regenerating models. Review orientation, supports and multipart alignment in the slicer. For mounting changes, print the project's fit coupon or mount test strip and dry-fit it with the actual mating parts before a full print. Record physical fit results separately from digital checks.

If submitting a change for review, use a short, action-oriented summary such as “Adjust crab-ear receiver clearance.” Identify the affected variant and dimensions, link any relevant issue, and include a CAD or slicer preview for visible changes.
