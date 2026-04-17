#!/usr/bin/env python3
"""
Phase 18 — Expansion I/O additions.

Daughterboard-style expansion on the west edge of the PCB.

New refdes:
    J4  Conn_02x07_Odd_Even  2.54 mm pin header, 14-pin 'expansion bus'
    J5  Conn_01x04           JST-SH horizontal 4-pin, Qwiic / STEMMA QT
    F1  Fuse                 500 mA polyfuse (0805) on EXP_VBAT rail
    R24 R                    10 k pull-up on EXP_IRQ (MCP23017 INTA)

New nets:
    EXP_VBAT            F1 pin2  <-- VBAT_SYS (F1 pin1)
    EXP_GP1..EXP_GP6    MCP23017 U4 GPA1..GPA6 (were NC in Phase 2)
    EXP_IRQ             MCP23017 U4 INTA (pin 20, was NC) + R24 pull-up

Pin map on J4 (2x7 Odd/Even):
    1 3V3        2 EXP_VBAT
    3 GND        4 I2C_SDA
    5 I2C_SCL    6 GND
    7 EXP_GP1    8 EXP_GP2
    9 EXP_GP3   10 EXP_GP4
   11 EXP_GP5   12 EXP_GP6
   13 GND       14 EXP_IRQ

Pin map on J5 (Qwiic / STEMMA QT order):
    1 GND
    2 3V3
    3 I2C_SDA
    4 I2C_SCL

Schematic side-effects:
    * remove U4 NC flags on INTA (337.82, 251.46) and
      GPA1..GPA6 (373.38, 259.08..271.78)
    * keep INTB, GPB1..GPB7, GPA7 NC

Idempotent: bails out if the Phase-18 sentinel (J4) is already present.
"""
from __future__ import annotations

import pathlib
import re
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"

PHASE18_MARKER = "J4"  # J4 only exists after Phase 18 is applied


def newuuid() -> str:
    return str(uuid.uuid4())


# ----------------------------- pin offset tables -------------------------

# Lib-space pin offsets (Y-up). Schematic absolute pin = sym + (px, -py).
PIN = {
    # Conn_02x07_Odd_Even: odd pins left column, even pins right column.
    # Spacing 2.54 mm vertical, columns at x = -5.08 and x = 7.62.
    "Conn_02x07_Odd_Even": {
        "1":  (-5.08,  7.62),  "2":  (7.62,  7.62),
        "3":  (-5.08,  5.08),  "4":  (7.62,  5.08),
        "5":  (-5.08,  2.54),  "6":  (7.62,  2.54),
        "7":  (-5.08,  0.00),  "8":  (7.62,  0.00),
        "9":  (-5.08, -2.54), "10":  (7.62, -2.54),
        "11": (-5.08, -5.08), "12":  (7.62, -5.08),
        "13": (-5.08, -7.62), "14":  (7.62, -7.62),
    },
    # Conn_01x04: all pins in left column, 2.54 spacing. Pin 4 at y=-5.08.
    "Conn_01x04": {
        "1": (-5.08,  2.54),
        "2": (-5.08,  0.00),
        "3": (-5.08, -2.54),
        "4": (-5.08, -5.08),
    },
    # Device:Fuse: pin 1 at (0, 3.81), pin 2 at (0, -3.81).
    "Fuse": {"1": (0, 3.81), "2": (0, -3.81)},
    # Device:R: pin 1 at (0, 3.81), pin 2 at (0, -3.81).
    "R": {"1": (0, 3.81), "2": (0, -3.81)},
}


# ----------------------------- instances ---------------------------------

