# R6 flat star-field thickness test

The two volumes replace `head_purple.stl` in the flat R6 front. The cap is 0.12 mm thick and covers the four broad exposed field regions. The base carries the raised inner lip, neck, ornament sockets and bow lands and ribs. The cap path leaves a narrow line of base material along the field edge and around the ornaments, plus a few small gaps that stay base-colored. The original gold, cream and blue meshes supply their existing geometry. Assign the original `head_cream.stl` volume to solid white for this trial.

Import `head_base.stl`, `head_field_cap.stl`, and the original `head_gold.stl`, `head_cream.stl` and `head_blue.stl` together as one multipart object. The STLs use the original assembly coordinates in millimeters. Keep +Z up and put the shared card-contact plane at Z = 0.90 mm on the bed. The cap spans 2.78–2.90 mm in assembly coordinates and 1.88–2.00 mm above the bed. A 0.20 mm first layer and fifteen 0.12 mm layers bring the cap to print Z = 2.00 mm, layer 16. Check the two field tools in the actual layer preview.

The mask comes from the pinned R6 star-field, castle, rim and bow arrangement, as stored in the [editable R6 artwork](../../../art/R6/castle_profiles.json) and the [exact R6 assembly STEP](../purple_castle_card_wand_R6.step). The builder offsets the field and ornament boundaries and removes narrow connections and small disconnected regions before intersecting the mask with the original carrier. The resulting cap covers 86.2% of the field area exposed in the artwork projection. The [cap region](cap_region.json) records the precise slice-audit footprint in assembly XY millimeters. The [validation report](validation_report.json) records the source and output hashes, bounds, and solid and mesh checks.

Use the 0.6 mm K2 nozzle and the fit-coupon orientation from the R6 release. The cap allows paired HueForge-style tests with a blue base and red field cap or a red base and blue field cap. Printed color, layer bonding and fit require a physical check.

From the repository root, use the existing CadQuery 2.7 environment to regenerate the two STLs, the exchange STEP and the validation report.

```powershell
& '.venv/Scripts/python.exe' -B 'Projects/purple_castle_card_wand/cad/R6/hueforge_flat/build_field_cap.py'
```
