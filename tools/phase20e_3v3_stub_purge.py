#!/usr/bin/env python3
"""Phase 20e: remove the small /3V3 stubs that used to feed IC1.69 and
C29.1 (now /SIM_VDD_EXT).  These are flagged by DRC as 'shorting_items',
'solder_mask_bridge', and 'tracks_crossing'.

We match exact endpoints (mm) so we only touch the 8 known stale items.
"""
from __future__ import annotations
import pathlib, sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"


# (layer, (x1,y1), (x2,y2)) in mm; order-insensitive endpoints.
TRACK_TARGETS = [
    (pcbnew.F_Cu, (53.60, 41.50), (53.00, 40.90)),
    (pcbnew.F_Cu, (53.00, 40.90), (51.44, 40.90)),
    (pcbnew.F_Cu, (51.44, 40.90), (50.90, 41.44)),
    (pcbnew.F_Cu, (50.90, 41.44), (50.90, 42.16)),
    (pcbnew.F_Cu, (50.90, 42.16), (50.90, 43.08)),
    (pcbnew.F_Cu, (50.90, 43.08), (53.28, 45.46)),
    (pcbnew.B_Cu, (52.65, 41.50), (51.99, 42.16)),
    (pcbnew.B_Cu, (51.99, 42.16), (50.90, 42.16)),
    (pcbnew.B_Cu, (50.83, 42.10), (50.90, 42.16)),
    (pcbnew.B_Cu, (22.12, 42.10), (50.83, 42.10)),
]
# (x,y) in mm
VIA_TARGETS = [
    (50.90, 42.16),
]

TOL_MM = 0.005


def _eq(a: float, b: float) -> bool:
    return abs(a - b) < TOL_MM


def _match_track(t, layer: int, a: tuple[float, float],
                 b: tuple[float, float]) -> bool:
    if t.GetLayer() != layer:
        return False
    s = t.GetStart(); e = t.GetEnd()
    sx, sy, ex, ey = s.x / 1e6, s.y / 1e6, e.x / 1e6, e.y / 1e6
    m = lambda p, q: _eq(p[0], q[0]) and _eq(p[1], q[1])
    pa, pb = (sx, sy), (ex, ey)
    return (m(pa, a) and m(pb, b)) or (m(pa, b) and m(pb, a))


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))

    # Build /3V3 code filter so we ONLY remove on that net (defensive).
    v3 = None
    for k, n in board.GetNetsByName().items():
        if str(k) == "/3V3":
            v3 = n.GetNetCode()
            break
    if v3 is None:
        print("!! /3V3 net missing, aborting"); return 2

    to_remove = []
    for t in list(board.Tracks()):
        if t.GetNetCode() != v3:
            continue
        if t.GetClass() == "PCB_TRACK":
            for (ly, a, bpt) in TRACK_TARGETS:
                if _match_track(t, ly, a, bpt):
                    to_remove.append(("trk", t))
                    break
        else:
            p = t.GetPosition()
            px, py = p.x / 1e6, p.y / 1e6
            for (vx, vy) in VIA_TARGETS:
                if _eq(px, vx) and _eq(py, vy):
                    to_remove.append(("via", t))
                    break
    print(f"   found {sum(1 for k,_ in to_remove if k=='trk')} tracks and "
          f"{sum(1 for k,_ in to_remove if k=='via')} vias to remove")
    for _, t in to_remove:
        board.Remove(t)
    print(f"   removed {len(to_remove)} items")

    board.Save(str(PCB))
    print("   saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