# Placed on the empty schematic strip to the right of the existing sheet
# (x ≈ 290..310). All on the 2.54 mm grid.
INSTANCES = [
    # J4 — 2x7 expansion GPIO header
    {
        "ref": "J4",
        "lib": "Connector_Generic:Conn_02x07_Odd_Even",
        "value": "Expansion_Header",
        "fp": "Connector_PinHeader_2.54mm:PinHeader_2x07_P2.54mm_Vertical",
        "at": (292.10, 203.20),
        "fam": "Conn_02x07_Odd_Even",
        "nets": {
            "1":  "3V3",      "2":  "EXP_VBAT",
            "3":  "GND",      "4":  "I2C_SDA",
            "5":  "I2C_SCL",  "6":  "GND",
            "7":  "EXP_GP1",  "8":  "EXP_GP2",
            "9":  "EXP_GP3",  "10": "EXP_GP4",
            "11": "EXP_GP5",  "12": "EXP_GP6",
            "13": "GND",      "14": "EXP_IRQ",
        },
    },
    # J5 — Qwiic / STEMMA QT (JST-SH 4-pin horizontal)
    {
        "ref": "J5",
        "lib": "Connector_Generic:Conn_01x04",
        "value": "Qwiic",
        "fp": "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal",
        "at": (317.50, 203.20),
        "fam": "Conn_01x04",
        "nets": {
            "1": "GND",
            "2": "3V3",
            "3": "I2C_SDA",
            "4": "I2C_SCL",
        },
    },
    # F1 — 500 mA polyfuse on EXP_VBAT rail
    {
        "ref": "F1",
        "lib": "Device:Fuse",
        "value": "500mA_PTC",
        "fp": "Fuse:Fuse_0805_2012Metric",
        "at": (292.10, 220.98),
        "fam": "Fuse",
        "nets": {"1": "VBAT_SYS", "2": "EXP_VBAT"},
    },
    # R24 — 10 k pull-up on EXP_IRQ
    {
        "ref": "R24",
        "lib": "Device:R",
        "value": "10k",
        "fp": "Resistor_SMD:R_0805_2012Metric",
        "at": (317.50, 220.98),
        "fam": "R",
        "nets": {"1": "3V3", "2": "EXP_IRQ"},
    },
]


# U4 pin coordinates (absolute, as already in the schematic).
# These NC flags must be DELETED so the new labels below can own the pin.
U4_NC_COORDS_TO_REMOVE = [
    (337.82, 251.46),  # INTA    -> EXP_IRQ
    (373.38, 259.08),  # GPA1    -> EXP_GP1
    (373.38, 261.62),  # GPA2    -> EXP_GP2
    (373.38, 264.16),  # GPA3    -> EXP_GP3
    (373.38, 266.70),  # GPA4    -> EXP_GP4
    (373.38, 269.24),  # GPA5    -> EXP_GP5
    (373.38, 271.78),  # GPA6    -> EXP_GP6
]

# New labels placed AT those pin coordinates after NC removal.
U4_NEW_LABELS = [
    (337.82, 251.46, "EXP_IRQ"),
    (373.38, 259.08, "EXP_GP1"),
    (373.38, 261.62, "EXP_GP2"),
    (373.38, 264.16, "EXP_GP3"),
    (373.38, 266.70, "EXP_GP4"),
    (373.38, 269.24, "EXP_GP5"),
    (373.38, 271.78, "EXP_GP6"),
]


# ----------------------------- helpers ----------------------------------

def absolute_pin(inst, pin_num) -> tuple[float, float]:
    sx, sy = inst["at"]
    px, py = PIN[inst["fam"]][pin_num]
    # Symbol placed at angle 0 everywhere here. Y-flip from lib to sch.
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


def remove_nc_at(text: str, coords: list[tuple[float, float]]) -> tuple[int, str]:
    """Remove (no_connect (at X Y ...) (uuid ...)) nodes whose (at X Y) matches."""
    removed = 0
    for cx, cy in coords:
        # Two common formats: with or without the extra field between at and uuid.
        pat = re.compile(
            r'\(no_connect\s*\(at\s+'
            + re.escape(f"{cx}") + r'\s+' + re.escape(f"{cy}")
            + r'[^)]*\)\s*\(uuid\s+"[^"]+"\)\s*\)'
        )
        new_text, n = pat.subn('', text, count=1)
        if n == 0:
            # try with .0 suffix variants
            pat2 = re.compile(
                r'\(no_connect\s*\(at\s+'
                + re.escape(f"{cx}") + r'\.0\s+' + re.escape(f"{cy}")
                + r'[^)]*\)\s*\(uuid\s+"[^"]+"\)\s*\)'
            )
            new_text, n = pat2.subn('', text, count=1)
        if n == 0:
            # try rounded to integer match
            pat3 = re.compile(
                r'\(no_connect\s*\(at\s+'
                + re.escape(str(cx)) + r'\s+' + re.escape(str(cy))
                + r'[^)]*\)\s*\(uuid\s+"[^"]+"\)\s*\)'
            )
            new_text, n = pat3.subn('', text, count=1)
        if n:
            text = new_text
            removed += n
        else:
            print(f"  WARNING: couldn't find NC at ({cx}, {cy})", file=sys.stderr)
    return removed, text


