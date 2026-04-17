#!/usr/bin/env python3
"""
Phase 7 — add variant hardware to the Warden Apex Master schematic so the
same PCB can be populated as Drone / Cell Master / Apex.

Additions:

    Modem rail gate (P-FET load switch + N-FET driver + gate pull-up)
        Q2   AO3401A  (P-MOSFET, SOT-23)         VBAT_SYS -> MODEM_VBAT_SW
        Q3   2N7002   (N-MOSFET, SOT-23)         MODEM_EN -> pulls Q2 gate low
        R16  100k     (0805)                     Q2 gate pull-up to VBAT_SYS

    UART pull-downs on ESP32 RX / modem-TX lines (prevents float when modems DNP)
        R17  100k (0805) on UART1_RX
        R18  100k (0805) on UART2_RX  (Swarm -> SC16IS740 path)
        R19  100k (0805) on UART2_TX

    I2C-to-UART bridge for the Swarm satellite modem (no free ESP32 UART)
        U6   SC16IS740 (TSSOP-20)
        X1   14.7456 MHz crystal (3.2x2.5mm)
        C23, C24  22 pF crystal load caps (0805)
        C25  100 nF decoupler (0805)
        C26  10 uF bulk (0805)

    Four solder jumpers (SolderJumper_2_Open, 1.3mm pitch)
        JP1  JP_MODEM_RAIL  : bypass Q2 for Cell Master (normally OPEN)
        JP2  JP_SIM_VCC     : break SIM holder VCC when SIM7080G DNP (normally CLOSED)
        JP3  JP_SAT_UART_TX : SC16IS740 TX -> Swarm RX (normally CLOSED)
        JP4  JP_SAT_UART_RX : Swarm TX -> SC16IS740 RX (normally CLOSED)

All new nets are named so the MCP23017's free GPB0 drives MODEM_EN.
MODEM_VBAT on the existing IC1/U3/C22 is rewritten to MODEM_VBAT_SW so
the new load switch is actually in-circuit.

This script is idempotent — detects Phase-7 markers and refuses to run
twice.

Usage:
    python3 tools/phase7_add_variant_hw.py
"""
from __future__ import annotations
import pathlib
import re
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
STOCK_SYM_DIR = pathlib.Path("/usr/share/kicad/symbols")

PHASE7_MARKER = "Q_MODEM (Phase 7)"   # sentinel embedded in schematic


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def newuuid() -> str:
    return str(uuid.uuid4())


def _find_block(text: str, name: str) -> tuple[int, int]:
    marker = f'(symbol "{name}"'
    idx = text.find(marker)
    if idx < 0:
        raise KeyError(name)
    depth = 0
    i = idx
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return idx, i + 1
        i += 1
    raise RuntimeError("unterminated sexp")


def _parent_of(text: str, name: str) -> str | None:
    s, e = _find_block(text, name)
    m = re.search(r'\(extends "([^"]+)"', text[s:e])
    return m.group(1) if m else None


def _children_of_sexp(text: str, start: int, end: int) -> list[tuple[str, int, int]]:
    """Return list of (top-level sub-sexp head name, start, end) immediately
    inside the sexp text[start:end] (i.e. depth-1 children). Head name is
    the first token after '('."""
    out = []
    i = start + 1  # skip opening '(' of outer sexp
    depth = 0
    # skip the opening head token (e.g. "symbol " "lib_id" etc.)
    while i < end:
        ch = text[i]
        if ch == "(":
            # start of a child
            child_start = i
            depth = 0
            while i < end:
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        child_end = i + 1
                        # extract head token
                        hm = re.match(r"\(\s*([A-Za-z_]+)", text[child_start:child_end])
                        if hm:
                            out.append((hm.group(1), child_start, child_end))
                        i = child_end
                        break
                i += 1
        else:
            i += 1
    return out


