---
name: voron-print-preflight
description: Use when checking CAD exports, STL or 3MF models, or PrusaSlicer projects for printing on this workspace's Voron 2, including nozzle compatibility, mounting fit and layer review.
---

# Voron Print Preflight

Review the requested model through geometry, slicer settings and physical fit evidence. Read [PRINT_WORKFLOW.md](../../../PRINT_WORKFLOW.md) for project commands and machine paths. Locate the workspace from this skill's directory so invocation also works from a project subfolder.

## Establish the target

Identify the exact revision, intended parts and mating interfaces. Record units, material, installed nozzle when known, load direction, critical dimensions and desired fit. Read existing project instructions and validation reports. Treat measurements and physical test results as evidence, and identify assumptions explicitly.

Inspect the current PrusaSlicer printer, print and filament presets from the documented configuration directory. The documented VictorCustom values are a starting reference. Verify current values, including inherited settings, against the selected project. A third-party 3MF can bring different profiles and custom G-code. An unconfirmed physical nozzle or material leaves the corresponding check pending while geometry work continues.

## Check geometry and toolpaths

- For scripted model changes, use the project's generator and validator. Use a scratch copy for a preflight-only request because the scripts overwrite exports and reports. Check both process exit status and report contents. The crab report uses a failures array, while the sorcerer report uses a status field.
- Inspect exported dimensions in millimeters, manifoldness, winding, expected component count and assembly intersections. Check source-derived mounting geometry at original scale. Separate color islands may be intentional. Preserve multipart coordinates and distinguish an assembly preview from individual printable parts.
- For Fusion designs, inspect body and feature health and compare exported dimensions with CAD. The existing ear validators have project-specific assumptions. Select checks applicable to the actual design.
- Inspect the selected PrusaSlicer profile and actual layer preview for first-layer contact, missing thin features, wall continuity, unsupported islands, overhangs, bridge spans and access for support removal. Account for the nozzle and extrusion width when evaluating reliefs, stems, walls and holes. Assess orientation against load direction and visible finish.
- Use local CLI help before constructing automated slicing commands. Work with scratch profile copies or an exported effective configuration. Preserve the user's installed presets and live plater. Check post-processing commands before executing them. A successful slice still needs layer review. If GUI access is unavailable, report the visual check as pending.

## Apply Ellis's 45° layout and verify the saved 3MF

For Voron plates, use +45° around Z as the starting layout after choosing the print face. Preserve 100% scale and multipart alignment. Check the part's strength direction, finish, overhangs and pocket access when choosing that face. Use [Ellis's layout guidance](../../../PRINT_WORKFLOW.md#ellis-45-voron-layout) for the rationale and source links.

1. Rotate each object +45° around Z, keeping it flat on its chosen face. After arranging, verify the saved rotations, intended part quantities and bed bounds.
2. Allow space for brims and airflow. Measure clearance between the footprints including brims. Choose brim width for each part's adhesion needs.
3. Review seam placement on the actual toolpaths. If using rear seams, aim a suitable edge toward the back of the plate. Treat infill angle as a separate setting and inspect solid fill and bridges with the chosen combination.
4. Save the project 3MF with the effective printer, print, filament and per-object settings. Reopen and slice that file directly to verify that its embedded settings and layout load correctly.
5. Check the reopened project's bed size, nozzle, layer heights, filament, temperatures and startup G-code against the selected presets. Inspect first-layer contact for every part, selective brims, thin relief, wall continuity, seams and magnet-pocket bridges. Record any warnings, estimates and pending physical fit checks.

The NX3 crab plate used +45° Z rotation, 0° base infill angle and 4 mm outer brims on its five mount pieces. Select infill and brim settings for the current geometry and material.

## Resolve fit and report

For mounting or tolerance changes, use the matching magnet coupon or mount strip with the intended material, nozzle, orientation and print settings. Record measured fit and corrections. Apply dimensional corrections to the relevant feature, preserving the original interface scale. Choose material and wall settings for the part's loads and environment using available calibration evidence.

Return the model path and revision, selected presets and observed settings, commands and results, warnings, completed geometry and layer checks, and outstanding physical tests. Mark each area as passed, needs changes or unverified. State what evidence is still needed before printing. Stop when the scoped checks are complete or dependent access is unavailable, and continue checks that remain possible.

Use the installed print3d role for fit and material decisions, automation for repeatable local checks, computer_use for slicer UI work, and reviewer for an independent review of consequential changes. Main selects current role settings and serializes app ownership. Local review and slicing do not authorize printer transfer, firmware changes or print start. Honor any separate authorization already provided for those actions.
