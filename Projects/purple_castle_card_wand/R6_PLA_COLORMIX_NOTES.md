# R6 K2 PLA ColorMix setup

Use the frozen R6 slot geometry. Load the CFS once, then use the nozzle that matches each project.

| CFS slot | G-code | Filament |
| --- | --- | --- |
| A | T0 | Creality Hyper PLA Blue |
| B | T1 | Creality Hyper PLA Red |
| C | T2 | Creality Hyper PLA White |
| D | T3 | Polymaker PolyLite PLA Pro Metallic Gold |

The purple body uses 50% blue and 50% red. The bow uses 25% red and 75% white. The roofs use 25% blue and 75% white. The castle walls and doorway emblem use white directly. The trim, flags, curls and grip bands use metallic gold directly.

Open the native 3MF projects in PrusaSlicer with **File → Open Project**. The virtual recipes alternate physical filaments by layer. Expect stronger mixing on steep sides, with more visible bands and dominant top-layer color on flat faces. Print the swatches before committing to the face or grip. The flat star background is about 91% red in the projected top toolpaths. The 50/50 mixture is more evident on curved sides. The production face stays flat to preserve the shell bonding surface. [Prusa ColorMix guide](https://help.prusa3d.com/pl/article/colormix_1210432)

The 0.6 mm trials use 0.12 mm model layers and a 0.20 mm first layer, 215 °C first-layer and 210 °C running nozzle temperatures, a 60 °C first-layer and 55 °C running bed, and a 6 mm³/s flow cap per spool. These temperatures are inside the published ranges for both grades. [Creality Hyper PLA guide](https://store.creality.com/blogs/all/troubleshooting-3d-print-stringing-guide) · [Polymaker Metallic PLA Pro](https://shop.polymaker.com/collections/polylite-series/products/polylite-metallic-pla-pro?variant=41019989819449)

| Nozzle | Plate order |
| --- | --- |
| 0.4 mm | Gold-free ColorMix swatches, slot-and-thread coupon, pink bow, rear shell, pocket frame |
| 0.6 mm | Castle star face and one grip variant, both of which use metallic gold |

Print the gold-free plates first so only one nozzle change is needed. Keep slot D loaded. The 0.4 mm projects do not select it. Use 0.10 mm layers on the gold-free production parts and swatch, and 0.12 mm on the 0.4 mm fit coupon. The solid-blue rear and frame and the blue-and-gold grip are options to reduce spool swaps.

PrusaSlicer is the validated workflow for these projects. Creality Print also offers thinner color sublayers, which may reduce visible banding on curves. A flat top can still expose mainly the finishing color. No side-by-side print has established which slicer gives the closer shade with these spools. At 0.12 mm layer height, a face tilted 45 degrees from the bed exposes theoretical 0.17 mm bands measured along the face. An upright face exposes 0.12 mm bands. The flat plate remains the fit baseline. [Creality layered-color guide](https://wiki.creality.com/en/software/6-0/CMYW) · [Creality sublayer settings](https://wiki.creality.com/en/software/6-0/release-notes-7-3-2)

The upright star trial rotates the original front 90 degrees and uses a disposable cradle with six cuttable perimeter ties. The 0.6 mm project retains the gold and exposes alternating red and blue at every adjacent sampled field layer. The upright trial and removal coupon sliced without warnings. The trial estimates 10 h 18 min and 2,266 swaps, compared with 3 h 23 min and 95 swaps for the flat star. Time through the CFS is additional. Test cradle removal on the small coupon before using the full upright plate.

The 0.4 mm coupon checks the slot and thread geometry in PLA. Dry-fit the actual 0.6 mm front and grip with the 0.4 mm rear and frame before bonding. The assembled wand still needs adult fit, retention, grip-loosening, drop, bond and reader checks before child use.

The native projects that embed R6 geometry remain local while redistribution rights for the supplied artwork are unverified.