def find_sheet_instances_start(text: str) -> int:
    idx = text.rfind("(sheet_instances")
    if idx < 0:
        raise RuntimeError("no sheet_instances block")
    return idx


# ---------- library cache helpers ------------------------------------------

KICAD_SYMS = pathlib.Path("/usr/share/kicad/symbols")


def extract_balanced(text: str, start: int) -> tuple[int, int]:
    d = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            d += 1
        elif text[i] == ")":
            d -= 1
            if d == 0:
                return start, i
    raise ValueError("unterminated s-expr")


def load_lib_symbol(lib_name: str, sym_name: str) -> str:
    """Return the full (symbol "lib:name" ...) s-expression for the cache,
    with lib_id normalised to '<lib>:<sym>'.
    """
    lib_path = KICAD_SYMS / f"{lib_name}.kicad_sym"
    lib = lib_path.read_text()
    needle = f'(symbol "{sym_name}"'
    i = lib.find(needle)
    if i < 0:
        raise RuntimeError(f"symbol {sym_name} not found in {lib_path}")
    _, j = extract_balanced(lib, i)
    body = lib[i:j + 1]
    # Cache uses namespaced ID "<lib>:<sym>" rather than bare "<sym>".
    # ONLY rewrite the top-level symbol name. Sub-symbol names like
    # "Conn_02x07_Odd_Even_1_1" keep their bare form (matches how existing
    # cached symbols are stored in the project schematic).
    body = body.replace(needle, f'(symbol "{lib_name}:{sym_name}"', 1)
    return body


def add_cached_symbols(text: str, need: list[tuple[str, str]]) -> tuple[int, str]:
    """Splice missing (symbol "lib:name" ...) blocks into the lib_symbols
    block. `need` is [(lib_name, sym_name), ...]. Returns (count_added, text).
    """
    added = 0
    for lib_name, sym_name in need:
        marker = f'"{lib_name}:{sym_name}"'
        if marker in text:
            continue
        block = load_lib_symbol(lib_name, sym_name)
        # Locate (lib_symbols ...) and insert just before its closing paren.
        ls_idx = text.find("(lib_symbols")
        _, ls_end = extract_balanced(text, ls_idx)
        text = text[:ls_end] + "\n" + block + "\n" + text[ls_end:]
        added += 1
    return added, text


# ----------------------------- main -------------------------------------

def main() -> int:
    text = SCH.read_text()

    # Sentinel: "Reference" "J4" appears only after Phase 18 ran.
    if '"Reference" "J4"' in text:
        print("Phase 18 marker already present — nothing to do.")
        return 0

    # 1) Ensure missing lib_symbols are cached in the schematic.
    needed_cache = [
        ("Connector_Generic", "Conn_02x07_Odd_Even"),
        ("Connector_Generic", "Conn_01x04"),
        ("Device", "Fuse"),
    ]
    added_cache, text = add_cached_symbols(text, needed_cache)
    print(f"Cached {added_cache} missing library symbols in schematic.")

    # 2) Remove NC flags on U4 pins that we'll take over.
    n, text = remove_nc_at(text, U4_NC_COORDS_TO_REMOVE)
    print(f"Removed {n} NC flags from U4 (expected {len(U4_NC_COORDS_TO_REMOVE)}).")

    # 3) Build additions (new symbols + new labels + U4 pin labels).
    inst_blobs = []
    label_blobs = []
    for inst in INSTANCES:
        inst_blobs.append(emit_instance(inst))
        for pin_num, net in inst["nets"].items():
            px, py = absolute_pin(inst, pin_num)
            label_blobs.append(emit_label(net, px, py))

    for x, y, net in U4_NEW_LABELS:
        label_blobs.append(emit_label(net, x, y))

    splice_at = find_sheet_instances_start(text)
    additions = "\n".join(inst_blobs + label_blobs) + "\n"
    text = text[:splice_at] + additions + text[splice_at:]

    SCH.write_text(text)
    print(f"Phase 18 applied:")
    print(f"  {len(inst_blobs)} new symbol instances: J4, J5, F1, R24")
    print(f"  {len(label_blobs)} new net labels")
    print(f"  freed U4 pins: INTA, GPA1..GPA6 (now on expansion nets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
