# 3D Print Projects

CAD sources, printable models, reference assets and validation tools for the Voron 2.4 and Creality K2.

## Printers

| Printer | Setup | Workflow |
| --- | --- | --- |
| Voron 2.4 | PrusaSlicer profiles for 0.4 mm Rapido, 0.5 mm high-flow Bozzle and 0.6 mm high-flow bimetal CHT nozzles | [Prepare a Voron print](#prepare-a-voron-print) |
| Creality K2 | Stock Costco hardware, 0.2, 0.4, 0.6 and 0.8 mm Unicorn nozzles, and one four-slot CFS | [Slice and print with CFS](PRINT_WORKFLOW.md#slice-and-print-on-the-creality-k2-with-cfs) · [Mainsail at `192.168.1.246:4409` and installed software](Printer/README.md#creality-k2) |

## Project index

| Project | Contents |
| --- | --- |
| [Sorcerer ears](Projects/sorcerer_ears_CAD_STL_v2/READ_ME_FIRST.txt) | NX3 print files, uniform-rim ears and 3D center hats, plus CAD and source references for the NX3 and Tim J mounting families. Generate the Tim J STLs before slicing that family. |
| [Treasure crab ears for NX3](Projects/magnetic_treasure_crab_ears_NX3/README.md) | Integrated five-pocket ear carriers, a matched three-pocket crown base and eye unit, a Voron 3MF, and digital validation reports. |
| [Small-arm clamp adapter](Projects/small_arm_40x40_clamp_adapter/README.md) | CAD source, STEP and STL for an 18 × 18 mm holder on a 40 × 40 mm clamp. Physical assembly fit is pending. |
| [Chube hotend integration](Projects/Chube_Hotend_Integration/README.md) | A4T cowling adaptation for the Chube Air UHF and CW2/Tap, with source references and print files. |
| [Sorcerer hat](Projects/sorcerer_hat/README.md) | Standalone hat with separate moon and star geometry. |
| [Container lid](Projects/container-lid/README.md) | Original replacement lid STL. |

The earlier magnetic treasure crab ears v3 kit is in Git history at `a9a95b8`. It uses its own receivers.

## Model library and printer files

| Folder | Contents |
| --- | --- |
| [Printables downloads](Printables/README.md) | Downloaded models grouped by listing, with maker notes and original filenames. |
| [GitHub mods](GitHub-Mods/README.md) | Index of the separate A4T, A4Tv2 and whopping Voron mods checkouts. |
| [Printer files](Printer/README.md) | K2 software inventory, [rewiring parts](Printer/rewiring/README.md), cutter and [Voron roller](Printer/mod-parts/voron2-roller/) mods, test patterns and [ASA-CF08 Bozzle flow calibration](Printer/calibration/flow/ASA-CF08%20Bozzle/README.md). |
| [Star Wars source notes](Unverified-Downloads/README.md) | Candidate download pages, maker instructions, license evidence and local plate contents. |
| [Migration records](Migration/2026-11-10/README.md) | Import manifests, source-path records and the rewiring reorganization. |

### Local workspace projects and files

- `Projects/mulan_openwork_ears_NX3/` contains the Mulan lithograph-relief ear study, its artwork and source notes, CAD scripts, a single-extruder print plate and a separate color review plate. Start with its local `README.md`.
- The workspace also holds Sorcerer NX3 relief studies and K2 plates, alternate small-arm plates, and the downloaded Multifunction Arm mounting system. These files are local to the workstation.

## Choose a design pathway

- **Autodesk Fusion and Fusion MCP** support interactive CAD design, dimensions and assembly inspection. Preserve the editable design reference and export STEP and print meshes.
- **CadQuery** supports scripted geometry, reproducible builds and parameter variants. Edit the existing generator when revising a scripted project.
- **PrusaSlicer** handles orientation, supports, layer inspection and G-code for both printers. Use the matching machine and nozzle preset. The K2 presets support CFS slot assignment and multicolor preview.
- **Blender is optional** for rendered previews using the included scripts. Use an assembly view or a render from generated geometry when appearance and placement need review.

See [CAD and Print Workflow](PRINT_WORKFLOW.md) for detailed pathway selection and print checks.

### Illustration to CAD

Start with supplied or generated artwork and a dimensioned front-view guide from the carrier. Fit the illustration inside the available field, review it at print size, and record the selected file and hash. Hand CAD the editable contours, region masks, or relief inputs with their scale and placement. Use the [Printable Art Design skill](.agents/skills/printable-art-design/SKILL.md) for the handoff and optional local ComfyUI procedure.

The Mulan NX3 study in `Projects/mulan_openwork_ears_NX3/` is a local example. Its `artwork/SOURCES.md` records the references and their roles. Its `previews/reference_comparison.png` shows the fitted illustration, existing STL relief, and paint guide side by side. Use the geometric relief and the target printer's toolpaths to evaluate printed detail.

## Codex skills and agent operations

Project skills live in `.agents/skills/`. Open a new Codex session in this workspace after adding them, so the client can discover them. They support automatic selection when relevant and explicit invocation using `$skill-name`. If the current client has not refreshed its skill list, ask it to read the linked `SKILL.md` directly.

| Skill | Use | Example prompt |
| --- | --- | --- |
| [fusion-print-design](.agents/skills/fusion-print-design/SKILL.md) | Fusion MCP modeling, assembly inspection and verified exports | `Use $fusion-print-design to revise this bracket using the supplied mating dimensions, export STEP and STL into its project folder, and report the checks.` |
| [voron-print-preflight](.agents/skills/voron-print-preflight/SKILL.md) | Geometry, saved Voron presets, layer review and physical fit evidence | `Use $voron-print-preflight on the Crab NX3 fit strip with the installed Voron nozzle and intended filament. Report warnings and pending checks.` |
| [k2-cfs-preflight](.agents/skills/k2-cfs-preflight/SKILL.md) | K2 presets, four-slot assignments, layer preview and startup and shutdown G-code | `Use $k2-cfs-preflight to check this plate against its intended nozzle and CFS slots.` |
| [printable-art-design](.agents/skills/printable-art-design/SKILL.md) | Illustration generation and review, editable print artwork, and CAD handoff | `Use $printable-art-design to fit this supplied illustration to the approved carrier and prepare its editable CAD inputs.` |

Fusion MCP, local executables and app access must be available to the executing agent. For a new Fusion design, use the design skill through export, then use the target printer's preflight skill. For existing scripted projects, rebuild with CadQuery and its validator before preflight. Physical fit results belong with the part revision and selected settings.

### Worker assignments

Repo profiles live in [`.codex/agents/`](.codex/agents/). Use a fresh trusted local Codex session to pick up the repo roster and instructions. Main proactively delegates substantial independent work and supplies an explicit supported model and effort from each profile's routing guidance. On clients that expose only installed global roles, use the fallback with the repo profile's assignment instructions. [OpenAI custom agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)

| Repo role | Assignment inputs and acceptance | Installed fallback |
| --- | --- | --- |
| [`print-inspector`](.codex/agents/print-inspector.toml) | Compare the actual exports to the exact approved interface and revision. Return measured deviations, mesh evidence, interference and pending physical checks. | `explorer` for inspection, `reviewer` for independent fit review |
| [`print-cad-designer`](.codex/agents/print-cad-designer.toml) | Verify the selected artwork revision and placement for illustration-led designs. Use the owning project generator or identified Fusion design and mating files. Return editable source, regenerated exports and geometry validation. | `print3d` |
| [`print-art-designer`](.codex/agents/print-art-designer.toml) | Use scoped visual references, the dimensioned envelope, and keepouts. Return the exact reviewed image and hash, fitted preview, editable CAD inputs, placement and feature measurements, and unresolved defects. | `adaptive_worker` |
| [`print-process-specialist`](.codex/agents/print-process-specialist.toml) | Use the actual printer, nozzle, material and model revision. Return toolpath evidence, effective settings, CFS mapping when applicable and pending physical checks. | `print3d` |

For each assignment, main records the objective, literal input and exclusive output paths, prerequisites, authorized actions, live tool access, time and retry limits, and the acceptance check. Use an empty write scope for read-only inspection and a verified worktree for complex independent writers. Serialize access to each live Fusion or PrusaSlicer session. Match checks to the actual project, using the [documented build and validation commands](PRINT_WORKFLOW.md#rebuild-and-preview) in an owned worktree or scratch copy when they overwrite files. Main owns the local ledger at `.coordination/ledger.json`, integration and approvals. Printer transfer, firmware changes, print start and publication require authorization covering those actions.

For example, `Design a new NX3 ear face using the approved Sorcerer interface` can start a source-interface inspection and an artwork study in parallel once the envelope is known. The CAD worker integrates the fitted artwork, then the process specialist checks the resulting plate. Keep reusable scripts with `automation` and use `computer_use` when a visual app operation needs its own assignment.

## Rebuild scripted models

Use Python 3.12 and uv. From the workspace root, prepare a local environment.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r Projects/sorcerer_ears_CAD_STL_v2/CAD/requirements.txt
.\.venv\Scripts\Activate.ps1
```

If the configured uv cache is inaccessible, add `--no-cache` immediately after `uv`. Run builds in a scratch copy when comparing revisions because the scripts update generated files.

| Project | Commands from the project directory | Evidence to review |
| --- | --- | --- |
| Sorcerer ears, base mounting families | Run `python CAD/build_reference_mounts.py`, then `python CAD/check_and_position.py`. | `validation_results.json` and the variant's assembly previews. |
| Sorcerer NX3, uniform-rim ears and 3D center hats | Choose the variant and its generator in [the print and build notes](Projects/sorcerer_ears_CAD_STL_v2/READ_ME_FIRST.txt). | The variant's `CAD/NX3/.../validation.json` and print-part coordinates. |
| Treasure crab ears for NX3 | Run `python cad/build_crab_nx3.py` with the Sorcerer ears project beside it. | `validation_report.json` and a fresh layer check of the affected parts. The checked-in `slicer_preflight.json` records the tracked plate. |
| Small-arm clamp adapter | Run `python build_adapter.py`. | STEP and reloaded STL dimensions, hole pattern, counterbores and print orientation. |

Optional Blender rendering commands are listed in the workflow guide.

## Prepare a Voron print

Launch `C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer.exe`. Installed presets are in `C:\Users\vic-l\AppData\Roaming\PrusaSlicer`.

1. Select the installed nozzle's printer profile and matching `Voron PIF - … mm` print preset, then select the intended filament. The saved printer profiles specify Klipper and a 350 × 350 × 320 mm configured envelope. Some existing 3MFs embed a `VictorCustom` profile. Check the selected settings against the installed nozzle and usable volume.
2. Review the layers for thin details, continuous walls, unsupported islands, bridges and first-layer adhesion. Review imported 3MF printer settings and custom G-code.
3. Before a physical run of a tolerance-critical part, test a fit coupon or mount strip in the intended material and settings. For digital-only work, record the physical fit check as pending.
4. Save the configured project as 3MF and export reviewed G-code. Printer transfer and print start are separate actions.

The printer's SSH endpoint is `192.168.1.37`. Use it for authorized diagnostics. Keep credentials and physical-printer secrets out of shared project files.

## License

Original code and documentation are licensed under [MIT](LICENSES/MIT.txt). Original CAD designs, models and renders are licensed under [CC BY-NC-SA 4.0](LICENSES/CC-BY-NC-SA-4.0.txt). See [LICENSE](LICENSE) and the [third-party source index](LICENSES/THIRD-PARTY.md) for scope and asset-specific attribution.

## Contributions and attribution

Follow [Repository Guidelines](AGENTS.md). Preserve source geometry, attribution and license notices. Read each project's attribution file before redistributing its assets. Include the affected variant, critical dimensions, validation results and relevant previews when proposing a change.
