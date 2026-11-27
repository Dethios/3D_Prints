# R6 K2 trial plates

R6 has a 130 mm star, inset flag pennants and a covered bottom-loading card channel. The full-size threaded grip closes the channel. Use the [CAD assembly and coupon instructions](../../cad/R6/README.md) for alignment, bonding and loading.

The K2 0.4 mm Polymaker ASA starting profile sliced all six projects in PrusaSlicer 2.9.7. They use 0.12 mm layers above the first layer. The front, rear and frame use solid rectilinear infill. Their neck bridges run across the opening, with longest front and rear bridge moves below 7.6 mm. The wipe tower is disabled in each saved project. The installed preset was preserved.

| Trial plate | CFS slots | Slicer estimate |
| --- | --- | --- |
| [Slot and thread coupon](K2_04_ASA_Castle_R6_Slot_and_Thread_Coupon.3mf) | A purple | 3 h 1 min |
| [Castle star face](K2_04_ASA_Castle_R6_Star_Face.3mf) | A purple, B gold, C cream, D blue | 4 h 48 min |
| [Rear shell](K2_04_ASA_Castle_R6_Rear_Shell.3mf) | A purple | 2 h 46 min |
| [Pocket frame](K2_04_ASA_Castle_R6_Pocket_Frame.3mf) | A purple | 1 h 14 min |
| [Threaded grip](K2_04_ASA_Castle_R6_Threaded_Grip.3mf) | A purple, B gold | 7 h 15 min |
| [Pink bow](K2_04_ASA_Castle_R6_Pink_Bow.3mf) | A pink | 49 min |

Each plate sliced without warnings. Support generation is enabled for the relevant shell and grip plates, but the audited G-code emitted no support paths. The coupon should be used by an adult at the workbench to check slot travel, thread fit and actual card thickness. Full wand retention, loosening, drop, bond and reader checks are pending. The coupon is an assembly tool.

The [preflight report](preflight.json) records the exact meshes, profile overrides, startup and shutdown macros, tools, first-layer and flag path measurements.
