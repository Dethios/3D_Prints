# 3D Print Projects

CAD sources, printable models, reference assets and validation tools for projects intended for a Voron 2.

## Projects

| Folder or file | Contents |
| --- | --- |
| [Magnetic treasure crab ears](magnetic_treasure_crab_ears_v3/README.md) | CadQuery source, STEP solids, STL parts, adapters, fit coupons and validation tools. |
| [Sorcerer ears](sorcerer_ears_CAD_STL_v2/READ_ME_FIRST.txt) | NX3 and TimJ mounting variants, editable source, STEP/STL exports, fit strips and previews. |
| `polymaker-refill-spool/` | Spool STEP and STL assets. |
| `watch-5-5-pro-6-7-ultra-charging-stand.stl` | Standalone charging-stand mesh. |
| `todolist_without_amsorcaslicer.3mf` | Existing slicer project. Check its embedded settings before using it with the Voron. |

## Choose a design pathway

- **Autodesk Fusion and Fusion MCP** support interactive CAD design, dimensions and assembly inspection. Preserve the editable design reference and export STEP and print meshes.
- **CadQuery** supports scripted geometry, reproducible builds and parameter variants. Edit the existing generator when revising a scripted project.
- **PrusaSlicer** is the main slicer for orientation, supports, layer inspection and G-code generation.
- **Blender is optional** for rendered previews using the included scripts. Fusion and PrusaSlicer provide the normal design-to-print workflow. Blender is currently uninstalled.

See [CAD and Print Workflow](PRINT_WORKFLOW.md) for detailed pathway selection and print checks.

## Codex skills and agent operations

Project skills live in `.agents/skills/`. Open a new Codex session in this workspace after adding them so the client can discover them. They support automatic selection when relevant and explicit invocation using `$skill-name`. If the current client has not refreshed its skill list, ask it to read the linked `SKILL.md` directly.

| Skill | Use | Example prompt |
| --- | --- | --- |
| [fusion-print-design](.agents/skills/fusion-print-design/SKILL.md) | Fusion MCP modeling, assembly inspection and verified exports | `Use $fusion-print-design to revise this bracket using the supplied mating dimensions, export STEP and STL into its project folder, and report the checks.` |
| [voron-print-preflight](.agents/skills/voron-print-preflight/SKILL.md) | Geometry, saved Voron presets, layer review and physical fit evidence | `Use $voron-print-preflight on magnetic_treasure_crab_ears_v3/stl/magnet_fit_coupon.stl with my VictorCustom printer and actual filament. Report warnings and pending checks.` |

Skills guide the available tools. Fusion MCP, local executables and app access must be available to the executing agent. For a new Fusion design, use the design skill through export, then the preflight skill through local slicing and layer review. For existing scripted projects, rebuild with CadQuery and its validator before preflight. Physical fit results belong with the part revision and selected settings.

Main owns integration and chooses installed roles according to the current global `agents/*.toml` files. Assign only independent work that benefits from delegation, using explicit supported model and effort settings from those roles.

| Installed role | Recommended operation | Expected evidence |
| --- | --- | --- |
| `print3d` | CAD dimensions, tolerances, materials, orientation and fit decisions | Critical measurements, assumptions, interface checks and proposed coupon |
| `automation` | Reusable CadQuery builds, validation and local slicing helpers | Commands, exit status, report contents and output paths |
| `computer_use` | Supported Fusion or PrusaSlicer UI operations | Observed target document, layer inspection and saved project path when requested |
| `reviewer` | Independent review of consequential mounting, load or tolerance changes | Findings tied to source geometry, changes and validation evidence |

Give each worker an objective, input paths, owned files or application session, allowed actions, acceptance checks and stopping condition. Verify its actual tools before assigning Fusion or GUI work. One agent owns each live Fusion or PrusaSlicer session at a time. Keep ordinary workers as leaves and preserve others' edits.

For example, ask `Use print3d with $fusion-print-design for the bracket, then use reviewer to inspect its critical dimensions and export evidence. Keep Fusion edits serialized.` Main can perform small tasks directly. Printer transfer, firmware changes and print start require authorization covering those actions.

## Rebuild scripted models

Use Python 3.12 and uv. From the workspace root, prepare a local environment.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r sorcerer_ears_CAD_STL_v2/CAD/requirements.txt
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

From `sorcerer_ears_CAD_STL_v2/`, run the build and validator in order.

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
3. Print a fit coupon or mount strip for tolerance-critical interfaces. Use the intended material and settings and record the result.
4. Save the configured project as 3MF and export reviewed G-code. Printer transfer and print start are separate actions.

The printer's SSH endpoint is `192.168.1.37`. Use it for authorized diagnostics. Keep credentials and physical-printer secrets out of shared project files.

## License

Original code and documentation are licensed under [MIT](LICENSES/MIT.txt). Original CAD designs, models and renders are licensed under [CC BY-NC-SA 4.0](LICENSES/CC-BY-NC-SA-4.0.txt). See [LICENSE](LICENSE) for scope, attribution and third-party exceptions. Retain asset-specific source notices when sharing models or derivatives.

## Contributions and attribution

Follow [Repository Guidelines](AGENTS.md). Preserve source geometry, attribution and license notices. Read each project's attribution file before redistributing its assets. Include the affected variant, critical dimensions, validation results and relevant previews when proposing a change.
