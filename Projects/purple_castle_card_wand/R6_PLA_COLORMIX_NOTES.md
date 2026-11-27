# R6 K2 0.6 mm PLA ColorMix setup

Use the frozen R6 slot geometry with a Creality K2 0.6 mm preset. Load the CFS once and keep the same mapping for each plate.

| CFS slot | G-code | Filament |
| --- | --- | --- |
| A | T0 | Creality Hyper PLA Blue |
| B | T1 | Creality Hyper PLA Red |
| C | T2 | Creality Hyper PLA White |
| D | T3 | Polymaker PolyLite PLA Pro Metallic Gold |

The purple body uses 50% blue and 50% red. The bow uses 25% red and 75% white. The roofs use 25% blue and 75% white. The castle walls and doorway emblem use white directly. The trim, flags, curls and grip bands use metallic gold directly.

Open the native 3MF projects in PrusaSlicer with **File → Open Project**. The virtual recipes alternate physical filaments by layer. Expect stronger mixing on steep sides, with more visible bands and dominant top-layer color on flat faces. Print the swatches before committing to the face or grip. The flat star background is about 91% red in the projected top toolpaths. The 50/50 mixture is more evident on curved sides. The production face stays flat to preserve the shell bonding surface. [Prusa ColorMix guide](https://help.prusa3d.com/pl/article/colormix_1210432)

The 0.6 mm trials use 0.12 mm model layers and a 0.20 mm first layer, 215 °C first-layer and 210 °C running nozzle temperatures, a 60 °C first-layer and 55 °C running bed, and a 6 mm³/s flow cap per spool. These temperatures are inside the published ranges for both grades. [Creality Hyper PLA guide](https://store.creality.com/blogs/all/troubleshooting-3d-print-stringing-guide) · [Polymaker Metallic PLA Pro](https://shop.polymaker.com/collections/polylite-series/products/polylite-metallic-pla-pro?variant=41019989819449)

Print the swatches and the slot-and-thread coupon first. Then print the face and bow for a visual check, followed by the rear shell, pocket frame and grip. The solid-blue rear, frame and blue-and-gold grip are options to reduce spool swaps. The assembled PLA wand still needs adult fit, retention, grip-loosening, drop, bond and reader checks before child use.

The native projects that embed R6 geometry remain local while redistribution rights for the supplied artwork are unverified.
