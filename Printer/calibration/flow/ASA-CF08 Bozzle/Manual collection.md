# ASA-CF08 weighed flow with labeled cups

Use this method if the automatic bed pattern shifts or merges samples. Every weighing sample goes into its own labeled foil cup, one at a time. The test uses your 0.5 mm Bozzle and 1.75 mm ASA-CF08. Each sample is 200 mm of filament in two adjacent 100 mm moves, inside the printer’s verified 101 mm limit per extrusion move.

1. If an automatic job is paused, resolve it before sending any console commands. With the printer idle and the build plate clear, use the printer controls to home and put the nozzle well clear of the plate so a long strand can emerge into a heat-resistant catch cup. Keep cups and hands clear during toolhead motion.
2. Heat the nozzle to 275 °C and purge leftover material into a scrap cup until the ASA-CF08 feed is consistent. Label the weighing cups before starting. Use **275-04A** for the first reference, **275-10**, **275-14**, and so on, then **275-04B** for the last reference. Keep purge, pre-existing strands and between-sample ooze out of the weighing cups. Use tweezers to separate the string once extrusion stops.
3. Place one labeled cup to catch its full sample, then send the whole block below as one command batch with both feed rates set to the value from the table. The example is the **4 mm³/s** reference. Allow about **120 seconds** for one slow reference. Wait for the batch to finish before switching cups.
4. After collecting both references and the test rates, cool and weigh the samples using a 0.001 g scale. Tare each empty cup first, or weigh only the cooled plastic. Turn the nozzle heater off when finished. For a temperature comparison, repeat the same sequence at 270 °C and 280 °C using new labels.

```gcode
SAVE_GCODE_STATE NAME=CF08_CUP_TEST
M83
M220 S100
M221 S100
G1 E100 F100
G1 E100 F100
M400
RESTORE_GCODE_STATE NAME=CF08_CUP_TEST MOVE=0
```

| Target flow (mm³/s) | Feed rate F (mm of filament/min) |
|---:|---:|
| 4 | 100 |
| 10 | 249 |
| 14 | 349 |
| 18 | 449 |
| 22 | 549 |
| 24 | 599 |
| 26 | 649 |
| 28 | 698 |
| 30 | 748 |
| 32 | 798 |

Average the two slow reference masses at each temperature. Flow loss (%) = 100 × (1 − test mass ÷ reference mean). Start with a print cap 10% below the highest consistent test rate with no more than 2% loss, then confirm on a representative part. This pass measures free-air extrusion.
