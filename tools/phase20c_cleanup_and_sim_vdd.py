#!/usr/bin/env python3
"""Phase 20c: PCB cleanup + /SIM_VDD_EXT short-route.

Operations, each atomic:
1. Dedupe co-located duplicate tracks and vias (same net, layer, width,
   endpoints).  Duplicates creep in from earlier surgical edits.
2. Purge ALL tracks / vias on /UART1_TX and /UART1_RX.  These nets used
   to route IC1.x -> Swarm U3.x, but U3.x pads are now on /UART2_TX /
   /UART2_RX and the ESP32 pins U1.18 / U1.19 are now the real
   endpoints.  Re-routing these two signal nets is a one-time, clean
   operation; the safest thing is a full wipe before adding new tracks.
3. Add the minimal /SIM_VDD_EXT local loop:
       IC1.69 (F.Cu)  --short track-- blind via -- C29.1 (B.Cu)
   Net-code is created lazily if missing.

Saves atomically.  No zone refill here; do that in 20e after routing.
"""
from __future__ import annotations

import pathlib
import sys
from collections import defaultdict

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"


PURGE_NETS = ("/UART1_TX", "/UART1_RX")


def _net(b: pcbnew.BOARD, name: str):
    for k, n in b.GetNetsByName().items():
        if str(k) == name:
            return n
    return None


def _ensure_net(b: pcbnew.BOARD, name: str):
    n = _net(b, name)
    if n is not None:
        return n
    ni = pcbnew.NETINFO_ITEM(b, name, b.GetNetCount())
    b.Add(ni)
    return ni


def _mm(x: float) -> int:
    return int(round(x * 1e6))


def _add_track(b, net, layer: int, x1: float, y1: float, x2: float,
               y2: float, width_mm: float = 0.25) -> None:
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(_mm(width_mm))
    t.SetNet(net)
    b.Add(t)


def _add_via(b, net, x: float, y: float,
             drill_mm: float = 0.3, width_mm: float = 0.6) -> None:
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

    # --- 1. dedupe tracks and vias ---
    by_key: dict = defaultdict(list)
    for t in list(b.Tracks()):
        if t.GetClass() == "PCB_TRACK":
            s = t.GetStart()
            e = t.GetEnd()
            key = ("T", t.GetNetCode(), t.GetLayer(), t.GetWidth(),
                   min((s.x, s.y), (e.x, e.y)),
                   max((s.x, s.y), (e.x, e.y)))
        else:
            p = t.GetPosition()
            key = ("V", t.GetNetCode(),
                   t.GetWidth(pcbnew.F_Cu) if hasattr(t.GetWidth, "__call__") else t.GetDrill(),
                   t.GetDrill(), (p.x, p.y))
        by_key[key].append(t)
    dedup_removed = []
    for lst in by_key.values():
        for t in lst[1:]:
            dedup_removed.append(t)
    for t in dedup_removed:
        b.Remove(t)
    print(f"   deduped {len(dedup_removed)} items")

    # --- 2. purge stale /UART1_TX and /UART1_RX routing ---
    purge_codes = []
    for name in PURGE_NETS:
        ni = _net(b, name)
        if ni is None:
            print(f"   {name}: net missing (nothing to purge)")
            continue
        purge_codes.append((name, ni.GetNetCode()))
    purge_items = [t for t in list(b.Tracks())
                   if any(t.GetNetCode() == c for _, c in purge_codes)]
    for t in purge_items:
        b.Remove(t)
    per_net = defaultdict(int)
    for name, code in purge_codes:
        per_net[name] = sum(1 for t in purge_items if t.GetNetCode() == code)
    for name in PURGE_NETS:
        print(f"   purged {per_net[name]} items from {name}")

    # --- 3. add minimal /SIM_VDD_EXT local loop ---
    sim = _ensure_net(b, "/SIM_VDD_EXT")
    # IC1.69 is on F.Cu at (53.60, 41.50); C29.1 on B.Cu at (52.65, 41.50).
    # Place a through-via at C29.1 location (it's already a B.Cu pad) and
    # route a short F.Cu stub from IC1.69 to the via.
    via_x, via_y = 52.65, 41.50
    _add_via(b, sim, via_x, via_y, drill_mm=0.3, width_mm=0.6)
    _add_track(b, sim, pcbnew.F_Cu, 53.60, 41.50, via_x, via_y, width_mm=0.25)
    print("   added /SIM_VDD_EXT short via + F.Cu stub between IC1.69 and C29.1")

    b.Save(str(PCB))
    print("   saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
