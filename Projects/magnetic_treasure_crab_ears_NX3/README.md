# Treasure crab Mickey ears for NX3

Each 99.8 mm ear prints as one solid with the five-pocket NX3 carrier built in. The rim is nominally 4.6 mm wide and reaches 10.47 mm overall. The carrier follows the inner and outer rim walls through its full height, including at the rounded mounting corners. The artwork backing sits flush with the ring underside. The larger purple gem and smaller blue gem have flat tables and sloped facets. Foreground coins overlap their lower edges, and the pile reaches both sides of each rim. Left and right refer to the front view.

The coins have rounded rims and crowned faces. Foreground pieces hide the edges of coins behind them. A low, flat pad with rounded ends connects each sculpted claw shoulder to the rim. The stars rise from rounded points to a sculpted center. The squinting eyes have domed lids, whites and irises. The eye stalks retain their 3.6 mm structural thickness.

The center base glues to the front of the crown. Its three pockets face forward and mate with three rear-facing pockets in the eye unit. The eyes sit ahead of the center base. The new center base and eye unit are a matched pair.

## Print list

| File in stl/ | Quantity |
| --- | ---: |
| left_crab_face.stl | 1 |
| right_crab_face.stl | 1 |
| glue_on_base_SOURCE_GEOMETRY.stl | 2 |
| crab_eyes.stl | 1 |
| center_hat_glue_base_3_of_5.stl | 1 |
| ear_magnet_fit_test_strip.stl | 1 for a separate ear fit test |

Use **26 magnets, each 6 mm in diameter × 3 mm thick**, for the complete set. Each ear and its band base take five magnets apiece. The eyes and center base take three apiece. The revised center pockets are 6.25 mm in diameter and 3.15 mm deep.

## Print and assemble

1. Open [the Voron 3MF](Crab_NX3_Voron24_45deg.3mf) as a project. It uses VictorCustom, Polymaker PolyChroma Matte PLA, a 0.5 mm nozzle, 0.15 mm layers, a 0.25 mm first layer and +45° Z rotation. The rings and recessed ear artwork share the print bed. Supports are disabled. The three glue-on bases use 4 mm outer brims.
2. For a fit test, print the ear strip and one ear base. Dry-fit the center pair and actual magnets before gluing. Remove brims and any first-layer flare that interferes with seating.
3. Position the ear bases approximately 40° to either side of the crown. Dry-fit all three assemblies together, then bond the center base by its flat back with the pockets facing forward. The actual band determines contact area and final position.
4. Mark mating magnet polarity and secure the magnets in their pockets. Let the adhesive cure before bringing the parts together. Check seating and retention on the actual headband.

## Validation

All six STL files reloaded as single watertight solids. The ear bases retain the approved NX3 source geometry. The integrated carriers add no interference against the original bases or inside the magnet bores. The geometry check verified 1.05 mm of solid material behind each ear pocket. The revised center pockets align in opposing planes and accept nominal 6 × 3 mm magnet envelopes in CAD. The nominal assembly check found zero intersections between the left, right and center assemblies. Physical fit and retention remain pending.

PrusaSlicer 2.9.7 reopened and sliced the six-part project using its embedded settings. The checked toolpaths include first-layer contact for every part, the sculpted relief, and the closed top layer of each rim. The estimated print is 5 h and 93 g of PLA. The slicer flagged floating bridge anchors and long bridge extrusions on the left ear. The longest bridge extrusion segment measured 25.2 mm at Z = 1.90 mm. Bridge performance still needs a print check. See the [layer preview](previews/Crab_NX3_Voron24_45deg_Layers.png), [geometry report](validation_report.json) and [slicer report](slicer_preflight.json).

The mesh review shows the reloaded STL surfaces from the front, from below and at an angle. [Rim joins](previews/rim-carrier-joins.png) · [Left coin close-up](previews/left-coin-closeup.png) · [Claw supports](previews/claw-support-joins.png) · [Ear details](previews/stl-review-1.png) · [Ear undersides and eyes](previews/stl-review-2.png) · [Receivers and fit strip](previews/stl-review-3.png)

Run [the generator](cad/build_crab_nx3.py) with Python 3.12 and the sibling Sorcerer project's CAD requirements. The generator reads the approved ear geometry from that project.

## Source credit

Mounting geometry derives from NX3Creations LLC's interchangeable Mickey ears, dressyspider's reupload and larger-band reference, and Titanhunter's NX3 glue-on adapter remix. This kit integrates the ear strips with the decorative faces and adapts the center pair to opposing front and rear pockets. The claw, treasure and eye outlines were developed from the supplied reference image.

See the sibling Sorcerer project's [source and license record](../sorcerer_ears_CAD_STL_v2/SOURCES_AND_ATTRIBUTION.txt). [NX3 ears](https://www.printables.com/model/413543-disney-interchangeable-headband-and-ears) · [Larger-band reference](https://www.printables.com/model/413611-larger-disney-interchangeable-headband) · [Glue-on adapter](https://www.printables.com/model/1907777-disney-interchangeable-headband-adapter-5-magnet-h) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
