# Enchanted rose · provisional front artwork R2

The cream rose sits directly below Mickey, between the gold scrolls. Its outer petal curls around the spiral center and the purple field shows through the petal gaps. The three cream profiles sit on the common purple face, with proposed elevations of 2.4 mm for the left petal, 2.8 mm for the outer petal and 3.2 mm for the spiral. Their respective projected areas are 17.36, 57.52 and 27.30 mm². The star uses purple, gold, cream and blue. The independent bow uses pink.

The bottom-left close-up in the user-supplied `C:/Users/vic-l/Downloads/Purple Castle Star Card Wand Blueprint.png` supplied the rose contours, orientation and relative placement. Its SHA-256 is `7c4202584515bbf4c98f5578b08741578a1eb9dc0a10efa11c703502ac942650`. The original purple castle appearance and pink bow come from `Purple Princess Castle Star Card Holder.png` and the doorway emblem from the Castle Rose wand in `Star Wand Credit Card Collection.png`. Their paths and hashes are in [the initial brief](../design_brief.md).

| R2 artifact | SHA-256 |
| --- | --- |
| [Editable SVG](castle_front.svg) | `7ddc0bd53e0631c577f7b10237cafec47f2eb7ca92b57c9549179a37531de0a5` |
| [37 CAD profiles, mm](castle_profiles.json) | `157e4526ce2e8a31cf1bcfd0d903d3c1fd56db4d6431e11811acd003a2974cfa` |
| [Transparent full front](castle_front.png) | `9e46dade5bb63144ab5cbca97099a12fad6b30076364558232bba7322425326c` |
| [Blueprint and artwork close-ups](rose_reference_detail.png) | `13c66332be621c1282c0b8d83d8b84733bb5b411e8770bad6fdb652ee0ae4356` |
| [Geometric checks](rose_checks.json) | `23c6d7bf9d03401a1e906aac48da559f8ee1908dfe9d6a89fed3cf6575c4dc8b` |
| [R2 build and comparison script](prepare_rose.py) | `5cd0977e678cb2ee8a2ca01f967906037f9b138bd4ce052e0b7145524e34f0cc` |

The 140 mm star uses R1’s front XY coordinates and scale. The rose spans X −7.294 to +7.668 mm and Y −39.189 to −26.080 mm. Its center lies 0.067 mm left of Mickey’s center. The minimum edge gap to Mickey is 1.155 mm. The clearances to the shortened left and right gold scroll tips are 0.918 and 0.877 mm. The closest separate cream petals leave 0.672 mm of purple. The central spiral tapers into a curved terminal.

The R2 generator compared all 34 existing features with the R1 exchange and checked each exported contour for validity. Only the two scroll terminals changed among the prior features. All three component footprints are geometrically equal to R1 and use the identical serialized outlines. Bow attachment, grip alignment and protected card interfaces therefore retain the R1 artwork envelope. The independent mechanical design determines actual contact and clearance.

The author reviewed the saved fitted front at the nominal 140 mm scale and the enlarged detail at matched Mickey width. The spiral, Mickey silhouette and pink bow read separately. User selection, CAD and slicer verification, and physical print appearance are independent of this visual review.

Rebuild with the repository Python environment by running `prepare_rose.py`. It uses the existing R1 converter and rendering code and reads R1 profiles for the regression checks.
