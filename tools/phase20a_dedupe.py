#!/usr/bin/env python3
"""Phase 20a: dedupe tracks and vias in place; save."""
from __future__ import annotations
import pathlib, sys
from collections import defaultdict
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"

def main() -> int:
    b = pcbnew.LoadBoard(str(PCB))
    by_key: dict = defaultdict(list)
    for t in b.Tracks():
        if t.GetClass() == "PCB_TRACK":
            s = t.GetStart(); e = t.GetEnd()
            key = ("T", t.GetNetCode(), t.GetLayer(), t.GetWidth(),
                   min((s.x, s.y), (e.x, e.y)),
                   max((s.x, s.y), (e.x, e.y)))
        else:
            p = t.GetPosition()
            key = ("V", t.GetNetCode(), t.GetWidth(), t.GetDrill(), (p.x, p.y))
        by_key[key].append(t)
    to_remove = []
    for lst in by_key.values():
        for t in lst[1:]:
            to_remove.append(t)
    for t in to_remove:
        b.Remove(t)
    print(f"   deduped {len(to_remove)} items", flush=True)
    b.Save(str(PCB))
    print(f"   saved", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
