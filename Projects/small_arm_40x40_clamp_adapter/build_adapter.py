"""Build a plate for RostaP's 40 mm clamp and 18 mm small-arm holder.

The holder face is at Z=0 for printing. The screw heads at the inner
pattern are recessed in the clamp face at Z=9.
"""

from pathlib import Path

import cadquery as cq


def square_pattern(pitch: float) -> list[tuple[float, float]]:
    half_pitch = pitch / 2
    return [
        (x, y)
        for x in (-half_pitch, half_pitch)
        for y in (-half_pitch, half_pitch)
    ]


def build() -> cq.Workplane:
    plate = (
        cq.Workplane("XY")
        .rect(54, 54)
        .extrude(9)
        .edges("|Z")
        .fillet(3)
    )
    plate = plate.faces(">Z").workplane().pushPoints(square_pattern(40)).hole(5.6)
    return (
        plate.faces(">Z")
        .workplane()
        .pushPoints(square_pattern(18))
        .cboreHole(4.5, 8.2, 4.5)
    )


if __name__ == "__main__":
    solid = build()
    assert solid.val().isValid() and len(solid.solids().vals()) == 1
    output = Path(__file__).with_name("Small_Arm_18x18_to_Clamp_40x40")
    cq.exporters.export(solid, str(output.with_suffix(".step")))
    cq.exporters.export(
        solid, str(output.with_suffix(".stl")), tolerance=0.03, angularTolerance=0.08
    )
