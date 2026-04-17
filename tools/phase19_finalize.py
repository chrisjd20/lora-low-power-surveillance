#!/usr/bin/env python3
"""
Phase 19b - post-Freerouting hygiene in a fresh subprocess.

Runs in its own Python process because pcbnew's SWIG bindings get
corrupted after many back-to-back subprocess + ExportSpecctraDSN calls
in the parent process (`SwigPyObject` returned from LoadBoard instead
of a real BOARD object). Calling this as a subprocess gives us a
clean interpreter state.

Steps:
    1. Force every QFN/LCC exposed-thermal pad on IC2/IC3/IC4 to /GND
       so the ground pour ties them through the EP copper. Carries the
       Phase 18 rule.
    2. Stamp a short F.Cu bridge from U6 pad 14 (/3V3 VDD pin) to the
       nearest /3V3 track end, closing a connection Freerouting
       declined to make (pads_3/11/14 are a tight fan-out trio).
    3. Full zone re-fill.
    4. Save.
"""
from __future__ import annotations

import pathlib
import pcbnew

ROOT = pathlib.Path('/home/admin/github/lora-low-power-surveillance')
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"

MM = 1_000_000

EP_TO_GND_REFS = {"IC2", "IC3", "IC4"}
EP_TO_GND_EXPLICIT = {("IC3", "16")}

# Hand-drawn bridges on F.Cu for nets that Freerouting chose not to
# close. Format: (net_name, layer_name, (x1, y1), (x2, y2), width_mm)
HAND_BRIDGES = [
    # IC3 EP tie bridges — carry-forward from Phase 18. Freerouting
    # does not re-stamp these after `phase19_audit_fixes.py` clears
    # the entire track list, so they have to be rebuilt alongside the
    # EP -> GND net assignment so the F.Cu GND pour reaches the EP.
    # IC3.2 / IC3.16 EP: pitch 0.275 mm (pour can't squeeze through).
    ("/GND", "F.Cu", (46.85, 79.75), (47.60, 79.75), 0.20),
    # IC3.15 / IC3.16 EP east side.
    ("/GND", "F.Cu", (48.50, 78.40), (48.50, 78.78), 0.20),
]

# Vias + matching F.Cu/B.Cu track pairs for nets that need layer
# switching. Empty by default - Phase 19's surgical track cleanup
# preserves the Phase-18 IC2.9 routing so no hand-bridge needed here.
# Format: (net_name, via_xy, via_drill_mm, via_dia_mm,
#          F.Cu_from, F.Cu_to, B.Cu_from, B.Cu_to, trace_w_mm)
HAND_VIA_BRIDGES: list = []


def assign_ep_gnd(board: pcbnew.BOARD) -> int:
    gnd = board.FindNet("/GND")
    if gnd is None:
        print("  !! /GND net missing")
        return 0
    n = 0
    for fp in board.Footprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            num = pad.GetNumber()
            want_gnd = False
            if ref in EP_TO_GND_REFS and num == "" and pad.GetNetname() == "":
                want_gnd = True
            elif (ref, num) in EP_TO_GND_EXPLICIT and pad.GetNetname() != "/GND":
                want_gnd = True
            if not want_gnd:
                continue
            pad.SetNet(gnd)
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            n += 1
            print(f"  {ref}.{num or 'EP'} -> /GND")
    return n


def stamp_bridges(board: pcbnew.BOARD) -> int:
    n = 0
    for net_name, layer_name, (x1, y1), (x2, y2), w in HAND_BRIDGES:
        net = board.FindNet(net_name)
        if net is None:
            print(f"  skip bridge ({net_name} missing)")
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(x1 * MM), int(y1 * MM)))
        t.SetEnd(pcbnew.VECTOR2I(int(x2 * MM), int(y2 * MM)))
        t.SetWidth(int(w * MM))
        t.SetLayer(board.GetLayerID(layer_name))
        t.SetNet(net)
        board.Add(t)
        n += 1
        print(f"  + bridge {net_name} {layer_name} "
              f"({x1:.3f},{y1:.3f})->({x2:.3f},{y2:.3f})  w={w}")
    return n


def stamp_via_bridges(board: pcbnew.BOARD) -> int:
    n = 0
    for (net_name, (vx, vy), drill, dia,
         (fx1, fy1), (fx2, fy2),
         (bx1, by1), (bx2, by2), w) in HAND_VIA_BRIDGES:
        net = board.FindNet(net_name)
        if net is None:
            print(f"  skip via-bridge ({net_name} missing)")
            continue
        # F.Cu track
        t1 = pcbnew.PCB_TRACK(board)
        t1.SetStart(pcbnew.VECTOR2I(int(fx1 * MM), int(fy1 * MM)))
        t1.SetEnd(pcbnew.VECTOR2I(int(fx2 * MM), int(fy2 * MM)))
        t1.SetWidth(int(w * MM))
        t1.SetLayer(pcbnew.F_Cu)
        t1.SetNet(net)
        board.Add(t1)
        # Via
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(int(vx * MM), int(vy * MM)))
        v.SetWidth(int(dia * MM))
        v.SetDrill(int(drill * MM))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(net)
        board.Add(v)
        # B.Cu track
        t2 = pcbnew.PCB_TRACK(board)
        t2.SetStart(pcbnew.VECTOR2I(int(bx1 * MM), int(by1 * MM)))
        t2.SetEnd(pcbnew.VECTOR2I(int(bx2 * MM), int(by2 * MM)))
        t2.SetWidth(int(w * MM))
        t2.SetLayer(pcbnew.B_Cu)
        t2.SetNet(net)
        board.Add(t2)
        n += 1
        print(f"  + via-bridge {net_name} F({fx1:.3f},{fy1:.3f})->"
              f"({fx2:.3f},{fy2:.3f})/via({vx:.3f},{vy:.3f})/"
              f"B({bx1:.3f},{by1:.3f})->({bx2:.3f},{by2:.3f})")
    return n


def refill_zones(board: pcbnew.BOARD) -> int:
    filler = pcbnew.ZONE_FILLER(board)
    zones = list(board.Zones())
    filler.Fill(zones)
    return len(zones)


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    print("[19b.1] EP -> /GND re-assignment ...")
    n_ep = assign_ep_gnd(board)
    print(f"  {n_ep} EP pads assigned")
    print("[19b.2] Hand-drawn bridges ...")
    n_b = stamp_bridges(board)
    print(f"  {n_b} bridges stamped")
    print("[19b.2b] Hand-drawn via-bridges ...")
    n_vb = stamp_via_bridges(board)
    print(f"  {n_vb} via-bridges stamped")
    print("[19b.3] Full zone refill ...")
    n_z = refill_zones(board)
    print(f"  {n_z} zones refilled")
    board.Save(str(PCB))
    print(f"Saved {PCB}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
