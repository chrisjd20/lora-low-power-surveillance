#!/usr/bin/env python3
"""
Generate the add_schematic_component batch for Phase 2.

Places:
    - all 50 BOM components
    - added parts L1 (charger inductor) and RSNS (sense resistor)
    - 5 power flags (GND, 3V3, VBAT_SYS, SOLAR_IN, MODEM_VBAT)

Component positions use the ZONES dict (zone center coordinates) from
phase2_pin_map, scattered inside each zone on a 10 mm grid using the
Flux pick-and-place coords as a *relative ordering* hint so parts cluster
the same way in the schematic as they will on the board.

Output: tools/_phase2_batch_place.json
"""
from __future__ import annotations
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from phase2_pin_map import (
    SYMBOL_CHOICE,
    ADDED_PARTS,
    POWER_FLAG_NETS,
    REF_ZONE,
    ZONES,
)

NETLIST = json.loads((ROOT / "hardware/warden-apex-master/flux-netlist.json").read_text())
BOM     = json.loads((ROOT / "hardware/warden-apex-master/flux-bom.json").read_text())
SCHEMA  = str(ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch")

# Refdes → BOM row for value / footprint / MPN overrides
BOM_BY_REF = {r["ref"]: r for r in BOM["components"]}

# Refs we intentionally skip (unpopulated schematic placeholders not in BOM)
SKIP_REFS = {
    "C6", "C7", "C8", "C9", "C10", "C11", "C12",
    "R6", "R7", "R8", "R9",
    "TP6", "TP7", "TP8", "TP9", "TP10", "TP11", "TP12",
}


def position_in_zone(zone_name: str, index: int):
    """Lay out components in a 5-per-row grid inside the zone. Positions
    are 25.4 mm spaced to give every symbol room for its pin labels and
    wire stubs without overlapping its neighbour. All multiples of
    2.54 mm to keep KiCad's connection grid happy."""
    cx, cy = ZONES[zone_name]
    cols = 5
    row = index // cols
    col = index % cols
    x = cx + col * 25.4
    y = cy + row * 25.4
    return {"x": x, "y": y}


def main() -> int:
    calls = []

    # -- Group components by zone so we can lay them out neatly ---------
    by_zone: dict[str, list[str]] = {}
    for comp in NETLIST["components"]:
        ref = comp["ref"]
        if ref in SKIP_REFS:
            continue
        zone = REF_ZONE.get(ref)
        if zone is None:
            # Not mapped explicitly — default to io zone
            zone = "io"
        by_zone.setdefault(zone, []).append(ref)

    # Also add L1 / RSNS to power_in zone
    by_zone.setdefault("power_in", []).extend(["L1", "RSNS"])

    for zone, refs in by_zone.items():
        for i, ref in enumerate(sorted(refs)):
            if ref in [p["ref"] for p in ADDED_PARTS]:
                added = next(p for p in ADDED_PARTS if p["ref"] == ref)
                sym = f'{added["library"]}:{added["symbol"]}'
                footprint = added["footprint"]
                value = added["value"]
            else:
                comp = next((c for c in NETLIST["components"] if c["ref"] == ref), None)
                if comp is None:
                    continue
                choice = SYMBOL_CHOICE.get(comp["cell"])
                if choice is None:
                    print(f"!! no SYMBOL_CHOICE for cell {comp['cell']!r} (ref {ref})", file=sys.stderr)
                    continue
                lib, sym_name, fp_override = choice
                sym = f"{lib}:{sym_name}"
                footprint = fp_override
                bom = BOM_BY_REF.get(ref, {})
                value = bom.get("value") or bom.get("mpn") or ref
            pos = position_in_zone(zone, i)
            args = {
                "schematicPath": SCHEMA,
                "symbol": sym,
                "reference": ref,
                "value": value,
                "position": pos,
            }
            if footprint:
                args["footprint"] = footprint
            calls.append({
                "tool": "add_schematic_component",
                "args": args,
                "label": f"place {ref} ({sym})",
            })

    # -- Power flags ----------------------------------------------------
    # Space them out enough that their wire stubs don't merge onto one net.
    flag_x0, flag_y0 = 25.4, 25.4
    for i, net in enumerate(POWER_FLAG_NETS):
        calls.append({
            "tool": "add_schematic_component",
            "args": {
                "schematicPath": SCHEMA,
                "symbol": "power:PWR_FLAG",
                "reference": f"#FLG{i+1}",
                "value": net,
                "position": {"x": flag_x0 + i * 25.4, "y": flag_y0},
            },
            "label": f"pwr_flag {net}",
        })

    out = HERE / "_phase2_batch_place.json"
    out.write_text(json.dumps(calls, indent=2))
    print(f"wrote {out.relative_to(ROOT)}  ({len(calls)} calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
