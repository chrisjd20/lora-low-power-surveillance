#!/usr/bin/env python3
"""
Phase 18b — PCB placement for expansion I/O.

Adds four new footprints on the west edge of the board, where the PIR
header (H1) already lives:

    J4   PinHeader_2x07_P2.54mm_Vertical         (5.00, 62.00) rot=90
    J5   JST_SH_SM04B-SRSS-TB_1x04-1MP_Horizontal (5.00, 48.00) rot=180
    F1   Fuse_0805_2012Metric                    (10.00, 54.00) rot=0
    R24  R_0805_2012Metric                       (10.00, 58.00) rot=0

After placement the board netlist is re-synced from the schematic
using the `/NET` hierarchical-path form (same convention as Phase 10).

Idempotent: if J4 already exists on the board, just re-runs the net
sync pass.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
SCH = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
KICAD_FP = pathlib.Path("/usr/share/kicad/footprints")

MM = 1_000_000


# (ref, lib, fp, x_mm, y_mm, rot_deg)
# West-edge expansion strip sits between H1 (PIR, Y=34) and C15 (BQ24650
# input cap column, Y=74). For plug-and-play we pack these so pads face
# the board edge and a ribbon cable / Qwiic cable can exit the enclosure
# cleanly on the west side.
#
# PinHeader_2x07_Vertical: anchor is pad 1, so pad 1 = (x, y) in natural
# orientation (rot=0). Pads extend +X (second column) and +Y (pins 3-13).
PLACEMENTS = [
    # J4 — 2x7 expansion GPIO header. Pad 1 at (5, 54.5). Pads span
    # X=[5.0, 7.54], Y=[54.5, 69.74]. Clears J5 at Y=52.77 and C15 at 72.55.
    ("J4",
     "Connector_PinHeader_2.54mm",
     "PinHeader_2x07_P2.54mm_Vertical",
     5.00, 54.50, 0.0),
    # J5 — Qwiic / STEMMA QT facing west. Body centred at (5, 50).
    # Pads span X=[1.6, 8.4], Y=[47.23, 52.77].
    ("J5",
     "Connector_JST",
     "JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
     5.00, 50.00, 180.0),
    # F1 — polyfuse 0805 on EXP_VBAT. East of J4 pin 2 (7.54, 57.04).
    ("F1",
     "Fuse",
     "Fuse_0805_2012Metric",
     11.50, 56.00, 0.0),
    # R24 — 10 k pull-up on EXP_IRQ. East of J4 pin 14 (7.54, 69.74).
    ("R24",
     "Resistor_SMD",
     "R_0805_2012Metric",
     11.50, 68.00, 0.0),
]

# TP4 (SOLAR_IN test point) sits at (7, 46) in the pre-Phase-18 layout —
# right where J5 would land. Move it 5 mm east to clear the west-edge
# expansion strip; still on the solar path, still a valid probe point.
RELOCATE = [
    ("TP4", 12.00, 46.00, 0.0),
]


def load_footprint(lib: str, fp_name: str) -> pcbnew.FOOTPRINT:
    path = KICAD_FP / f"{lib}.pretty" / f"{fp_name}.kicad_mod"
    fp = pcbnew.FootprintLoad(str(path.parent), fp_name)
    if fp is None:
        raise RuntimeError(f"could not load {path}")
    return fp


def place_new(board: pcbnew.BOARD) -> int:
    existing = {fp.GetReference(): fp for fp in board.Footprints()}
    added = 0
    for ref, lib, fp_name, x, y, rot in PLACEMENTS:
        pos = pcbnew.VECTOR2I(int(x * MM), int(y * MM))
        if ref in existing:
            fp = existing[ref]
            fp.SetPosition(pos)
            fp.SetOrientationDegrees(rot)
            print(f"  repositioned {ref} -> ({x:.2f}, {y:.2f}) rot={rot}")
            continue
        fp = load_footprint(lib, fp_name)
        fp.SetReference(ref)
        fp.Reference().SetText(ref)
        fp.Value().SetText(fp_name)
        fp.SetPosition(pos)
        fp.SetOrientationDegrees(rot)
        fp.SetAttributes(pcbnew.FP_SMD if "0805" in fp_name or "SH" in fp_name
                          else pcbnew.FP_THROUGH_HOLE)
        board.Add(fp)
        added += 1
        print(f"  placed {ref} at ({x:.2f}, {y:.2f}) rot={rot}")

    # Also relocate any existing-footprint collisions (e.g. TP4 out of J5).
    for ref, x, y, rot in RELOCATE:
        if ref not in existing:
            continue
        fp = existing[ref]
        pos = pcbnew.VECTOR2I(int(x * MM), int(y * MM))
        fp.SetPosition(pos)
        fp.SetOrientationDegrees(rot)
        print(f"  relocated {ref} -> ({x:.2f}, {y:.2f}) rot={rot}")
    return added


def sync_nets(board: pcbnew.BOARD) -> tuple[int, int]:
    """Re-assign every pad's net using /NET names from the schematic.
    Mirrors tools/phase10_drc_fix.py resync (preserves leading slash).
    """
    netfile = ROOT / "build/warden-apex.net"
    netfile.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist",
         "--format", "kicadsexpr", "--output", str(netfile), str(SCH)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    text = netfile.read_text()

    net_map: dict[tuple[str, str], str] = {}
    pos = 0
    while True:
        m = re.search(r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)', text[pos:])
        if not m:
            break
        start = pos + m.start()
        name = m.group(1)
        d, i = 0, start
        while i < len(text):
            if text[i] == "(":
                d += 1
            elif text[i] == ")":
                d -= 1
                if d == 0:
                    break
            i += 1
        body = text[start:i + 1]
        for nm in re.finditer(
            r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', body,
        ):
            net_map[(nm.group(1), nm.group(2))] = name
        pos = i + 1

    assigned = 0
    missing = 0
    for fp in board.Footprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in net_map:
                name = net_map[key]
                ni = board.FindNet(name)
                if ni is None:
                    ni = pcbnew.NETINFO_ITEM(board, name)
                    board.Add(ni)
                pad.SetNet(ni)
                assigned += 1
            elif pad.GetNumber() != "":
                missing += 1
    return assigned, missing


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    print("Placing expansion footprints…")
    added = place_new(board)
    print(f"  added {added} footprints")

    print("Syncing nets from schematic (/NET form)…")
    assigned, missing = sync_nets(board)
    print(f"  pads assigned: {assigned}, unmatched: {missing}")

    board.Save(str(PCB))
    print(f"Saved {PCB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
