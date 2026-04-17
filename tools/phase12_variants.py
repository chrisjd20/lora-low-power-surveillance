#!/usr/bin/env python3
"""
Phase 12 — Generate per-tier fab packages from a single PCB source.

Produces, for each tier in tools/variants.yaml:
  fab/<tier>/
    gerbers/*           <-- IDENTICAL across all three tiers
    warden-apex-master.d356
    warden-apex-master-pos.csv
    warden-apex-master-pos-jlc.csv
    warden-apex-master-bom-kicad.csv
    warden-apex-master-bom-jlc.csv
    warden-apex-master-bom-full.csv
    README.md
  fab/warden-<tier>-v2.zip
"""
from __future__ import annotations
import csv
import json
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path('/home/admin/github/lora-low-power-surveillance')
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
SCH  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch"
FAB  = ROOT / "fab"


def load_variants() -> dict:
    """Hand-parse tools/variants.yaml (no yaml import dep)."""
    out = {}
    text = (ROOT / "tools/variants.yaml").read_text()
    # Very simple parser: tier is top-level key (unindented), 'dnp:' sublist
    current: str | None = None
    in_dnp = False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isalpha() and raw.rstrip().endswith(":"):
            current = raw.split(":", 1)[0].strip()
            out[current] = {"dnp": [], "description": ""}
            in_dnp = False
        elif raw.strip().startswith("dnp:"):
            in_dnp = True
        elif raw.strip().startswith("description:"):
            in_dnp = False
        elif in_dnp and raw.strip().startswith("-"):
            ref = raw.strip().lstrip("- ").split("#")[0].strip()
            if ref:
                out[current]["dnp"].append(ref)
        elif in_dnp and not raw.strip().startswith("-"):
            in_dnp = False
    return out


def parse_netlist_bom() -> list[dict]:
    """Return list of {ref, value, footprint, mpn, lcsc, descr} from the
    schematic netlist export."""
    # Export netlist in KiCad Sexpr form
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist",
         "--format", "kicadsexpr",
         "--output", str(ROOT / "build/warden-apex.net"),
         str(SCH)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    text = (ROOT / "build/warden-apex.net").read_text()
    out = []
    # Each (comp (ref "R1") (value "100k") (footprint "...") ...)
    for m in re.finditer(
        r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]+)"\)\s*\(footprint "([^"]*)"\)',
        text,
    ):
        out.append({
            "ref": m.group(1),
            "value": m.group(2),
            "footprint": m.group(3),
            "mpn": "",
            "lcsc": "",
            "descr": "",
        })
    return out


