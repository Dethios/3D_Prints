---
name: k2-cfs-preflight
description: Validate a Creality K2 PrusaSlicer plate or G-code using its nozzle-matched presets and four-slot CFS. Use for single-slot or multicolor setup, multipart alignment, toolpath checks and verification of K2 start and end macros.
---

# K2 CFS Preflight

1. Follow the [K2 workflow](../../../PRINT_WORKFLOW.md#slice-and-print-on-the-creality-k2-with-cfs) for the machine, current presets, slot mapping and expected G-code order. Confirm model revision, nozzle, filament and intended CFS slots. Record any physical setup that still needs confirmation.
2. Inspect the effective printer, print and filament settings, including inherited or embedded 3MF overrides and post-processing commands. Preserve installed presets. Use scratch profiles for CLI trials and consult the installed CLI help. Record any settings that differ from the installed profiles.
3. Preserve aligned multipart coordinates and verify color, support and brim assignments in the actual sliced preview. Check adhesion, thin features, islands, bridges and color boundaries. When changing a profile that affects slot handling, exercise a four-slot plate plus single-slot plates using the first and last slots.
4. Inspect exported G-code for the intended tool selections and the expected start, purge and end sequence. Verify wipe tower and slicer priming settings against the K2 workflow. If delivering a saved plate, reopen it and verify the embedded settings and assignments before slicing again.
5. Report slicer version, selected presets, actual tool sequence, saved artifacts, warnings and pending physical checks. Any printer transfer, print start or firmware action requires authorization covering it.
