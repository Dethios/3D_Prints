# R6 flat castle face color-cap trials

These two native PrusaSlicer 2.9.7 projects keep the original R6 front geometry flat and use the K2 **0.6 mm nozzle**. The broad background carries a single **0.12 mm** exposed cap. The body and raised inner lip use the opposite solid base color. The castle, stars and Mickey use white directly, the rim, curls and flags use metallic gold, and the roofs keep the existing blue/white Light Blue recipe.

| Plate | Body and lip | Surface cap | PrusaSlicer estimate | CFS swaps |
| --- | --- | --- | --- | ---: |
| [Red over blue](K2_06_PLA_Castle_R6_Flat_Red_over_Blue.3mf) | A blue | B red | 3 h 23 min | 73 |
| [Blue over red](K2_06_PLA_Castle_R6_Flat_Blue_over_Red.3mf) | B red | A blue | 3 h 23 min | 88 |

Keep the existing CFS order of A blue, B red, C white and D metallic gold. Use **File → Open Project** so that native filament assignments and the roof recipe load. The first layer is 0.20 mm and normal layers are 0.12 mm. The broad field prints its base at Z1.88 mm and its cap at Z2.00 mm. The cap covers four broad patches. The base remains visible along the lip and in narrow areas around the artwork and mounting features.

The [side-by-side preview](flat_cap_preview.png) draws the physical tools from the sliced G-code. It shows the exposed spool colors and the solid white artwork. It cannot predict how much light travels through the top layer of the actual Hyper PLA. HueForge-style layering relies on that transmission, so a purple result still needs a physical check. [HueForge explanation](https://shop.thehueforge.com/blogs/news/what-is-hueforge)

Both 3MFs reopened and sliced without warnings. For the narrow shell neck, the plates keep the limited removable supports and preserve the flat card-contact surface. Remove any support residue and check the assembled fit, thread and card retention before use. The quoted times exclude unmeasured CFS operations.

[Color-cap CAD source and volume checks](../../cad/R6/hueforge_flat/README.md) · [Toolpath audit](preflight.json) · [Original split-nozzle guide](../R6_04_PLA/README.md)