def extract_lib_symbol(lib_file: str, sym_name: str) -> str:
    """Return a self-contained (symbol "lib_file:sym_name" …) S-expression
    ready to paste into a (lib_symbols …) block, with any `(extends …)`
    chain fully flattened into the returned symbol."""
    path = STOCK_SYM_DIR / lib_file
    text = path.read_text()
    lib_prefix = lib_file.replace(".kicad_sym", "")

    # Walk extends chain root -> parent -> grandparent
    chain = [sym_name]
    while True:
        p = _parent_of(text, chain[-1])
        if p is None:
            break
        chain.append(p)
    # Parents in order [root(child), ..., topmost ancestor]

    # Start with the topmost ancestor as the base block.
    base_name = chain[-1]
    bs, be = _find_block(text, base_name)
    base = text[bs:be]
    # Rename its top-level head to "lib_prefix:sym_name"
    base = re.sub(
        rf'\(symbol "{re.escape(base_name)}"',
        f'(symbol "{lib_prefix}:{sym_name}"',
        base,
        count=1,
    )

    # Rename the sub-unit graphic blocks ("BaseName_0_1", "BaseName_1_1")
    # to "sym_name_0_1" WITHOUT lib prefix — the schematic cache format
    # expects bare sub-unit names (see existing Connector:TestPoint entry
    # which caches sub-units as "TestPoint_0_1", "TestPoint_1_1").
    base = re.sub(
        rf'\(symbol "{re.escape(base_name)}_(\d+)_(\d+)"',
        rf'(symbol "{sym_name}_\1_\2"',
        base,
    )

    # Now walk child blocks (newer generations) and merge in their
    # property overrides. We skip their `(extends "..")` clause. KiCad
    # cached lib_symbols for "extended" parts show the FULL resolved form
    # (no extends, all properties inlined), so we do the same.
    for child_name in reversed(chain[:-1]):
        cs, ce = _find_block(text, child_name)
        child = text[cs:ce]
        # Collect child's direct property overrides
        child_props = re.findall(
            r'\(property "([^"]+)" "([^"]*)"(?:[^()]|\([^()]*\))*?\)',
            child,
        )
        # Replace each corresponding property in `base` with child's value.
        for pname, pval in child_props:
            pname_re = re.escape(pname)
            old_pat = re.compile(
                rf'\(property "{pname_re}" "[^"]*"(\s*\([^()]*\)\s*\([^()]*\)\s*\([^()]*\)\s*)?\s*(\([^()]*(?:\([^()]*\)[^()]*)*\))?\s*\)',
                re.DOTALL,
            )
            # Build a small replacement property block.
            repl = f'(property "{pname}" "{pval}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
            if re.search(rf'\(property "{pname_re}" ', base):
                base = re.sub(
                    rf'\(property "{pname_re}" "[^"]*"\s*\(at[^\)]*\)\s*\(effects.*?\)\s*\)',
                    repl,
                    base,
                    count=1,
                    flags=re.DOTALL,
                )
            else:
                # append before the closing ')' of the symbol
                base = base[:-1] + " " + repl + ")"

    return base


# ---------------------------------------------------------------------------
# component definitions
# ---------------------------------------------------------------------------

# Pin positions in LIB space (Y-up). Schematic uses Y-down: abs_y = sy - py
# for symbols placed at angle 0 with no mirror.

