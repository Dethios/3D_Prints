# Castle card wand R6 · split-nozzle K2 PLA plates

Start with the gold-free **0.4 mm** swatch and coupon. Print the 0.4 mm bow, rear and frame in the same session, then make one change to **0.6 mm** for the star face and grip. The face and both grip variants contain Metallic Gold. Use the embedded nozzle-matched PrusaSlicer 2.9.7 project settings.

**The front still prints face-up and its broad star field is red-dominant.** The flatter field and raised lip expose different top layers. The finer 0.4 mm swatch changes the band spacing on its slope and sides. The tops of the flat samples still show a single spool. [Front physical-tool projection](../R6_06_PLA/Star_Face_Physical_Tools.png) · [Prusa ColorMix documentation](https://help.prusa3d.com/pl/article/colormix_1210432)

## CFS load order

| CFS slot | Tool | Spool |
| --- | --- | --- |
| A / T1A | `T0` | Creality Hyper PLA Blue |
| B / T1B | `T1` | Creality Hyper PLA Red |
| C / T1C | `T2` | Creality Hyper PLA White |
| D / T1D | `T3` | Polymaker PolyLite PLA Pro Metallic Gold |

The purple recipe is 50% red and 50% blue, the pink is 25% red and 75% white, and the light blue is 25% blue and 75% white. The front uses solid white for the cream shapes and solid metallic gold for the trim and flags. Slot D can stay loaded during the 0.4 mm session. All seven 0.4 mm plates use only A through C.

## 0.4 mm first

| Order | Plate | Slots | Layer height | Slicer time | Swaps |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | [ColorMix swatches](K2_04_PLA_Castle_R6_ColorMix_Swatches.3mf) | A, B, C | 0.10 mm | 29m 46s | 75 |
| 2 | [Slot and thread coupon](K2_04_PLA_Castle_R6_Slot_and_Thread_Coupon.3mf) | A, B | 0.12 mm | 2h 47m 4s | 141 |
| 3 | [Rear shell](K2_04_PLA_Castle_R6_Rear_Shell.3mf) | A, B | 0.10 mm | 2h 50m 52s | 59 |
| 4 | [Pocket frame](K2_04_PLA_Castle_R6_Pocket_Frame.3mf) | A, B | 0.10 mm | 1h 17m 51s | 16 |
| 5 | [Pink bow](K2_04_PLA_Castle_R6_Pink_Bow.3mf) | B, C | 0.10 mm | 51m 10s | 35 |

The [solid-blue rear](K2_04_PLA_Castle_R6_Rear_Shell_Solid_Blue.3mf) and [solid-blue frame](K2_04_PLA_Castle_R6_Pocket_Frame_Solid_Blue.3mf) each use A with zero swaps.

On the swatch plate, the flat and upright pairs run left to right as purple, pink and light blue. The 18° purple wedge sits at far right. Its center scan shows 32 alternating bands with a median projected width of about 0.33 mm. The comparable 0.12 mm trial had 26 bands at about 0.37 mm. The 0.10 mm upright purple swatch alternates roughly evenly, with 22 blue and 21 red layers. Pink and light blue each have 11 layers of the darker spool and 32 white layers. The flat tops end entirely in blue, white and white. Compare under the intended lighting before printing the main pieces. [Slope physical-tool projection](Purple_Slope_Physical_Tools.png) · [Bow physical-tool projection](Pink_Bow_Physical_Tools.png)

## 0.6 mm after the nozzle change

| Order | Plate | Slots | Layer height | Slicer time | Swaps |
| ---: | --- | --- | ---: | ---: | ---: |
| 6 | [Star face](../R6_06_PLA/K2_06_PLA_Castle_R6_Star_Face.3mf) | A, B, C, D | 0.12 mm | 3h 22m 50s | 95 |
| 7 | [Threaded grip](../R6_06_PLA/K2_06_PLA_Castle_R6_Threaded_Grip.3mf) | A, B, D | 0.12 mm | 4h 3m 26s | 219 |
| 7 alternate | [Solid-blue grip with gold bands](../R6_06_PLA/K2_06_PLA_Castle_R6_Threaded_Grip_Solid_Blue.3mf) | A, D | 0.12 mm | 4h 3m 25s | 147 |

An [optional 0.6 mm gold-only control](../R6_06_PLA/Control_D_Gold.3mf) selects D at startup. Its sliced estimate is 3m 16s with no swaps. The manufacturer specifies a 0.4 mm minimum for this Metallic Gold filament. These plates follow the 0.6 mm choice for every gold-bearing job. [Polymaker Metallic PLA Pro](https://shop.polymaker.com/collections/polylite-series/products/polylite-metallic-pla-pro?variant=41019989819449)

Slicer estimates cover modeled toolpaths. Time CFS changes and inspect purge carryover on the swatch to estimate real elapsed time and purge use. On the 0.6 mm front, projected top coverage is about 91% red across the broad field. The inner lip is about 99% blue and the roof surfaces are 69–72% white. The front stays flat to preserve the smooth card-contact face and wide bonding lands. [0.6 mm process details](../R6_06_PLA/README.md)

## Coupon, assembly and settings

The 0.4 mm coupon uses 0.12 mm layers and bridges across the stub to keep its longest bridge move to 8.69 mm. Removable build-plate support sits around the exposed grip stub and at the front coupon's split-thread entrance, outside the card path. The rear shell, frame and bow emitted zero support paths. Clear brim, support and any bridge strands from the fit surfaces before testing.

Use the [R6 coupon and assembly guide](../../cad/R6/README.md) to check the actual card and the basic slot and thread fit. **Dry-fit the full 0.6 mm front and grip with the full 0.4 mm rear and frame before bonding.** The 0.4 mm coupon cannot establish the fit of the mixed-nozzle assembly. An adult should check the seated grip for loosening, card retention and release, bow and bond retention, drop resistance and reader operation before a child handles the wand.

The 0.4 mm projects resolve the installed `Creality K2 (0.4 mm)` presets. They use a 0.20 mm first layer, 0.42–0.45 mm nominal bead widths and a 0.50 mm first-layer width. All four recorded material vectors use 215°C/60°C for the first layer, 210°C/55°C afterward and a 6 mm³/s flow ceiling. The embedded 0.4 mm projects disable wipe tower and slicer priming. The seven 0.4 mm 3MFs reopened and sliced without warnings. Their G-code includes object polygons, the correct initial tool, temperature wait, line purge, extrusion reset and `END_PRINT`. [Preflight report](preflight.json)

To rebuild and audit locally from the repository root:

```powershell
$plates = 'Projects/purple_castle_card_wand/k2/R6_04_PLA'
$scratch = '.coordination/r6-pla-04'
& '.venv/Scripts/python.exe' -B "$plates/build_plates_04.py" --scratch $scratch
& '.venv/Scripts/python.exe' -B "$plates/audit_plates_04.py" --scratch $scratch --report "$plates/preflight.json"
```
