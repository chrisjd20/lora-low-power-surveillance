#!/usr/bin/env python3
"""Phase 20b: remove orphan tracks/vias on stale nets near moved pads."""
from __future__ import annotations
import pathlib, sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"

# (net_name, seed_mm, tol_mm)
SEEDS = [
    ("/3V3", (53.60, 41.50)),
    ("/3V3", (52.65, 41.50)),
    ("/UART1_RX", (52.91, 5.90)),
    ("/UART1_TX", (71.60, 18.18)),
]


def _net(b, name):
    for k, ni in b.GetNetsByName().items():
        if str(k) == name:
            return ni
    return None


def _near(ax, ay, bx, by, tol=0.05):
    return abs(ax - bx) < tol and abs(ay - by) < tol


def _ep(t):
    if t.GetClass() == "PCB_TRACK":
        s = t.GetStart(); e = t.GetEnd()
        return [(s.x / 1e6, s.y / 1e6), (e.x / 1e6, e.y / 1e6)]
    p = t.GetPosition()
    return [(p.x / 1e6, p.y / 1e6)]


def flood(b, net_name, seed):
    ni = _net(b, net_name)
    if ni is None:
        return []
    code = ni.GetNetCode()
    # Snapshot candidates on this net.
    cand = [t for t in b.Tracks() if t.GetNetCode() == code]
    positions = {seed}
    picked = set()
    changed = True
    while changed:
        changed = False
        for i, t in enumerate(cand):
            if i in picked:
                continue
            for ep in _ep(t):
                if any(_near(ep[0], ep[1], p[0], p[1]) for p in positions):
                    picked.add(i)
                    for ep2 in _ep(t):
                        if not any(_near(ep2[0], ep2[1], p[0], p[1]) for p in positions):
                            positions.add(ep2)
                            changed = True
                    break
    return [cand[i] for i in picked]


def main() -> int:
    b = pcbnew.LoadBoard(str(PCB))
    all_remove = []
    for net, seed in SEEDS:
        picks = flood(b, net, seed)
        all_remove.extend(picks)
        print(f"   {net}@{seed}: {len(picks)} orphans", flush=True)
    # dedupe to avoid removing the same item twice
    seen = set()
    uniq = []
    for t in all_remove:
        k = id(t)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    for t in uniq:
        b.Remove(t)
    print(f"   removed {len(uniq)} orphan items total", flush=True)
    b.Save(str(PCB))
    print(f"   saved", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
