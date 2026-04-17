#!/usr/bin/env python3
"""
Phase 14 — schematic engineering audit.

Adds missing decoupling / bulk capacitance and a pull-up for the
MAX98357A ~SD_MODE line, which was strapped to GND in Phase 2 and
therefore held the amplifier in permanent shutdown.

Changes:
    1. Rename the single `GND` label sitting on IC4 pin 4 (~SD_MODE at
       absolute (292.1, 154.94)) to `SD_MODE`.
    2. Add R23 100k pull-up from /SD_MODE to /3V3 (puts the amp in
       "right-channel mono, enabled" per data sheet, since 1.4 V <
       V(~SD) < 3.3 V).
    3. Add missing local decoupling / bulk on existing rails:
         C27  100 nF  near IC2 (BQ24650)   on /SOLAR_IN
         C28  100 nF  near U2  (Ra-01)     on /3V3
         C29  100 nF  near IC1 (SIM7080G)  on /3V3
         C30  100 nF  near U3  (Swarm)     on /MODEM_VBAT_SW
         C31  47 uF  bulk  near U3         on /MODEM_VBAT_SW
         C32  10 uF  bulk  near IC3        on /3V3
    4. Verify I2C pull-ups R13/R14 are wired to /I2C_SCL and /I2C_SDA
       respectively (already correct in Phase-7-era schematic).

Idempotent: bails out if the Phase-14 sentinel is already present.

Usage:
    python3 tools/phase14_schematic_audit.py
"""
from __future__ import annotations

import pathlib
import re
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"

PHASE14_MARKER = "R_SD_MODE_PU"  # sentinel embedded in schematic as R23 value suffix


def newuuid() -> str:
    return str(uuid.uuid4())


# ----------------------------- pin offsets --------------------------------

# Lib-space offsets for a Device:C / Device:R symbol placed at angle 0.
# KiCad convention (Y-down): abs_y = sy - py_lib.
PIN = {
    "R": {"1": (0, 3.81), "2": (0, -3.81)},
    "C": {"1": (0, 3.81), "2": (0, -3.81)},
}


# ----------------------------- instances ----------------------------------

# All new schematic instances live in an empty mid-sheet region.
# Placement coords are multiples of 2.54 mm to stay on grid.
INSTANCES = [
    # Local 100 nF decouplers at each IC VDD/VIN pin
    {"ref": "C27", "lib": "Device:C",
     "value": "100nF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (165.10, 177.80), "fam": "C",
     "nets": {"1": "SOLAR_IN", "2": "GND"}},
    {"ref": "C28", "lib": "Device:C",
     "value": "100nF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (190.50, 177.80), "fam": "C",
     "nets": {"1": "3V3", "2": "GND"}},
    {"ref": "C29", "lib": "Device:C",
     "value": "100nF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (215.90, 177.80), "fam": "C",
     "nets": {"1": "3V3", "2": "GND"}},
    {"ref": "C30", "lib": "Device:C",
     "value": "100nF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (241.30, 177.80), "fam": "C",
     "nets": {"1": "MODEM_VBAT_SW", "2": "GND"}},

    # Bulk reservoirs (ceramic, non-polarized so schematic stays Device:C)
    {"ref": "C31", "lib": "Device:C",
     "value": "47uF",  "fp": "Capacitor_SMD:C_1210_3225Metric",
     "at": (266.70, 177.80), "fam": "C",
     "nets": {"1": "MODEM_VBAT_SW", "2": "GND"}},
    {"ref": "C32", "lib": "Device:C",
     "value": "10uF",  "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (165.10, 203.20), "fam": "C",
     "nets": {"1": "3V3", "2": "GND"}},

    # MAX98357A ~SD_MODE pull-up to /3V3 (sentinel component for Phase 14)
    {"ref": "R23", "lib": "Device:R",
     "value": f"100k {PHASE14_MARKER}",
     "fp": "Resistor_SMD:R_0805_2012Metric",
     "at": (190.50, 203.20), "fam": "R",
     "nets": {"1": "3V3", "2": "SD_MODE"}},
]


