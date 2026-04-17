#!/usr/bin/env python3
"""
Define 4 net classes and assign nets to them in the project file.

Classes:
    Default            — signal, 0.2 mm trace / 0.2 mm clearance / 0.6/0.3 via
    POWER_3V3          — 0.4 mm trace, 0.25 mm clearance, 0.8/0.4 via
    POWER_HIGH_CURRENT — 0.6 mm trace, 0.3 mm clearance, 1.0/0.5 via
                         (nets: VBAT_SYS, MODEM_VBAT, SOLAR_IN, CHG_PH,
                          CHG_SENSE_NEG, CHG_BST, CHG_REGN, CHG_GATE_HI,
                          CHG_GATE_LO)
    RF_50OHM           — 0.4 mm trace, 0.25 mm clearance, 0.6/0.3 via
                         (nets: CELL_RF, LORA_RF)

The KiCad net-class assignment is done via `netclass_patterns` — a list
of glob patterns that map net names to class names.
"""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRO  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pro"


def main() -> int:
    pro = json.loads(PRO.read_text())
    ns = pro.setdefault("net_settings", {})

    default_class = next(c for c in ns["classes"] if c["name"] == "Default")
    template = {
        **default_class,
        "priority": 10,
    }
    template.pop("name", None)

    ns["classes"] = [
        default_class,
        {**template, "name": "POWER_3V3",
         "track_width": 0.4, "clearance": 0.2,   # relaxed for QFN-15 pitch
         "via_diameter": 0.8, "via_drill": 0.4,
         "pcb_color": "rgba(255, 140, 0, 0.700)"},
        {**template, "name": "POWER_HIGH_CURRENT",
         "track_width": 0.6, "clearance": 0.2,   # clearance matched to QFN pitch
         "via_diameter": 1.0, "via_drill": 0.5,
         "pcb_color": "rgba(220, 30, 30, 0.700)"},
        {**template, "name": "RF_50OHM",
         "track_width": 0.4, "clearance": 0.25,
         "via_diameter": 0.6, "via_drill": 0.3,
         "pcb_color": "rgba(120, 60, 200, 0.700)"},
    ]

    # Pattern-based assignment. KiCad's glob is simple text match.
    ns["netclass_patterns"] = [
        {"netclass": "POWER_3V3", "pattern": "3V3"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "VBAT_SYS"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "MODEM_VBAT"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "SOLAR_IN"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "CHG_PH"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "CHG_SENSE_NEG"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "CHG_BST"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "CHG_REGN"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "CHG_GATE_HI"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "CHG_GATE_LO"},
        {"netclass": "POWER_HIGH_CURRENT", "pattern": "REG_IN"},
        {"netclass": "RF_50OHM", "pattern": "CELL_RF"},
        {"netclass": "RF_50OHM", "pattern": "LORA_RF"},
    ]

    PRO.write_text(json.dumps(pro, indent=2))
    print(f"wrote {len(ns['classes'])} net classes and "
          f"{len(ns['netclass_patterns'])} pattern assignments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
