# Printer files

- [Rewiring](rewiring/README.md) lists the PUG glands, mounting options and other wiring parts with their source status.
- A4T AFC cutter part (local `mod-parts/a4t-afc-cutter/`): loose cutter arm base STL. Exact source not recorded.
- Flow calibration (local `calibration/flow/`): VictorCustom 3MFs and previously generated G-code. Confirm the intended printer, nozzle and material before use.
- Hexagon test pattern (local `test-patterns/`): standalone 3MF. The Chube cowling plate is with the [Chube project](../Projects/Chube_Hotend_Integration/README.md).

## Creality K2

Stock Costco hardware with one four-slot Creality Filament System (CFS) and four bundled Unicorn nozzle sizes, 0.2, 0.4, 0.6 and 0.8 mm. The printer reported a configured 0.4 mm nozzle during the November 22, 2026 inspection. Check the physical nozzle before slicing. See [K2 slicing and CFS printing](../PRINT_WORKFLOW.md#slice-and-print-on-the-creality-k2-with-cfs).

| LAN service | Address |
| --- | --- |
| Mainsail dashboard and saved PrusaSlicer Moonraker host | `http://192.168.1.246:4409` |
| Fluidd dashboard | `http://192.168.1.246:4408` |
| Direct Moonraker API | `http://192.168.1.246:7125` |

### Installed printer software

Inventory checked November 22, 2026 against the Helper Script manifest, Moonraker and printer processes.

| Software | Installed features and observed state |
| --- | --- |
| K2 Helper Script | Update Manager reported `v2.2.0-0`. The manifest includes Moonraker Extensions and the Updatable Moonraker option, Entware, Git Backup and Klipper G-code Shell Command. |
| Klipper macros | The manifest lists KAMP-K2 adaptive meshing and line purge, fan controls, useful macros, Z-offset macros, M600 support and improved shaper calibration. KAMP objects, line purge, object exclusion and shaper macros were visible in Klipper. |
| Web and API | Mainsail `v2.19.0`, Fluidd `v1.30.0` and upstream Moonraker `v0.11.0-4-gb559b9a`. All three ports reported Klipper ready with zero failed Moonraker components. Moonraker Timelapse was loaded and Klipper exposed its macros. |
| Camera and touchscreen | Helper Script Camera Support and HelixScreen are installed. HelixScreen, uStreamer and go2rtc were running. The dashboard camera uses the shared uStreamer feed and the Mainsail snapshot endpoint returned a JPEG. |
| Remote clients | OctoEverywhere and Mobileraker Companion were running. Update Manager listed Mobileraker `v0.0.0-1`. Remote client access was outside this check. |

The CFS is part of Creality's printer configuration. Moonraker reported one connected CFS unit. Verify the actual filament and slot assignments at the printer before a job.
