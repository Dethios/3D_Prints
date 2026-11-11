SORCERER EARS v2 — REFERENCE MOUNTINGS

This revision replaces v1's invented rectangular mounting feet with the
functional mounting strips cut directly from the original source STL files.
No interface was scaled. The source mating curves, five magnet bores and
10 mm mounting depth are retained. Magnets are 6 mm diameter x 3 mm thick.
The v1 6 x 2 mm magnets, keyed rectangular feet and cover discs do not apply.

CHOOSE ONE FAMILY — DO NOT MIX THEM

STL/NX3 and CAD/NX3:
  Matches the first two supplied references:
  https://www.printables.com/model/413543-disney-interchangeable-headband-and-ears
  https://www.printables.com/model/413611-larger-disney-interchangeable-headband
  The mounting strip is from the original NX3Creations ear in model 413543.
  The glue-on base is the existing Titanhunter remix of that same interface:
  https://www.printables.com/model/1907777-disney-interchangeable-headband-adapter-5-magnet-h
  It is included as source geometry after a rigid rotation/translation only.
  Original adult/larger printable headbands are in Reference_files.

STL/TimJ and CAD/TimJ:
  Matches the supplied pretzel ear's mounting family:
  https://www.printables.com/model/765654-interchangeable-mickey-ear-pretzel
  Its original blank and glue-on base are from Tim J's model:
  https://www.printables.com/model/82037-interchangeable-mickey-ears
  The original Tim J base is supplied, with its source geometry unchanged.

Both use five 6 x 3 mm magnet positions, but their spacing, axes and mating
curves differ. A five-hole count alone does not make them interchangeable.

PARTS TO PRINT WITHIN YOUR CHOSEN FAMILY
For the two ears:
  2 x ear_blue_base.stl
  1 x left_brooms_raised_gold.stl
  1 x right_mouse_raised_gold.stl
  2 x glue_on_base_SOURCE_GEOMETRY.stl (if using a store-bought headband)
OR print the two *_assembled.stl files instead of the separate color parts.

For the optional interchangeable center hat:
  1 x center_hat_blue_base.stl
  1 x center_hat_raised_white.stl
  1 x center_hat_glue_base_3_of_5.stl
OR print center_hat_assembled.stl instead of its separate color parts.

Fit test first:
  1 x mount_test_strip.stl plus 1 x glue_on_base_SOURCE_GEOMETRY.stl.
The test strip contains the actual five-hole functional interface used by
the full ears. It is extracted from the original source, not a simplified
rectangle or a newly guessed hole-spacing coupon.

MAGNET QUANTITY
Two ears using all five positions: 20 magnets total (10 in ears, 10 in bases).
Optional center hat: 6 more magnets, three per mating side.
Use consistent polarity on every accessory and the opposite on its bases.

DIMENSIONS AND TWO-LAYER ARTWORK
The ear outlines are approximately 100 mm / 3.94 in wide, as in the source
templates. They are not the 88 mm v1 outlines. Keeping the interfaces at the
source scale is essential. Do not scale the complete model to adjust fit.
Blue artwork backing: 2.0 mm. Raised gold/white artwork: 1.2 mm.
The source mounting strip remains locally 10 mm deep. It is a functional
mounting structure, not a third decorative layer.

The mouse and broom artwork comes from v1. It was fitted into each original
outline without clipping stars or silhouette features. The Tim J version's
artwork is scaled to 94%; mounting geometry remains at 100% in both versions.
Artwork is counter-rotated for a nominal 40 degree ear location either side
of the crown. This matches the measured NX3 headband mounting angle.
The Tim J glue-on bases should be positioned at the same nominal angles for
the included artwork to read upright. Dry-fit before gluing.
Filenames refer to a FRONT VIEW: brooms on viewer's left / wearer's right,
mouse on viewer's right / wearer's left.

