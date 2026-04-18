# Warden Apex Master — fab output package

Generated from `hardware/warden-apex-master/warden-apex-master.kicad_pcb`
in the current **Phase 24 live rework state** (see
`hardware/warden-apex-master/PLAN.md` § Phase 24). These outputs are
useful for review, bring-up debugging, and diffing fab artefacts across
changes, but this snapshot is **not yet release/fab sign-off clean**.

Refresh snapshot (2026-04-18, current live state):

- `kicad-cli sch erc --severity-error` -> 0 errors
- `kicad-cli pcb drc --schematic-parity --severity-error` -> 10 violations, 5 unconnected, 0 parity issues
- `kicad-cli sch erc --severity-all` -> 22 warnings
- `kicad-cli pcb drc --schematic-parity --severity-all` -> 232 violations, 5 unconnected, 121 parity issues
- Re-generated: `fab/warden-drone-v3.zip`, `fab/warden-cell-master-v3.zip`, `fab/warden-apex-v3.zip`
- UART/cellular block is under active level-shift + control-path rework
  in this snapshot; do not treat these packages as production release
  artefacts until DRC is restored to error-clean.
- Board envelope is now `125 x 125 mm` (expanded by +15 mm left, +10 mm
  right, +5 mm top, +20 mm bottom) and `MH1..MH4` were moved to the new
  corners with the same 3.5 mm edge inset.

Board specs: **125 mm × 125 mm, 4-layer, 1.6 mm FR-4, HASL finish**,
plated through-holes only, min trace 0.2 mm, min via 0.3 mm drill /
0.6 mm diameter.  Stackup assumed: F.Cu / In1.Cu (GND plane) /
In2.Cu (VBAT_SYS plane) / B.Cu.

## Contents

The authoritative outputs live under one folder per stuffing tier,
each produced by `tools/phase12_variants.py`:

```
fab/
├── README.md                                    this file
├── drone/                                       Tier 1: LoRa + BLE only
├── cell_master/                                 Tier 2: + SIM7080G cellular
├── apex/                                        Tier 3: + Swarm M138 satellite
│   ├── gerbers/                                 Gerber X2 + Excellon drill files
│   │   ├── warden-apex-master-F_Cu.gbr          top copper (signals + F.Cu GND pour)
│   │   ├── warden-apex-master-GND.gbr           In1.Cu solid GND plane
│   │   ├── warden-apex-master-PWR.gbr           In2.Cu VBAT_SYS power plane
│   │   ├── warden-apex-master-B_Cu.gbr          bottom copper
│   │   ├── warden-apex-master-{F,B}_Mask.gbr    solder mask
│   │   ├── warden-apex-master-{F,B}_Silkscreen.gbr   silk
│   │   ├── warden-apex-master-{F,B}_Paste.gbr   stencil paste
│   │   ├── warden-apex-master-Edge_Cuts.gbr     board outline
│   │   ├── warden-apex-master-{PTH,NPTH}.drl    Excellon drill files
│   │   ├── warden-apex-master-{PTH,NPTH}-drl_map.pdf
│   │   └── warden-apex-master-job.gbrjob        KiCad job definition
│   ├── warden-apex-master.d356                  IPC-D-356 bare-board test netlist
│   ├── warden-apex-master-pos.csv               KiCad native P&P
│   ├── warden-apex-master-pos-jlc.csv           JLCPCB-format P&P
│   ├── warden-apex-master-bom-kicad.csv         KiCad native BOM
│   ├── warden-apex-master-bom-jlc.csv           JLCPCB assembly BOM (LCSC)
│   └── warden-apex-master-bom-full.csv          full BOM with MPN, Manufacturer, LCSC, Role
├── warden-drone-v3.zip                          upload-ready bundle — Tier 1
├── warden-cell-master-v3.zip                    upload-ready bundle — Tier 2
└── warden-apex-v3.zip                           upload-ready bundle — Tier 3
```

Gerbers and drill files are byte-identical across tiers — only assembly
artifacts differ by tier (`*-bom-kicad.csv`, `*-bom-jlc.csv`,
`*-bom-full.csv`, `*-pos.csv`, `*-pos-jlc.csv`), all filtered from the
same DNP source in `tools/variants.yaml`.
See `hardware/warden-apex-master/VARIANTS.md` for the per-tier
stuffing tables and jumper map.

## JLCPCB upload checklist

Current note: this checklist is retained for workflow continuity, but
the present Phase 24 snapshot should not be submitted for production
until the error-level DRC blockers are cleared.

1. **PCB manufacturing** — upload the relevant `<tier>-v3.zip` (or the
   `<tier>/gerbers/` directory zipped up). JLCPCB auto-detects a
   4-layer board from `*-F_Cu.gbr / *-GND.gbr / *-PWR.gbr /
   *-B_Cu.gbr`. Surface finish: HASL (leaded) is cheapest; ENIG is
   better for the RF antenna pads if budget allows. Stackup:
   JLC04161H-7628 or equivalent. Board thickness 1.6 mm.

