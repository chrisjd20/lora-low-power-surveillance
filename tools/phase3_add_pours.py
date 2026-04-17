#!/usr/bin/env python3
"""
Add copper pour zones on F.Cu, B.Cu, In1.Cu (GND plane), and In2.Cu
(power plane, VBAT_SYS) using the pcbnew Python API directly. MCP's
add_zone is layer-name-sensitive and doesn't play well with our custom
stackup names.

Strategy:
    - GND pour on F.Cu, B.Cu, In1.Cu (solid ground reference plane)
    - VBAT_SYS pour on In2.Cu (simple power plane; router cuts as needed)
    - Stitching vias on a 4 mm grid within the ground pour regions that
      are well clear of other traces/pads (added later in Phase 4).

Outline is 100 x 100 mm. Pours extend 0.5 mm inside the edge cut.
"""
from __future__ import annotations
import pathlib
import sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"


def mk_rect_zone(board, net, layer_id, x1, y1, x2, y2, priority=0):
    """Create a rectangular filled zone on the given copper layer."""
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer_id)
    zone.SetNetCode(net.GetNetCode())
    zone.SetIsFilled(False)
    zone.SetLocalClearance(pcbnew.FromMM(0.2))
    zone.SetThermalReliefGap(pcbnew.FromMM(0.25))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    zone.SetMinThickness(pcbnew.FromMM(0.25))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetAssignedPriority(priority)
    # Outline polygon
    pts = pcbnew.SHAPE_POLY_SET()
    poly = [
        pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)),
        pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y1)),
        pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)),
        pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y2)),
    ]
    pts.NewOutline()
    for v in poly:
        pts.Append(v.x, v.y)
    zone.SetOutline(pts)
    zone.HatchBorder()
    board.Add(zone)
    return zone


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    netinfo = board.GetNetInfo()
    nets = netinfo.NetsByName()
    if not nets.has_key("GND"):
        print("!! GND net not present on board", file=sys.stderr)
        return 1
    gnd = nets["GND"]
    vbat = nets["VBAT_SYS"] if nets.has_key("VBAT_SYS") else None

    # Layer resolution via name
    def L(name: str) -> int:
        lid = board.GetLayerID(name)
        return lid

    margin = 0.5
    x1, y1, x2, y2 = margin, margin, 100 - margin, 100 - margin

    zones = [
        (gnd, L("F.Cu"),   "GND @ F.Cu"),
        (gnd, L("B.Cu"),   "GND @ B.Cu"),
        (gnd, L("In1.Cu"), "GND @ In1.Cu"),
    ]
    for net, lay, label in zones:
        z = mk_rect_zone(board, net, lay, x1, y1, x2, y2, priority=0)
        print(f"added zone: {label}")

    if vbat is not None:
        mk_rect_zone(board, vbat, L("In2.Cu"), x1, y1, x2, y2, priority=0)
        print("added zone: VBAT_SYS @ In2.Cu")

    # Fill zones so check_clearance sees them
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    print(f"filled {board.Zones().size()} zones")
    board.Save(str(PCB))
    print("saved board")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
