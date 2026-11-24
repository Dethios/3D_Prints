# Repository Guidelines

## Project Structure

- Use the [root project index](README.md#project-index) to find the tracked designs in `Projects/`. Keep each design and its derivative references with its owning project. Keep upstream checkout changes within the appropriate nested repository.
- [Sorcerer ears](Projects/sorcerer_ears_CAD_STL_v2/READ_ME_FIRST.txt) owns the NX3 and Tim J CAD and reference geometry. The repository includes NX3 STLs and base Voron plates. Generate Tim J STLs before slicing that family. Check which geometry an existing plate embeds before using it for a revised variant.
- [Crab NX3](Projects/magnetic_treasure_crab_ears_NX3/README.md) uses the approved Sorcerer NX3 ear interface and owns its revised crown base and eye pair. The earlier crab v3 kit and its receivers are in Git history at `a9a95b8`.
- [Printables](Printables/README.md) groups downloaded models by listing and preserves original filenames. [GitHub-Mods](GitHub-Mods/README.md) indexes the separately managed local checkouts. [Unverified-Downloads](Unverified-Downloads/README.md) records source and license evidence by model.
- [Printer](Printer/README.md) contains machine notes, mods, test patterns and calibration. [Printer rewiring](Printer/rewiring/README.md) records PUG choices, mounting options and maker sources. [Migration records](Migration/2026-11-10/README.md) describe the original import and rewiring reorganization.
- The Mulan NX3 project, Sorcerer NX3 relief studies and some slicer plates are local workspace files. Check `git ls-files` and `git status` before citing an asset as available in a fresh clone or preparing it for publication.

## Build and Preview

Use [CAD and Print Workflow](PRINT_WORKFLOW.md) to select CadQuery or Autodesk Fusion MCP, validate the geometry, render a Blender preview when useful, and slice in PrusaSlicer. Confirm the target printer, installed nozzle and material before choosing presets.

- **Voron 2.4.** Select the printer preset for the installed nozzle and its matching `Voron PIF - … mm` print preset. Active sizes are 0.4 mm Rapido, 0.5 mm high-flow Bozzle and 0.6 mm high-flow bimetal CHT. Some saved plates embed `VictorCustom`. Inspect their effective settings before exporting. See [Prepare a Voron print](README.md#prepare-a-voron-print).
- **Creality K2.** Use the matching `Creality K2 (… mm)` printer and print presets for the installed 0.2, 0.4, 0.6 or 0.8 mm Unicorn nozzle. The Costco unit has stock hardware and one four-slot CFS. For multicolor, preserve part alignment and verify the slot assignments, toolpaths and K2 startup and shutdown macros. Use [the K2 workflow](PRINT_WORKFLOW.md#slice-and-print-on-the-creality-k2-with-cfs) and [installed software inventory](Printer/README.md#creality-k2). Mainsail is at `192.168.1.246:4409`.

Use the [build table](README.md#rebuild-scripted-models) for current Sorcerer, Crab NX3 and small-arm generators and their validation evidence. Run commands from each project folder with the documented Python 3.12 environment. Use a scratch copy for trial builds that overwrite exports or reports. For illustration-led projects kept locally, follow the project's own build and validation instructions.

For reference-led redesigns, capture the visual features to preserve and the exact approved mating files before modeling. Check the silhouette and front view alongside an assembly view that shows the mount. Treat Blender as optional for this check. A render from the generated geometry can establish appearance and placement while slicer toolpaths establish which features survive slicing.

For illustration-led parts, use the [illustration-to-CAD handoff](.agents/skills/printable-art-design/SKILL.md). Before generating artwork, record the role of each reference, the dimensioned artwork envelope and keepouts, the features to preserve, and the intended print treatment. Identify the selected artwork by path and hash before using it as a production CAD input. Provisional fit studies can use a labeled candidate. Keep visual review, artwork selection, and CAD and slicer validation as separate results.

## Editing and Naming

Use four-space indentation in Python and keep dimensions in millimeters. Follow existing descriptive filenames such as `left_face_gold.stl` and `ear_adapter_W10_R65_print_two.stl`. Update the generator and its inputs when changing generated geometry, then regenerate the matching exports. Preserve reference meshes and attribution files. Keep NX3 and TimJ parts in their respective folders and preserve shared coordinates for multipart color exports.

Reuse approved mating geometry at its original scale. Preserve the pocket pattern, axes and depth. When adapting a visual design, place changes in the decorative body or its attachment to the carrier where possible. Check the nominal assembly after adding the artwork, including clearance around the center mount. Compare mating interference with the source pair so inherited tessellation overlap and new collisions are distinguishable.

## Skills and Agents

Use [fusion-print-design](.agents/skills/fusion-print-design/SKILL.md) for Fusion CAD and exports, [printable-art-design](.agents/skills/printable-art-design/SKILL.md) for printable decoration, and the matching [Voron](.agents/skills/voron-print-preflight/SKILL.md) or [K2 CFS](.agents/skills/k2-cfs-preflight/SKILL.md) preflight skill for slicing and layer review.

GPT-6.2 Sol Medium is the saved main coordinator. Main resolves requirements, assigns work, coordinates dependencies, owns approvals, integrates specialist deliverables and verifies the result.

**Route substantial work at intake.** At the start of a substantial request and after any material correction, identify the work that benefits from higher reasoning or independent evidence. Use standing authorization to reserve and dispatch the specialist as soon as the assignment can advance the request, before main starts that work. This includes reference research and inspection, design and fit decisions, difficult implementation or debugging, and consequential validation. Use at least **High** reasoning for those assignments and follow the role profile when the problem warrants a stronger route. Tell the user which assignments are underway, or give the concrete reason local work is appropriate. Main continues independent coordination, evidence gathering and routine execution. Record each assignment, its expected evidence and the corresponding acceptance check in the coordination ledger.

**Inspect mechanical references before design.** When the user supplies a model as a functional reference, assign a specialist to open the actual CAD, STL or 3MF and inspect the relevant parts, dimensions, assembly, insertion path and retention. Record the exact file and revision plus measured evidence. Use listing text and photos as supporting evidence. Resolve material differences between the author's instructions and the actual geometry before relying on either. If the model is inaccessible, report the blocker and keep any dependent design pending while continuing independent work.

**Required design ownership.** Before creating or revising a design, dispatch the applicable design specialist to own the design decisions and author the changed artwork, CAD, generator geometry or design preview. This applies to concepts, reference tracing, silhouette and proportion changes, alignment, fit, dimensions, retention, joints and print-driven geometry changes. It applies again on follow-up corrections, including small revisions. Reuse a qualified specialist when available. A read-only audit or critique does not satisfy authoring ownership.

Dispatch design authors with an explicit supported model and at least **High** reasoning. Use the role profile's higher-reasoning route for cases where reference fidelity, fit, alignment or print constraints interact. Main may gather measurements, run acceptance checks and integrate the specialist's output. If a qualified design author, required reservation or tool is unavailable, report the blocker and continue independent work while leaving the affected design revision pending.

Proactively dispatch useful bounded inspection, development and validation assignments without waiting for a separate delegation request.

- Dispatch `print-inspector` for fit, dimensions, source interfaces, mesh quality and validation evidence. Start independent inspection while main establishes requirements. Use an independent inspector on consequential CAD changes once the exports are ready.
- Dispatch `print-cad-designer` to author mechanical design, CAD revisions and editable generator geometry. Give it the approved geometry and the target fit, loads, material and process.
- Dispatch `print-art-designer` to author visual concepts, reference geometry, vector, openwork, relief and multipart color artwork. Start it in parallel with mechanical work when the carrier envelope, keepouts and alignment are established. Main assigns ownership of any shared ComfyUI queue and records the allowed render and retry scope.
- Dispatch `print-process-specialist` for material and nozzle tradeoffs, calibration interpretation, multilayer printability and K2 CFS toolpaths. It can plan against a stable specification and verify once the affected export exists.
- Reuse `automation` for generator tooling and repeatable checks, `computer_use` for supported UI operations, and a risk-matched `reviewer` for consequential code changes. Use `researcher` or `reviewer_compliance` when maker-source or publication-rights questions warrant a separate assignment.

Use the [repo role profiles](.codex/agents/) for routing. Supply an explicit supported model and effort per assignment. If a repo role is absent from the live tool, use a compatible available role with the same scoped instructions and required reasoning level, and report the fallback. Main can keep routine lookups and non-design integration edits local. Follow native-coordination and use the [assignment contract](README.md#worker-assignments). Verify tools, reserve through the ledger, and serialize Fusion and PrusaSlicer ownership.

## Validation and Review

**Independent design validation.** Assign a separate specialist with at least **High** reasoning to check each design revision against the user's requirements, the exact references and the actual deliverable. Match the validation to the revision. A concept can be checked against a reference overlay and functional layout, while CAD or slicer deliverables need geometric or toolpath evidence as applicable. The validator must independently check the changed behavior and confirm which aspects remain unverified. Main reviews that evidence and resolves any material discrepancy before presenting the revision as verified.

Reload the exported STLs and check units, dimensions, watertightness, winding and expected solid counts. Inspect `validation_report.json` or `validation_results.json` after regenerating models. Review orientation, first-layer contact, thin relief, bridges, supports and multipart alignment in the slicer.

For K2 CFS plates, review the preview by tool and confirm that each `T0`–`T3` command selects the intended slot. Use the K2 presets for CFS tool changes and keep the wipe tower and slicer priming disabled. Local slicing, printer transfer and physical print start are separate actions. Transfer and start require authorization that covers them.

When applying Ellis's Voron layout, establish the print face first, then rotate the objects +45° around Z as a starting point. Verify the final rotation and spacing after arranging, including brims. Review the seam and bridge toolpaths before saving the 3MF. See [Ellis's 45° Voron layout](PRINT_WORKFLOW.md#ellis-45-voron-layout) for the rationale and the NX3 example.

When a saved print preset fails in the CLI, isolate which preset causes the failure. Preserve installed profiles. If a scratch profile allows a geometry check, record the slicer version, settings used, differences from the original preset and observed layer results. Keep geometry checks, slicer evidence and physical fit as separate results. If the user requests digital files or documentation only, record physical fit as pending. Before an eventual full print of a revised mount, test its coupon or strip with the actual mating parts.

If submitting a change for review, use a short, action-oriented summary such as “Adjust crab-ear receiver clearance.” Identify the affected variant and dimensions, link any relevant issue, and include a CAD or slicer preview for visible changes.

Before publishing a model, verify the asset-specific notices and rights for the source geometry and artwork. Stage only the authorized files. Keep local studies, generated archives, machine-specific slicer files and unrelated edits out of documentation-only pushes.
