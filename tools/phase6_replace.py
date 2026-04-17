#!/usr/bin/env python3
"""
Phase-6 placement refinement.

Goals (user-requested):
    1. U1 (XIAO) flanks U3 on the LEFT, U2 (Ra-01) flanks U3 on the RIGHT.
       All three form the top row so the board shifts upward as a whole.
    2. U4 (MCP23017) moved well away from the south board edge.
    3. Spread the BQ24650 and TPS63070 passives so nothing overlaps and
       so small 0805 parts have hand-soldering clearance.
    4. Rotate silk reference text where adjacent labels would collide
       (primarily the 0805 resistor / capacitor rows in the power
       stages).
"""
from __future__ import annotations
import pathlib
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"


# ---------------------------------------------------------------------------
# Explicit coordinates + rotation for every non-mounting-hole footprint.
# Layout zones (board is 0..100 mm each axis, MH pads at each corner
# taking up 0.9..6.1 mm):
#
#   y =  6 .. 24   TOP ROW   U1 | U3 | U2  + J2/D2 right, J1/D1 below U2
#   y = 30 .. 52   MID ROW   H1 / IC1 / Card1 / U5
#   y = 58 .. 72   LOWER MID IC4 + J3 (audio)  and  U4 (I/O expander)
#   y = 74 .. 94   POWER     BQ24650 cluster (SW)  +  TPS63070 cluster (mid)
#
# All coordinates are of the FOOTPRINT CENTRE in millimetres.
# ---------------------------------------------------------------------------
PLACEMENT: dict[str, tuple[float, float, float]] = {

    # ---- TOP ROW: radio modules --------------------------------------
    # All three at the same Y; widths sum to 80 mm + gaps + mounting-hole
    # clearance. Layout geometry: U1 right = 28.25, U3 left = 29.5 -> 1.25 mm.
    #                             U3 right = 72.5, U2 left = 74.25 -> 1.75 mm.
    "U1":    (17.5, 15, 0),     # XIAO ESP32-S3 Sense (21 x 17.5)
    "U3":    (51,   15, 0),     # Swarm M138 (42.5 x 19.6)
    "U2":    (83.5, 15, 0),     # Ai-Thinker Ra-01 (17 x 16)

    # RF antennas on the east edge (J2 = LoRa antenna, D2 = TVS on it)
    "J2":    (95, 30, 0),       # U.FL for Ra-01 (moved down away from U2)
    "D2":    (91, 30, 0),       # TVS just west of J2

    # ---- MID ROW -----------------------------------------------------
    "H1":    (7,  34, 90),      # PIR 3-pin header at left edge
    "TP4":   (7,  46, 0),       # MODEM_VBAT test point
    "IC1":   (50, 40, 0),       # SIM7080G (24 x 24)
    "Card1": (78, 42, 0),       # Nano-SIM socket (12.8 x 14)
    "J1":    (95, 38, 0),       # U.FL cellular
    "D1":    (95, 48, 0),       # TVS cellular

    # ---- LOWER MID: audio + IO expander ------------------------------
    "U4":    (78, 64, 90),      # MCP23017 ROTATED vertical (was horizontal)
    "R13":   (66, 60, 0),       # I2C SCL pullup
    "R14":   (66, 63, 0),       # I2C SDA pullup
    "IC4":   (58, 64, 0),       # MAX98357A
    "J3":    (62, 68, 0),       # speaker header
    "U5":    (92, 64, 0),       # SRV05-4 TVS

    # ---- BQ24650 CHARGER CLUSTER: SW quadrant ------------------------
    # Reserved block: x = 4 .. 36, y = 74 .. 94
    # Passive pitch relaxed from 3.0 to 4.0 mm (gave 0.1 mm neighbour
    # clearance, failed) and 0805 caps sit 2.0+ mm clear of modules.
    "IC2":   (19, 80, 0),       # BQ24650 VQFN-16 (3x3)
    "Q1":    (26, 80, 0),       # dual N-MOSFET SOT-23-6
    "L1":    (14, 88, 0),       # 4.7 uH charger inductor (6 x 6) moved east of C column
    "D3":    (15, 74, 0),       # BAT54HT1G bootstrap Schottky
    "RSNS":  (33, 88, 90),      # 20 m-ohm sense 2512 (vertical)
    "C19":   (23, 74, 0),       # bootstrap cap
    "C15":   (6,  74, 90),      # REGN cap (vertical, left edge)
    "C1":    (19, 74, 0),       # 100 nF bulk near IC2
    "C20":   (6,  80, 90),      # SRP filter cap
    "C21":   (6,  84, 90),      # diff filter cap (SRP<->SRN)
    "C22":   (6,  92, 90),      # 100 nF bulk
    "R1":    (30, 72, 90),      # VFB bottom (10 k)  - moved up away from RSNS
    "R2":    (33, 72, 90),      # VFB top (100 k)
    "R3":    (30, 76, 90),      # TS sense (10 k)
    "R4":    (33, 76, 90),      # STAT1 pullup (10 k)
    "R5":    (27, 88, 90),      # STAT2 pullup - moved down-left
    "R10":   (27, 92, 90),      # PG pullup - moved down-left
    "TP2":   (10, 94, 0),       # SOLAR_IN test point (clear of MH3)
    "TP3":   (16, 94, 0),       # VBAT_SYS test point
    "C13":   (20, 94, 0),       # VBAT_SYS bulk 10 uF
    "C14":   (24, 94, 0),       # VBAT_SYS bulk 10 uF

    # ---- TPS63070 CLUSTER: mid-bottom --------------------------------
    # Reserved block: x = 38 .. 70, y = 74 .. 94
    "IC3":   (48, 80, 0),       # TPS63070 QFN-15 (3x4)
    "L3":    (55, 80, 0),       # 1.5 uH buck-boost inductor (4x4)
    "C2":    (40, 74, 0),       # VIN decoupling 100 nF - 4 mm pitch
    "C3":    (44, 74, 0),
    "C4":    (48, 74, 0),
    "C5":    (52, 74, 0),       # VAUX cap
    "C16":   (56, 74, 0),       # VBAT bulk 10 uF
    "C17":   (60, 74, 0),       # VBAT bulk 10 uF
    "C18":   (64, 74, 0),       # 3V3 bulk 10 uF
    "R11":   (62, 80, 90),      # FB top 1 M
    "R12":   (66, 80, 90),      # FB bot 180 k (4 mm pitch)
    "R15":   (40, 80, 90),      # EN pullup 100 k (moved to left side of IC3)
    "TP1":   (52, 90, 0),       # 3V3 test point
    "TP5":   (58, 90, 0),       # 3V3 test point
}


