# 3D Print Projects

CAD sources, printable models, reference assets and validation tools for projects intended for a Voron 2.

## Projects

| Folder or file | Contents |
| --- | --- |
| Magnetic treasure crab ears v3 | Earlier crab design; its project folder is not present in this workspace. |
| [Sorcerer ears](Projects/sorcerer_ears_CAD_STL_v2/READ_ME_FIRST.txt) | NX3 and TimJ mounting variants, editable source, STEP/STL exports, fit strips and previews. |
| [Treasure crab ears for NX3](Projects/magnetic_treasure_crab_ears_NX3/README.md) | NX3 mounting kit, parts list and assembly notes. The design and print plates are in the local workspace. |
| [Printables downloads](Printables/README.md) | Downloaded models grouped by listing, with maker notes and original filenames. |
| [Custom projects](Projects/README.md) | Ear kits, sorcerer hat and the Chube Air UHF integration. |
| [GitHub mods](GitHub-Mods/README.md) | Separate A4T, A4Tv2, and whopping Voron mods checkouts with their upstream history. |
| [Printer files](Printer/README.md) | Rewiring parts, cutter mod, and calibration and test prints. |
| [Star Wars source notes](Unverified-Downloads/README.md) | Candidate download pages, maker instructions, license evidence and local plate contents. |

The local workspace includes print plates, downloaded models, GitHub checkouts and migration records. Download listings and local filenames are recorded in the linked indexes.

## Choose a design pathway

- **Autodesk Fusion and Fusion MCP** support interactive CAD design, dimensions and assembly inspection. Preserve the editable design reference and export STEP and print meshes.
- **CadQuery** supports scripted geometry, reproducible builds and parameter variants. Edit the existing generator when revising a scripted project.
- **PrusaSlicer** is the main slicer for orientation, supports, layer inspection and G-code generation.
- **Blender is optional** for rendered previews using the included scripts. Use an assembly view or a render from generated geometry when appearance and placement need review.

See [CAD and Print Workflow](PRINT_WORKFLOW.md) for detailed pathway selection and print checks.

## Codex skills and agent operations

Project skills live in `.agents/skills/`. Open a new Codex session in this workspace after adding them, so the client can discover them. They support automatic selection when relevant and explicit invocation using `$skill-name`. If the current client has not refreshed its skill list, ask it to read the linked `SKILL.md` directly.

| Skill | Use | Example prompt |
| --- | --- | --- |
| [fusion-print-design](.agents/skills/fusion-print-design/SKILL.md) | Fusion MCP modeling, assembly inspection and verified exports | `Use $fusion-print-design to revise this bracket using the supplied mating dimensions, export STEP and STL into its project folder, and report the checks.` |
| [voron-print-preflight](.agents/skills/voron-print-preflight/SKILL.md) | Geometry, saved Voron presets, layer review and physical fit evidence | `Use $voron-print-preflight on magnetic_treasure_crab_ears_v3/stl/magnet_fit_coupon.stl with my VictorCustom printer and actual filament. Report warnings and pending checks.` |

Skills guide the available tools. Fusion MCP, local executables and app access must be available to the executing agent. For a new Fusion design, use the design skill through export, then the preflight skill through local slicing and layer review. For existing scripted projects, rebuild with CadQuery and its validator before preflight. Physical fit results belong with the part revision and selected settings.

Main owns integration and chooses installed roles according to the current global `agents/*.toml` files. Assign only independent work that benefits from delegation, using explicit supported model and effort settings from those roles.

| Installed role | Recommended operation | Expected evidence |
| --- | --- | --- |
| `print3d` | CAD dimensions, tolerances, materials, orientation and fit decisions | Critical measurements, assumptions, interface checks and proposed coupon |
| `automation` | Reusable builds, mesh checks and local slicing helpers | Commands, tool versions, exit status, report contents and output paths |
| `computer_use` | Supported Fusion or PrusaSlicer UI operations | Observed target document, layer inspection and saved project path when requested |
| `reviewer` | Independent review of consequential mounting, load or tolerance changes | Findings tied to approved mating geometry, nominal assembly and export evidence |

Give each worker an objective, input paths, owned files or application session, allowed actions, acceptance checks and stopping condition. Verify its actual tools before assigning Fusion or GUI work. One agent owns each live Fusion or PrusaSlicer session at a time. Keep ordinary workers as leaves and preserve others' edits.

For example, ask `Use print3d to compare the proposed carrier against the approved NX3 interface, then use automation to verify the exported STL and scratch slices. Keep app edits serialized.` Main can keep tightly coupled CAD and preview iterations local. Printer transfer, firmware changes and print start require authorization covering those actions.