PIN = {
    # Device:R — vertical, pin 1 on top
    "R":      {"1": (0,  3.81), "2": (0, -3.81)},
    # Device:C — vertical, pin 1 on top
    "C":      {"1": (0,  3.81), "2": (0, -3.81)},
    # Device:Crystal — horizontal, pin 1 left
    "Xtal":   {"1": (-3.81, 0), "2": (3.81, 0)},
    # Transistor_FET:{AO3401A, 2N7002} — shared TP0610T / Q_NMOS_GSD layout
    "FET":    {"1": (-5.08, 0), "2": (2.54, -5.08), "3": (2.54, 5.08)},
    # Jumper:SolderJumper_2_Open
    "JP":     {"1": (-3.81, 0), "2": (3.81, 0)},
    # Interface_UART:SC16IS740 (full 16-pin set)
    "SC16IS740": {
        "1":  (0,      17.78),    # VDD  (north)
        "9":  (0,     -17.78),    # VSS  (south)
        "14": (-12.7,  12.7),     # RESET
        "8":  (-12.7,  10.16),    # I2C/SPI select (tie HIGH for I2C)
        "2":  (-12.7,   5.08),    # A0
        "3":  (-12.7,   2.54),    # A1
        "4":  (-12.7,   0.00),    # SO (SPI-only, unused in I2C mode)
        "5":  (-12.7,  -2.54),    # SCL/SCLK
        "6":  (-12.7,  -5.08),    # SDA
        "15": (-12.7, -10.16),    # XTAL1
        "16": (-12.7, -12.70),    # XTAL2
        "13": ( 12.7,   5.08),    # RX
        "11": ( 12.7,   2.54),    # ~CTS
        "10": ( 12.7,   0.00),    # ~RTS
        "12": ( 12.7,  -2.54),    # TX
        "7":  ( 12.7,  -7.62),    # ~IRQ
    },
}


# Symbol instances to add — (ref, lib_id, value, footprint, (x, y), pin_family, pin_net_map)
# Coordinates in mm, placed in an under-used region of the A3 sheet
# (Y ~ 40-120, X ~ 250-390 — current schematic uses Y ~ 50-260 at X < 230).
INSTANCES = [
    # ----- Modem rail gate -----
    {"ref": "Q2",  "lib": "Transistor_FET:AO3401A",
     "value": "AO3401A", "fp": "Package_TO_SOT_SMD:SOT-23",
     "at": (259.08, 58.42), "fam": "FET",
     "nets": {"1": "Q_MODEM_G", "2": "VBAT_SYS", "3": "MODEM_VBAT_SW"},
     "note": PHASE7_MARKER},
    {"ref": "Q3",  "lib": "Transistor_FET:2N7002",
     "value": "2N7002", "fp": "Package_TO_SOT_SMD:SOT-23",
     "at": (279.40, 58.42), "fam": "FET",
     "nets": {"1": "MODEM_EN", "2": "GND", "3": "Q_MODEM_G"}},
    {"ref": "R16", "lib": "Device:R",
     "value": "100k", "fp": "Resistor_SMD:R_0805_2012Metric",
     "at": (251.46, 50.80), "fam": "R",
     "nets": {"1": "VBAT_SYS", "2": "Q_MODEM_G"}},

    # ----- UART pull-downs -----
    {"ref": "R17", "lib": "Device:R",
     "value": "100k", "fp": "Resistor_SMD:R_0805_2012Metric",
     "at": (299.72, 50.80), "fam": "R",
     "nets": {"1": "UART1_RX", "2": "GND"}},
    {"ref": "R18", "lib": "Device:R",
     "value": "100k", "fp": "Resistor_SMD:R_0805_2012Metric",
     "at": (309.88, 50.80), "fam": "R",
     "nets": {"1": "UART2_RX", "2": "GND"}},
    {"ref": "R19", "lib": "Device:R",
     "value": "100k", "fp": "Resistor_SMD:R_0805_2012Metric",
     "at": (320.04, 50.80), "fam": "R",
     "nets": {"1": "UART2_TX", "2": "GND"}},

    # ----- SC16IS740 I2C-UART bridge -----
    {"ref": "U6",  "lib": "Interface_UART:SC16IS740",
     "value": "SC16IS740", "fp": "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
     "at": (360.68, 91.44), "fam": "SC16IS740",
     "nets": {
         "1":  "3V3",        "9":  "GND",
         "14": "3V3",        # ~RESET tied high (keep bridge enabled)
         "8":  "3V3",        # I2C/~SPI select = I2C
         "2":  "GND",        "3":  "GND",   # A0/A1 both low -> I2C addr 0x90 / 0x91
         "4":  "U6_SO_NC",   # SPI SO pin unused in I2C mode
         "5":  "I2C_SCL",    "6":  "I2C_SDA",
         "15": "U6_XTAL1",   "16": "U6_XTAL2",
         "13": "U6_UART_RX", "12": "U6_UART_TX",
         "11": "GND",        # ~CTS tie low = always-allow
         "10": "U6_RTS_NC",  # ~RTS unused
         "7":  "U6_IRQ_NC",  # ~IRQ unused
     }},
    {"ref": "X1", "lib": "Device:Crystal",
     "value": "14.7456MHz", "fp": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
     "at": (388.62, 76.20), "fam": "Xtal",
     "nets": {"1": "U6_XTAL1", "2": "U6_XTAL2"}},
    {"ref": "C23", "lib": "Device:C",
     "value": "22pF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (388.62, 86.36), "fam": "C",
     "nets": {"1": "U6_XTAL1", "2": "GND"}},
    {"ref": "C24", "lib": "Device:C",
     "value": "22pF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (388.62, 66.04), "fam": "C",
     "nets": {"1": "U6_XTAL2", "2": "GND"}},
    {"ref": "C25", "lib": "Device:C",
     "value": "100nF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (345.44, 66.04), "fam": "C",
     "nets": {"1": "3V3", "2": "GND"}},
    {"ref": "C26", "lib": "Device:C",
     "value": "10uF", "fp": "Capacitor_SMD:C_0805_2012Metric",
     "at": (335.28, 66.04), "fam": "C",
     "nets": {"1": "3V3", "2": "GND"}},

    # ----- Solder jumpers -----
    {"ref": "JP1", "lib": "Jumper:SolderJumper_2_Open",
     "value": "JP_MODEM_RAIL", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "at": (259.08, 83.82), "fam": "JP",
     "nets": {"1": "VBAT_SYS", "2": "MODEM_VBAT_SW"}},
    {"ref": "JP2", "lib": "Jumper:SolderJumper_2_Open",
     "value": "JP_SIM_VCC", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "at": (279.40, 83.82), "fam": "JP",
     "nets": {"1": "SIM_VDD", "2": "SIM_VDD_HOLDER"}},
    {"ref": "JP3", "lib": "Jumper:SolderJumper_2_Open",
     "value": "JP_SAT_UART_TX", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "at": (299.72, 83.82), "fam": "JP",
     "nets": {"1": "U6_UART_TX", "2": "UART2_TX"}},
    {"ref": "JP4", "lib": "Jumper:SolderJumper_2_Open",
     "value": "JP_SAT_UART_RX", "fp": "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
     "at": (320.04, 83.82), "fam": "JP",
     "nets": {"1": "UART2_RX", "2": "U6_UART_RX"}},
]

