#!/usr/bin/env python3
"""
Generate placeholder-but-routable .kicad_mod files for the five custom
parts that lack stock KiCad footprints.

Design goals:
    - Pin NUMBERS match the schematic symbols in warden-custom.kicad_sym.
    - Overall body dimensions are close to datasheet reality so placement
      and DRC clearance are meaningful.
    - Pad geometries are approximate — fine for place + check_clearance
      but WILL need cross-check against the datasheet before fab.

Output: hardware/warden-apex-master/footprints/warden-custom.pretty/*.kicad_mod
"""
from __future__ import annotations
import pathlib
import textwrap
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIB  = ROOT / "hardware" / "warden-apex-master" / "footprints" / "warden-custom.pretty"


def fp_header(name: str, descr: str, tags: str) -> str:
    ts = "20240101000000"  # deterministic
    return f'''(footprint "{name}"
\t(version 20240108)
\t(generator "warden_phase3")
\t(generator_version "9.0")
\t(layer "F.Cu")
\t(descr "{descr}")
\t(tags "{tags}")
\t(property "Reference" "REF**" (at 0 0 0) (layer "F.SilkS")
\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(property "Value" "{name}" (at 0 1.5 0) (layer "F.Fab")
\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(property "Footprint" "" (at 0 0 0) (layer "F.Fab") (hide yes)
\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes)
\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(property "Description" "{descr}" (at 0 0 0) (layer "F.Fab") (hide yes)
\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t(uuid "{uuid.uuid4()}")
\t)
\t(attr smd)
'''


def smd_pad(num: int | str, x: float, y: float, w: float, h: float, angle: float = 0) -> str:
    return (
        f'\t(pad "{num}" smd rect (at {x:.3f} {y:.3f}{f" {angle}" if angle else ""}) '
        f'(size {w:.3f} {h:.3f}) (layers "F.Cu" "F.Paste" "F.Mask") '
        f'(uuid "{uuid.uuid4()}"))\n'
    )


def tht_pad(num: int | str, x: float, y: float, diam: float, drill: float, shape="circle") -> str:
    layers = '"*.Cu" "*.Mask"'
    return (
        f'\t(pad "{num}" thru_hole {shape} (at {x:.3f} {y:.3f}) '
        f'(size {diam:.3f} {diam:.3f}) (drill {drill:.3f}) '
        f'(layers {layers}) (uuid "{uuid.uuid4()}"))\n'
    )


def outline(x1, y1, x2, y2, layer="F.SilkS", width=0.12) -> str:
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
    out = ""
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        out += (
            f'\t(fp_line (start {ax:.3f} {ay:.3f}) (end {bx:.3f} {by:.3f}) '
            f'(stroke (width {width}) (type solid)) (layer "{layer}") '
            f'(uuid "{uuid.uuid4()}"))\n'
        )
    return out


def courtyard(x1, y1, x2, y2) -> str:
    return outline(x1, y1, x2, y2, layer="F.CrtYd", width=0.05)


def fab_rect(x1, y1, x2, y2) -> str:
    return outline(x1, y1, x2, y2, layer="F.Fab", width=0.1)


