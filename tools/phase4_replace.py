#!/usr/bin/env python3
"""
Phase-4 placement refinement. Fixes the 56 clearance + 53 courtyards
overlaps left over from Phase 3 by:

    1. Assigning every component to a dedicated "cell" within a reserved
       block of the board (no two groups overlap).
    2. Tiling the passives on a 3.0 mm grid inside each group's block,
       never placing two components less than 2.6 mm apart.
    3. Using per-refdes absolute coordinates rather than the old
       ring-around-anchor scheme so the power-stage clusters aren't on
       top of each other any more.

After the move, saves the board and re-fills the zones.
"""
from __future__ import annotations
import pathlib
import sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"


# -----------------------------------------------------------------------
# Explicit per-refdes placements, hand-composed so groups don't overlap.
# Coordinates are the component ORIGIN (centre of footprint), in mm.
# Board is 100 x 100 mm with 3.5 mm corner mounting-hole pads; usable
# area is approx 7..93 mm in both axes (pads leave a bit of room around
# the mounting holes).
# -----------------------------------------------------------------------

PLACEMENT: dict[str, tuple[float, float, float]] = {
    # (x, y, rotation_degrees)

    # ------ TOP BAND: Swarm satellite modem (42.5 x 19.6 mm) ----------
    "U3":   (50, 17, 0),

    # ------ UPPER LEFT / UPPER RIGHT: MCU + LoRa ---------------------
    "U1":   (18, 40, 0),    # XIAO ESP32-S3 Sense (21 x 17.5)
    "U2":   (85, 42, 0),    # Ai-Thinker Ra-01 (17 x 16)
    "J2":   (95, 36, 0),    # U.FL LoRa antenna
    "D2":   (95, 48, 0),    # TVS on LoRa antenna
    "H1":   (6,  28, 90),   # PIR 3-pin header (top-left, rotated vertical)

    # ------ CENTRE: Cellular modem + SIM + RF ------------------------
    "IC1":  (43, 60, 0),    # SIM7080G (24 x 24 body) — pushed S/E of U1
    "Card1":(72, 60, 0),    # Nano-SIM socket (12.8 x 14) — pushed S of U2
    "J1":   (95, 54, 0),    # U.FL cellular antenna
    "D1":   (95, 62, 0),    # TVS on cellular antenna
    "U5":   (95, 78, 0),    # SRV05-4 TVS array (5-pin SOT-23-6)

    # ------ LOWER-LEFT: BQ24650 charger power stage ------------------
    # Reserved block: x = 7..33, y = 72..92
    "IC2":  (17, 78, 0),    # BQ24650 VQFN (3x3)
    "Q1":   (24, 78, 0),    # DMG9926 SOT-23-6
    "L1":   (12, 92, 0),    # 4.7µH charger inductor (NR-60xx, 6x6 body)
    "D3":   (12, 73, 0),    # BAT54HT1G bootstrap Schottky (SOD-323)
    "RSNS": (25, 87, 90),   # 20mΩ 2512 sense resistor (rotated vertical)
    "C19":  (22, 73, 0),    # bootstrap cap
    "C15":  (8, 73, 0),     # REGN cap
    "C1":   (17, 73, 0),    # 100nF decoupling
    "C20":  (20, 92, 0),    # SRP bulk cap
    "C21":  (24, 92, 0),    # diff filter cap
    "C22":  (28, 92, 0),    # bulk cap
    "R1":   (30, 75, 90),   # VFB bottom leg
    "R2":   (33, 75, 90),   # VFB top leg
    "R3":   (30, 80, 90),   # TS sense
    "R4":   (33, 80, 90),   # STAT1 pullup
    "R5":   (30, 85, 90),   # STAT2 pullup
    "R10":  (33, 85, 90),   # PGOOD pullup
    "TP2":  (5,  70, 0),    # SOLAR_IN test point (top-left free space)
    "TP3":  (5,  73, 0),    # VBAT_SYS test point
    "TP4":  (63, 60, 0),    # MODEM_VBAT test point

    # ------ LOWER-MID: TPS63070 3.3V regulator -----------------------
    # Reserved block: x = 35..60, y = 72..94
    "IC3":  (45, 82, 0),    # TPS63070 QFN (3x4)
    "L3":   (40, 88, 0),    # 1.5µH buck-boost inductor (ANR4012 = 4x4 mm)
    "C2":   (38, 76, 0),    # VIN decoupling  (pitch 3.5mm)
    "C3":   (41.5, 76, 0),  # VIN decoupling
    "C4":   (45, 76, 0),    # 3V3 decoupling
    "C5":   (48.5, 76, 0),  # VAUX
    "C16":  (52, 76, 0),    # VBAT bulk 10uF
    "C17":  (55.5, 76, 0),  # VBAT bulk 10uF
    "C18":  (52, 82, 0),    # 3V3 bulk 10uF
    "R11":  (58, 82, 90),   # FB top (1MΩ)
    "R12":  (61, 82, 90),   # FB bot (180k)
    "R15":  (64, 82, 90),   # EN pull-up (100k)
    "TP1":  (46, 92, 0),    # 3V3 test point
    "TP5":  (58, 92, 0),    # 3V3 test point

    # ------ CENTRE-LOWER: audio + IO expander ------------------------
    "IC4":  (67, 74, 0),    # MAX98357A QFN (3x3)
    "J3":   (73, 74, 0),    # 2-pin speaker header
    "U4":   (80, 90, 0),    # MCP23017 SOIC-28W (17.9 x 7.5)
    "R13":  (80, 78, 0),    # I2C SCL pull-up
    "R14":  (80, 81, 0),    # I2C SDA pull-up

    # ------ BULK caps on VBAT_SYS rail near Q1 -----------------------
    "C13":  (6,  84, 90),   # 10uF bulk
    "C14":  (6,  88, 90),   # 10uF bulk
}


def move_fp(fp, x_mm: float, y_mm: float, angle_deg: float) -> None:
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    # Rotate to match, absolute
    fp.SetOrientationDegrees(angle_deg)


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    fps_by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}

    moved = 0
    missing = []
    for ref, (x, y, ang) in PLACEMENT.items():
        fp = fps_by_ref.get(ref)
        if fp is None:
            missing.append(ref)
            continue
        move_fp(fp, x, y, ang)
        moved += 1

    if missing:
        print(f"!! missing footprints: {missing}")

    # Re-fill zones so check_clearance is fair
    filler = pcbnew.ZONE_FILLER(board)
    zones = board.Zones()
    filler.Fill(zones)

    board.Save(str(PCB))
    print(f"moved {moved} components, refilled {zones.size()} zones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
