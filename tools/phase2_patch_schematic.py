#!/usr/bin/env python3
"""
Post-processor that fixes the schematic after Phase 2 wire+label
generation. The KiCAD MCP server's `connect_to_net` / `add_schematic_net_label`
tools compute pin absolute positions WITHOUT applying the Y-axis flip that
KiCad itself applies when rendering (symbol files use Y-up, schematics
use Y-down). That causes 2 × pin_y offset on every wire stub and label —
ERC reports them as "Pin not connected" / "Label not connected".

This script:
    1. Strips every wire / label / junction from the schematic.
    2. Parses every symbol library referenced in lib_symbols to get the
       authoritative pin positions.
    3. Walks the cached netlist and emits a single `(label "NET" (at X Y 0))`
       at each CORRECT (pin) endpoint. KiCad treats a label placed on a
       pin endpoint as a direct electrical connection — no wire stub
       required.
    4. Writes the patched .kicad_sch back.

Run AFTER phase2_build_placement + phase2_build_wires have populated the
schematic. Idempotent; can be re-run after further placement edits.
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
import uuid

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from phase2_pin_map import (
    SYMBOL_CHOICE, NET_RENAME, ADDED_NET_NODES, POWER_FLAG_NETS,
    resolve_pin,
)

NETLIST  = json.loads((ROOT / "hardware/warden-apex-master/flux-netlist.json").read_text())
SCH      = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"

# Refs we never placed — so we don't emit labels for them either
SKIP_REFS = {
    "C6","C7","C8","C9","C10","C11","C12","R6","R7","R8","R9",
    "TP6","TP7","TP8","TP9","TP10","TP11","TP12",
}

# FANOUT: same as wire builder (multi-pin groups under one Flux name)
FANOUT = {
    ("U1",    "GND"):    ["13", "24"],
    ("U3",    "SHIELD"): ["14", "16", "17", "19", "22", "34", "43"],
    ("Card1", "EP"):     ["7", "8", "9", "10"],
}


# ---------------------------------------------------------------------------
# Parse the lib_symbols block to learn pin definitions
# ---------------------------------------------------------------------------
def extract_balanced(text: str, start: int) -> tuple[int, int]:
    """Given text[start] == '(', return (start, end_inclusive_of_matching)."""
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return start, i
    raise ValueError("unterminated s-expr")


def parse_lib_symbols(sch_text: str) -> dict[str, dict[str, tuple[float, float, float]]]:
    """Returns {lib_id: {pin_identifier: (x, y, angle)}}.
    pin_identifier includes both pin NUMBER and pin NAME so callers can
    look up by either.
    """
    idx = sch_text.find("(lib_symbols")
    if idx < 0:
        return {}
    _, end = extract_balanced(sch_text, idx)
    block = sch_text[idx:end+1]

    # Top-level (symbol "Library:Name" ...) entries. We need the TOP-level
    # symbols (with colon in the name); the nested "_0_1" / "_1_1" are
    # unit-sub-symbols that hold the actual pin geometry.
    lib_pins: dict[str, dict[str, tuple[float, float, float]]] = {}
    pos = 0
    while True:
        pos = block.find('(symbol "', pos)
        if pos < 0:
            break
        _, sym_end = extract_balanced(block, pos)
        header = block[pos:pos+200]
        m = re.match(r'\(symbol "([^"]+)"', header)
        if not m:
            pos = sym_end + 1
            continue
        name = m.group(1)
        if ":" not in name:
            pos = sym_end + 1  # sub-symbol, skip
            continue
        sym_body = block[pos:sym_end+1]
        # Iterate nested (symbol "X_Y_Z" ...) children that contain pins
        inner_pos = sym_body.find('(symbol "', 1)
        pins: dict[str, tuple[float, float, float]] = {}
        while inner_pos >= 0:
            _, inner_end = extract_balanced(sym_body, inner_pos)
            inner = sym_body[inner_pos:inner_end+1]
            # Find each (pin ...) block, extract at + name + number
            for pm in re.finditer(r'\(pin\s+\w+\s+\w+\s+\(at ([\d.-]+) ([\d.-]+) ([\d.-]+)\)', inner):
                # get the enclosing pin block for number + name
                pin_start = pm.start()
                _, pin_end = extract_balanced(inner, pin_start)
                pin_body = inner[pin_start:pin_end+1]
                x, y, ang = float(pm.group(1)), float(pm.group(2)), float(pm.group(3))
                num_m = re.search(r'\(number "([^"]+)"', pin_body)
                nam_m = re.search(r'\(name "([^"]+)"', pin_body)
                if num_m:
                    pins[num_m.group(1)] = (x, y, ang)
                if nam_m:
                    # Store by name too, so lookups like pin_pos(ref, "MTMS") work.
                    # Only first occurrence wins for duplicate names (BQ24650 has
                    # two 'GND's — the numeric lookup resolves those distinctly).
                    pins.setdefault(nam_m.group(1), (x, y, ang))
            inner_pos = sym_body.find('(symbol "', inner_end + 1)
        lib_pins[name] = pins
        pos = sym_end + 1
    return lib_pins


# ---------------------------------------------------------------------------
# Parse placed component instances
# ---------------------------------------------------------------------------
def parse_placements(sch_text: str) -> dict[str, tuple[str, float, float, float]]:
    """Returns {refdes: (lib_id, x, y, angle)}."""
    result = {}
    # Iterate top-level (symbol (lib_id "...") ...) sections
    pos = 0
    # Skip the lib_symbols block entirely
    lib_idx = sch_text.find("(lib_symbols")
    if lib_idx >= 0:
        _, lib_end = extract_balanced(sch_text, lib_idx)
        search_from = lib_end + 1
    else:
        search_from = 0
    pos = search_from
    while True:
        pos = sch_text.find("(symbol (lib_id ", pos)
        if pos < 0:
            break
        _, sym_end = extract_balanced(sch_text, pos)
        body = sch_text[pos:sym_end+1]
        m = re.search(r'\(lib_id "([^"]+)"\)\s*\(at ([\d.-]+) ([\d.-]+) ([\d.-]+)\)', body)
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', body)
        if m and ref_m:
            result[ref_m.group(1)] = (m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)))
        pos = sym_end + 1
    return result


def pin_abs(placement: tuple[str, float, float, float],
            pin_def: tuple[float, float, float]) -> tuple[float, float]:
    """Compute absolute pin endpoint, applying KiCad Y-flip convention."""
    _, cx, cy, cangle = placement
    px, py, _pa = pin_def
    # Y is flipped: schematic_y = cy - py
    # X is preserved: schematic_x = cx + px
    # (we assume component rotation == 0 for Phase 2 — placements are upright)
    if abs(cangle) > 0.1:
        # Rotation not supported (not used here)
        raise NotImplementedError("component rotation not supported")
    return (cx + px, cy - py)


# ---------------------------------------------------------------------------
# Rewrite the schematic
# ---------------------------------------------------------------------------
def main() -> int:
    text = SCH.read_text()
    lib_pins = parse_lib_symbols(text)
    placements = parse_placements(text)
    print(f"lib_symbols with pins: {len(lib_pins)}")
    print(f"placed components:     {len(placements)}")

    # Strip every wire / label / junction and any stray no_connect
    # We preserve the lib_symbols block and placed symbol blocks.
    def strip_block(text: str, opener: str) -> tuple[str, int]:
        count = 0
        out = []
        i = 0
        while i < len(text):
            if text.startswith(opener, i):
                _, end = extract_balanced(text, i)
                count += 1
                i = end + 1
                # consume trailing whitespace/newline
                while i < len(text) and text[i] in " \t\n":
                    i += 1
                continue
            out.append(text[i])
            i += 1
        return "".join(out), count

    for opener in ("(wire ", "(label ", "(global_label ", "(junction ", "(no_connect "):
        text, n = strip_block(text, opener)
        print(f"  stripped {n}× '{opener.strip()}'")

    # Build (ref, pin) -> absolute position map, using CORRECT Y-flip
    def pin_pos(ref: str, pin_num: str) -> tuple[float, float] | None:
        p = placements.get(ref)
        if not p:
            return None
        lib_id = p[0]
        pins = lib_pins.get(lib_id, {})
        pd = pins.get(pin_num)
        if not pd:
            return None
        return pin_abs(p, pd)

    # Resolve symbol name from lib_id (e.g. "Battery_Management:BQ24650" -> "BQ24650")
    def sym_of(ref: str) -> str | None:
        p = placements.get(ref)
        if not p:
            return None
        return p[0].split(":", 1)[-1]

    labels_to_add: list[tuple[str, float, float]] = []

    # Track L3 pin assignments across multiple nets. Flux netlist records
    # two "L3.~" entries (both SW_A and SW_B) with no disambiguation.
    # The first "~" we see goes to pin 1, the second to pin 2.
    l3_used_pins: set[str] = set()

    def ensure_pin(ref: str, flux_pin: str, net: str):
        # Use fanout if applicable
        key = (ref, flux_pin)
        if key in FANOUT:
            nums = FANOUT[key]
        elif ref == "L3" and flux_pin == "~":
            # disambiguate L3's two "~" pins: first → 1, second → 2
            if "1" not in l3_used_pins:
                nums = ["1"]; l3_used_pins.add("1")
            else:
                nums = ["2"]; l3_used_pins.add("2")
        else:
            sym = sym_of(ref)
            if sym is None:
                print(f"!! no placement for {ref}", file=sys.stderr)
                return
            num = resolve_pin(sym, flux_pin)
            nums = [num]
        for n in nums:
            pos = pin_pos(ref, n)
            if pos is None:
                print(f"!! cannot resolve {ref}.{flux_pin} (pin {n})", file=sys.stderr)
                continue
            labels_to_add.append((net, pos[0], pos[1]))

    for net in NETLIST["nets"]:
        name = NET_RENAME.get(net["name"], net["name"])
        for ref, flux_pin in net["nodes"]:
            if ref in SKIP_REFS:
                continue
            ensure_pin(ref, flux_pin, name)

    # Added nodes (L1 / RSNS / LORA_DIO1 fix)
    for net, ref, pin in ADDED_NET_NODES:
        p = pin_pos(ref, pin)
        if p is None:
            print(f"!! cannot resolve added {ref}.{pin}", file=sys.stderr)
            continue
        labels_to_add.append((net, p[0], p[1]))

    # Power flags: #FLG1 GND, #FLG2 3V3, etc.
    for i, n in enumerate(POWER_FLAG_NETS):
        ref = f"#FLG{i+1}"
        p = pin_pos(ref, "1")
        if p is None:
            print(f"!! no placement for {ref}", file=sys.stderr)
            continue
        labels_to_add.append((n, p[0], p[1]))

    # Deduplicate
    seen = set()
    uniq: list[tuple[str, float, float]] = []
    for net, x, y in labels_to_add:
        k = (net, round(x, 3), round(y, 3))
        if k in seen:
            continue
        seen.add(k)
        uniq.append((net, x, y))

    # Emit (label ...) elements into the schematic, before the closing ')' of kicad_sch
    # Find sheet_instances and insert labels just before it (KiCad is tolerant of order)
    insert_at = text.rfind("(sheet_instances")
    if insert_at < 0:
        insert_at = text.rfind(")")
    chunks: list[str] = []
    for net, x, y in uniq:
        uid = str(uuid.uuid4())
        chunks.append(
            f'\t(label "{net}" (at {x:.2f} {y:.2f} 0)\n'
            f'\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n'
            f'\t\t(uuid "{uid}")\n'
            f'\t)\n'
        )
    new_text = text[:insert_at] + "".join(chunks) + text[insert_at:]
    SCH.write_text(new_text)
    print(f"emitted {len(uniq)} unique labels; schematic now {len(new_text)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