CENTER HAT — A REFERENCE-DERIVED ADAPTATION
The supplied references do not provide a center hat mount. The center parts
use the three middle magnet positions and mating curve from the chosen
source interface; the ends containing the outer two positions are trimmed.
No new hole spacing, keyed latch, cap system or magnet size was introduced.

The center glue-on base is placed against the FRONT face of the band, with
the original flat side used for bonding. It sits ahead of the ears in depth
to clear their reference mounting strips. This position is shown in the
assembly previews; the center part is not intended to attach to an
unmodified crown on the NX3 printed headband. The geometry check uses a
nominal 0.4 mm adhesive gap. Your band and adhesive bond need a physical test.

PRINTING
Print on the large flat backs, Z=0 on the bed. Starting settings:
0.4 mm nozzle, 0.2 mm layers, three walls, your normal proven material profile.
Review the source horizontal magnet bores in the slicer. Keep supports out
of blind bores. This revision retains the sources' snug holes rather than
silently increasing their clearance. Check your printer and actual magnets
with the source test strip before printing the artwork.

For multiple materials, import ear_blue_base.stl and the selected raised-art
STL as ONE multipart object. Preserve their original coordinates. The raised
layer begins at Z=2.0 and intentionally contains separate stars and islands.
Do not arrange those islands individually. Assign navy/gold or navy/white.

For a single extruder, the *_assembled.stl can be printed with a color change
after the 2.0 mm backing, or painted after printing. A height-based color
change also changes the upper part of the original mounting strip, which
continues to Z=10.0. Painting the raised artwork is another simple option.

ASSEMBLY
1. Test the printed strip/base and your 6 x 3 mm magnets. Do not force a fit
   hard enough to crack the plastic. Inspect for stress cracking.
2. Mark mating magnet polarity before installation. Secure magnets in their
   original pockets with a suitable adhesive if needed, following its cure
   instructions. Keep adhesive off the detachable mating faces and allow it
   to cure before bringing the two parts together.
3. Temporarily assemble ears, bases and optional hat. Adjust the positions
   for upright artwork, clearances and comfort. Use only one mounting family.
4. Glue the source bases to the headband. For the center hat use the front
   face placement shown in the preview. A fabric covering is only as strong
   as its bond to the headband underneath.
5. After cure, inspect and check retention before wearing. Keep loose magnets
   and damaged parts away from children. Physical holding-force, drop, heat,
   adhesive and comfort tests have not been performed here.

WHAT WAS VERIFIED
Each finished STL: watertight, consistent winding, positive volume, and the
expected connected components. Each STEP solid: valid in the CAD kernel.
The functional strip above the thin backing (Z >= 2.01 mm) was compared
against the downloaded source by symmetric volume difference, not just
overall dimensions. All five original bores are retained. The backing also
fills the visual gap above the bar, inset from the mating outline. Tiny
differences at the floating-point mesh
precision are recorded in CAD/reference_geometry_report.json.
The new strips were also checked against the original matching bases to
ensure they introduce no additional interference beyond the source meshes'
own small tessellation overlaps. Nominal ear/hat collisions were checked.
See validation_results.json for measurements and limits. No physical test
has been performed; a CAD check is not a retention-force certification.

EDITABLE CAD
CAD/build_reference_mounts.py rebuilds both variants using the bundled source
meshes and artwork.json. CAD/check_and_position.py verifies the result.
CAD/render_reference_previews.py renders the actual exported STLs in Blender.
Install CAD/requirements.txt in Python 3.12, then from this folder run:
  python CAD/build_reference_mounts.py
  python CAD/check_and_position.py
  blender --background --python CAD/render_reference_previews.py

STEP files are solids with faceted mounting surfaces imported from the source
STLs. The *_layer_assembly.step files retain blue and gold as separate solids
for editing; *_assembled.stl files are fused printable objects. They are not
a reconstructed parametric feature tree of the original author's model.

Attributions, source links, license notices and modification scope are in
SOURCES_AND_ATTRIBUTION.txt. Original reference files are included separately.
