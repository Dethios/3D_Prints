# ASA-CF08 weighed flow test

Voron 2.4, 0.5 mm Rentable Socks Bozzle, 1.75 mm Polymaker Fiberon ASA-CF08. The bed target is 100 °C and the part fan is off. The planned sweep uses 33 samples across 270, 275 and 280 °C, up to a commanded 32 mm³/s. The 200 mm samples use 6.6 m of filament, approximately 17.4 g at 1.094 g/cm³, before priming.

**Provisional PrusaSlicer cap: 12.6 mm³/s at 275 °C.** The anchored run had one surviving low-flow reference, and the 10 mm³/s sample showed more loss than the 14 mm³/s sample. Repeat the low-flow baseline and near-threshold samples, then confirm the setting on a representative print. See the [anchored sample map and measured results](275C%20anchored%20sample%20map.md) and the [manual collection method](Manual%20collection.md).

## Run the test

1. Confirm the 0.5 mm Bozzle is physically installed. Live Klipper and the saved PrusaSlicer preset both report **0.5 mm**. Klipper reports **1.75 mm** filament, which is the diameter used in the flow calculation.
2. Load dry ASA-CF08, purge the previous filament, and clear the build plate. The automatic sweep uses a local G-code file specific to this Voron’s homing, QGL, Cartographer touch and bed mesh. The manual collection method provides a way to collect samples individually. During the automatic sweep, watch the first sample to make sure it separates cleanly from the nozzle and the prime line. Cancel if filament wraps the nozzle or the extruder grinds or repeatedly skips.
3. Let the samples cool. The short strip to the left of each blob is purge material. Weigh only the blob with a tared 0.001 g scale and record it before removing more samples. Coordinates refer to printer X/Y, with Y increasing away from the front.

| Y (mm) | Commanded flow (mm³/s) | 270 °C (g), X99 | 275 °C (g), X194 | 280 °C (g), X289 |
|---:|---:|---:|---:|---:|
| 45 | 4 (reference A) | | | |
| 65 | 10 | | | |
| 85 | 14 | | | |
| 105 | 18 | | | |
| 125 | 22 | | | |
| 145 | 24 | | | |
| 165 | 26 | | | |
| 185 | 28 | | | |
| 205 | 30 | | | |
| 225 | 32 | | | |
| 245 | 4 (reference B) | | | |

## Choose the PrusaSlicer settings

For each temperature, average the two 4 mm³/s references. If those references differ by more than 2% of their mean, repeat the column before relying on its results. A 200 mm sample is roughly 0.526 g at the published density. Use the measured reference in the calculations.

- Flow loss (%) = 100 × (1 − sample mass ÷ reference mean).
- Delivered flow (mm³/s) ≈ commanded flow × sample mass ÷ reference mean.
- Start with the highest rate in a consistent sequence with **at most 2% loss**, then set the print cap **10% below** that rate. For example, 26 mm³/s passing gives a starting cap of **23.4 mm³/s**. Repeat isolated or borderline results. If the last rate passes, this sweep establishes a lower bound on capacity.
- Compare the temperatures at your intended printing speed. Confirm the chosen temperature and cap on a representative part or coupon, including layer bonding and surface quality. This benchmark measures delivery into open air. Tune extrusion multiplier separately in the actual print.

The upstream VBA raises Z as it extrudes each blob. This adaptation keeps that motion and splits each 200 mm sample into two collinear 100 mm moves at the same rate, with no deliberate pause at the join. On inspection Klipper allowed 101 mm per extrusion-only move, and treats extrusion with Z but no XY motion as extrusion-only. The generator uses Klipper’s temperature and dwell syntax and the homing sequence observed in the live Voron configuration. No firmware edits are required for the observed limits.

[CNC Kitchen benchmark and VBA](https://github.com/CNCKitchen/ExtrusionSystemBenchmark) · [Polymaker material specifications](https://shop.polymaker.com/products/fiberon-asa-cf08/) · [Ellis’s flow tuning guide](https://ellis3dp.com/Print-Tuning-Guide/articles/determining_max_volumetric_flow_rate.html)