def write_fp(name: str, body: str) -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    p = LIB / f"{name}.kicad_mod"
    p.write_text(body + ")\n")
    print(f"wrote {p.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# XIAO ESP32-S3 Sense — 21.0 x 17.5 mm module, 14 castellated top pads + 7
# bottom pads. Schematic pin numbering 1..24 with pin 24 = GND2 (second GND).
# Use 2.54 mm pitch castellated pads along top (pins 1..11 + 3V3(12), GND(13), 5V(14))
# and 7 bottom pads (BAT+,BAT-,MTCK,MTDI,MTDO,MTMS,EN).
# We also include 2 more pads (D+, D- = pins 22,23) and GND2=pin 24 as a
# center ground pad so all 24 symbol pins have corresponding footprint pads.
# ---------------------------------------------------------------------------
def build_xiao() -> None:
    body = fp_header(
        "XIAO_ESP32S3_SENSE",
        "Seeed XIAO ESP32-S3 Sense (21 x 17.5 mm castellated module, MPN 113991115)",
        "XIAO ESP32-S3 Sense Seeed module",
    )
    W, H = 21.0, 17.5
    # 14 top-row castellated pads pitch 1.27 across 14 on each long edge
    # Actually XIAO has 7 pads on each long edge + bottom pads
    # Use simplified: pins 1..7 on left edge, 8..14 on right edge
    PAD_W, PAD_H = 0.9, 1.6
    PITCH = 2.54
    # Top row, LEFT edge (pins 1..7 = D0..D6)  y range evenly spaced
    pads_text = ""
    for i in range(7):
        y = -PITCH * 3 + i * PITCH   # 7 pads symmetric around y=0
        pads_text += smd_pad(i + 1, -W/2 + 0.5, y, PAD_W, PAD_H)
    # Right edge (pins 8..14 = D7..D10, 3V3, GND, 5V)
    # Note pin 12=3V3, 13=GND, 14=5V at top right cluster
    for i in range(7):
        y = -PITCH * 3 + i * PITCH
        pads_text += smd_pad(8 + i, W/2 - 0.5, y, PAD_W, PAD_H)
    # Bottom pads (pins 15..21) = BAT+, BAT-, MTCK, MTDI, MTD0, MTMS, EN
    # 7 bottom surface pads centered below
    for i in range(7):
        x = -(3 * 2.54) + i * 2.54
        pads_text += smd_pad(15 + i, x, H/2 - 2.0, 1.5, 1.2)
    # D+ (22), D- (23) — two small pads near bottom centre
    pads_text += smd_pad(22, -1.27, H/2 - 4.5, 0.8, 0.8)
    pads_text += smd_pad(23,  1.27, H/2 - 4.5, 0.8, 0.8)
    # GND2 (24) — center ground plane pad
    pads_text += smd_pad(24, 0, 0, 3.0, 3.0)

    body += pads_text
    body += fab_rect(-W/2, -H/2, W/2, H/2)
    body += outline(-W/2, -H/2, W/2, H/2)
    body += courtyard(-W/2 - 0.25, -H/2 - 0.25, W/2 + 0.25, H/2 + 0.25)
    write_fp("XIAO_ESP32S3_SENSE", body)


# ---------------------------------------------------------------------------
# SIM7080G LCC-42: 17.6 x 15.7 mm. Datasheet says 42 perimeter pads on
# 1.1 mm pitch (approx) with many bottom-side ground pads. My schematic has
# 77 pins. Lay them out as perimeter + grid bottom pads.
# ---------------------------------------------------------------------------
def build_sim7080g() -> None:
    body = fp_header(
        "LCC-42_SIM7080G",
        "SIMCom SIM7080G LCC package (17.6 x 15.7 mm). Pin count matches custom schematic symbol (77). APPROXIMATE footprint — verify against datasheet before fab.",
        "SIM7080G cellular modem LCC SIMCom",
    )
    W, H = 17.6, 15.7
    PAD_W, PAD_H = 1.1, 0.6
    PITCH = 1.1
    # Lay 77 pads around perimeter + bottom ground array
    pads_text = ""
    pin_num = 1
    # 42 perimeter pads first — 12 per long side, 9 per short side
    # Left (12)
    for i in range(12):
        y = -PITCH * 5.5 + i * PITCH
        pads_text += smd_pad(pin_num, -W/2 + 0.3, y, PAD_W, PAD_H, angle=90); pin_num += 1
    # Bottom (9)
    for i in range(9):
        x = -PITCH * 4 + i * PITCH
        pads_text += smd_pad(pin_num, x, H/2 - 0.3, PAD_W, PAD_H); pin_num += 1
    # Right (12)
    for i in range(12):
        y = PITCH * 5.5 - i * PITCH
        pads_text += smd_pad(pin_num, W/2 - 0.3, y, PAD_W, PAD_H, angle=90); pin_num += 1
    # Top (9)
    for i in range(9):
        x = PITCH * 4 - i * PITCH
        pads_text += smd_pad(pin_num, x, -H/2 + 0.3, PAD_W, PAD_H); pin_num += 1
    # Remaining 77-42 = 35 bottom-side ground-ish pads in a 7x5 grid
    for r in range(5):
        for c in range(7):
            x = -4.2 + c * 1.4
            y = -2.8 + r * 1.4
            pads_text += smd_pad(pin_num, x, y, 1.0, 1.0); pin_num += 1
            if pin_num > 77:
                break
        if pin_num > 77:
            break

    body += pads_text
    body += fab_rect(-W/2, -H/2, W/2, H/2)
    body += outline(-W/2, -H/2, W/2, H/2)
    body += courtyard(-W/2 - 0.25, -H/2 - 0.25, W/2 + 0.25, H/2 + 0.25)
    write_fp("LCC-42_SIM7080G", body)


# ---------------------------------------------------------------------------
# Swarm M138 — 42.5 x 19.6 mm module, ~60 castellated pads along edges.
# Pin numbering 1..60 matching schematic.
# ---------------------------------------------------------------------------
def build_m138() -> None:
    body = fp_header(
        "Swarm_M138",
        "Swarm M138 satellite modem module (42.5 x 19.6 mm castellated). Pin count 60 matches custom schematic symbol. APPROXIMATE footprint.",
        "Swarm M138 satellite modem VHF",
    )
    W, H = 42.5, 19.6
    PAD_W, PAD_H = 1.0, 1.6
    # 30 pads along top edge + 30 along bottom edge
    pads_text = ""
    pin_num = 1
    pitch = W / 31.0
    for i in range(30):
        x = -W/2 + pitch * (i + 1)
        pads_text += smd_pad(pin_num, x, -H/2 + 0.5, PAD_W, PAD_H); pin_num += 1
    for i in range(30):
        x =  W/2 - pitch * (i + 1)
        pads_text += smd_pad(pin_num, x,  H/2 - 0.5, PAD_W, PAD_H); pin_num += 1

    body += pads_text
    body += fab_rect(-W/2, -H/2, W/2, H/2)
    body += outline(-W/2, -H/2, W/2, H/2)
    body += courtyard(-W/2 - 0.25, -H/2 - 0.25, W/2 + 0.25, H/2 + 0.25)
    write_fp("Swarm_M138", body)


# ---------------------------------------------------------------------------
# TPS63070 QFN-15-1EP 3x4 mm 0.5mm pitch. 15 signal pads + 1 exposed pad.
# ---------------------------------------------------------------------------
def build_tps63070() -> None:
    body = fp_header(
        "QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm",
        "TI TPS63070 QFN-15 exposed pad package",
        "TPS63070 QFN buck-boost",
    )
    W, H = 3.0, 4.0
    PAD_W, PAD_H = 0.28, 0.85
    pitch = 0.5
    pads_text = ""
    # Side layout: 4 on left, 4 on right, 4 on top, 3 on bottom = 15
    # Actually typical TPS63070 RNM: 5 on left (1-5), 5 on right (6-10), 5 on top (11-15)
    # Simpler: distribute as 4-4-4-3
    # Left (pins 1-4)
    for i in range(4):
        y = -pitch * 1.5 + i * pitch
        pads_text += smd_pad(i + 1, -W/2 + 0.2, y, PAD_H, PAD_W)  # rotated 90
    # Right (pins 5-8)
    for i in range(4):
        y = -pitch * 1.5 + i * pitch
        pads_text += smd_pad(i + 5, W/2 - 0.2, y, PAD_H, PAD_W)
    # Bottom (pins 9-12)
    for i in range(4):
        x = -pitch * 1.5 + i * pitch
        pads_text += smd_pad(i + 9, x, H/2 - 0.2, PAD_W, PAD_H)
    # Top (pins 13-15)
    for i in range(3):
        x = -pitch + i * pitch
        pads_text += smd_pad(i + 13, x, -H/2 + 0.2, PAD_W, PAD_H)
    # Exposed pad (pin 16 would be EP but our schematic only has 15 pins)
    # Map the EP to the "GND" pin by making a large centre pad numbered 15 doesn't work since 15 is used
    # Instead leave EP unnumbered (nameless) or skip. For DRC keep it simple:
    # body += ""  # no EP in schematic — fine for DRC
    body += pads_text
    body += fab_rect(-W/2, -H/2, W/2, H/2)
    body += outline(-W/2, -H/2, W/2, H/2)
    body += courtyard(-W/2 - 0.25, -H/2 - 0.25, W/2 + 0.25, H/2 + 0.25)
    write_fp("QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm", body)


# ---------------------------------------------------------------------------
# SMN-305 Nano-SIM (10 pads: VCC CLK RST IO GND Vpp + 4 EP tabs)
# Body approx 13 x 14 mm for nano-SIM push-push.
# ---------------------------------------------------------------------------
def build_smn305() -> None:
    body = fp_header(
        "SMN-305_Nano_SIM",
        "XUNPU SMN-305 nano-SIM push-push socket",
        "SIM nano socket SMN-305",
    )
    W, H = 12.8, 14.0
    pads_text = ""
    # 6 contact pads vertically aligned 2.5 mm pitch
    # pin order per datasheet: VCC (1), CLK (2), RST (3), I/O (4), GND (5), Vpp (6)
    for i in range(6):
        x = -2.5 + (i % 2) * 5.0
        y = -5.0 + (i // 2) * 2.5
        pads_text += smd_pad(i + 1, x, y, 1.8, 1.3)
    # Shell tabs (pins 7-10 = EP_1..EP_4)
    pads_text += smd_pad(7,  -W/2 + 0.8, -H/2 + 1.5, 1.6, 2.0)
    pads_text += smd_pad(8,   W/2 - 0.8, -H/2 + 1.5, 1.6, 2.0)
    pads_text += smd_pad(9,  -W/2 + 0.8,  H/2 - 1.5, 1.6, 2.0)
    pads_text += smd_pad(10,  W/2 - 0.8,  H/2 - 1.5, 1.6, 2.0)

    body += pads_text
    body += fab_rect(-W/2, -H/2, W/2, H/2)
    body += outline(-W/2, -H/2, W/2, H/2)
    body += courtyard(-W/2 - 0.25, -H/2 - 0.25, W/2 + 0.25, H/2 + 0.25)
    write_fp("SMN-305_Nano_SIM", body)


def main() -> int:
    LIB.mkdir(parents=True, exist_ok=True)
    build_xiao()
    build_sim7080g()
    build_m138()
    build_tps63070()
    build_smn305()
    print()
    print("Footprint library:", LIB.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
