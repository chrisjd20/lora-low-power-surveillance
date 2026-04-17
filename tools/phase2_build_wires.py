#!/usr/bin/env python3
"""
Generate the connect_to_net batch for Phase 2.

Produces one MCP call per (ref, pin, net) triple, with:
    * Flux pin names translated to KiCad pin numbers (see phase2_pin_map)
    * Flux "Net 1..5" renamed to CHG_GATE_LO/HI/BST/REGN/PH
    * Added nodes: L1 bridging CHG_PH↔VBAT_SYS, RSNS bridging
      VBAT_SYS↔CHG_SENSE_NEG, LORA_DIO1→U1.MTMS
    * Symbols with multiple pins of the same semantic (XIAO dual GND,
      Swarm M138 7× SHIELD, SMN-305 4× EP) get a connection per pin
    * 5 PWR_FLAG markers wired to their respective power nets

Output: tools/_phase2_batch_wires.json
"""
from __future__ import annotations
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from phase2_pin_map import (
    SYMBOL_CHOICE, PIN_MAP, resolve_pin,
    NET_RENAME, ADDED_NET_NODES, POWER_FLAG_NETS,
)

NETLIST = json.loads((ROOT / "hardware/warden-apex-master/flux-netlist.json").read_text())
SCHEMA  = str(ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch")

# Refs we don't place and therefore don't wire
SKIP_REFS = {
    "C6", "C7", "C8", "C9", "C10", "C11", "C12",
    "R6", "R7", "R8", "R9",
    "TP6", "TP7", "TP8", "TP9", "TP10", "TP11", "TP12",
}

# Symbols that have identical-name pin groups we need to fan out.
# When the flux netlist lists "<ref>.<name>" once, we still need to
# connect every physical pin to that net.
FANOUT = {
    # (ref, flux_pin) -> list of kicad pin numbers to emit
    ("U1",   "GND"):    ["13", "24"],           # XIAO two GND pads (GND, GND2)
    ("U3",   "SHIELD"): ["14", "16", "17", "19", "22", "34", "43"],  # Swarm M138 SHIELD pins
    ("Card1", "EP"):    ["7", "8", "9", "10"],  # SMN-305 EP shield tabs
}


def symbol_for(ref: str) -> str | None:
    for comp in NETLIST["components"]:
        if comp["ref"] == ref:
            choice = SYMBOL_CHOICE.get(comp["cell"])
            if choice:
                return choice[1]
    return None


def resolve_nodes(ref: str, flux_pin: str) -> list[str]:
    """Return list of KiCad pin *numbers* to connect for this (ref, pin)."""
    fan = FANOUT.get((ref, flux_pin))
    if fan is not None:
        return fan
    sym = symbol_for(ref)
    if sym is None:
        return []
    return [resolve_pin(sym, flux_pin)]


def emit_connect(ref: str, pin: str, net: str, label: str) -> dict:
    return {
        "tool": "connect_to_net",
        "args": {
            "schematicPath": SCHEMA,
            "componentRef": ref,
            "pinName": pin,
            "netName": net,
        },
        "label": label,
    }


def main() -> int:
    calls: list[dict] = []

    # Track which added-net-node triples we've already emitted so we don't
    # double up when a net is named both in the EDIF and in ADDED_NET_NODES.
    already: set[tuple[str, str, str]] = set()

    # ----- EDIF-derived nets -------------------------------------------
    for net in NETLIST["nets"]:
        name = NET_RENAME.get(net["name"], net["name"])
        for ref, flux_pin in net["nodes"]:
            if ref in SKIP_REFS:
                continue
            pins = resolve_nodes(ref, flux_pin)
            if not pins:
                print(f"!! unresolved pin {ref}.{flux_pin}", file=sys.stderr)
                continue
            for p in pins:
                key = (ref, p, name)
                if key in already:
                    continue
                already.add(key)
                calls.append(emit_connect(ref, p, name,
                                          f"{name}  {ref}.{flux_pin}→pin{p}"))

    # ----- Added nodes (L1, RSNS, LORA_DIO1 fix) ----------------------
    for net, ref, pin in ADDED_NET_NODES:
        key = (ref, pin, net)
        if key in already:
            continue
        already.add(key)
        calls.append(emit_connect(ref, pin, net, f"{net}  {ref}.pin{pin} (added)"))

    # ----- Power-flag wiring ------------------------------------------
    for i, net in enumerate(POWER_FLAG_NETS):
        ref = f"#FLG{i+1}"
        calls.append(emit_connect(ref, "1", net, f"pwr_flag {ref}→{net}"))

    out = HERE / "_phase2_batch_wires.json"
    out.write_text(json.dumps(calls, indent=2))
    print(f"wrote {out.relative_to(ROOT)}  ({len(calls)} connections)")

    # Stats
    by_net: dict[str, int] = {}
    for c in calls:
        by_net[c["args"]["netName"]] = by_net.get(c["args"]["netName"], 0) + 1
    print(f"unique nets: {len(by_net)}")
    for n in sorted(by_net, key=lambda k: -by_net[k])[:10]:
        print(f"  {n:20s} {by_net[n]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
