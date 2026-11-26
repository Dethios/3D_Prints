# K2 CFS sync for PrusaSlicer 2.9.7

Save a K2 project as a 3MF and double-click **Sync K2 CFS.cmd**. Select the
project to open a new copy with the four current Moonraker assignments applied.
You can also drop a saved 3MF onto the launcher. The new copy is saved beside
the original with `- CFS synced` in the name. Review it before slicing.

The utility checks the K2's live CFS mapping and uses the order below.

| PrusaSlicer extruder | G-code tool | CFS slot |
| --- | --- | --- |
| 1 | T0 | 1A |
| 2 | T1 | 1B |
| 3 | T2 | 1C |
| 4 | T3 | 1D |

The colors come from Moonraker's shared HelixScreen and CFSail assignments.
PrusaSlicer assembles the filament settings from the installed presets, including
each preset's slice temperatures, flow, cooling, and filament G-code. The sync
preserves the project print and printer settings apart from display colors. It
also preserves model placement, object and painted assignments, and purge
settings. Installed profiles and the source 3MF are read-only inputs.

## Preset matching

The utility recognizes the installed Polymaker ASA, ASA-CF08 and Panchroma
Matte PLA profiles. For a spool with no matching rule, set its installed profile
once in `spool-presets.json`. The filament preset must be saved locally as a
standalone preset. The mapping includes the exact Moonraker material to catch a
Spoolman record that was later edited. For example, the current spool #1 could
be mapped as follows.

```json
{
  "1": { "material": "PLA", "preset": "Polymaker PolyChroma Matte" }
}
```

The sync uses the inventory currently in the CFS. A saved design can use
different colors and different materials than the spools currently assigned.
Check the part colors and materials in the synced plate before slicing or printing.

## Command line

Use `sync_k2_cfs.py PROJECT.3mf` to create a copy without opening it. Add
`--open` to open it. `--help` lists the output, Moonraker and data-folder
overrides. The launcher uses the workspace's Python 3.12 environment.
