# R6 upright star with removable cradle

This local 0.6 mm PLA trial rotates the four unchanged star-face meshes 90° and prints them together with one disposable blue cradle. Six thin ties brace the star on its outer purple edges. Gapped supports catch the lower star points and curl undersides. The native project adds a small amount of slicer support below the star and blocks support at the threaded throat. The actual support toolpaths clear the card-contact and thread keepouts.

| Project | Purpose | PrusaSlicer toolpath estimate | CFS swaps |
| --- | --- | --- | ---: |
| [Cradle removal coupon](K2_06_PLA_Castle_R6_Upright_Cradle_Release_Coupon.3mf) | Test an actual lower point, gold rim and removable tie | 1 h 10 min | 356 |
| [Upright star trial](K2_06_PLA_Castle_R6_Upright_Star_Trial.3mf) | Four-color front at 90° | 10 h 18 min | 2,266 |
| [Flat star baseline](../R6_06_PLA/K2_06_PLA_Castle_R6_Star_Face.3mf) | Original face-up orientation | 3 h 23 min | 95 |

Both new projects contain gold and require the 0.6 mm nozzle. Open them with **File → Open Project**. Use 0.12 mm model layers and a 0.20 mm first layer. Keep the established load order A blue, B red, C white, D metallic gold. The coupon uses A, B and D. The full star uses all four. These time estimates do not include measured CFS cutting, loading and purge time.

Print the removal coupon at the workbench first. Let it cool, support the shell close to the tie and snip the tie with flush cutters. Lift off the cradle and remove the light separate support and any burrs. Check whether the gold point peels cleanly and whether the purple edge cracks or marks. The full plate repeats six purple-edge ties. Its central neck has about 13 mm² of direct bed contact, separate from the cradle and brim. Watch the first layers of the full star for neck adhesion. The coupon verifies local release and has a different foot. Discard all cradle fragments. The physical release force, final finish and actual color remain untested.

The sampled upright field shows blue and red on consecutive visible 0.12 mm layers. The flat field remains mostly red at the top. Upright printing exposes both colors, and the perceived color depends on the spools and lighting. The lower face bond, card slot and threads keep their original geometry. Before assembly, dry-fit the actual mixed-nozzle covers and grip and check the slot, bond and retention. Keep the prototype away from the child until those physical checks are complete.

[Split-nozzle plate guide](../R6_04_PLA/README.md) · [Cradle CAD and removal detail](../../cad/R6/upright_fixture/README.md) · [Upright toolpath audit](upright_audit.json) · [Coupon toolpath audit](coupon_audit.json)
