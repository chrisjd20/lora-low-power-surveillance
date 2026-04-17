#!/usr/bin/env python3
"""
Replacement for the KiCAD MCP `sync_schematic_to_board` (which relies on
the same Y-flip buggy pin locator we worked around in Phase 2).

Steps:
    1. Export the schematic netlist via kicad-cli (source of truth).
    2. Parse the netlist to build {(ref, pin_number): net_name}.
    3. Open the .kicad_pcb via pcbnew, add missing nets, assign each pad
       to its correct net.
    4. Save the board.
"""
from __future__ import annotations
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
NET  = ROOT / "hardware/warden-apex-master/_warden.net"


def export_netlist():
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist",
         "--format=kicadsexpr", str(SCH), "-o", str(NET)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def parse_netlist() -> dict[tuple[str, str], str]:
    text = NET.read_text()
    pad_net: dict[tuple[str, str], str] = {}
    for m in re.finditer(
        r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)([\s\S]*?)\)\s*(?=\(net |\)$)',
        text,
    ):
        name = m.group(1).lstrip("/")
        if not name:
            continue
        for nd in re.finditer(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"', m.group(2)):
            pad_net[(nd.group(1), nd.group(2))] = name
    return pad_net


def apply_to_board(pad_net: dict[tuple[str, str], str]) -> dict:
    import pcbnew
    board = pcbnew.LoadBoard(str(PCB))
    # Ensure every net exists
    netinfo = board.GetNetInfo()
    existing = set(str(n) for n in netinfo.NetsByName().keys())
    added = 0
    for n in set(pad_net.values()):
        if n not in existing:
            item = pcbnew.NETINFO_ITEM(board, n)
            board.Add(item)
            added += 1
    netinfo = board.GetNetInfo()
    nets_by_name = netinfo.NetsByName()

    assigned = 0
    unmatched: list[str] = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            pad_num = str(pad.GetNumber())
            key = (ref, pad_num)
            if key in pad_net:
                nn = pad_net[key]
                if nets_by_name.has_key(nn):
                    pad.SetNet(nets_by_name[nn])
                    assigned += 1
                    continue
            unmatched.append(f"{ref}/{pad_num}")
    board.Save(str(PCB))
    return {"nets_added": added, "pads_assigned": assigned,
            "unmatched_sample": unmatched[:12], "unmatched_total": len(unmatched)}


def main() -> int:
    export_netlist()
    pad_net = parse_netlist()
    print(f"netlist entries: {len(pad_net)}")
    res = apply_to_board(pad_net)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
