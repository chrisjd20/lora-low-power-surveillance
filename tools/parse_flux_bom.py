#!/usr/bin/env python3
"""
Flatten Flux's rich BOM CSV into per-reference-designator records so the
schematic/PCB build phase can look up exact MPN, LCSC part #, value,
footprint, role and role detail for every component.

Output:  hardware/warden-apex-master/flux-bom.json
"""
from __future__ import annotations
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC  = ROOT / "flux-archive" / "seed" / "BOM" / "chrisjd20-warden-apex-master-BOM-Vd9d779aa-Flux.csv"
PNP  = ROOT / "flux-archive" / "seed" / "pick_and_place.csv"
OUT  = ROOT / "hardware" / "warden-apex-master" / "flux-bom.json"


def clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    return s or None


def main() -> int:
    by_ref: dict[str, dict] = {}

    with SRC.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            desigs = [d.strip() for d in (row.get("Designator") or "").split(",") if d.strip()]
            mpn    = clean(row.get("Manufacturer Part Number"))
            lcsc   = clean(row.get("LCSC Part Number"))
            mfg    = clean(row.get("Manufacturer Name"))
            pkg    = clean(row.get("Package") or row.get("Package or Case Code"))
            role   = clean(row.get("Role"))
            details= clean(row.get("Role Details"))
            ds     = clean(row.get("Datasheet URL"))
            resist = clean(row.get("Resistance"))
            capval = clean(row.get("Capacitance"))
            induct = clean(row.get("Inductance"))
            ptype  = clean(row.get("Part Type"))
            value  = resist or capval or induct or mpn  # pick the most useful label
            for d in desigs:
                by_ref[d] = {
                    "ref": d,
                    "value": value,
                    "mpn": mpn,
                    "lcsc": lcsc,
                    "manufacturer": mfg,
                    "package": pkg,
                    "part_type": ptype,
                    "role": role,
                    "role_detail": details,
                    "datasheet": ds,
                }

    # Merge in pick-and-place positions
    with PNP.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ref = clean(row.get("Designator"))
            if not ref or ref not in by_ref:
                # extra test points / passives not in Flux BOM
                by_ref.setdefault(ref or "_", {"ref": ref})
            entry = by_ref.get(ref)
            if not entry:
                continue
            entry["pnp"] = {
                "x_mm": float(row["Mid X"].replace("mm", "")),
                "y_mm": float(row["Mid Y"].replace("mm", "")),
                "layer": row["Layer"],
                "rotation": float(row["Rotation"]),
                "package": row["Package"],
                "value": row["Value"] or None,
            }

    def sort_key(r):
        ref = r.get("ref") or ""
        prefix = "".join(c for c in ref if c.isalpha()) or "zzz"
        num = int("".join(c for c in ref if c.isdigit()) or "0")
        return (prefix, num)

    # Drop any stubs that never got a real ref
    cleaned = [r for r in by_ref.values() if r.get("ref")]
    ordered = sorted(cleaned, key=sort_key)
    OUT.write_text(json.dumps({"components": ordered}, indent=2))
    print(f"wrote {OUT.relative_to(ROOT)}   ({len(ordered)} components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