# IC4 pin 4 (~SD_MODE) is at absolute (292.1, 154.94). Phase 2 placed a
# GND label at that coordinate (strap to GND -> amp in shutdown). We
# rename that one specific label to SD_MODE.
RENAME_LABEL_AT: list[tuple[float, float, str, str]] = [
    (292.10, 154.94, "GND", "SD_MODE"),
]


# ----------------------------- helpers ------------------------------------

def load_sch() -> str:
    return SCH.read_text()


def save_sch(text: str) -> None:
    SCH.write_text(text)


def find_sheet_instances_start(text: str) -> int:
    idx = text.rfind("(sheet_instances")
    if idx < 0:
        raise RuntimeError("no sheet_instances block")
    return idx


def absolute_pin(inst, pin_num) -> tuple[float, float]:
    sx, sy = inst["at"]
    fam_map = PIN[inst["fam"]]
    px, py = fam_map[pin_num]
    return (sx + px, sy - py)


def emit_instance(inst) -> str:
    ref = inst["ref"]
    lib = inst["lib"]
    val = inst["value"]
    fp = inst["fp"]
    sx, sy = inst["at"]
    u = newuuid()
    ref_offset = 2.54
    val_offset = -2.54
    return (
        f'(symbol (lib_id "{lib}") (at {sx} {sy} 0) (unit 1) '
        f'(in_bom yes) (on_board yes) (dnp no) (uuid "{u}") '
        f'(property "Reference" "{ref}" (at {sx} {sy - ref_offset} 0) '
        f'(effects (font (size 1.27 1.27)))) '
        f'(property "Value" "{val}" (at {sx} {sy - val_offset} 0) '
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
    return n, text


def verify_i2c_pullups(text: str) -> None:
    """Cross-check R13 / R14 pin-2 nets from the already-rendered netlist.
    This is a defensive print-only audit — fix-ups live in schematic edits
    upstream of this script."""
    import subprocess
    netlist = ROOT / "build/warden-apex.net"
    netlist.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
         "--output", str(netlist), str(SCH)],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    nl = netlist.read_text() if netlist.exists() else ""
    nets = {}
    pos = 0
    while True:
        m = re.search(r'\(net \(code "?\d+"?\) \(name "([^"]+)"\)', nl[pos:])
        if not m:
            break
        start = pos + m.start()
        name = m.group(1)
        depth, i = 0, start
        while i < len(nl):
            if nl[i] == "(":
                depth += 1
            elif nl[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        nets[name] = re.findall(
            r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', nl[start:i + 1]
        )
        pos = i + 1
    want = {"R13": {"1": "/3V3", "2": "/I2C_SCL"},
            "R14": {"1": "/3V3", "2": "/I2C_SDA"}}
    for ref, wants in want.items():
        for pin, net_target in wants.items():
            found = None
            for netname, nodes in nets.items():
                for r, p in nodes:
                    if r == ref and p == pin:
                        found = netname
            status = "OK" if found == net_target else f"MISMATCH (got {found})"
            print(f"    I2C pull-up audit: {ref}.{pin} -> {net_target} : {status}")


# ----------------------------- main ---------------------------------------

def main() -> int:
    text = load_sch()

    if PHASE14_MARKER in text:
        print("Phase 14 marker already present — nothing to do.")
        return 0

    count, text = rename_label_at(text, RENAME_LABEL_AT)
    print(f"Renamed {count} label(s): GND -> SD_MODE at IC4 pin 4")
    if count != 1:
        print("  WARNING: expected exactly 1 rename", file=sys.stderr)

    inst_blobs = []
    label_blobs = []
    for inst in INSTANCES:
        inst_blobs.append(emit_instance(inst))
        for pin_num, net in inst["nets"].items():
            px, py = absolute_pin(inst, pin_num)
            label_blobs.append(emit_label(net, px, py))

    splice_at = find_sheet_instances_start(text)
    additions = "\n".join(inst_blobs + label_blobs) + "\n"
    text = text[:splice_at] + additions + text[splice_at:]

    save_sch(text)
    print(f"Phase 14 applied:")
    print(f"  {len(inst_blobs)} new symbol instances (C27-C32, R23)")
    print(f"  {len(label_blobs)} new net labels")

    verify_i2c_pullups(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