2. **SMT assembly** — upload from `fab/<tier>/`:
   - P&P:  `warden-apex-master-pos-jlc.csv`
   - BOM:  `warden-apex-master-bom-jlc.csv`

   JLCPCB's web form expects columns in the order the files provide.
   LCSC part numbers are pre-populated for:
   `Card1 (C266890)`, `D1/D2 (C907863)`, `H1 (C306148)`.
   **Everything else needs manual LCSC lookup** in JLCPCB's web UI —
   see `warden-apex-master-bom-full.csv` for MPNs.

3. Things NOT on this board and to source separately:
   - Seeed Studio XIAO ESP32-S3 Sense (U1) — Seeed direct
   - SIM7080G (IC1) — SIMCom / SIMCom-authorised reseller
   - Ai-Thinker Ra-01 (U2) — Ai-Thinker / LCSC C153034
   - Swarm M138 (U3) — Swarm direct / Digi-Key
   - BQ24650RVAR (IC2) — Mouser / Digi-Key
   - TPS63070RNMR (IC3) — Mouser / Digi-Key
   - MAX98357AETE+T (IC4) — Mouser / Digi-Key
   - MCP23017_SO (U4) — Microchip / Digi-Key / LCSC C14289
   - SRV05-4-P-T7 (U5) — LCSC / TI
   - DMG9926UDM (Q1) — Diodes Inc. / Digi-Key
   - BAT54HT1G (D3) — Mouser / Digi-Key

## Known caveats — READ BEFORE ORDERING

**1. Phase 20/21 SIM7080 repair (applied, no action required).**
The `LCC-42_SIM7080G` symbol's pin-to-name mapping was corrected in
Phase 20 (77 pins rewritten to match SIMCom SIM7080G datasheet V1.04),
every `IC1` pad on the PCB was re-mapped to the correct net, 83
mis-routed legacy traces around IC1 were purged, and two local-VBAT
decouplers were added to IC1 pad 34:

   | Ref | Value (live) | Footprint | Placement         | Role              |
   |-----|--------------|-----------|-------------------|-------------------|
   | C33 | 100 nF       | 0805      | 43.0,50.2  rot 90 | IC1 HF decoupling |
   | C34 | bulk cap (see BOM) | 1206 | 46.5,50.5  rot 90 | IC1 local reservoir |

Both sit on `/MODEM_VBAT_SW` (POWER_HI netclass, 0.6 mm trace) and fan
out directly to IC1 pad 34 (VBAT). All ~60 unused SIM7080 pads are
intentionally tied to `/GND` with `zone_connect 2` thermal relief so
the GND pour contacts them rather than shorting through the fill.
These changes are already baked into the `.kicad_pcb` and reflected in
every file in this folder.

**2. Routing hardening history + current status.**
Phase 21/22 closed major historical routing and power-integrity
blockers (open nets, power-rail width compliance, GND stitch density),
but the current Phase 24 live edits re-opened error-level PCB issues.
At this snapshot, `--severity-error` DRC is **not clean** (10
violations, 5 unconnected), so further cleanup is required before
production fab submit.

**3. Custom-footprint datasheet re-verification (recommended).**
These five footprints pass ERC but have NOT been cross-checked
against vendor mechanical drawings:

  - `LCC-42_SIM7080G.kicad_mod` — SIMCom SIM7080G LCC body/pads
    (span 15.60 × 18.70 mm center-to-center, 18.10 × 16.20 mm courtyard)
  - `Swarm_M138.kicad_mod` — Swarm M138 edge-castellated pads
    (span 41.20 × 22.60 mm, courtyard 43.10 × 20.20 mm; verify the
    Y span against the 27.0 mm module body before fab)
  - `XIAO_ESP32S3_SENSE.kicad_mod` — Seeed XIAO ESP32-S3 Sense
    (pad span 16.10 × 24.00 mm; verify against the 21.0 × 17.5 mm
    board footprint — the 24 mm span suggests breakout rows that
    extend past the board edge and must be confirmed)
  - `SMN-305_Nano_SIM.kicad_mod` — Attend SMN-305 Nano-SIM holder
    (body 11.2 × 11.0 mm, courtyard 13.3 × 14.5 mm)
  - `QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm.kicad_mod` — TPS63070
    buck-boost (body 3.0 × 4.0 mm EP 1.45 × 2.45 mm, datasheet-correct
    per TI RNM drawing, but re-inspect before stencil cut).

**4. RF trace routing** is functional but not impedance-controlled
coplanar waveguide. Fine for LTE-M / 433 MHz proof-of-concept; plan a
dedicated RF tune-up before any production run that targets formal
conducted-emissions or antenna-efficiency specs.

**5. DRC snapshot (current live state).**

`kicad-cli pcb drc --schematic-parity --severity-error` on the
current live board reports:

   - 10 violations
   - 5 unconnected items
   - 0 schematic-parity errors

At full severity (`--severity-all`):

   - 232 violations
   - 5 unconnected items
   - 121 schematic-parity issues

These are not publish-ready cosmetic-only leftovers; treat this as an
engineering rework snapshot.
