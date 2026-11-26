# Mulan NX3 illustrated lithograph ears

Print one left fan-trio ear and one right Mulan ear. Each is a single solid
with a continuous 10 mm deep outer ring and an integrated five-pocket NX3
carrier. The ring is about 5.06 mm wide in front view, and each ear is about
99.99 × 88.54 mm in its flat print coordinates. Use a matching NX3 headband
or the approved glue-on bases and 6 × 3 mm magnets.

- [Fitted artwork, actual STL relief, and paint guide](previews/reference_comparison.png)
- [Hand-corrected trio](artwork/fan-trio-hands-corrected.png), [supplied Mulan PNG](artwork/mulan-illustration2.png), and [brighter dragon reference](artwork/Brighter-dragon.jpg)
- [Left fan-trio STL](stl/left_fan_trio_integrated_NX3.stl) and [right Mulan STL](stl/right_mulan_integrated_NX3.stl)
- [Two-ear PrusaSlicer project for the 0.25 mm nozzle](Mulan_NX3_Voron24_025mm_45deg.3mf)
- [PrusaSlicer color review plate](Mulan_NX3_Color_Review.3mf) and [full-color 3D model](previews/mulan_nx3_painted_3d.glb)

Open the color review plate as a project and click empty space on the plate
to see both ears' paint assignments. It uses 17 virtual filament slots to
approximate the guide and is for viewing. The textured GLB carries the
paint guide's full colors. Use the single-extruder 0.25 mm plate for printing
the parts to paint by hand. The color assignments survived a local
PrusaSlicer 2.9.7 reopen and re-export.

The red guard grips the fan with four visible curled fingers and his thumb
behind the hinge. Both lower fans use uninterrupted outer curves and ribs.
The orange blades and hinge share the same rib positions. The robes extend
behind the fans to meet the rim and the blue shoulder follows a continuous
contour. The brighter source
places the dragon and the rocket
beneath his feet behind Mulan. The rocket joins the inner rim. The dragon has
alternating belly plates, stepped wing panels and ribs, and recessed nostrils.
The smaller, closer-set eyes have narrow outer rims and smooth recessed
sockets. The gap between the inner tips is about 0.6 mm. The angled jaw and
tooth outline follow the supplied close-up. The tooth plate is smooth for
painting the center line by hand.
[Face comparison](previews/dragon_face_comparison.png) · [Art sources](artwork/SOURCES.md)

The coin border has 30 nested keys between parallel rails on each ear. The
recessed field, shoulder, key, and outer rails sit at Z = 9.20, 9.48, 9.72,
and 10.00 mm. The keys at the two mount corners follow nested inset curves
and each covers about 9.26 mm along the rim.

The shell comes from the [Sorcerer Uniform Rim base](../sorcerer_ears_CAD_STL_v2/STL/NX3/Uniform_Rim/ear_blue_base.stl).
The [Crab NX3 design](../magnetic_treasure_crab_ears_NX3/README.md) informed the
integrated ring construction and fit checks. Mesh comparisons with the prior
approved meshes confined the latest changes to the decorative rim and trio
art. The pocket and nominal assembly checks passed.
[Geometry report](validation_report.json)

Open the 0.25 mm 3MF as a project after changing the nozzle. PrusaSlicer 2.9.7
sliced it with the project-local VictorCustom PLA profile at 0.08 mm layers,
0.15 mm first layer, +45° bed rotation and supports off. The actual toolpaths
use 0.28 mm external perimeters and 0.25 mm top infill. The longest straight
bridge move was 4.24 mm over a stock magnet pocket. The 0.045 mm contour
resolution and 0.065 mm gap-closing radius were retained for the clean
slice. Toolpaths reach all 30 keys on each ear. Estimated print time and
consumption are 20 h 36 min and 75.54 g.
[Toolpath review](previews/slicer_layers_025mm.png) · [Slicer report](slicer_preflight.json)

The smallest details may soften in the print. Physical seating, magnet fit,
and retention remain unverified. The
[stock NX3 fit strip](../sorcerer_ears_CAD_STL_v2/STL/NX3/mount_test_strip.stl)
can be used to test fit. Match magnet polarity to the existing set and keep
the models at 100% scale.

Use the workspace Python 3.12 environment to regenerate. The three linked images
are the relief inputs. The original medallion photos are optional provenance.

```powershell
python cad/build_ears.py
python cad/check_exports.py
python cad/make_plate.py
python cad/make_color_preview.py
```

Mounting geometry credits are recorded in the
[Sorcerer attribution file](../sorcerer_ears_CAD_STL_v2/SOURCES_AND_ATTRIBUTION.txt).
The supplied artwork was used for this personal project.