# Library cache entries to ensure are present (lib_file, sym_name)
EXTRA_LIB_SYMBOLS = [
    ("Transistor_FET.kicad_sym", "AO3401A"),
    ("Transistor_FET.kicad_sym", "2N7002"),
    ("Interface_UART.kicad_sym", "SC16IS740"),
    ("Device.kicad_sym",         "Crystal"),
    ("Jumper.kicad_sym",         "SolderJumper_2_Open"),
]


# Net updates to existing schematic (net -> renamed) so our new hardware
# actually cuts into the existing circuit.
NET_RENAMES = {
    # The old MODEM_VBAT net ties VBAT_SYS through a single (unused) L2
    # inductor that is DNP by default. We rename it to MODEM_VBAT_SW so
    # the SIM7080G and Swarm's modem-rail pins all come off the new
    # switch drain. JP1 (JP_MODEM_RAIL) gives the Cell Master assembler
    # a solder-blob path to bypass the switch if they don't want Q2.
    "MODEM_VBAT": "MODEM_VBAT_SW",
}

# Additional label endpoints that land on existing module pins.
# MCP23017 U4 schematic position: (355.6, 254.0) angle 0 no mirror.
# Library pin 1 "GPB0" is at (17.78, 20.32) in MCP23017_SO symbol; with
# our placement that maps to abs (373.38, 233.68). Pin 1 currently has
# a no_connect flag (GPB0 is unused in Phase 2). Phase 7 removes that
# NC flag and drops a MODEM_EN label at that position.
EXTRA_LABEL_ENDPOINTS: list[tuple[str, float, float]] = [
    ("MODEM_EN", 373.38, 233.68),
]