## Lessons from the NX3 crab study

The NX3 study reused the approved Sorcerer ear and crown receivers for 6 × 3 mm magnets. Separate keyed carriers kept the mounts behind the flat decorative faces. The nominal assembly exposed interference between the ear faces and the center mount, which was resolved by trimming the artwork at the lower inside corners. The original pocket geometry stayed at source scale.

The study's seven STLs passed digital mesh checks. PrusaSlicer 2.9.7 on Windows crashed when its CLI loaded the full saved Cosmetic Parts and Functional Parts INIs. Scratch profiles using their geometry settings allowed slicing and layer review. The narrow mounts cleared the slicer's bed-adhesion warnings with a 4 mm outer brim in that check. Physical fit, bonding and retention remain unverified.

### Recommended next improvements

1. **Record the approved interface once.** Add a small per-family manifest for source paths and hashes, pocket counts and axes, assembly poses, expected clearance and attribution. Start with NX3. Have builders and validators read it, so decorative variants share the same mounting evidence.
2. **Automate the digital checks.** Give each scripted project a documented build and validation entry point. Reuse checks for reloaded STL solids, source-interface differences and nominal assembly collisions. Run the inexpensive geometry checks first, then render the changed views and slice the affected parts. Publish verified exports per revision when authorized.
3. **Make slicer checks reproducible.** Add a versioned geometry-only slicer profile or a repeatable export of the effective settings. Record the nozzle, layer heights, orientation, brim, support settings and layer evidence. Keep machine-specific startup code and physical-printer configuration local.
4. **Refine the existing skills before adding roles.** Extend `fusion-print-design` to cover preserving approved interfaces in scripted CAD and extend `voron-print-preflight` with the isolated CLI fallback. Use `print3d` for fit and source geometry, `automation` for repeatable checks, and `reviewer` when a mounting change merits independent review. Verify tool access and the coordination ledger before dispatch.

## Rebuild scripted models

Use Python 3.12 and uv. From the workspace root, prepare a local environment.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r Projects/sorcerer_ears_CAD_STL_v2/CAD/requirements.txt
.\.venv\Scripts\Activate.ps1
```

If the configured uv cache is inaccessible, add `--no-cache` immediately after `uv`. Run builds in a scratch copy when comparing revisions because the scripts update generated files.

### Crab ears

From `magnetic_treasure_crab_ears_v3/`, run the build and validator in order.

```powershell
python cad/build_crab_v3.py
python analysis/validate_v3.py
```

Inspect `validation_report.json`, including its `failures` array.

### Sorcerer ears

From `Projects/sorcerer_ears_CAD_STL_v2/`, run the build and validator in order.

```powershell
python CAD/build_reference_mounts.py
python CAD/check_and_position.py
```

Inspect `validation_results.json` and confirm its status. Keep each mounting family's parts together and preserve original coordinates for multipart color exports.

Optional Blender rendering commands are listed in the workflow guide.

## Prepare a Voron print

Launch `C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe`. Installed presets are in `C:\Users\vic-l\AppData\Roaming\PrusaSlicer`.

1. Select the `VictorCustom` printer and the appropriate print and filament presets. The saved printer profile specifies Klipper, a 0.5 mm nozzle and a 350 × 350 × 320 mm envelope. Confirm the actual nozzle and usable volume.
2. Review the layers for thin details, continuous walls, unsupported islands, bridges and first-layer adhesion. Review imported 3MF printer settings and custom G-code.
3. Before a physical run of a tolerance-critical part, test a fit coupon or mount strip in the intended material and settings. For digital-only work, record the physical fit check as pending.
4. Save the configured project as 3MF and export reviewed G-code. Printer transfer and print start are separate actions.

The printer's SSH endpoint is `192.168.1.37`. Use it for authorized diagnostics. Keep credentials and physical-printer secrets out of shared project files.

## License

Original code and documentation are licensed under [MIT](LICENSES/MIT.txt). Original CAD designs, models and renders are licensed under [CC BY-NC-SA 4.0](LICENSES/CC-BY-NC-SA-4.0.txt). See [LICENSE](LICENSE) and the [third-party source index](LICENSES/THIRD-PARTY.md) for scope and asset-specific attribution.

## Contributions and attribution

Follow [Repository Guidelines](AGENTS.md). Preserve source geometry, attribution and license notices. Read each project's attribution file before redistributing its assets. Include the affected variant, critical dimensions, validation results and relevant previews when proposing a change.
