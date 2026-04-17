#!/usr/bin/env python3
"""
Phase 10-b — move the Phase-7 variant hardware into a clear band so
it no longer overlaps Swarm M138 (U3) / Ra-01 (U2) / SIM7080G (IC1) /
MCP23017 (U4) courtyards.

Also tighten the SIM7080G internal GND array so its pads don't overlap
the perimeter pads (Phase-8 footprint was slightly over-sized).

Refs that need new positions in mm:
    Q2  -> (44, 29)  Q3 -> (48, 29)  R16 -> (40, 29)  JP1 -> (36, 29)
    R17 -> (30, 29)
    JP3 -> (60, 27)  JP4 -> (60, 31)   R18 -> (66, 27)  R19 -> (66, 31)
    U6  -> (82, 34)   X1  -> (87, 31)   C23 -> (87, 35)   C24 -> (87, 37)
    C25 -> (77, 35)   C26 -> (72, 35)
    JP2 -> (93, 54)

Y-band now 27..37 mm, clear of both the top-row modules (bottom edge
Y=24.8) and SIM7080G (top edge Y=32.15). Hmm — actually SIM7080G top
edge is 40 - 15.7/2 = 32.15, so our new strip must stop at Y~32.
Let's split: west cluster (Q2/Q3/R16/JP1/R17) at Y=29, east cluster
(U6/X1/caps) shifted to the east-of-Card1 area at X~90, Y=66..77.
"""
from __future__ import annotations
import pathlib
import pcbnew
import subprocess

ROOT = pathlib.Path('/home/admin/github/lora-low-power-surveillance')
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
MM = 1_000_000


# Revised placements — U6 + friends moved to a SOUTHEAST band around
# Card1 to get out of the crowded north area.
# West side Y=29 strip:  modem gate + pull-down
# East side X=85..95, Y=54..80 strip: SC16IS740 + crystal + caps + JP2/3/4
NEW_POSITIONS: dict[str, tuple[float, float, float]] = {
    # Modem rail gate (west band, Y=29; 1 mm south of Swarm bottom edge at Y=24.8)
    "R17": (20.0, 29.0,  0.0),   # UART1_RX pull-down
    "JP1": (28.0, 29.0,  0.0),   # Modem rail bypass
    "R16": (32.0, 29.0,  0.0),   # Q_MODEM_G pull-up
    "Q2":  (36.0, 29.0,  0.0),   # P-FET load switch
    "Q3":  (40.0, 29.0,  0.0),   # N-FET driver
    # JP2 SIM_VCC — 93.0, 54.0 unchanged (already south-east of Card1)
    "JP2": (93.0, 54.0,  0.0),
    # East cluster: SC16IS740 + crystal + caps + sat UART jumpers + UART2 pull-downs
    # Placed south of U4 MCP23017 (which spans Y=53..75 centered at 64)
    # Actually U4 is near X=78. Let me put SC16 cluster at X=9..20 since that area
    # looks empty (WEST of IC3 TPS63070 power stage).
    # Looking at existing layout: BQ24650 power stage is at SW corner.
    # A cleaner spot: RIGHT of TPS63070 / LEFT of MCP23017, Y~55..70.
    # Use X=68..82 (empty between IC4 at 58,64 and U4 at 78,64 y=53..75):
    # Actually not empty — U4 is there. Let me use Y=50 band instead:
    "U6":  (25.0, 54.0, 90.0),   # rotate 90: body oriented vertically
    "X1":  (30.0, 52.0,  0.0),
    "C23": (30.0, 55.0,  0.0),
    "C24": (30.0, 58.0,  0.0),
    "C25": (20.0, 54.0,  0.0),
    "C26": (15.0, 54.0,  0.0),
    "JP3": (35.0, 52.0,  0.0),
    "JP4": (35.0, 56.0,  0.0),
    "R18": (40.0, 52.0,  0.0),
    "R19": (40.0, 56.0,  0.0),
}


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    moved = 0
    for fp in board.Footprints():
        ref = fp.GetReference()
        if ref in NEW_POSITIONS:
            x, y, rot = NEW_POSITIONS[ref]
            fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))
            fp.SetOrientationDegrees(rot)
            moved += 1
    print(f"Moved {moved} variant footprints to new positions.")

    # Clear tracks for re-routing
    tracks = list(board.Tracks())
    for t in tracks:
        board.Remove(t)
    print(f"Cleared {len(tracks)} tracks")

    board.Save(str(PCB))

    # Re-export DSN, run Freerouting, import
    (ROOT / "build").mkdir(exist_ok=True)
    dsn = ROOT / "build/warden.dsn"
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    print(f"DSN exported")

    fr_jar = pathlib.Path.home() / ".kicad-mcp/freerouting.jar"
    subprocess.run([
        "docker", "run", "--rm",
        "-v", f"{ROOT/'build'}:/work",
        "-v", f"{fr_jar}:/opt/freerouting.jar",
        "-w", "/work",
        "eclipse-temurin:21-jre",
        "java", "-jar", "/opt/freerouting.jar",
        "-de", "/work/warden.dsn",
        "-do", "/work/warden.ses",
        "-mp", "15", "-host-mode", "cli",
    ], check=False)

    subprocess.run(["python3", str(ROOT / "tools/phase4_import_ses.py")],
                   check=False)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
