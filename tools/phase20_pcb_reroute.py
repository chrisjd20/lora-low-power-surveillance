#!/usr/bin/env python3
"""
Phase 20 - PCB track cleanup + surgical re-route of the nets that
moved during schematic fix.

Two-pass strategy to avoid swig iterate-while-mutate crashes:
  PASS A - collect removals into a list, then remove.
  PASS B - add new tracks/vias/refill zones.

Repeated invocations are idempotent: orphan sweeps only remove
items on the stale net still touching the listed coords.
"""
from __future__ import annotations

import pathlib
import sys
from collections import defaultdict

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB_PATH = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"


# Tracks whose CURRENT net is in this set AND whose connected component
# (via flood-fill through coincident endpoints on the same net) touches
# any of the listed pad positions are stale.
ORPHAN_CLEANUPS: list[tuple[str, tuple[float, float]]] = [
    # /3V3 orphans near IC1.69 / C29.1 (now /SIM_VDD_EXT)
    ("/3V3", (53.60, 41.50)),
    ("/3V3", (52.65, 41.50)),
    # /UART1_RX orphans going to Swarm U3.12 (now /UART2_RX)
    ("/UART1_RX", (52.91, 5.90)),
    # /UART1_TX orphans going to Swarm U3.28 (now /UART2_TX)
    ("/UART1_TX", (71.60, 18.18)),
]


def _net(b: pcbnew.BOARD, name: str):
    for k, ni in b.GetNetsByName().items():
        if str(k) == name:
            return ni
    return None


def _near(px_mm: float, py_mm: float, x: float, y: float, tol_mm: float = 0.05) -> bool:
    return abs(px_mm - x) < tol_mm and abs(py_mm - y) < tol_mm


def _mm(v: float) -> int:
    return int(round(v * 1e6))


def _add_track(b, net_code, x1, y1, x2, y2, layer, width_mm=0.25):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetLayer(layer)
    t.SetWidth(_mm(width_mm))
    t.SetNetCode(net_code)
    b.Add(t)


def _add_via(b, net_code, x, y, diameter_mm=0.6, drill_mm=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x), _mm(y)))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(_mm(diameter_mm))
    v.SetDrill(_mm(drill_mm))
    v.SetNetCode(net_code)
    b.Add(v)


def _flood_remove(b, net_name: str, seed: tuple[float, float]) -> int:
    """Remove every track/via on `net_name` that is reachable from the
    seed coord through shared endpoints.  Returns count removed."""
    ni = _net(b, net_name)
    if ni is None:
        return 0
    code = ni.GetNetCode()

    # Snapshot tracks on this net once; indexes are stable as long as we
    # only remove, not add.
    candidates = [
        t for t in b.Tracks() if t.GetNetCode() == code
    ]

    def endpoints_mm(t):
        if t.GetClass() == "PCB_TRACK":
            s = t.GetStart()
            e = t.GetEnd()
            return [(s.x / 1e6, s.y / 1e6), (e.x / 1e6, e.y / 1e6)]
        else:
            p = t.GetPosition()
            return [(p.x / 1e6, p.y / 1e6)]

    # Flood-fill over positions in a set.
    reachable_positions = {seed}
    to_remove = set()  # indices into candidates
    changed = True
    while changed:
        changed = False
        for i, t in enumerate(candidates):
            if i in to_remove:
                continue
            eps = endpoints_mm(t)
            if any(_near(p[0], p[1], rx, ry) for p in eps for (rx, ry) in reachable_positions):
                to_remove.add(i)
                for ep in eps:
                    if not any(_near(ep[0], ep[1], rx, ry) for (rx, ry) in reachable_positions):
                        reachable_positions.add(ep)
                        changed = True

    # Now actually remove.
    items_to_remove = [candidates[i] for i in to_remove]
    for t in items_to_remove:
        b.Remove(t)
    return len(items_to_remove)


def _dedupe_tracks(b) -> int:
    by_key: dict = defaultdict(list)
    for t in b.Tracks():
        if t.GetClass() == "PCB_TRACK":
            s = t.GetStart()
            e = t.GetEnd()
            key = (
                t.GetNetCode(),
                t.GetLayer(),
                t.GetWidth(),
                min((s.x, s.y), (e.x, e.y)),
                max((s.x, s.y), (e.x, e.y)),
            )
        else:
            p = t.GetPosition()
            key = (
                t.GetNetCode(),
                "VIA",
                t.GetWidth(),
                t.GetDrill(),
                (p.x, p.y),
            )
        by_key[key].append(t)
    dup_list = []
    for lst in by_key.values():
        for t in lst[1:]:
            dup_list.append(t)
    for t in dup_list:
        b.Remove(t)
    return len(dup_list)


