#!/usr/bin/env python3
"""
Phase 19 — Audit fix-up (four BLOCKING + three non-blocking items).

Catastrophic issues closed:
    BLOCKING-1: IC3 (TPS63070) VSEL (pin 4) re-wired to /GND instead of
                /REG_EN. Forces 3.3 V output; the previous wiring drove
                the main logic rail to 5 V on power-up.
    BLOCKING-2: BQ24650 VFB upper-divider resistor (R20, 7.15 k) added
                between /VBAT_SYS and /CHG_VFB. Sets LiFePO4 float at
                2.1 V * (1 + 7.15/10) = 3.60 V.
    BLOCKING-3: BQ24650 TS upper-divider resistor (R21, 10 k) added
                between /CHG_REF (VREF 2.1 V) and /TS_BIAS. With the
                existing R3 = 10 k to GND, V_TS = 1.05 V -> charger
                inside the TS safe window.
    BLOCKING-4: BQ24650 MPPSET rebuilt as a proper VREF -> R22 (100 k)
                -> MPPSET -> R2 (100 k, repurposed) -> GND divider.
                V_MPPSET = 1.05 V -> V_IN(REG) = 5.25 V (6 V panel MPP).
                Also re-labels R2.1 from /CHG_SENSE_NEG to /GND.

Non-blocking items fixed in the same pass:
    - R4.2 and R5.2 flipped from /GND to /3V3 (proper pull-ups on
      BQ24650 STAT1/2 open-drain outputs).
    - IC3 PS/SYNC (pin 3) re-wired from /3V3 to /GND so the TPS63070
      auto-selects PFM power-save mode at light load.
    - C5 value changed from 100 nF to 1 uF (per TPS63070 datasheet
      recommendation for the VAUX internal-bias pin).

Idempotent: bails out if the Phase-19 sentinel (R20) is already
present in the schematic.

Usage:
    python3 tools/phase19_audit_fixes.py [--no-freeroute]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import uuid

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
DRC = ROOT / "hardware/warden-apex-master/drc-report.txt"
ERC = ROOT / "hardware/warden-apex-master/erc-report.txt"
BUILD = ROOT / "build"
FR_JAR = pathlib.Path.home() / ".kicad-mcp/freerouting.jar"

PHASE19_MARKER = '"Reference" "R20"'  # R20 only exists after Phase 19

MM = 1_000_000


# --------------------------- schematic surgery ----------------------------

# Device:R lib pin offsets (Y-up). absolute = (sx + px, sy - py).
PIN_R = {"1": (0, 3.81), "2": (0, -3.81)}


# Three new charger-section resistors, placed on the empty Y=228.60
# schematic strip so they don't collide with the Phase-14 (Y=177.80)
# or Phase-18 (Y=203.20/220.98) additions.
INSTANCES = [
    {
        "ref": "R20",
        "lib": "Device:R",
        "value": "7.15k",
        "fp": "Resistor_SMD:R_0805_2012Metric",
        # Phase-14 X-strip (165.10, 190.50, 215.90), dropped down to
        # Y=232.41 so pins (228.60, 236.22) land on the 1.27 mm
        # connection grid clear of C27..C31 (Y=177.80) and R23/C32
        # (Y=203.20).
        "at": (165.10, 232.41),
        "fam": "R",
        # pin 1 top  -> VBAT_SYS;  pin 2 bottom -> CHG_VFB (upper leg)
        "nets": {"1": "VBAT_SYS", "2": "CHG_VFB"},
    },
    {
        "ref": "R21",
        "lib": "Device:R",
        "value": "10k",
        "fp": "Resistor_SMD:R_0805_2012Metric",
        "at": (190.50, 232.41),
        "fam": "R",
        # pin 1 top  -> CHG_REF (VREF);  pin 2 bottom -> TS_BIAS
        "nets": {"1": "CHG_REF", "2": "TS_BIAS"},
    },
    {
        "ref": "R22",
        "lib": "Device:R",
        "value": "100k",
        "fp": "Resistor_SMD:R_0805_2012Metric",
        "at": (215.90, 232.41),
        "fam": "R",
        # pin 1 top  -> CHG_REF (VREF);  pin 2 bottom -> MPPSET
        "nets": {"1": "CHG_REF", "2": "MPPSET"},
    },
]


# Rename labels at specific schematic coordinates. (x, y, old_net,
# new_net). Coordinates are pin-endpoint-anchored labels that the
# Phase-2 schematic generator dropped at each IC pin stub.
RENAME_LABEL_AT: list[tuple[float, float, str, str]] = [
    # BLOCKING-1: IC3 VSEL pin 4 stub  (345.44, 74.93) label is at
    # (342.90, 74.93) because the label sits one grid unit west of
    # the pin endpoint.
    (342.90, 74.93, "REG_EN", "GND"),
    # Non-blocking: IC3 PS/SYNC pin 3 -> GND for power-save mode.
    (342.90, 72.39, "3V3", "GND"),
    # BLOCKING-4b: R2 pin 1 relabelled so R2 acts as the MPPSET
    # lower-leg to GND instead of a stray 100 k pull to
    # /CHG_SENSE_NEG.
    (101.60, 97.79, "CHG_SENSE_NEG", "GND"),
    # Non-blocking: R4.2 (STAT1 pull-down) -> STAT1 pull-up.
    (152.40, 105.41, "GND", "3V3"),
    # Non-blocking: R5.2 (STAT2 pull-down) -> STAT2 pull-up.
    (50.80, 130.81, "GND", "3V3"),
]


# Component-value updates (schematic-side). (ref, old_value, new_value).
VALUE_CHANGES = [
    ("C5", "100nF", "1uF"),
]


# --------------------------- PCB surgery ----------------------------------

# New PCB footprints. Placed just east of the existing R1/R2/R3 column
# in the BQ24650 cluster so the new divider legs have a short trace to
# their target IC2 pins.
NEW_FOOTPRINTS = [
    # R20: VFB upper divider, sits in row with R1 (VFB bottom, x=30,y=72).
    #   pad 1 north -> /VBAT_SYS (long run west to C20/C21 column)
    #   pad 2 south -> /CHG_VFB  (0.2 mm trace to R1.1 at (30,72.91))
    {"ref": "R20", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "7.15k", "xy": (36.0, 72.0), "rot": 90},
    # R21: TS upper divider, sits in row with R3 (TS bottom, x=30,y=76).
    #   pad 1 north -> /CHG_REF
    #   pad 2 south -> /TS_BIAS  (0.2 mm trace to R3.1 at (30,76.91))
    {"ref": "R21", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "10k",  "xy": (36.0, 76.0), "rot": 90},
    # R22: MPPSET upper divider, above R20/R21. Pad 1 north -> /CHG_REF,
    # pad 2 south -> /MPPSET (joins R2.2 at (33, 71.09)).
    {"ref": "R22", "fp": "Resistor_SMD:R_0805_2012Metric",
     "value": "100k", "xy": (36.0, 68.0), "rot": 90},
]


# Refs whose unnumbered-EP and explicitly numbered EP pads should land
# on /GND. Carried forward from Phase 18 so the re-route preserves EP
# assignments after any net resync.
EP_TO_GND_REFS = {"IC2", "IC3", "IC4"}
EP_TO_GND_EXPLICIT = {("IC3", "16")}


# ------------------------------ helpers ----------------------------------

def newuuid() -> str:
    return str(uuid.uuid4())


def absolute_pin(inst, pin_num) -> tuple[float, float]:
    sx, sy = inst["at"]
    if inst["fam"] == "R":
        px, py = PIN_R[pin_num]
    else:
        raise KeyError(f"unknown pin family {inst['fam']}")
    return (sx + px, sy - py)


def emit_instance(inst) -> str:
    ref = inst["ref"]
    lib = inst["lib"]
    val = inst["value"]
    fp = inst["fp"]
    sx, sy = inst["at"]
    u = newuuid()
    return (
        f'(symbol (lib_id "{lib}") (at {sx} {sy} 0) (unit 1) '
        f'(in_bom yes) (on_board yes) (dnp no) (uuid "{u}") '
        f'(property "Reference" "{ref}" (at {sx} {sy - 2.54} 0) '
        f'(effects (font (size 1.27 1.27)))) '
        f'(property "Value" "{val}" (at {sx} {sy + 2.54} 0) '
        f'(effects (font (size 1.27 1.27)))) '
        f'(property "Footprint" "{fp}" (at {sx} {sy} 0) '
        f'(effects (font (size 1.27 1.27)) (hide yes))) '
        f'(property "Datasheet" "~" (at {sx} {sy} 0) '
        f'(effects (font (size 1.27 1.27)) (hide yes))) '
        f'(instances (project "project" '
        f'(path "/" (reference "{ref}") (unit 1)))))'
    )


def emit_label(net: str, x: float, y: float) -> str:
    u = newuuid()
    return (
        f'(label "{net}" (at {x:.2f} {y:.2f} 0)\n'
        f'\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'\t\t(uuid "{u}")\n'
        f'\t)'
    )


def rename_label_at(text: str, renames) -> tuple[int, str]:
    n = 0
    for x, y, old, new in renames:
        pat = re.compile(
            rf'(\(label )"{re.escape(old)}"(\s*\(at {re.escape(f"{x:.2f}")} {re.escape(f"{y:.2f}")} )'
        )
        m = pat.search(text)
        if m:
            prefix = m.group(1) + f'"{new}"' + m.group(2)
            text = text[:m.start()] + prefix + text[m.end():]
            n += 1
        else:
            print(f"  WARNING: label {old!r} @ ({x:.2f},{y:.2f}) not found",
                  file=sys.stderr)
    return n, text


def change_value(text: str, ref: str, old_val: str, new_val: str) -> tuple[int, str]:
    """Change the `(property "Value" "..."` string of the instance whose
    `(property "Reference" "<ref>"` appears later in the same symbol
    block. We locate the symbol by its Reference property, then rewrite
    the nearby Value property."""
    ref_marker = f'"Reference" "{ref}"'
    idx = text.find(ref_marker)
    if idx < 0:
        return 0, text
    sym_start = text.rfind("(symbol (lib_id", 0, idx)
    if sym_start < 0:
        return 0, text
    # Find the balanced end of this (symbol ...) block to bound the replace
    depth, i = 0, sym_start
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                i += 1
                break
        i += 1
    block = text[sym_start:i]
    pat = re.compile(
        r'\(property "Value" "' + re.escape(old_val) + r'"'
    )
    replacement = f'(property "Value" "{new_val}"'
    new_block, n = pat.subn(replacement, block, count=1)
    if n:
        text = text[:sym_start] + new_block + text[i:]
    return n, text


def find_sheet_instances_start(text: str) -> int:
    idx = text.rfind("(sheet_instances")
    if idx < 0:
        raise RuntimeError("no sheet_instances block")
    return idx


# ---------------------- PCB / net sync / freeroute -----------------------

def mm_vec(x: float, y: float) -> "pcbnew.VECTOR2I":
    return pcbnew.VECTOR2I(int(x * MM), int(y * MM))


def load_fp(lib_id: str) -> pcbnew.FOOTPRINT:
    lib, name = lib_id.split(":", 1)
    fp = pcbnew.FootprintLoad(f"/usr/share/kicad/footprints/{lib}.pretty", name)
    if fp is None:
        raise KeyError(f"footprint {lib_id} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def place_fp(board, ref, lib_id, value, x, y, rot):
    fp = load_fp(lib_id)
    board.Add(fp)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(mm_vec(x, y))
    fp.SetOrientationDegrees(rot)
    return fp


def kicad_netlist_map() -> dict[tuple[str, str], str]:
    BUILD.mkdir(exist_ok=True)
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
         "--output", str(BUILD / "warden-apex.net"), str(SCH)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    text = (BUILD / "warden-apex.net").read_text()
    out: dict[tuple[str, str], str] = {}
    pos = 0
    while True:
        m = re.search(r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)', text[pos:])
        if not m:
            break
        start = pos + m.start()
        name = m.group(1)
        depth, i = 0, start
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        for nm in re.finditer(
            r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', body,
        ):
            out[(nm.group(1), nm.group(2))] = name
        pos = i + 1
    return out


def sync_nets(board) -> tuple[int, int]:
    """Re-assign every pad's net from the schematic's /NET-prefixed names."""
    net_map = kicad_netlist_map()
    assigned = missing = 0
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
            else:
                pad.SetNet(board.FindNet(""))
                missing += 1
    return assigned, missing


def _safe_tracks(board):
    try:
        return list(board.Tracks())
    except TypeError:
        out = []
        coll = board.Tracks()
        try:
            n = coll.size()
        except Exception:
            return out
        for i in range(n):
            out.append(coll[i])
        return out


def clear_all_tracks(board) -> int:
    tracks = _safe_tracks(board)
    for t in tracks:
        board.Remove(t)
    return len(tracks)


def clear_conflicting_tracks(board) -> tuple[int, int]:
    """Remove only tracks/vias whose net no longer matches the net of
    a pad their endpoint overlaps, OR whose net is one of the rails
    whose topology changed in Phase 19.

    This preserves the Phase-18 routing for the >95% of nets that were
    not touched, so Freerouting only has to close the new R20..R22
    fan-out plus reroute around the net-changed pads.
    """
    MM_LOCAL = MM
    # Build pad_net map keyed by (x, y, layer). Use 2 decimal mm.
    pad_net = {}
    for fp in board.Footprints():
        for pad in fp.Pads():
            net = pad.GetNetname()
            p = pad.GetPosition()
            pad_net[(round(p.x / MM_LOCAL, 3),
                    round(p.y / MM_LOCAL, 3))] = (net, pad, fp.GetReference())

    # Nets whose topology explicitly changed this phase. Empty by
    # default - we only clear tracks that the pad-conflict check
    # (Rule 2) catches. Non-conflicting routing is preserved so
    # Freerouting only has to close the new R20..R22 fan-out plus
    # any airwires that result from pad-net changes.
    MODIFIED_NETS: set[str] = set()

    tracks = _safe_tracks(board)
    removed_conflict = 0
    removed_modified = 0
    for t in tracks:
        net_name = t.GetNetname()
        # Rule 1: track is on a MODIFIED_NET -> remove so Freerouter
        # re-plans it in light of the new pad connections.
        if net_name in MODIFIED_NETS:
            board.Remove(t)
            removed_modified += 1
            continue
        # Rule 2: track endpoint overlaps a pad whose net differs ->
        # short candidate, remove.
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            hit = pad_net.get((round(p.x / MM_LOCAL, 3),
                              round(p.y / MM_LOCAL, 3)))
            if hit and hit[0] and hit[0] != net_name:
                board.Remove(t)
                removed_conflict += 1
            continue
        s = t.GetStart()
        e = t.GetEnd()
        bad = False
        for p in (s, e):
            hit = pad_net.get((round(p.x / MM_LOCAL, 3),
                              round(p.y / MM_LOCAL, 3)))
            if hit and hit[0] and hit[0] != net_name:
                bad = True
                break
        if bad:
            board.Remove(t)
            removed_conflict += 1
    return removed_conflict, removed_modified


def run_freerouting() -> bool:
    BUILD.mkdir(exist_ok=True)
    dsn = BUILD / "warden.dsn"
    ses = BUILD / "warden.ses"
    ses.unlink(missing_ok=True)

    board = pcbnew.LoadBoard(str(PCB))
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    if not dsn.exists():
        print("  DSN export failed")
        return False

    if not FR_JAR.exists():
        print(f"  freerouting.jar missing at {FR_JAR} - skip")
        return False

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{BUILD}:/work",
        "-v", f"{FR_JAR}:/opt/freerouting.jar",
        "-w", "/work",
        "eclipse-temurin:21-jre",
        "java", "-jar", "/opt/freerouting.jar",
        "-de", "/work/warden.dsn",
        "-do", "/work/warden.ses",
        "-mp", "30",
        "-host-mode", "cli",
    ]
    print("  running Freerouting (30 passes)...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join(r.stdout.splitlines()[-12:])
    print(tail)
    if r.returncode != 0:
        print(r.stderr[-500:])

    if not ses.exists():
        print("  SES not produced")
        return False

    print("  importing SES -> PCB (via tools/phase4_import_ses.py)")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_import_ses.py")],
        capture_output=True, text=True,
    )
    print("\n".join(r.stdout.splitlines()[-5:]))
    return True


def assign_ep_gnd(board) -> int:
    gnd = board.FindNet("/GND")
    if gnd is None:
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
    return n


def refill_zones(board) -> int:
    filler = pcbnew.ZONE_FILLER(board)
    zones = list(board.Zones())
    filler.Fill(zones)
    return len(zones)


def run_drc() -> None:
    subprocess.run(
        ["kicad-cli", "pcb", "drc",
         "--schematic-parity",
         "--severity-error",
         "--format=report",
         "--units=mm",
         "--output", str(DRC),
         str(PCB)],
        check=False,
    )


def run_erc() -> None:
    subprocess.run(
        ["kicad-cli", "sch", "erc",
         "--severity-all",
         "--format=report",
         "--units=mm",
         "--output", str(ERC),
         str(SCH)],
        check=False,
    )


# ------------------ static verification of fix landings ------------------

EXPECTED_FIXES = {
    # (ref, pad) -> expected net
    ("IC3", "3"): "/GND",       # PS/SYNC
    ("IC3", "4"): "/GND",       # VSEL (BLOCKING-1)
    ("R2", "1"): "/GND",        # MPPSET bottom leg (BLOCKING-4b)
    ("R4", "2"): "/3V3",        # STAT1 pull-up
    ("R5", "2"): "/3V3",        # STAT2 pull-up
    ("R20", "1"): "/VBAT_SYS",  # BLOCKING-2
    ("R20", "2"): "/CHG_VFB",
    ("R21", "1"): "/CHG_REF",   # BLOCKING-3
    ("R21", "2"): "/TS_BIAS",
    ("R22", "1"): "/CHG_REF",   # BLOCKING-4
    ("R22", "2"): "/MPPSET",
}


def verify_fixes(board) -> int:
    bad = 0
    print("  Static fix verification:")
    pad_net: dict[tuple[str, str], str] = {}
    for fp in board.Footprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            pad_net[(ref, pad.GetNumber())] = pad.GetNetname()
    for (ref, pin), want in EXPECTED_FIXES.items():
        have = pad_net.get((ref, pin), "<missing>")
        status = "OK  " if have == want else "FAIL"
        if have != want:
            bad += 1
        print(f"    {status}  {ref}.{pin:<3s} -> {have} (want {want})")
    return bad


# ------------------------------- main -------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-freeroute", action="store_true",
                    help="Skip Freerouting (for faster debugging).")
    args = ap.parse_args()

    # ---------- 0) Schematic ----------
    print("[19.0] Patching schematic ...")
    text = SCH.read_text()
    if PHASE19_MARKER in text:
        print("  Phase 19 marker already present - skipping schematic patch")
    else:
        n, text = rename_label_at(text, RENAME_LABEL_AT)
        print(f"  renamed {n}/{len(RENAME_LABEL_AT)} net labels")
        for ref, old, new in VALUE_CHANGES:
            n2, text = change_value(text, ref, old, new)
            print(f"  {ref}.Value: {old} -> {new} ({n2} replacement)")
        inst_blobs, label_blobs = [], []
        for inst in INSTANCES:
            inst_blobs.append(emit_instance(inst))
            for pin_num, net in inst["nets"].items():
                px, py = absolute_pin(inst, pin_num)
                label_blobs.append(emit_label(net, px, py))
        splice_at = find_sheet_instances_start(text)
        additions = "\n".join(inst_blobs + label_blobs) + "\n"
        text = text[:splice_at] + additions + text[splice_at:]
        SCH.write_text(text)
        print(f"  added {len(inst_blobs)} symbols (R20/R21/R22), "
              f"{len(label_blobs)} net labels")

    # ---------- 1) PCB footprint placement ----------
    print("[19.1] Placing R20/R21/R22 on the PCB ...")
    board = pcbnew.LoadBoard(str(PCB))
    added = moved = 0
    for spec in NEW_FOOTPRINTS:
        existing = board.FindFootprintByReference(spec["ref"])
        if existing is not None:
            existing.SetPosition(mm_vec(spec["xy"][0], spec["xy"][1]))
            existing.SetOrientationDegrees(spec["rot"])
            print(f"  reposition {spec['ref']:4s} -> {spec['xy']} rot={spec['rot']}")
            moved += 1
            continue
        fp = place_fp(board, spec["ref"], spec["fp"], spec["value"],
                      spec["xy"][0], spec["xy"][1], spec["rot"])
        print(f"  + {spec['ref']:4s} {spec['fp']} @ {spec['xy']} rot={spec['rot']}")
        added += 1
    print(f"  {added} added, {moved} repositioned")

    # ---------- 2) C5 value ----------
    print("[19.2] Updating C5 value on PCB ...")
    c5 = board.FindFootprintByReference("C5")
    if c5 is not None:
        if c5.GetValue() != "1uF":
            c5.SetValue("1uF")
            print("  C5.Value -> 1uF")
        else:
            print("  C5.Value already 1uF - skipped")

    board.Save(str(PCB))

    # ---------- 3) Net re-sync (pads -> schematic /NET names) ----------
    print("[19.3] Re-syncing pad nets from schematic ...")
    board = pcbnew.LoadBoard(str(PCB))
    a, m = sync_nets(board)
    print(f"  {a} pads netted, {m} left un-netted")
    board.Save(str(PCB))

    # ---------- 4) Static verification of the fixes ----------
    bad = verify_fixes(board)
    if bad:
        print(f"  !! {bad} fix(es) missing — aborting before Freerouting")
        return 2

    # ---------- 5) Re-route ----------
    if not args.no_freeroute:
        print("[19.5] Surgical track cleanup (preserve Phase-18 routing) ...")
        board = pcbnew.LoadBoard(str(PCB))
        rc, rm = clear_conflicting_tracks(board)
        print(f"  {rc} conflicting + {rm} modified-net tracks/vias removed")
        board.Save(str(PCB))

        print("[19.6] Running Freerouting ...")
        ok = run_freerouting()
        if not ok:
            print("  Freerouting step failed - continuing to hygiene pass")

        # Phase 10 hygiene (net sync, thermal pads, zones, silk)
        print("[19.7] Running Phase 10 hygiene (re-sync + zone fill + silk) ...")
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools/phase10_drc_fix.py")],
            capture_output=True, text=True,
        )
        print("\n".join(r.stdout.splitlines()[-12:]))

        # EP -> GND + U6.14 bridge + zone refill in a fresh subprocess
        # because pcbnew.LoadBoard starts returning SwigPyObject stubs
        # after the Freerouting + phase10 subprocess chain has run in
        # this interpreter.
        print("[19.8] Finalize (EP assign + bridges + refill) ...")
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools/phase19_finalize.py")],
            capture_output=True, text=True,
        )
        print("\n".join(r.stdout.splitlines()[-20:]))
        if r.returncode != 0:
            print(r.stderr[-500:])

    # ---------- 6) ERC + DRC ----------
    print("[19.9] Running ERC ...")
    run_erc()
    print(f"  wrote {ERC}")
    print("[19.10] Running DRC (errors only) ...")
    run_drc()
    print(f"  wrote {DRC}")

    # ---------- 7) Final verification (schematic netlist only) ----------
    # Avoid pcbnew.LoadBoard here - the SWIG bindings get flaky after
    # the Freerouting + phase10 + phase19_finalize subprocess chain.
    # The /NET map from `kicad-cli sch export netlist` is the canonical
    # authority KiCad uses anyway.
    print("[19.11] Final fix verification from schematic netlist ...")
    net_map = kicad_netlist_map()
    bad = 0
    for (ref, pin), want in EXPECTED_FIXES.items():
        have = net_map.get((ref, pin), "<missing>")
        status = "OK  " if have == want else "FAIL"
        if have != want:
            bad += 1
        print(f"    {status}  {ref}.{pin:<3s} -> {have} (want {want})")
    if bad:
        print(f"  !! {bad} fix(es) regressed after reroute")
        return 3

    print("\nPhase 19 complete.")
    print("  Next step: python3 tools/phase12_variants.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
