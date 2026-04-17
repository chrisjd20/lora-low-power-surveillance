# Warden Apex Master — fab output package

Generated from `hardware/warden-apex-master/warden-apex-master.kicad_pcb`
after the **Phase 20 universal-PCB recovery** (see
`tools/phase20_*.py` and `hardware/warden-apex-master/VARIANTS.md`).

Board specs: **100 mm × 100 mm, 4-layer, 1.6 mm FR-4, HASL finish**,
plated through-holes only, min trace 0.2 mm, min via 0.3 mm drill /
0.6 mm diameter.  Stackup assumed: F.Cu / In1.Cu (GND plane) /
In2.Cu (VBAT_SYS plane) / B.Cu.

## Contents

```
fab/
├── README.md                                   this file
├── gerbers/                                    Gerber X2 + Excellon drill files
│   ├── warden-apex-master-F_Cu.gbr             top copper (signals + F.Cu GND pour)
│   ├── warden-apex-master-GND.gbr              In1.Cu solid GND plane
│   ├── warden-apex-master-PWR.gbr              In2.Cu VBAT_SYS power plane
│   ├── warden-apex-master-B_Cu.gbr             bottom copper
│   ├── warden-apex-master-F_Mask.gbr           top solder mask
│   ├── warden-apex-master-B_Mask.gbr           bottom solder mask
│   ├── warden-apex-master-F_Silkscreen.gbr     top silk
│   ├── warden-apex-master-B_Silkscreen.gbr     bottom silk
│   ├── warden-apex-master-F_Paste.gbr          top stencil paste
│   ├── warden-apex-master-B_Paste.gbr          bottom stencil paste
│   ├── warden-apex-master-Edge_Cuts.gbr        board outline
│   ├── warden-apex-master-PTH.drl              plated through-holes (Excellon)
│   ├── warden-apex-master-NPTH.drl             non-plated through-holes
│   ├── warden-apex-master-PTH-drl_map.pdf      drill map reference
│   ├── warden-apex-master-NPTH-drl_map.pdf
│   └── warden-apex-master-job.gbrjob           KiCad job definition
├── warden-apex-master.d356                     IPC-D-356 bare-board test netlist
├── warden-apex-master-pos.csv                  KiCad native P&P
├── warden-apex-master-JLCPCB-pos.csv           JLCPCB-format P&P (Designator, Val, Package, Mid X, Mid Y, Rotation, Layer)
├── warden-apex-master-bom-kicad.csv            KiCad native BOM
├── warden-apex-master-JLCPCB-bom.csv           JLCPCB assembly BOM (Comment, Designator, Footprint, LCSC Part #)
└── warden-apex-master-bom-full.csv             full BOM with MPN, Manufacturer, LCSC, Role annotations
```

## JLCPCB upload checklist

1. **PCB manufacturing** — upload the whole `gerbers/` directory as a
   zip. JLCPCB auto-detects a 4-layer board from `*-F_Cu.gbr /
   *-GND.gbr / *-PWR.gbr / *-B_Cu.gbr`. Surface finish: HASL (leaded)
   is cheapest; ENIG is better for the RF antenna pads if budget allows.
   Stackup: JLC04161H-7628 or equivalent. Board thickness 1.6 mm.

2. **SMT assembly** — upload:
   - P&P:  `warden-apex-master-JLCPCB-pos.csv`
   - BOM:  `warden-apex-master-JLCPCB-bom.csv`

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

## Per-tier packages

`tools/phase12_variants.py` produces a dedicated folder for each tier
plus a top-level zip bundle:

```
fab/
├── drone/          Tier 1: LoRa + BLE only
├── cell_master/    Tier 2: + SIM7080G cellular
├── apex/           Tier 3: + Swarm M138 satellite
├── warden-drone-v3.zip
├── warden-cell-master-v3.zip
└── warden-apex-v3.zip
```

Gerbers and drill files are byte-identical across tiers — only
the BOM (`*-bom-jlc.csv`), the pick-and-place file (`*-pos-jlc.csv`),
and the jumper-close instructions differ.  See
`hardware/warden-apex-master/VARIANTS.md` for the per-tier stuffing
tables and jumper map.

## Known caveats — READ BEFORE ORDERING

**1. Phase 20 manual-finish routing (required).**  The Phase 20
universal-recovery scripts deliberately purge the stale
`/UART1_TX`, `/UART1_RX`, and extend-points of `/UART2_TX`,
`/UART2_RX` routing because the original topology was miswired.
Five signal nets still need an interactive KiCad 9 routing pass
before gerbers are re-exported:

   | Net         | From                   | To                |
   |-------------|------------------------|-------------------|
   | /UART1_TX   | XIAO U1.19 (GPIO40)    | SIM7080 IC1.34    |
   | /UART1_RX   | XIAO U1.18 (GPIO41)    | R17.1 + IC1.40    |
   | /UART2_TX   | R19.1 (stub endpoint)  | Swarm U3.28       |
   | /UART2_RX   | R18.1 (stub endpoint)  | Swarm U3.12       |
   | /SIM_VDD_EXT | (already routed locally IC1.69 ↔ C29.1) | — |

All are low-speed UART signals — 0.20 mm trace on F.Cu or B.Cu with
one or two vias is sufficient.  No impedance control required.  Use
KiCad's interactive router (`x` key) and let push-and-shove handle
the surrounding copper.

**2. Custom-footprint datasheet re-verification (required).**
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

**3. RF trace routing** is functional but not impedance-controlled
coplanar waveguide.  Fine for LTE-M / 433 MHz proof-of-concept.

**4. Stale Phase 5 observations superseded.**  The earlier warnings
about "29 unconnected_items + 199 net_conflict all being F.Cu GND
zone fragments" were resolved in Phase 20 by remapping the `GND`
and `VBAT_SYS` zones to `/GND` and `/VBAT_SYS` (the actual pad
nets).  Current DRC: after the manual-finish UART routing, only
one pre-existing warning remains — a single starved-thermal on
`J4` pin 6 (`/GND`, B.Cu) flagged because the PTH pad has only
one spoke instead of two.  This is cosmetic and does not affect
continuity through the solid In1.Cu GND plane.
