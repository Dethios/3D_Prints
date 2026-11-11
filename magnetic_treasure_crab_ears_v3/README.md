# Image-based crab ears with glue-on magnetic headband adapters

This revision follows the supplied picture: crescent claws, a filled gold coin heap, large faceted jewels, gold stars, and tall curved eye stalks. The stalks are **6.5 mm wide with 3.0 mm structural thickness**. The ear faces use a 1.8 mm backing plus 0.6 mm shallow detail. Printed color regions approximate the picture's colors; the illustrated gradients and metallic finish require painting or other finishing.

**Use this revision's front plates, rear carriers and receivers as a matched kit.** It is meant for a store-bought headband. No printed headband is required. A representative headband is shown in the assembly only to explain placement; it is not a model of your eventual purchased band.

## Parts and files

| Print | Quantity | Purpose |
|---|---:|---|
| `left_face.stl`, `right_face.stl` | 1 each | Decorated thin front plates |
| `rear_magnet_carrier_print_two.stl` | 2 | Curved five-magnet shoes bonded behind the front plates |
| One selected `ear_adapter_W…_R…_print_two.stl` | 2 | Receivers glued to the store-bought headband |
| `tall_eyes.stl` | 1 | Tall eyes with thicker curved stalks |
| One selected `eye_adapter_W…_R….stl` | 1 | Center receiver glued to the headband |
| `magnet_fit_coupon.stl` | 1 initially | Tests magnet-hole tolerance |
| `radius_fit_R55.stl`, `radius_fit_R65.stl`, `radius_fit_R75.stl` | As needed | Lightweight curved-edge gauges for choosing an underside radius |

The completed front plate and rear carrier stay bonded together. That completed ear lifts off the receiver magnetically. This keeps the mounting bulk behind the decoration instead of covering the treasure. The eyes lift off their center receiver independently.

`cad/crab_v3_assembly.step` is the colored solid CAD assembly. The dark `headband_reference_ONLY` body is a visual reference. Individual STEP solids and `cad/build_crab_v3.py` are included for editing. STEP contains editable B-rep bodies; the parameter history is in the Python source, rather than a Fusion feature timeline.

The `*_purple`, `*_violet`, `*_blue`, `*_gold`, `*_white`, and `*_black` STL files are aligned color regions. They are intended to load together as one multicolor object, not to print as loose decorations. The ordinary face/eye STL files are complete single-color solids suitable for painting.

## Choose an adapter

Files in `stl/adapters/` cover these choices:

| Parameter | Choices | Meaning |
|---|---|---|
| `W` | 10, 15, 20 mm | Front-to-back width of the bonding pad |
| `R` | 55, 65, 75 mm | Radius of the concave underside along the headband's curve |

The default assembly uses **W10/R65**. These are alternatives, not a universal-fit claim. Choose the pad width for the actual band, then hold the curved underside against the band before bonding. You can test with the thin `radius_fit` gauges first: one notch identifies R55, two R65, three R75. Match the concave edge to the actual mounting location; an oval band may need a different radius at its center and sides. The radius values describe each saddle's underside, not a head-size specification. The parameters are editable if none fits.

Use a headband with a reasonably flat surface across its width. Heavily padded, domed, fabric-wrapped or unusually shaped bands may need another underside profile or a different adhesive attachment. The saddle has a nominal 0.1 mm bonding gap over the default reference curve; the real band and adhesive determine the actual joint.

Only default W10/R65 adapters have individual STEP exports; all 18 width/radius variants are supplied as STLs and can be regenerated as CAD from the source. Two identical ear receivers are printed and oriented separately on the left and right of the band.

## Printing

Suggested starting point: PETG, 0.4 mm nozzle, 0.20 mm layers, four walls, and 20–30% infill. These are starting settings, not a tested strength specification.

- Print the front plates flat on their backs, with decorated faces upward. Decorative thickness is **2.4 mm** total, with a backing and one shallow relief zone; small coin steps and grooves stay inside that relief.
- Print the rear carriers flat at Z = 0. They are 10 mm deep, with 0.8 mm locating pegs on the front. The structural mount is separate from the thin decoration.
- The 6.2 mm ear magnet bores are horizontal. Use well-tuned bridging and remove any small sag before installing magnets. Avoid support material inside the bores.
- Print the eyes flat on their backs. The stalk/globe backing is 3 mm, with 0.6 mm face details; the center anchor is locally thicker to hold its magnets.
- Print the chosen glue-on adapters at their exported orientation. All widths/radii should be test-fitted to the actual band before permanent bonding.

The coupon uses shallow notches: **one = 6.0 mm bore, two = 6.1 mm, three = 6.2 mm**. Supplied parts use 6.2 mm glue-fit bores for nominal **6 mm diameter × 3 mm thick magnets**. Adjust `BORE_D` if your printer/magnets need another tolerance. Do not scale the entire model, because that changes the magnet pattern.

## Assembly

1. Print the magnet coupon and one plain rear carrier first. Confirm your magnets and the corresponding ear receiver fit before printing/bonding the full kit.
2. Dry-fit each front plate onto a rear carrier. The two 3.2 mm locating pegs enter 3.5 mm blind holes. Bond the broad flat contact area with a plastic-compatible adhesive; the small gap is for the adhesive. The pegs locate the plate and do not replace the adhesive joint.
3. Check magnet polarity against each matching receiver, then securely bond the magnets. The magnets are not mechanically captive; loose small magnets must be kept away from children. Keep detachable parts apart while adhesive cures.
4. Position the two ear receivers on the store-bought headband. The illustrated starting position is about 50 degrees to each side of the crown, but adjust the position for the actual band and check ear/eye clearance before bonding. Glue the concave underside to the band, keeping adhesive off the magnetic seating surface.
5. Center the eye receiver at the crown. Its two magnet openings face forward. The eye unit has matching back-facing openings. The concave underside bonds to the top of the headband.
6. After all joints cure, attach the ears and eyes and check resistance to gentle pulling and shaking. Magnet strength, adhesive durability, fatigue resistance and comfort have not been physically tested.

| Magnet location | Number of 6 × 3 mm magnets |
|---|---:|
| Two rear ear carriers | 10 |
| Two glue-on ear receivers | 10 |
| Eye unit | 2 |
| Center eye receiver | 2 |
| Total for the complete kit | **24** |

Ear pocket axes follow the original five-magnet pattern. The new adapters are separate parts intended for bonding onto a real headband. The center eye connection uses front-facing magnets, so it is different from the previous kit's upward-facing eye mount.

## Finishing and verification

For a simple finish, print the complete solids and paint the coins/star/facet outlines gold, the claw purple and blue, and the eye whites/pupils. A purple/blue paint blend can reproduce the image's gradient. With multicolor hardware, load each part's aligned color regions together and retain their original coordinates.

Actual CAD renders are in `previews/verified/`. Digital validation results are in `validation_report.json`. These checks cover connected solids, STL integrity, model intersections and nominal magnet envelopes; they do not establish physical fit on a headband that has not yet been selected.

To regenerate with CadQuery 2.7 and SciPy installed:

```text
python cad/build_crab_v3.py
python analysis/validate_v3.py
```

See `ATTRIBUTION.txt` for reference and license notes.