# no_connect flags to REMOVE (at these absolute positions). Required
# because MODEM_EN now lands on MCP23017 pin 1 which was previously
# strapped as NC in Phase 2.
REMOVE_NO_CONNECT_AT: list[tuple[float, float]] = [
    (373.38, 233.68),
]

# One existing SIM_VDD label is near the Nano-SIM holder Card1 (at 38.10,
# 248.92). Phase 7 renames that ONE label to SIM_VDD_HOLDER so the new
# JP2 jumper is in series between the SIM7080G and the Nano-SIM holder.
RENAME_LABEL_AT: list[tuple[float, float, str, str]] = [
    (38.10, 248.92, "SIM_VDD", "SIM_VDD_HOLDER"),
]


# ---------------------------------------------------------------------------
# schematic rewrite
# ---------------------------------------------------------------------------

def load_sch() -> str:
    return SCH.read_text()


def save_sch(text: str) -> None:
    SCH.write_text(text)


def find_lib_symbols_bounds(text: str) -> tuple[int, int]:
    start = text.find("(lib_symbols")
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise RuntimeError("unterminated lib_symbols")


def find_sheet_instances_start(text: str) -> int:
    idx = text.rfind("(sheet_instances")
    if idx < 0:
        raise RuntimeError("no sheet_instances block")
    return idx


def lib_symbol_cached(text: str, qualified_name: str) -> bool:
    lib_start, lib_end = find_lib_symbols_bounds(text)
    return f'(symbol "{qualified_name}"' in text[lib_start:lib_end]


def cache_extra_symbols(text: str) -> str:
    lib_start, lib_end = find_lib_symbols_bounds(text)
    lib_block = text[lib_start:lib_end]

    additions: list[str] = []
    for lib_file, name in EXTRA_LIB_SYMBOLS:
        qualified = f'{lib_file.replace(".kicad_sym", "")}:{name}'
        if qualified in lib_block or any(qualified in a for a in additions):
            continue
        blob = extract_lib_symbol(lib_file, name)
        # also pull parents (already included by extract_lib_symbol)
        # sanitize: convert parent refs from bare (extends "Name") to
        # keep bare name — KiCad's cache uses bare name for the parent
        # of an extended symbol so leave that alone.
        additions.append(blob)

    if not additions:
        return text

    # Insert just before the closing ')' of (lib_symbols ...).
    # lib_end is the exclusive end, the ')' is at lib_end-1.
    insert_at = lib_end - 1
    new_text = (
        text[:insert_at]
        + "\n"
        + "\n".join(additions)
        + "\n"
        + text[insert_at:]
    )
    return new_text


def absolute_pin(inst, pin_num) -> tuple[float, float]:
    sx, sy = inst["at"]
    fam_map = PIN[inst["fam"]]
    px, py = fam_map[pin_num]
    # symbol placed at angle 0, no mirror
    return (sx + px, sy - py)


