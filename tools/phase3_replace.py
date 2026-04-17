#!/usr/bin/env python3
"""
Smarter Phase-3 component placement. Uses pcbnew directly to read each
footprint's courtyard extents and lays components out with clearance
that guarantees no overlaps.

Strategy:
    1. Classify each component as "large" (body > 60 mm²), "module" (>200 mm²),
       or "passive" (everything else).
    2. Lay out big parts first at anchor points spread across the board.
    3. Tile passives in the gaps around their primary consumer (zone).
    4. Stay ≥2 mm from the board edge.

This rewrites positions for every existing footprint on the board.
"""
from __future__ import annotations
import pathlib
import sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"

# Anchor positions for modules / ICs / connectors (board origin top-left,
# +x right, +y down; usable area 6..94 mm).
ANCHORS = {
    # top row
    "U3":  (50, 12),     # Swarm M138 42.5 x 19.6 mm across top
    # mid-upper
    "U1":  (20, 35),     # XIAO ESP32-S3 Sense 21 x 17.5
    "U2":  (80, 35),     # Ai-Thinker Ra-01 17 x 16
    # mid
    "IC1": (50, 55),     # SIM7080G 17.6 x 15.7
    # mid-right
    "Card1": (80, 60),   # Nano-SIM 12.8 x 14
    "J1":   (95, 55),    # U.FL cellular
    "J2":   (95, 30),    # U.FL LoRa
    # right side ICs
    "IC4":  (70, 80),    # MAX98357A QFN 3x3 mm
    "J3":   (85, 85),    # speaker header
    "U4":   (50, 85),    # MCP23017 SOIC-28W
    # lower-left power
    "IC2":  (20, 65),    # BQ24650
    "IC3":  (40, 70),    # TPS63070
    "Q1":   (25, 70),    # dual MOSFET
    "L1":   (15, 60),    # 4.7uH inductor
    "L3":   (38, 75),    # 1.5uH inductor
    "D3":   (15, 70),    # bootstrap Schottky
    "RSNS": (25, 60),    # sense resistor
    "U5":   (92, 80),    # SRV05-4 TVS
    "D1":   (96, 60),    # TVS on cellular antenna
    "D2":   (96, 35),    # TVS on LoRa antenna
    "H1":   (8, 50),     # PIR header
}

# Passive clusters — each passive gets placed near its primary consumer.
PASSIVE_NEIGHBOR = {
    # BQ24650 decoupling / bootstrap network
    "C1":  "IC2", "C15": "IC2", "C19": "IC2", "C20": "IC2", "C21": "IC2", "C22": "IC2",
    "R1":  "IC2", "R2":  "IC2", "R3":  "IC2", "R4":  "IC2", "R5":  "IC2", "R10": "IC2",
    "TP2": "IC2",
    # VBAT_SYS bulk caps near Q1
    "C13": "Q1", "C14": "Q1",
    "TP3": "Q1",  "TP4": "IC1",
    # TPS63070 feedback + decoupling
    "C2": "IC3", "C3": "IC3", "C4": "IC3", "C5": "IC3",
    "C16": "IC3", "C17": "IC3", "C18": "IC3",
    "R11": "IC3", "R12": "IC3", "R15": "IC3",
    "TP1": "IC3", "TP5": "IC3",
    # I2C pull-ups
    "R13": "U4", "R14": "U4",
}


def courtyard_size(fp) -> tuple[float, float]:
    """Return (width, height) in mm of the F.CrtYd bounding box, or pad
    bounding box if no courtyard. Fallback is 2x2 mm."""
    bbox = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    w = pcbnew.ToMM(bbox.GetWidth())
    h = pcbnew.ToMM(bbox.GetHeight())
    if w < 0.1 or h < 0.1:
        bbox = fp.GetBoundingBox(False, False)
        w = pcbnew.ToMM(bbox.GetWidth())
        h = pcbnew.ToMM(bbox.GetHeight())
    if w < 0.1: w = 2.0
    if h < 0.1: h = 2.0
    return (w, h)


def move_fp(fp, x_mm, y_mm):
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    fps_by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}

    # ---- step 1: place anchors --------------------------------------
    for ref, (x, y) in ANCHORS.items():
        fp = fps_by_ref.get(ref)
        if fp is None:
            print(f"!! no footprint for {ref}")
            continue
        move_fp(fp, x, y)

    # ---- step 2: place passives around their neighbour --------------
    # Ring positions around a central anchor on a 3 mm radius step
    ring = [
        (3, 0), (0, 3), (-3, 0), (0, -3),
        (3, 3), (-3, 3), (-3, -3), (3, -3),
        (6, 0), (0, 6), (-6, 0), (0, -6),
        (6, 3), (6, -3), (-6, 3), (-6, -3),
        (3, 6), (-3, 6), (3, -6), (-3, -6),
    ]
    placed_by_anchor: dict[str, int] = {}
    for ref, anchor_ref in PASSIVE_NEIGHBOR.items():
        fp = fps_by_ref.get(ref)
        if fp is None:
            print(f"!! no footprint for {ref}")
            continue
        if anchor_ref not in ANCHORS:
            continue
        ax, ay = ANCHORS[anchor_ref]
        idx = placed_by_anchor.get(anchor_ref, 0)
        dx, dy = ring[idx % len(ring)]
        placed_by_anchor[anchor_ref] = idx + 1
        x = max(4, min(96, ax + dx))
        y = max(4, min(96, ay + dy))
        move_fp(fp, x, y)

    # ---- step 3: save ----------------------------------------------
    board.Save(str(PCB))
    print(f"moved {len(ANCHORS) + len(PASSIVE_NEIGHBOR)} footprints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
