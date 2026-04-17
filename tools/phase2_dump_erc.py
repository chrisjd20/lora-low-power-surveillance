#!/usr/bin/env python3
"""Run ERC via MCP and dump categorized report to hardware/warden-apex-master/erc-report.txt."""
from __future__ import annotations
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from phase2_mcp_client import McpSession

SCHEMA = str(ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_sch")
OUT    = ROOT / "hardware/warden-apex-master/erc-report.txt"


def main() -> int:
    with McpSession() as s:
        r = s.call("run_erc", {"schematicPath": SCHEMA}, timeout=300)
    raw = r.get("raw", json.dumps(r))
    # Count error categories from the raw text
    lines = [l for l in raw.splitlines() if l.strip().startswith(("1.", "2.", "3.")) or l.startswith(tuple(str(i) + "." for i in range(1, 10000)))]
    # Simpler: regex match [error] / [warning]
    by_kind: dict[str, dict[str, int]] = {"error": {}, "warning": {}}
    for line in raw.splitlines():
        m = re.match(r"^\d+\.\s+\[(error|warning)\]\s+(.*?)\s*(@ \(.*?\))?$", line.strip())
        if not m:
            continue
        kind, msg = m.group(1), m.group(2)
        # Strip coordinates / refs, keep the issue category
        cat = re.sub(r'"[^"]+"', '"..."', msg)
        cat = re.sub(r"\b[A-Z][A-Z0-9_]+\b", "X", cat)[:120]
        by_kind[kind][cat] = by_kind[kind].get(cat, 0) + 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        fh.write(raw + "\n\n")
        fh.write("=== CATEGORIES ===\n")
        for kind in ("error", "warning"):
            fh.write(f"\n[{kind}]\n")
            for cat, n in sorted(by_kind[kind].items(), key=lambda kv: -kv[1]):
                fh.write(f"  {n:5d}  {cat}\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for kind in ("error", "warning"):
        total = sum(by_kind[kind].values())
        print(f"[{kind}] total={total}")
        for cat, n in sorted(by_kind[kind].items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {n:5d}  {cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