def emit_instance(inst) -> str:
    ref = inst["ref"]
    lib = inst["lib"]
    val = inst["value"]
    fp  = inst["fp"]
    sx, sy = inst["at"]
    u = newuuid()
    # Properties offset relative to origin
    ref_offset = 2.54
    val_offset = -2.54

    out = (
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
    return out


def emit_label(net: str, x: float, y: float) -> str:
    u = newuuid()
    return (
        f'(label "{net}" (at {x:.2f} {y:.2f} 0)\n'
        f'\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
        f'\t\t(uuid "{u}")\n'
        f'\t)'
    )


def emit_no_connect(x: float, y: float) -> str:
    u = newuuid()
    return (
        f'(no_connect (at {x:.2f} {y:.2f})\n'
        f'\t\t(uuid "{u}")\n'
        f'\t)'
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def remove_nc_at(text: str, positions: list[tuple[float, float]]) -> tuple[str, int]:
    removed = 0
    for px, py in positions:
        # match (no_connect (at px py)\n\t\t(uuid "…")\n\t) — trailing
        # whitespace variations handled
        pat = re.compile(
            rf'\(no_connect \(at {re.escape(f"{px:.2f}")} {re.escape(f"{py:.2f}")}\)\s*'
            rf'\(uuid "[^"]+"\)\s*\)\s*',
            re.MULTILINE,
        )
        new_text, n = pat.subn("", text)
        if n > 0:
            text = new_text
            removed += n
    return text, removed


def rename_label_at(text: str, renames: list[tuple[float, float, str, str]]) -> int:
    n = 0
    for x, y, old, new in renames:
        pat = re.compile(
            rf'(\(label )"{re.escape(old)}"(\s*\(at {re.escape(f"{x:.2f}")} {re.escape(f"{y:.2f}")} )',
        )
        # Note: we need to capture and rewrite in-place; use sub with backref
        m = pat.search(text)
        if m:
            text_before = text[:m.start()]
            text_after = text[m.end():]
            # rebuild the prefix with new name
            prefix = m.group(1) + f'"{new}"' + m.group(2)
            text = text_before + prefix + text_after
            n += 1
        # also allow the label to carry a mirror ordering
    return n, text


def main() -> int:
    text = load_sch()

    if PHASE7_MARKER in text:
        print("Phase 7 marker already present — nothing to do.")
        return 0

    # 0) Selective SIM_VDD label rename (one specific label, not all).
    count, text = rename_label_at(text, RENAME_LABEL_AT)
    print(f"Renamed {count} specific labels (SIM_VDD -> SIM_VDD_HOLDER near Card1)")

    # 1) Bulk net rename
    if "MODEM_VBAT" in NET_RENAMES:
        before = text.count('(label "MODEM_VBAT"')
        for old, new in NET_RENAMES.items():
            text = text.replace(f'(label "{old}"', f'(label "{new}"')
        after  = text.count('(label "MODEM_VBAT_SW"')
        print(f"Renamed MODEM_VBAT -> MODEM_VBAT_SW on {before} labels (now {after})")

    # 2) Remove obsolete no_connect flags where we now need a real label
    text, removed = remove_nc_at(text, REMOVE_NO_CONNECT_AT)
    print(f"Removed {removed} no_connect flags to free pins for Phase-7 nets")

    # 3) Cache extra library symbols
    text = cache_extra_symbols(text)

    # 4) Build instance + label blobs
    inst_blobs: list[str] = []
    label_blobs: list[str] = []
    nc_blobs: list[str] = []

    for inst in INSTANCES:
        inst_blobs.append(emit_instance(inst))
        for pin_num, net in inst["nets"].items():
            px, py = absolute_pin(inst, pin_num)
            label_blobs.append(emit_label(net, px, py))

    # Extra label endpoints that land on existing module pins
    for net, x, y in EXTRA_LABEL_ENDPOINTS:
        label_blobs.append(emit_label(net, x, y))

    # For SC16IS740 "unused" pins, drop no_connect flags at those pin
    # endpoints instead of labels (labels alone would hang dangling).
    u6 = next(i for i in INSTANCES if i["ref"] == "U6")
    for pin_num, net in u6["nets"].items():
        if net.endswith("_NC"):
            px, py = absolute_pin(u6, pin_num)
            nc_blobs.append(emit_no_connect(px, py))
            label_blobs = [
                L for L in label_blobs
                if not L.startswith(f'(label "{net}" (at {px:.2f} {py:.2f}')
            ]

    # 5) Splice into the schematic just before (sheet_instances ...)
    splice_at = find_sheet_instances_start(text)
    additions = "\n".join(inst_blobs + label_blobs + nc_blobs) + "\n"
    text = text[:splice_at] + additions + text[splice_at:]

    save_sch(text)
    print(f"Phase 7 applied:")
    print(f"  {len(inst_blobs)} new symbol instances")
    print(f"  {len(label_blobs)} new net labels (incl {len(EXTRA_LABEL_ENDPOINTS)} extra endpoints)")
    print(f"  {len(nc_blobs)} no-connect flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
