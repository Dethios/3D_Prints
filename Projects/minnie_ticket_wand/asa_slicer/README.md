# Minnie ticket wand ASA plates

Use PrusaSlicer 2.9.7 and the K2 with its 0.4 mm Unicorn nozzle. Use **File → Open Project** to retain the embedded settings, multipart geometry and ColorMix assignments. The virtual recipes are stored in the project and borrow only the two loaded filaments below. [Prusa ColorMix instructions](https://help.prusa3d.com/article/colormix_1210432)

| CFS slot | Physical G-code tool | Filament |
| --- | --- | --- |
| A / 1 | T0 | Galaxy Red ASA (#BF1A11) |
| B / 2 | T1 | Unused |
| C / 3 | T2 | White ASA (#DBD7D6) |
| D / 4 | T3 | Galaxy Black ASA (#212721) |

The physical spools and printer may display different names from the common **Polymaker ASA** settings used for all three. The second slicer channel is a preset placeholder.

## Color swatch

The swatch compares vertical walls at 25% red / 75% white on the left and 50% red / 50% white on the right. The small black tile exercises Black-to-light purge transitions. View the broad upright faces for color, at the distance that matters for the wand. Each panel includes a 3 mm solid-white dot. Their horizontal tops show the final physical layer. Both solid-white dots had T2 paths on all 25 intersecting layers.

Check the pink shade, white carryover, ASA adhesion and the first CFS swap on the swatch. Production uses the lighter 25:75 blend as a starting point. If the 50:50 swatch looks better, edit virtual extruder #5 to 50:50 in the coupon, handle and bow projects and preview them again. The physical White assignments remain available as extruder #3.

## Plate order

| Project | What to check | Slicer estimate | Tool changes |
| --- | --- | --- | ---: |
| [ColorMix swatches](K2_04_ASA_ColorMix_Swatches.3mf) | Pink shade, white dots and CFS flush | 13m 33s | 61 |
| [Card and thread coupon](K2_04_ASA_Card_and_Thread_Coupon.3mf) | Card insertion and handle closure on the short assembly | 1h 40m 15s | 105 |
| [Black shells](K2_04_ASA_Black_Shells.3mf) | Insides face the bed, rounded front and rear exteriors face up | 6h 21m 39s | 0 |
| [Black spacer and pins](K2_04_ASA_Black_Spacer_and_Pins.3mf) | Flat spacer, two upright pins | 1h 12m 29s | 0 |
| [Pink handle](K2_04_ASA_Pink_Handle.3mf) | Grip lies along its rear chord, support under the exposed connector | 1h 32m 36s | 66 |
| [Pink bow with white dots](K2_04_ASA_Pink_Bow_White_Dots.3mf) | Upright face, 8 mm brim and build-plate support | 1h 26m 6s | 163 |

Print the swatches and the fit coupon first. Remove the coupon's brims and supports, hold the three black pieces in their assembly positions, then test your actual card and the closure. Check that the handle threads easily, the sleeve reaches its stop, and the card moves freely. The times and model weights in the verification report exclude firmware-managed CFS flushes.

## Effective print settings and checks

All plates use 0.12 mm layers, a 0.20 mm first layer, 260 °C nozzle on the first layer and 250 °C thereafter, a 95 °C bed, and fan off. Actual extrusion speeds were at most 25 mm/s on all first layers and 50 mm/s overall. The local Polymaker ASA preset supplied a 0.94 extrusion multiplier. Polymaker lists a 0.6 mm or larger nozzle as an option for additional Galaxy clog margin. [Polymaker Galaxy ASA settings](https://shop.polymaker.com/products/polymaker-galaxy-asa)

All six projects were reopened by the PrusaSlicer 2.9.7 command-line slicer and sliced with zero warning stanzas. The physical tool stream used only the mapped slots. The output labeled objects before `START_PRINT`, selected the initial tool before the temperature wait and purge, reset extrusion after the purge, and ended with `END_PRINT`. The projects disable the wipe tower and slicer priming.

The solid Black shells retained short bridges around the pin seats and neck, with a longest bridge segment of 8.55 mm including its anchors. The handle and coupon bridge transversely below the connector, with bridge segments up to 5.95 mm on the handle. Sampled support paths stayed clear of the nominal sleeve void. The long overhang along the handle's rear chord overlaps the initial brim in projection, so check after trimming the brim.

The bow's 14 White dots each have only T2 paths in the printable-width sections, with no missing or unsupported White path flags. The upright geometry has roughly 8.9 mm² of first-layer bead area before its brim and supports. Inspect that first layer, both wings and support removal on the backside. Printed shade, purge cleanliness, adhesion and joint fit remain physical checks.

See [preflight.json](preflight.json) for the source and 3MF SHA-256 records and per-plate toolpath evidence. [build_plates.py](build_plates.py) rebuilds the native projects using the current local K2 and ASA presets and the adjoining CAD STLs. [inspect_gcode.py](inspect_gcode.py) audits a CLI export against its input project. The raw trial exports are local scratch files.