def build_tier(tier: str, dnp: list[str], description: str,
               all_parts: list[dict]) -> None:
    tier_dir = FAB / tier
    shutil.rmtree(tier_dir, ignore_errors=True)
    tier_dir.mkdir(parents=True, exist_ok=True)

    # ---- gerbers (identical across tiers) ----
    gerb_dir = tier_dir / "gerbers"
    gerb_dir.mkdir(exist_ok=True)
    subprocess.run([
        "kicad-cli", "pcb", "export", "gerbers",
        "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts,F.Paste,B.Paste",
        "--output", str(gerb_dir) + "/",
        "--no-protel-ext",
        str(PCB),
    ], check=False)
    subprocess.run([
        "kicad-cli", "pcb", "export", "drill",
        "--output", str(gerb_dir) + "/",
        "--format", "excellon",
        "--excellon-separate-th",
        "--generate-map", "--map-format", "pdf",
        str(PCB),
    ], check=False)

    # ---- IPC-D-356 netlist ----
    subprocess.run([
        "kicad-cli", "pcb", "export", "ipcd356",
        "--output", str(tier_dir / "warden-apex-master.d356"),
        str(PCB),
    ], check=False)

    # ---- Pick-and-place (filter out DNP refs) ----
    pos_csv = tier_dir / "warden-apex-master-pos.csv"
    subprocess.run([
        "kicad-cli", "pcb", "export", "pos",
        "--output", str(pos_csv),
        "--format", "csv",
        "--units", "mm",
        "--side", "both",
        str(PCB),
    ], check=False)
    # Filter P&P to drop DNP parts
    if pos_csv.exists():
        rows_in = list(csv.reader(pos_csv.open()))
        if rows_in:
            header = rows_in[0]
            rows_out = [header]
            # Find Ref column
            ref_col = header.index("Ref") if "Ref" in header else 0
            for r in rows_in[1:]:
                if r[ref_col] not in dnp:
                    rows_out.append(r)
            with pos_csv.open("w", newline="") as f:
                csv.writer(f).writerows(rows_out)
        # Also produce JLCPCB-formatted P&P: Designator, Mid X, Mid Y, Rotation, Layer
        jlc_pos = tier_dir / "warden-apex-master-pos-jlc.csv"
        with jlc_pos.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for r in rows_out[1:]:
                # KiCad POS cols: Ref, Val, Package, PosX, PosY, Rot, Side
                if len(r) < 7:
                    continue
                w.writerow([r[0], r[3], r[4], r[6].capitalize(), r[5]])

    # ---- BOM (KiCad + JLCPCB format + enriched) ----
    bom_kicad = tier_dir / "warden-apex-master-bom-kicad.csv"
    subprocess.run([
        "kicad-cli", "sch", "export", "bom",
        "--output", str(bom_kicad),
        "--fields", "Reference,Value,Footprint,${QUANTITY}",
        "--group-by", "Value,Footprint",
        "--ref-range-delimiter", "",
        str(SCH),
    ], check=False)

    # Filter KiCad BOM + produce JLCPCB BOM
    bom_jlc = tier_dir / "warden-apex-master-bom-jlc.csv"
    bom_full = tier_dir / "warden-apex-master-bom-full.csv"
    parts = [p for p in all_parts if p["ref"] not in dnp]

    # Group by (value, footprint)
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in parts:
        key = (p["value"], p["footprint"])
        groups.setdefault(key, []).append(p)

    with bom_jlc.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, footprint), grp in sorted(groups.items()):
            refs = ",".join(r["ref"] for r in grp)
            lcsc = grp[0].get("lcsc", "")
            w.writerow([value, refs, footprint, lcsc])

    with bom_full.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Ref", "Qty", "Value", "Footprint", "MPN", "LCSC", "Description"])
        for (value, footprint), grp in sorted(groups.items()):
            refs = ",".join(r["ref"] for r in grp)
            w.writerow([refs, len(grp), value, footprint,
                        grp[0].get("mpn", ""),
                        grp[0].get("lcsc", ""),
                        grp[0].get("descr", "")])

    # ---- README ----
    tier_name = {
        "drone": "Warden Drone (Tier 1 — LoRa + BLE/WiFi)",
        "cell_master": "Warden Cell Master (Tier 2 — LoRa + BLE/WiFi + Cellular)",
        "apex": "Warden Apex (Tier 3 — LoRa + BLE/WiFi + Cellular + Satellite)",
    }.get(tier, tier)
    (tier_dir / "README.md").write_text(
        f"# {tier_name}\n\n"
        f"{description.strip()}\n\n"
        f"## Files\n\n"
        f"- `gerbers/` — 4-layer PCB gerbers + drill (identical across all tiers)\n"
        f"- `warden-apex-master.d356` — IPC-D-356 netlist for bare-board test\n"
        f"- `warden-apex-master-pos.csv` — KiCad P&P, DNP refs filtered out\n"
        f"- `warden-apex-master-pos-jlc.csv` — JLCPCB P&P format\n"
        f"- `warden-apex-master-bom-kicad.csv` — KiCad native BOM\n"
        f"- `warden-apex-master-bom-jlc.csv` — JLCPCB assembly BOM\n"
        f"- `warden-apex-master-bom-full.csv` — enriched BOM with MPN/LCSC/descr\n\n"
        f"## DNP ({len(dnp)} parts)\n\n"
        + (", ".join(dnp) if dnp else "*none — fully populated*") + "\n\n"
        f"## JLCPCB upload\n\n"
        f"1. Upload `gerbers/` as a zip in the PCB manufacturing form.\n"
        f"2. Enable SMT assembly and upload:\n"
        f"   - P&P: `warden-apex-master-pos-jlc.csv`\n"
        f"   - BOM: `warden-apex-master-bom-jlc.csv`\n"
        f"3. Fill any missing LCSC numbers using the `bom-full.csv` supplement.\n"
    )

    # ---- Zip ----
    zip_path = FAB / f"warden-{tier.replace('_', '-')}-v2.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in tier_dir.rglob("*"):
            if p.is_file():
                z.write(p, arcname=str(p.relative_to(FAB)))
    print(f"  [ok] {tier}: {zip_path.name} ({zip_path.stat().st_size // 1024} KB)")


def main() -> int:
    FAB.mkdir(parents=True, exist_ok=True)
    variants = load_variants()
    all_parts = parse_netlist_bom()

    for tier, cfg in variants.items():
        print(f"=== {tier} ===")
        build_tier(tier, cfg["dnp"], cfg.get("description", ""), all_parts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
