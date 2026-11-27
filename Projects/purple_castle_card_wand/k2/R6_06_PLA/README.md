# Castle card wand R6 · K2 0.6 mm PLA trials

These PrusaSlicer 2.9.7 projects use one Creality K2 0.6 mm Unicorn nozzle and one four-slot CFS. Load the four spools in the order below for every plate and leave them in those positions. The six production and coupon projects use the exact R6 meshes, part alignment and build transforms from the [0.4 mm ASA projects](../R6/).

**Start with the swatches. The face-up star field is red-dominant in the verified toolpaths, even though its purple recipe alternates red and blue through the print.** ColorMix alternates physical materials by layer. It can produce a different apparent color on closely spaced side or slope bands, depending on the spools, light and viewing distance. A horizontal surface may show the color of its highest layer. [Prusa ColorMix documentation](https://help.prusa3d.com/pl/article/colormix_1210432)

## Load the CFS

| Slot | PrusaSlicer extruder | K2 tool | Spool |
| --- | ---: | --- | --- |
| A / T1A | 1 | `T0` | Creality Hyper PLA Blue |
| B / T1B | 2 | `T1` | Creality Hyper PLA Red |
| C / T1C | 3 | `T2` | Creality Hyper PLA White |
| D / T1D | 4 | `T3` | Polymaker PolyLite PLA Pro Metallic Gold |

| Target | Embedded recipe | Assignment |
| --- | --- | --- |
| Purple | 50% red, 50% blue | Main star field, lip, rear, frame, grip core and fit coupons |
| Pink | 25% red, 75% white | Separate bow |
| Light blue | 25% blue, 75% white | Three castle roofs |
| White | 100% white | Main castle, cornices, two twinkles and Mickey artwork |
| Metallic gold | 100% gold | Rim, three pennants, scrolls and three grip bands |

The display chips are recipe labels. Use the actual swatches to decide whether the visible colors work for you.

## Suggested order and plate estimates

| Order | Project | Physical tools used | Slicer estimate | Swaps | Estimated part and adhesion material |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | [Flat, upright and sloped swatches](K2_06_PLA_Castle_R6_ColorMix_Swatches.3mf) | A, B, C, D | 24m 28s | 67 | 4.62 g |
| 2 | [Slot and thread coupon](K2_06_PLA_Castle_R6_Slot_and_Thread_Coupon.3mf) | A, B | 2h 15m 18s | 141 | 25.90 g |
| 3 | [Castle star face](K2_06_PLA_Castle_R6_Star_Face.3mf) | A, B, C, D | 3h 22m 50s | 95 | 43.26 g |
| 4 | [Rear shell](K2_06_PLA_Castle_R6_Rear_Shell.3mf) | A, B | 1h 48m 8s | 49 | 27.25 g |
| 5 | [Pocket frame](K2_06_PLA_Castle_R6_Pocket_Frame.3mf) | A, B | 49m 19s | 13 | 11.96 g |
| 6 | [Threaded grip](K2_06_PLA_Castle_R6_Threaded_Grip.3mf) | A, B, D | 4h 3m 26s | 219 | 47.61 g |
| 7 | [Pink bow](K2_06_PLA_Castle_R6_Pink_Bow.3mf) | B, C | 29m 22s | 29 | 5.92 g |

The slicer estimates cover toolpath time and modeled extrusion. Firmware CFS cuts, loads and chute purges add real time and material. Time several changes on the swatch to estimate the overhead for a full plate. The swap counts exclude initial filament selection.

Three alternate plates trade a purple recipe for solid blue through the body. The [blue rear](K2_06_PLA_Castle_R6_Rear_Shell_Solid_Blue.3mf) and [blue frame](K2_06_PLA_Castle_R6_Pocket_Frame_Solid_Blue.3mf) run entirely from A, each with zero swaps. The [blue and gold grip](K2_06_PLA_Castle_R6_Threaded_Grip_Solid_Blue.3mf) uses A and D and still makes 147 swaps. Repeat the mechanical fit and retention checks with the material combinations selected for the wand.

## Swatches and appearance

The three pairs are purple on the left, pink in the middle and light blue on the right. Compare the flat tops, the wide upright sides and the 18° purple slope at the far right. The metallic gold sample is closest to the front edge. The upright samples deposited 18 blue and 18 red layers for purple, 9 red and 27 white for pink, and 9 blue and 27 white for light blue. The three flat tops ended in blue, white and white respectively. The 18° sample exposes 26 alternating red and blue bands in the center scan, with a median projected band width of 0.37 mm. Check color and purge carryover under the intended lighting. [Slope physical-tool projection](Purple_Slope_Physical_Tools.png)

On the [face physical-tool projection](Star_Face_Physical_Tools.png), about 91% of the broad star field is topped by red and 99% of the inner lip by blue. The curved roofs are about 69–72% white from above, with blue contour bands. The [bow physical-tool projection](Pink_Bow_Physical_Tools.png) shows red and white bands across the curved surfaces. These percentages approximate topmost extrusion coverage. The projection uses representative spool colors and omits light and purge effects. Tilting the whole front 18° would lift one side roughly 40–43 mm, depending on the axis, and change support against the flat card-contact and bond face. The finished plates retain the flat fit-coupon orientation.

## Effective settings and fit checks

The projects resolve the installed `Creality K2 (0.6 mm)` print and printer presets in PrusaSlicer 2.9.7. Embedded PLA values start at 215°C nozzle and 60°C bed, then run at 210°C and 55°C. Every slot uses a 6 mm³/s ceiling and 1.00 starting extrusion multiplier. PLA fan ramps from off on the first layer to 65% on layer four with up to 100% for cooling and bridges. The 0.6 mm preset's 0.62 mm nominal line width and 0.72 mm first-layer width are paired with 0.12 mm layers and a 0.20 mm first layer. Brims are 4 mm on most plates, 6 mm on the grip and 3 mm on the swatches. The material names identify embedded trial settings. [Creality Hyper PLA temperature guidance](https://store.creality.com/blogs/all/troubleshooting-3d-print-stringing-guide) · [Polymaker Metallic PLA Pro](https://shop.polymaker.com/collections/polylite-series/products/polylite-metallic-pla-pro?variant=41019989819449)

Each project reopened and sliced with zero CLI warnings. The [preflight report](preflight.json) records settings, mesh hashes, first-layer contact, bridge and support paths, recipes and actual physical tool commands. Three gold flags each deposit across 17 layers and reach roughly 97% of the source profile in the broadest layer. The cap bridges in the front and rear necks use moves up to 7.59 mm. There is light build-plate-only support at the entrance of the front and rear split threads, including their coupons. It stays within 2 mm of the thread axis in X and stops near assembly Y −68 mm, ahead of the seated card edge at −57.75 mm. Remove the support and brim while both halves are open. Clear thread chips, sagging bridge strands and residue before fitting the card or bonding. Wipe tower and slicer priming are disabled. The emitted K2 startup selects the physical tool and waits for temperature before the printer's line purge.

Use the [R6 assembly and coupon instructions](../../cad/R6/README.md) with a PLA-compatible bond. An adult should fit the exact card in the coupon, test the thread by hand, then check full-size card retention and release, grip loosening, bond and bow retention, drop resistance and card reading. Complete those physical tests before a child handles the prototype. CFS swap quality, printed colors, material fit and durability still need a physical trial.

## Rebuild the local plates

From the repository root, use the existing CAD Python environment.

```powershell
$plates = 'Projects/purple_castle_card_wand/k2/R6_06_PLA'
$scratch = '.coordination/r6-pla-worker'
& '.venv/Scripts/python.exe' -B "$plates/build_plates.py" --scratch $scratch --verify-end-slots --solid-blue-alternates
& '.venv/Scripts/python.exe' -B "$plates/audit_plates.py" --scratch $scratch --report "$plates/preflight.json"
```

The build and audit use the local ASA plate geometry, the repository's native 3MF and toolpath helpers, and the installed K2 and PLA base presets. G-code and logs go to the scratch directory. The audit also writes physical-tool projections there. These are local trial files.
