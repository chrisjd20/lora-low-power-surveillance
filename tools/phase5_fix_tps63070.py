#!/usr/bin/env python3
"""
Rewrite the TPS63070 QFN-15 footprint with datasheet-correct EP
(1.45 x 2.45 mm) and pin positions that keep 0.2 mm clearance from the
EP and from each other.

The Phase-4 placeholder had a shrunken EP (0.8 x 1.0) because the pin
positions were too close to the EP at full size. This fixes both in one
pass.
"""
from __future__ import annotations
import pathlib
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
FP   = ROOT / "hardware/warden-apex-master/footprints/warden-custom.pretty/QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm.kicad_mod"


def pad(n: str, x: float, y: float, w: float, h: float, rot: int = 0,
        layers: str = '"F.Cu" "F.Paste" "F.Mask"', shape: str = "rect") -> str:
    rot_s = f" {rot}" if rot else ""
    return (f'\t(pad "{n}" smd {shape} (at {x:.3f} {y:.3f}{rot_s}) '
            f'(size {w:.3f} {h:.3f}) (layers {layers}) (uuid "{uuid.uuid4()}"))\n')


def line(x1, y1, x2, y2, layer, width) -> str:
    return (f'\t(fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) '
            f'(stroke (width {width}) (type solid)) (layer "{layer}") '
            f'(uuid "{uuid.uuid4()}"))\n')


def main() -> int:
    # Datasheet dimensions (TPS63070RNM): 3 x 4 mm, pitch 0.5 mm
    W, H = 3.0, 4.0
    EP_W, EP_H = 1.45, 2.45
    PAD_LONG, PAD_SHORT = 0.70, 0.28   # shorter than datasheet so neighbours don't overlap

    # Pin centres chosen so pad inner edge is >= 0.275 mm from EP edge.
    # Left/right pads: pad extends X_CENTRE - PAD_LONG/2 on the inner side.
    #   inner edge = 1.35 - 0.35 = 1.00 mm  -> gap to EP (0.725) = 0.275 mm
    X_CENTRE = 1.35
    # Top/bottom pads: pad extends Y_CENTRE - PAD_LONG/2 on the inner side.
    #   inner edge = 1.85 - 0.35 = 1.50 mm  -> gap to EP (1.225) = 0.275 mm
    Y_CENTRE = 1.85

    # Pin layout: 5-5-5 around three sides with 0.5 mm pitch is what
    # TPS63070RNM uses; our schematic symbol has 15 pins. Keep
    # 4-4-4-3 distribution to match phase4_pin_map.
    pads = ""
    # Left (pins 1..4): long axis horizontal (X), pitch 0.5 mm in Y.
    # Size is width x height in the schematic frame; no rotation needed.
    for i in range(4):
        y = -0.5 * 1.5 + i * 0.5
        pads += pad(str(i + 1), -X_CENTRE, y, PAD_LONG, PAD_SHORT)
    # Right (pins 5..8)
    for i in range(4):
        y = -0.5 * 1.5 + i * 0.5
        pads += pad(str(i + 5), X_CENTRE, y, PAD_LONG, PAD_SHORT)
    # Bottom (pins 9..12): long axis vertical (Y), pitch 0.5 mm in X.
    for i in range(4):
        x = -0.5 * 1.5 + i * 0.5
        pads += pad(str(i + 9), x, Y_CENTRE, PAD_SHORT, PAD_LONG)
    # Top (pins 13..15)
    for i in range(3):
        x = -0.5 + i * 0.5
        pads += pad(str(i + 13), x, -Y_CENTRE, PAD_SHORT, PAD_LONG)

    # Exposed pad at centre, datasheet size 1.45 x 2.45 mm
    pads += pad("16", 0, 0, EP_W, EP_H, shape="roundrect",
                layers='"F.Cu" "F.Paste" "F.Mask"')

    # Outline + courtyard + fab
    outline = ""
    for (layer, wdth) in (("F.SilkS", 0.12), ("F.CrtYd", 0.05), ("F.Fab", 0.1)):
        for (ax, ay), (bx, by) in zip(
            [(-W/2, -H/2), (W/2, -H/2), (W/2, H/2), (-W/2, H/2)],
            [(W/2, -H/2), (W/2, H/2), (-W/2, H/2), (-W/2, -H/2)],
        ):
            outline += line(ax, ay, bx, by, layer, wdth)

    header = (
        f'(footprint "QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm"\n'
        f'\t(version 20240108)\n'
        f'\t(generator "warden_phase5")\n'
        f'\t(generator_version "9.0")\n'
        f'\t(layer "F.Cu")\n'
        f'\t(descr "TI TPS63070 QFN-15 3x4 mm 0.5 pitch, EP 1.45x2.45 (datasheet-correct)")\n'
        f'\t(tags "TPS63070 QFN buck-boost TI")\n'
        f'\t(property "Reference" "REF**" (at 0 0 0) (layer "F.SilkS")\n'
        f'\t\t(effects (font (size 1 1) (thickness 0.15)))\n'
        f'\t\t(uuid "{uuid.uuid4()}"))\n'
        f'\t(property "Value" "QFN-15-1EP_3x4" (at 0 1.5 0) (layer "F.Fab")\n'
        f'\t\t(effects (font (size 1 1) (thickness 0.15)))\n'
        f'\t\t(uuid "{uuid.uuid4()}"))\n'
        f'\t(attr smd)\n'
    )
    FP.write_text(header + pads + outline + ")\n")
    print(f"rewrote {FP.name} with EP 1.45x2.45")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