def move_fp(fp, x_mm: float, y_mm: float, angle_deg: float) -> None:
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    fp.SetOrientationDegrees(angle_deg)


def relocate_silk_ref(fp, dx_mm: float = 0, dy_mm: float = -2.3,
                      rot_deg: float | None = None,
                      size_mm: float | None = None,
                      hide: bool = False) -> None:
    """Move the Reference text (designator on F.SilkS) to a clean offset
    from the footprint centre."""
    ref = fp.Reference()
    if ref is None:
        return
    if hide:
        ref.SetVisible(False)
        return
    ref.SetTextPos(pcbnew.VECTOR2I(
        fp.GetPosition().x + pcbnew.FromMM(dx_mm),
        fp.GetPosition().y + pcbnew.FromMM(dy_mm),
    ))
    if rot_deg is not None:
        ref.SetTextAngleDegrees(rot_deg)
    if size_mm is not None:
        sz = pcbnew.FromMM(size_mm)
        ref.SetTextSize(pcbnew.VECTOR2I(sz, sz))
        ref.SetTextThickness(pcbnew.FromMM(size_mm * 0.15))
    ref.SetVisible(True)


# Passives placed vertical (rot=90) — label goes to their LEFT, rotated 90.
VERTICAL_LABEL_REFS = {
    "R1", "R2", "R3", "R4", "R5", "R10",
    "R11", "R12", "R15",
    "C15", "C20", "C21", "C22",
    "RSNS",
}

# Passives placed horizontal in a tight row — label above the part,
# smaller font so the text doesn't run into neighbours.
HORIZONTAL_TIGHT_REFS = {
    "C2", "C3", "C4", "C5", "C16", "C17", "C18",
    "C13", "C14", "C1", "C19",
    "D3",
}

# Mounting holes — hide the reference text; it sits on top of the pad
# and triggers silk_over_copper anyway.
HIDE_REFS = {"MH1", "MH2", "MH3", "MH4"}


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    fps_by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}

    moved = 0
    missing: list[str] = []
    for ref, (x, y, ang) in PLACEMENT.items():
        fp = fps_by_ref.get(ref)
        if fp is None:
            missing.append(ref)
            continue
        move_fp(fp, x, y, ang)
        if ref in HIDE_REFS:
            relocate_silk_ref(fp, hide=True)
        elif ref in VERTICAL_LABEL_REFS:
            # Label to the LEFT of body (out of courtyard), rotated 90°,
            # smaller font so pitch-4 mm rows still read cleanly.
            relocate_silk_ref(fp, dx_mm=-2.5, dy_mm=0.0,
                              rot_deg=90, size_mm=0.8)
        elif ref in HORIZONTAL_TIGHT_REFS:
            relocate_silk_ref(fp, dx_mm=0, dy_mm=-1.8,
                              rot_deg=0, size_mm=0.8)
        else:
            relocate_silk_ref(fp, dx_mm=0, dy_mm=-2.3, rot_deg=0)
        moved += 1

    # Also hide mounting hole refs even if we're not "moving" them
    for ref in HIDE_REFS:
        fp = fps_by_ref.get(ref)
        if fp:
            fp.Reference().SetVisible(False)

    if missing:
        print(f"!! missing footprints: {missing}")

    # Re-fill zones so the GND pour reflects the new layout
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    board.Save(str(PCB))
    print(f"moved {moved} footprints ({len(board.Zones())} zones refilled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
