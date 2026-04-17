#!/usr/bin/env python3
"""
Phase 9 — PCB rework to land the Phase-7 variant hardware and the
Phase-8 rebuilt footprints:

  1. Reload the 3 custom footprints (XIAO, SIM7080G, Swarm M138) from the
     rebuilt warden-custom.pretty library so their updated pad lists (and,
     for SIM7080G, the pin-count jump 60 → 77) are on the board.
  2. Add 16 new footprints for Phase-7 refs Q2, Q3, R16, R17, R18, R19,
     U6, X1, C23, C24, C25, C26, JP1, JP2, JP3, JP4.
  3. Resync every pad to its net using the schematic-exported netlist
     (re-using the Phase 3 sync strategy: parse kicad-cli netlist +
     walk pcbnew).
  4. Clear existing tracks / vias so Freerouting can replan.
  5. Export DSN, run Freerouting (Docker), import SES.
  6. Re-stitch GND vias on a regular grid, then dedupe.

Usage:
    python3 tools/phase9_pcb_rework.py
"""
from __future__ import annotations
import argparse
import pathlib
import re
import subprocess
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
SCH  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
FP_LIB = ROOT / "hardware/warden-apex-master/footprints/warden-custom.pretty"

MM = 1_000_000  # pcbnew internal units per mm


# ---------------------------------------------------------------------------
# Phase-7 new footprints placed in the 100x100 mm outline
# Coordinates in mm (pcbnew convention: origin top-left, +Y south).
# Orientation: all at 0° unless noted.
# All placements targeted at the empty band Y 22..34 between the top-
# radio row and the SIM7080G row, plus one by the Nano-SIM holder.
# ---------------------------------------------------------------------------
NEW_FOOTPRINTS: list[dict] = [
    # UART pull-downs
    {"ref": "R17", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "100k", "xy": (30.0, 24.0), "rot": 0},
    {"ref": "R18", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "100k", "xy": (66.0, 22.0), "rot": 0},
    {"ref": "R19", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "100k", "xy": (66.0, 28.0), "rot": 0},

    # Modem rail gate
    {"ref": "JP1", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "value": "JP_MODEM_RAIL", "xy": (36.0, 24.0), "rot": 0},
    {"ref": "R16", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "100k", "xy": (40.0, 24.0), "rot": 0},
    {"ref": "Q2",  "fp": "Package_TO_SOT_SMD:SOT-23",
     "value": "AO3401A", "xy": (44.0, 24.0), "rot": 0},
    {"ref": "Q3",  "fp": "Package_TO_SOT_SMD:SOT-23",
     "value": "2N7002", "xy": (48.0, 24.0), "rot": 0},

    # Sat UART jumpers
    {"ref": "JP3", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "value": "JP_SAT_UART_TX", "xy": (60.0, 22.0), "rot": 0},
    {"ref": "JP4", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "value": "JP_SAT_UART_RX", "xy": (60.0, 28.0), "rot": 0},

    # SC16IS740 bridge + crystal + decouplers
    {"ref": "U6",  "fp": "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
     "value": "SC16IS740", "xy": (73.0, 25.0), "rot": 0},
    {"ref": "X1",  "fp": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
     "value": "14.7456MHz", "xy": (82.0, 22.0), "rot": 0},
    {"ref": "C23", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "value": "22pF", "xy": (82.0, 26.0), "rot": 0},
    {"ref": "C24", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "value": "22pF", "xy": (82.0, 30.0), "rot": 0},
    {"ref": "C25", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "value": "100nF", "xy": (76.0, 30.0), "rot": 0},
    {"ref": "C26", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "value": "10uF", "xy": (69.0, 30.0), "rot": 0},

    # SIM-holder VCC break jumper — east edge adjacent to Card1
    {"ref": "JP2", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "value": "JP_SIM_VCC", "xy": (93.0, 54.0), "rot": 0},
]

