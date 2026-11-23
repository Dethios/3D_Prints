# ASA-CF08 275 °C anchored sample map

This rerun uses 11 spaced stations with a small printed anchor fused to each blob. The short strip off to the side of each station is separate purge material. Weigh each blob together with its attached anchor, and exclude the purge strip. Skip any station where the anchor or sample moved or mixed with another sample.

Use the physical front edge of the Voron as the reference. X increases to the right and Y increases toward the rear. The raw webcam feed used during monitoring was rotated 180°. In the corrected photo, X90 is on the left, X175 is in the center, and X260 is on the right. The rear row (Y235) is at the top and the front row (Y70) is at the bottom.

| Y (mm) from front | X90, left | X175, center | X260, right |
|---:|---:|---:|---:|
| 70 | 4, reference A | 22 | 30 |
| 125 | 10 | 24 | 32 |
| 180 | 14 | 26 | 4, reference B |
| 235 | 18 | 28 | |

Values in the grid are commanded mm³/s. Weigh the two reference assemblies first and average their masses. Repeat the column if the references differ by more than 2% of their mean. Correct for the nominal 6.38 mm of filament in each anchor using the formula below.

`Blob flow loss (%) = 100 × (1 − assembly mass ÷ mean reference assembly mass) × (206.38 ÷ 200)`

The correction assumes each anchor printed consistently. Select the highest rate in a consistent sequence within 2% loss, start the PrusaSlicer cap 10% below it, and verify on a real print. If the last rate passes, the result establishes a lower bound. This test holds 275 °C at the hotend, 100 °C at the bed and the part fan off.

## Completed run in the corrected photo

Read from the top of the corrected photo toward the bottom. Values are commanded mm³/s.

| Photo row | Physical left | Center | Physical right |
|---|---:|---:|---:|
| Top (Y235) | 18 | 28 | Empty |
| Second (Y180) | 14 | 26 | 4, reference B |
| Third (Y125) | 10 (right-hand blob of the left pair) | 24 | 32 |
| Bottom (Y70) | Empty | 22 | 30 |

In the left pair of the third row, the right-hand blob matches the 10 mm³/s station. The farther-left blob is unassigned. Use the intact 4 mm³/s reference B by itself for provisional calculations.

## Measured results at 275 °C

These calculations use reference B (0.493 g) and the nominal anchor correction. Reference A was unavailable.

| Commanded flow (mm³/s) | Assembly mass (g) | Corrected loss |
|---:|---:|---:|
| 4 | 0.493 | Reference B |
| 10 | 0.474 | 3.98% |
| 14 | 0.486 | 1.47% |
| 18 | 0.482 | 2.30% |
| 22 | 0.471 | 4.60% |
| 24 | 0.465 | 5.86% |
| 26 | 0.465 | 5.86% |
| 28 | 0.453 | 8.37% |
| 30 | 0.367 | 26.37% |
| 32 | 0.291 | 42.28% |

14 mm³/s was the highest tested rate under the 2% loss criterion. The 10 mm³/s result was lighter than the 14 and 18 mm³/s results, so the run did not establish a consistent passing sequence. **Provisional PrusaSlicer cap: 12.6 mm³/s at 275 °C** (14 × 0.90). Repeat the low-flow baseline and points near the threshold to confirm.
