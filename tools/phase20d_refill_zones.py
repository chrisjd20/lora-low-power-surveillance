#!/usr/bin/env python3
"""Phase 20d: refill copper zones after surgical edits."""
from __future__ import annotations
import pathlib, sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"


def main() -> int:
    b = pcbnew.LoadBoard(str(PCB))
    zones = list(b.Zones())
    print(f"   refilling {len(zones)} zones...")
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(zones)
    b.Save(str(PCB))
    print("   saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