def main() -> int:
    b = pcbnew.LoadBoard(str(PCB_PATH))

    # ---- PASS A: cleanup ----
    n_dup = _dedupe_tracks(b)
    print(f"   removed {n_dup} duplicate track/via items")

    n_orph = 0
    for net_name, seed in ORPHAN_CLEANUPS:
        n = _flood_remove(b, net_name, seed)
        if n:
            print(f"   flood-removed {n} {net_name} items from seed {seed}")
            n_orph += n
    print(f"   removed {n_orph} orphan stale-net segments total")

    # ---- PASS B: add routes ----
    sim_vdd = _net(b, "/SIM_VDD_EXT")
    u1tx = _net(b, "/UART1_TX")
    u1rx = _net(b, "/UART1_RX")
    u2tx = _net(b, "/UART2_TX")
    u2rx = _net(b, "/UART2_RX")
    assert sim_vdd and u1tx and u1rx and u2tx and u2rx

    F = pcbnew.F_Cu
    B = pcbnew.B_Cu

    # /SIM_VDD_EXT: IC1.69 F.Cu pad to C29.1 B.Cu pad (0.95mm apart).
    _add_via(b, sim_vdd.GetNetCode(), 53.60, 41.50)
    _add_track(b, sim_vdd.GetNetCode(), 53.60, 41.50, 52.65, 41.50, B, width_mm=0.3)
    print("   added /SIM_VDD_EXT")

    # /UART1_TX: U1.19 F.Cu -> B.Cu -> IC1.34 F.Cu via the free corridor below U1.
    _add_via(b, u1tx.GetNetCode(), 17.50, 11.50)
    _add_track(b, u1tx.GetNetCode(), 17.50, 11.50, 17.50, 27.00, B)
    _add_track(b, u1tx.GetNetCode(), 17.50, 27.00, 38.00, 27.00, B)
    _add_track(b, u1tx.GetNetCode(), 38.00, 27.00, 44.50, 33.50, B)
    _add_track(b, u1tx.GetNetCode(), 44.50, 33.50, 44.50, 47.30, B)
    _add_via(b, u1tx.GetNetCode(), 44.50, 47.30)
    print("   added /UART1_TX")

    # /UART1_RX: U1.18 F.Cu -> B.Cu -> pickup R17.1 -> IC1.40 F.Cu.
    _add_via(b, u1rx.GetNetCode(), 14.96, 11.50)
    _add_track(b, u1rx.GetNetCode(), 14.96, 11.50, 14.96, 25.00, B)
    _add_track(b, u1rx.GetNetCode(), 14.96, 25.00, 19.09, 29.00, B)
    _add_via(b, u1rx.GetNetCode(), 19.09, 29.00)
    _add_track(b, u1rx.GetNetCode(), 19.09, 29.00, 42.20, 29.00, B)
    _add_track(b, u1rx.GetNetCode(), 42.20, 29.00, 42.20, 38.90, B)
    _add_via(b, u1rx.GetNetCode(), 42.20, 38.90)
    print("   added /UART1_RX")

    # /UART2_TX: JP3.2 existing mesh -> extend to U3.28.
    _add_track(b, u2tx.GetNetCode(), 35.65, 52.00, 35.65, 48.00, F)
    _add_via(b, u2tx.GetNetCode(), 35.65, 48.00)
    _add_track(b, u2tx.GetNetCode(), 35.65, 48.00, 71.60, 48.00, B)
    _add_track(b, u2tx.GetNetCode(), 71.60, 48.00, 71.60, 18.18, B)
    _add_via(b, u2tx.GetNetCode(), 71.60, 18.18)
    print("   added /UART2_TX")

    # /UART2_RX: JP4.1 existing mesh -> extend to U3.12.
    _add_track(b, u2rx.GetNetCode(), 34.35, 56.00, 34.35, 48.50, F)
    _add_via(b, u2rx.GetNetCode(), 34.35, 48.50)
    _add_track(b, u2rx.GetNetCode(), 34.35, 48.50, 38.00, 44.85, B)
    _add_track(b, u2rx.GetNetCode(), 38.00, 44.85, 38.00, 3.00, B)
    _add_track(b, u2rx.GetNetCode(), 38.00, 3.00, 52.91, 3.00, B)
    _add_track(b, u2rx.GetNetCode(), 52.91, 3.00, 52.91, 5.90, B)
    _add_via(b, u2rx.GetNetCode(), 52.91, 5.90)
    print("   added /UART2_RX")

    # --- refill zones (save first to minimize swig-related crashes) ---
    b.Save(str(PCB_PATH))
    print(f"-- saved {PCB_PATH.name} (pre-fill)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
