# R6 · compact 130 mm star and recessed pennants

The star is 130.00 mm wide and 122.60 mm tall. All three gold flags now lie entirely inside the flat purple field. Their nearest edges clear the raised purple lip by at least 2.95 mm and the gold rim by at least 5.49 mm. The pennants still fly to the right. Each gold pole meets its blue roof through 1.65 mm of projected vertical overlap.

| Flag | Purple lip gap | Gold rim gap | Gold staff width | Flag and roof overlap |
| --- | ---: | ---: | ---: | ---: |
| Left | 4.07 mm | 6.65 mm | 2.12 mm | 3.15 mm² |
| Center | 3.04 mm | 5.61 mm | 2.12 mm | 2.93 mm² |
| Right | 2.96 mm | 5.49 mm | 2.12 mm | 3.15 mm² |

The frozen [R5 editable vector](../R5/castle_front.svg) supplies the castle, Mickey, gold rim, scrolls and pink bow. Its SHA-256 is `3b4059cbbc9f1ac54d4dce851f4ba0b8de6fa112de1b4f023c97dbaab371a0dc`. Its CAD exchange SHA-256 is `a6031a4b9d68d8ecbbac9994e19b6778341c953fbc49caba2d2faa16387127dd`. The R5 source registered for the bow and curl silhouettes was `C:/Users/vic-l/Downloads/f9a08a26-a8cc-4ed7-9b47-2e09e868a6c1.png`, SHA-256 `97320e79c886e506b5418e60d2dbbe786060c6c2c9db1c81310e0af0a00af00a`.

Redrawing the three pennants and shortening the matching spires moves the gold away from the high and right rims. The architectural bases and ornaments scale uniformly in XY by 13/14. The 28 other contours agree with scaled R5 to within 0.00012 mm after four-decimal exchange rounding. All original local relief heights, colors and the R5 relief map are retained. The [comparison](flag_comparison.png) enlarges R5 and R6 to the same apparent width for checking the gaps. The [full R6 front](castle_front.png) carries its own 185 dpi nominal print scale.

## Mechanical registration

The source master still places the origin at (310, 301) in its drawing grid. Use X = (u − 310) × 130/552, Y = (301 − v) × 130/552. The star extends from Y −60.659 to +61.938 mm. The visual grip lies on X = 0. Its illustrated dimensions follow the scaled composition. The full-size card, its insertion path, chin, retainer and actual grip come from the mechanical CAD. Import the already-scaled R6 polygons at 1:1 in millimeters.

The bow footprint spans 55.96 × 39.76 mm, from Y −71.589 to −31.833 mm. Its projected overlap with the fixed star is 882.20 mm² overall and 374.55 mm² under each raised loop. This gives CAD room to integrate broad continuous supports or mating lands. The actual contact patch depends on the surfaces modeled behind the bow. No pins, socket geometry or other mechanical attachment parts are defined by this artwork.

## Frozen outputs

| R6 artifact | SHA-256 |
| --- | --- |
| [Editable front vector](castle_front.svg) | `9258a0a0d2347132d66720457b8056754b517fe593edc0e7e249d5b1abef8e0e` |
| [34 CAD profiles](castle_profiles.json) | `ff1b7d81a01e941be9c393d3b716d585c54cd923cb2af1f61c3441d363779094` |
| [Relief targets](relief_map.json) | `0a73df176ea6965100df1e30e2ab8e6ef9c29b43f17cfa8f05a5e893c9331611` |
| [Transparent front](castle_front.png) | `980bad9e0cbbdd6dc67a56e371246d2f8537497d767c55866eb8bcd1e5882a4d` |
| [Pennant detail](flag_clearance_detail.png) | `86d5268840517135049297309127e6880824c71adab4dbcadc32393a58363c19` |
| [Comparison](flag_comparison.png) | `91f3800fddc71b7d70b14f911ea9615aa7b8c56a0f0334d11964facd9569acd0` |
| [Contour and clearance checks](compact_checks.json) | `067869665be6de014869ffba9afa1b6d72a509df3e534ddabd6280ef48a29213` |
| [Builder](prepare_compact.py) | `9704e79aeaaf2791e3b0912197314eb19d12346d8d5707cdeb7055dc0b44cd1c` |

The author reviewed the saved front and enlarged pennant comparison. All 34 profiles are valid. User selection, assembly geometry, card retention, printed adhesion and physical handling are separate checks.