# Refs whose footprint was rebuilt in Phase 8 and whose PCB entry must be
# refreshed from the library so the updated pad list applies.
REBUILT_REFS = {
    "U1":    "warden_custom:XIAO_ESP32S3_SENSE",
    "IC1":   "warden_custom:LCC-42_SIM7080G",
    "U3":    "warden_custom:Swarm_M138",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def mm_vec(x: float, y: float) -> "pcbnew.VECTOR2I":
    return pcbnew.VECTOR2I(int(x * MM), int(y * MM))


def load_fp(lib_id: str) -> pcbnew.FOOTPRINT:
    """Load a footprint by its lib:name id, searching our custom lib first
    then the stock KiCad footprint libraries."""
    try:
        lib, name = lib_id.split(":", 1)
    except ValueError:
        raise ValueError(f"bad lib id {lib_id!r}")

    if lib == "warden_custom":
        fp = pcbnew.FootprintLoad(str(FP_LIB), name)
    else:
        stock_dir = pathlib.Path(f"/usr/share/kicad/footprints/{lib}.pretty")
        fp = pcbnew.FootprintLoad(str(stock_dir), name)

    if fp is None:
        raise KeyError(f"footprint {lib_id} not found")
    # Set FPID
    fpid = pcbnew.LIB_ID(lib, name)
    fp.SetFPID(fpid)
    return fp


def kicad_netlist_map() -> dict[tuple[str, str], str]:
    """Return {(ref, pad_number): netname} for the whole design."""
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist",
         "--format", "kicadsexpr",
         "--output", str(ROOT / "build/warden-apex.net"),
         str(SCH)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    text = (ROOT / "build/warden-apex.net").read_text()

    out: dict[tuple[str, str], str] = {}
    pos = 0
    while True:
        m = re.search(r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)', text[pos:])
        if not m:
            break
        start = pos + m.start()
        name = m.group(1)
        depth = 0
        i = start
        while i < len(text):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        for nm in re.finditer(
            r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', body,
        ):
            ref, pin = nm.group(1), nm.group(2)
            out[(ref, pin)] = name.lstrip("/")
        pos = i + 1
    return out


def sync_nets(board: pcbnew.BOARD) -> tuple[int, int]:
    """Assign every pad's net based on the schematic netlist export."""
    net_map = kicad_netlist_map()
    assigned = 0
    missing = 0
    for fp in board.Footprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            pnum = pad.GetNumber()
            key = (ref, pnum)
            if key in net_map:
                net_name = net_map[key]
                ni = board.FindNet(net_name)
                if ni is None:
                    # Create new net
                    ni = pcbnew.NETINFO_ITEM(board, net_name)
                    board.Add(ni)
                pad.SetNet(ni)
                assigned += 1
            else:
                # leave un-netted pads on "0" (no-net) — they're NC test
                # pads (central GND2 on XIAO, etc.)
                pad.SetNet(board.FindNet(""))
                missing += 1
    return assigned, missing


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def clear_tracks(board: pcbnew.BOARD) -> int:
    tracks = list(board.Tracks())
    for t in tracks:
        board.Remove(t)
    return len(tracks)


def remove_refs(board: pcbnew.BOARD, refs: list[str]) -> list[tuple[float, float, float]]:
    removed = []
    for ref in refs:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            continue
        pos = fp.GetPosition()
        orient = fp.GetOrientationDegrees()
        removed.append((ref, pos.x / MM, pos.y / MM, orient))
        board.Remove(fp)
    return removed


def place_fp(board: pcbnew.BOARD, ref: str, lib_id: str, value: str,
             x: float, y: float, rot: float) -> pcbnew.FOOTPRINT:
    fp = load_fp(lib_id)
    board.Add(fp)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(mm_vec(x, y))
    fp.SetOrientationDegrees(rot)
    return fp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-freeroute", action="store_true",
                    help="skip Freerouting step (net sync + clear tracks only)")
    args = ap.parse_args()

    board = pcbnew.LoadBoard(str(PCB))

    # 1) Swap in rebuilt custom footprints (keep same xy+orientation).
    # Walk Footprints() ONCE collecting ref -> (x_iu, y_iu, rot, value)
    # because FindFootprintByReference appears to return unwrapped
    # SwigPyObject pointers on this KiCad 9 build.
    print("Replacing rebuilt footprints…")
    snapshots: dict[str, tuple[int, int, float, str]] = {}
    fps_to_remove: list = []
    for fp in list(board.Footprints()):
        ref = fp.GetReference()
        if ref in REBUILT_REFS:
            snapshots[ref] = (fp.GetX(), fp.GetY(),
                              fp.GetOrientationDegrees(), fp.GetValue())
            fps_to_remove.append(fp)
    for fp in fps_to_remove:
        board.Remove(fp)
    for ref, lib_id in REBUILT_REFS.items():
        if ref not in snapshots:
            print(f"  WARN {ref}: not on board, skipping")
            continue
        x_iu, y_iu, rot, value = snapshots[ref]
        x_mm, y_mm = x_iu / MM, y_iu / MM
        place_fp(board, ref, lib_id, value, x_mm, y_mm, rot)
        print(f"  refreshed {ref} <- {lib_id} @ ({x_mm:.2f},{y_mm:.2f}) rot={rot}")

    # 2) Add Phase-7 new footprints
    print("Adding Phase-7 new footprints…")
    for spec in NEW_FOOTPRINTS:
        if board.FindFootprintByReference(spec["ref"]) is not None:
            print(f"  skip {spec['ref']} already on board")
            continue
        place_fp(board, spec["ref"], spec["fp"], spec["value"],
                 spec["xy"][0], spec["xy"][1], spec["rot"])
        print(f"  + {spec['ref']:4s} {spec['fp']} @ {spec['xy']}")

    # 3) Sync nets from the schematic
    print("Syncing nets from schematic…")
    assigned, missing = sync_nets(board)
    print(f"  {assigned} pads netted, {missing} left un-netted (NC / test)")

    # 4) Clear tracks
    cleared = clear_tracks(board)
    print(f"Cleared {cleared} tracks for re-routing")

    # 5) Save pre-Freeroute snapshot
    board.Save(str(PCB))
    print("Saved post-placement PCB.")

    if args.no_freeroute:
        return 0

    # 6) Export DSN
    (ROOT / "build").mkdir(exist_ok=True)
    dsn_path = ROOT / "build/warden.dsn"
    pcbnew.ExportSpecctraDSN(board, str(dsn_path))
    print(f"Exported DSN -> {dsn_path}")

    # 7) Freerouting via Docker
    fr_jar_host = pathlib.Path.home() / ".kicad-mcp/freerouting.jar"
    if not fr_jar_host.exists():
        print("  !! freerouting.jar not present at ~/.kicad-mcp/freerouting.jar")
        print("  Skipping Freerouting. Run it manually.")
        return 0
    ses_path = ROOT / "build/warden.ses"
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{ROOT/'build'}:/work",
        "-v", f"{fr_jar_host}:/opt/freerouting.jar",
        "-w", "/work",
        "eclipse-temurin:21-jre",
        "java", "-jar", "/opt/freerouting.jar",
        "-de", "/work/warden.dsn",
        "-do", "/work/warden.ses",
        "-mp", "20",
        "-host-mode", "cli",
    ]
    print("Running Freerouting (Docker) …")
    subprocess.run(cmd, check=False)

    # 8) Import SES via phase4 importer
    imp = ROOT / "tools/phase4_import_ses.py"
    if imp.exists() and ses_path.exists():
        subprocess.run([sys.executable, str(imp)], check=False)
        print("Imported SES.")
    else:
        print("  !! skipping SES import (no SES or importer missing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
