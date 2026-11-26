# Castle wand R1 · front artwork and CAD handoff

R1 is a provisional front artwork revision. Author review used the source and candidate side by side at the same nominal 140 mm star width, the complete transparent front view, and measurements from the exported polygons. The cream Mickey is legible within the purple arch. The three flags, two sparkles, three towers, gold rim, two curls, bow and paired grip collars retain their original placement. The two scrolls terminate independently below the doorway. The field, windows, and the space around the emblem expose purple carrier material.

| Artifact | SHA-256 |
| --- | --- |
| Editable layered front, `castle_front.svg` | `75a3cd2a345a53180df45840b200144cd478ceb4e5525a55fbe62039ecc5eeae` |
| CAD profiles, `castle_profiles.json` | `b8750391561d2a4438f9448545d820af3ab60a9b48f23527400701c9f026e6f4` |
| Complete front view with transparent background, `castle_front.png` | `978fbf2f7c0944a3237e4780a523589152decda47dd3dea6198fed8e9304de7e` |
| Source and fitted head comparison, `reference_review.png` | `693ecc9daf4641edec2f4e5c47a2718fbf38592481c582b3d3d54ffffb7ebaed` |
| Conversion and rendering script, `prepare_art.py` | `c28f3a5821bf251d48c9d81dba343459c1ea070182b3cea762402fdc738d88dc` |

The SVG uses millimeter page dimensions, a source-pixel viewBox, editable closed curves, masks, and named layers. The independent bow and handle align with the head at the common origin. The JSON gives 34 named GeoJSON profiles with holes and three unified part footprints. Reloading the four-decimal-millimeter JSON produced valid contours throughout. All head decorations lie within the carrier footprint. The PNG is 1047 × 2574 pixels with genuine transparency and approximately 172 dpi. The artwork preview illustrates the proposed edge treatments. Use the CAD preview to inspect modeled relief and final grip proportions.

## Placement

The source transformation is X = (u − 310) × 140/552, Y = (301 − v) × 140/552. Positive Z comes out of the decorated face. All JSON transforms are baked in. The underlying source trace describes the visual envelope only. Adopt the verified mechanical assembly's seating depth, opening, surfaces and thread.

| Front projection | X range, mm | Y range, mm |
| --- | ---: | ---: |
| Star | −70.00 to +70.00 | −65.33 to +66.70 |
| Independent pink bow | −27.93 to +27.93 | −93.31 to −46.35 |
| Bow knot | −6.17 to +5.66 | −65.38 to −50.91 |
| Reference-proportioned grip and neck | −15.53 to +15.47 | −302.57 to −42.86 |
| Cream Mickey | −6.11 to +6.62 | −24.93 to −14.97 |

Each upper loop projects over approximately 168.21 mm² of fixed star. The knot and tails project below the center of the fixed star. Locate bow attachment patches on the loops and check the actual Z gaps, sliding card, cuff and handle motion in CAD. The photograph-length grip extends about 209.26 mm below the bow tips. The complete front reference silhouette spans roughly 140 × 369.27 mm.

## Material regions and height

| Region | Preview swatch | Suggested local face treatment |
| --- | --- | --- |
| Purple | `#8343a4` | Star carrier and recessed field at 0.00 mm, secondary purple inner lip at +0.80 mm. Purple handle and neck use the grip contour. |
| Gold | `#f4be4e` | Flags +1.20 mm, outer rim +1.80 mm, both scrolls +3.00 mm. Three gold collar bands on the handle. |
| Cream | `#ffefd5` | Central tower +1.20 mm, sparkles +1.40 mm, gatehouse and Mickey +1.60 mm, side towers +2.00 mm, cornices +2.00 or +2.60 mm. |
| Sky blue | `#55a6de` | Central roof +1.60 mm, side roofs +2.00 mm. |
| Pink | `#e75d91` | Separate part with continuous backing. Tails +1.20 mm, recessed crease surfaces +1.80 mm, loops +3.40 mm, knot +4.40 mm from its local datum. |

For overlapping profiles within the head, the highest exposed tier owns the surface. Equal heights use the later feature in drawing order. CAD can union same-color layers and partition overlaps for aligned multipart output. All proposed elevations are multiples of 0.20 mm.

## Measured detail and open checks

| Feature | Measurement |
| --- | ---: |
| Gold rim, minimum exterior-to-interior distance | 5.54 mm |
| Purple inner lip, minimum exterior-to-interior distance | 2.71 mm |
| Side flagstaff across source row 235 | 2.28 mm |
| Side tower window, width × height | 2.79 × 4.86 mm |
| Mickey, width × height | 12.73 × 9.96 mm |
| Mickey edge to surrounding cream gatehouse | 2.75 mm minimum |
| Gap between the two gold scrolls | 2.30 mm minimum |
| One bow crease, bounding width × height | 11.99 × 4.76 mm |

The tips of the sparkles, pennants, scrolls and ribbon folds taper to points. Final tip survival depends on toolpaths. The front illustration cannot establish card fit, bow bonding clearance, handle function, material color or physical print success. User selection and independent CAD and slicer validation remain separate. Original reference paths and hashes are in `design_brief.md`.

To rebuild, run the repository's Python environment on `prepare_art.py`. It resolves the SVG and outputs relative to the script. The optional comparison additionally reads the original PNG at its recorded Downloads path.
