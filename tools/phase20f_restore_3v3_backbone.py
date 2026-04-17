#!/usr/bin/env python3
"""Phase 20f: restore the /3V3 B.Cu backbone + layer-transition via that
got over-aggressively removed in 20e.

Phase 20e removed the entire IC1.69/C29.1 stub tree, which also
contained the cross-board /3V3 B.Cu backbone (22.12, 42.10) ->
(50.83, 42.10) and its F.Cu hop (50.90, 42.16) -> (53.28, 45.46) that
were genuinely needed to keep the west (U6/SC16IS740/J5/XIAO-support)
and east (IC4/U4/U5 etc.) halves of /3V3 connected.

This phase re-adds just those bridge elements - NOT the stubs that led
to IC1.69 / C29.1.  /SIM_VDD_EXT remains a separate, isolated net.
"""
from __future__ import annotations
import pathlib, sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"


def _mm(v): return int(round(v * 1e6))


def _net(b, name):
    for k, n in b.GetNetsByName().items():
        if str(k) == name:
            return n
    return None


def _add_track(b, net, layer, x1, y1, x2, y2, width_mm=0.25):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(_mm(width_mm))
    t.SetNet(net)
    b.Add(t)


def _add_via(b, net, x, y, drill_mm=0.3, width_mm=0.6):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetDrill(_mm(drill_mm))
    v.SetWidth(_mm(width_mm))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    b.Add(v)


def main() -> int:
    b = pcbnew.LoadBoard(str(PCB))
    v3 = _net(b, "/3V3")
    if v3 is None:
        print("!! /3V3 missing"); return 2

    # Restore the layer-transition via and the bridging tracks that
    # keep Comp 0 <-> Comp 1 connected, AVOIDING any path back to
    # IC1.69 (53.60, 41.50) or C29.1 (52.65, 41.50).
    _add_via(b, v3, 50.90, 42.16)
    _add_track(b, v3, pcbnew.F_Cu, 50.90, 42.16, 50.90, 43.08, width_mm=0.25)
    _add_track(b, v3, pcbnew.F_Cu, 50.90, 43.08, 53.28, 45.46, width_mm=0.25)
    _add_track(b, v3, pcbnew.B_Cu, 50.83, 42.10, 50.90, 42.16, width_mm=0.25)
    _add_track(b, v3, pcbnew.B_Cu, 22.12, 42.10, 50.83, 42.10, width_mm=0.25)
    print("   restored /3V3 backbone: via + F.Cu hop + B.Cu backbone")

    b.Save(str(PCB))
    print("   saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
