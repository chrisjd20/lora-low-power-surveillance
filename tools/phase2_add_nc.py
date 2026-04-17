#!/usr/bin/env python3
"""
Add `(no_connect (at X Y))` for every pin that ERC flags as
"pin_not_connected". These are module pins (SIM7080G / Swarm M138 /
MCP23017 / unused XIAO GPIOs / SRV05-4 IO channels) that were left
unwired in the Flux EDIF and are intentionally not used in this build.

Runs AFTER phase2_patch_schematic, re-runs ERC to pull the current
unconnected-pin list, then inserts the NCs directly into the .kicad_sch
file. Idempotent.
"""
from __future__ import annotations
import pathlib
import re
import subprocess
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
RPT  = ROOT / "hardware/warden-apex-master/erc-report.txt"


def main() -> int:
    subprocess.run(
        ["kicad-cli", "sch", "erc",
         "--format=report", "--units=mm", "--severity-all",
         str(SCH), "-o", str(RPT)],
        check=True, stdout=subprocess.PIPE,
    )
    text = RPT.read_text()
    coords: list[tuple[float, float, str, str]] = []
    for m in re.finditer(
        r'\[pin_not_connected\]: Pin not connected\s*;\s*error\s*@\(([\d.-]+) mm, ([\d.-]+) mm\): Symbol (\S+) Pin (\S+)',
        text,
    ):
        coords.append((float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)))
    print(f"unconnected pins: {len(coords)}")

    sch = SCH.read_text()
    # Skip positions that already have a no_connect (idempotency)
    existing = set(
        (round(float(m.group(1)), 3), round(float(m.group(2)), 3))
        for m in re.finditer(r'\(no_connect \(at ([\d.-]+) ([\d.-]+)\)', sch)
    )
    new_chunks: list[str] = []
    added = 0
    for x, y, ref, pin in coords:
        key = (round(x, 3), round(y, 3))
        if key in existing:
            continue
        existing.add(key)
        uid = str(uuid.uuid4())
        new_chunks.append(
            f'\t(no_connect (at {x:.2f} {y:.2f})\n\t\t(uuid "{uid}")\n\t)\n'
        )
        added += 1

    insert_at = sch.rfind("(sheet_instances")
    if insert_at < 0:
        insert_at = sch.rfind(")")
    new_sch = sch[:insert_at] + "".join(new_chunks) + sch[insert_at:]
    SCH.write_text(new_sch)
    print(f"inserted {added} no_connect flags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
