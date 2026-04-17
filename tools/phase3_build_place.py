#!/usr/bin/env python3
"""
Generate the place_component batch for Phase 3 PCB layout.

Reads the schematic to get refdes + footprint per component, maps each
ref to a PCB zone via phase2_pin_map.REF_ZONE, and emits place_component
calls targeting approximate positions inside each zone.
"""
from __future__ import annotations
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from phase2_pin_map import REF_ZONE

SCH = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"


# Zones on the 100x100 mm board.
# Origin (0, 0) is top-left corner of the PCB; +X right, +Y down.
# Board outline is 0..100 mm square with 4 mounting holes ⌀3.2 at corners.
PCB_ZONES = {
    # (center_x, center_y) for each functional block
    "power_in":   (20, 75),  # SW charger quadrant
    "vbat":       (30, 55),  # south-central
    "reg33":      (50, 55),  # centre bulk-power rail
    "mcu":        (30, 30),  # NW XIAO
    "lora":       (20, 45),  # west LoRa
    "audio":      (75, 30),  # NE audio output
    "cell":       (75, 65),  # E cellular
    "sat":        (85, 40),  # NE satellite
    "io":         (55, 80),  # south GPIO expander
    "tps":        (10, 90),  # test points strip (south edge)
}

# Pin numbers / sizes depend on component type; start with a simple
# grid layout within each zone.
STEP = 5.08  # mm, 200 mil (fits 0805 + pad clearance)


def inzone(zone: str, index: int) -> tuple[float, float]:
    cx, cy = PCB_ZONES[zone]
    cols = 4
    row = index // cols
    col = index %  cols
    return (cx - (cols-1) * STEP / 2 + col * STEP,
            cy + (row - 1) * STEP)


def main() -> int:
    s = SCH.read_text()
    # Parse each placed symbol (skip lib_symbols embedded defs)
    # keep placements whose lib_id contains ':' and ref NOT starting with '#'
    lib_end = 0
    idx = s.find("(lib_symbols")
    if idx >= 0:
        depth = 0
        for i in range(idx, len(s)):
            c = s[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    lib_end = i
                    break
    body = s[:idx] + s[lib_end+1:]
    comps = []
    for m in re.finditer(
        r'\(symbol \(lib_id "([^"]+)"\).*?\(property "Reference" "([^"]+)".*?\(property "Value" "([^"]+)".*?\(property "Footprint" "([^"]+)"',
        body, re.S,
    ):
        lib_id, ref, value, footprint = m.group(1), m.group(2), m.group(3), m.group(4)
        if ref.startswith("#"):
            continue  # skip PWR_FLAG and friends
        if footprint.strip() == "":
            continue  # skip unplaced
        comps.append((ref, value, footprint))
    print(f"components to place: {len(comps)}")

    # Group by zone, then index within zone
    by_zone: dict[str, list[tuple[str, str, str]]] = {}
    for c in comps:
        z = REF_ZONE.get(c[0], "io")
        by_zone.setdefault(z, []).append(c)

    calls = []
    for zone, refs in by_zone.items():
        refs.sort(key=lambda c: c[0])
        for i, (ref, value, fp) in enumerate(refs):
            x, y = inzone(zone, i)
            calls.append({
                "tool": "place_component",
                "args": {
                    "componentId": fp,
                    "footprint": fp,
                    "reference": ref,
                    "value": value,
                    "position": {"x": round(x, 3), "y": round(y, 3), "unit": "mm"},
                    "boardPath": str(PCB),
                },
                "label": f"place {ref} ({fp}) zone={zone} @({x:.1f},{y:.1f})",
            })

    out = HERE / "_phase3_batch_place.json"
    out.write_text(json.dumps(calls, indent=2))
    print(f"wrote {out.relative_to(ROOT)}  ({len(calls)} calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
