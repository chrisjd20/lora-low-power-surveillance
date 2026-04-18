# Warden Apex Master — fab output package

Generated from `hardware/warden-apex-master/warden-apex-master.kicad_pcb`
after the **Phase 21 SIM7080 repair** (see section below) on top of the
**Phase 20 universal-PCB recovery** (`tools/phase20_*.py` and
`hardware/warden-apex-master/VARIANTS.md`).

Board specs: **100 mm × 100 mm, 4-layer, 1.6 mm FR-4, HASL finish**,
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

Gerbers and drill files are byte-identical across tiers — only the BOM
(`*-bom-jlc.csv`) and pick-and-place file (`*-pos-jlc.csv`) differ.
See `hardware/warden-apex-master/VARIANTS.md` for the per-tier
stuffing tables and jumper map.

## JLCPCB upload checklist

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

**1. Phase 21 SIM7080 / decoupling repair.**  This fab package was
regenerated after a critical Phase 21 repair pass that fixed the
`LCC-42_SIM7080G` symbol's pin-to-name mapping (77 pins rewritten to
match SIMCom SIM7080G datasheet V1.04), re-mapped every `IC1` pad on
the PCB to the correct net, purged 83 mis-routed legacy traces in the
IC1 region, and added two new **IC1 local-VBAT decouplers**:

   | Ref | Value | Footprint | Placement         | Role              |
   |-----|-------|-----------|-------------------|-------------------|
   | C33 | 100 nF | 0805     | 43.0,50.2  rot 90 | IC1 HF decoupling |
   | C34 | 47 µF  | 1206     | 46.5,50.5  rot 90 | IC1 bulk reservoir |

Both are on `/MODEM_VBAT_SW` (POWER_HI netclass, 0.6 mm trace) and
fanout directly to IC1 pad 34 (VBAT).  All ~60 unused SIM7080 pads
are intentionally tied to `/GND` with `zone_connect 2` thermal relief
so the GND pour correctly contacts them instead of shorting through
the fill.

**2. Manual-finish routing (required).**  The autorouter (Freerouting
v2.0.1, 300 passes) converged with ~14 distinct nets still airwired
because of dense pours and the 0.6 mm POWER_HI minimum trace width.
They need an interactive KiCad 9 routing pass before fabrication:

   | Net            | From                   | To                          |
   |----------------|------------------------|-----------------------------|
   | /UART1_TX      | XIAO U1.19             | SIM7080 IC1.2               |
   | /UART1_RX      | XIAO U1.18 → R17.1     | SIM7080 IC1.1               |
   | /UART2_TX      | Swarm U3.28            | existing stub @35.65,52.00  |
   | /UART2_RX      | Swarm U3.12            | R18.1 @41.09,52.00          |
   | /SIM_CLK       | SIM7080 IC1.16         | Card1.2                     |
   | /SIM_RST       | SIM7080 IC1.17         | Card1.3                     |
   | /SIM_DATA      | SIM7080 IC1.15         | Card1.4                     |
   | /SIM_VDD       | SIM7080 IC1.18         | JP2.1 (and Card1.1 via JP2) |
   | /SIM_VDD_EXT   | SIM7080 IC1.40         | C29.1 (via on F.Cu→B.Cu)    |
   | /CELL_RF       | SIM7080 IC1.32         | D1.1 → J1.1 (U.FL)          |
   | /MODEM_VBAT_SW | TP4.1 / JP1.2 / Q2.3 / Swarm U3 (pins 1, 20, 35, 39) | bus stitching between modem power network nodes |

`/CELL_RF` must be routed as a 50 Ω coplanar waveguide between IC1.32,
D1 (TVS), and J1 (U.FL) — the RF_50OHM netclass handles width; keep
the trace length < 20 mm and surround it with stitched GND vias.  All
others are low-speed (UART / ISO7816 SIM / DC power) and accept a
simple 0.2 mm (signal) or 0.6 mm (POWER_HI) trace on F.Cu or B.Cu
with one or two vias.  Use KiCad's interactive router (`x` key).

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

**4. DRC snapshot (as shipped).**
   - 0 shorts, 0 clearance errors, 0 track-crossings
   - 18 unconnected items — the airwires in the table above
   - 2 track_dangling — stubs left for the manual `/UART2_*` routing
   - 1 starved_thermal on J4.6 (`/GND`, B.Cu) — cosmetic; the
     underlying solid In1.Cu GND plane carries the full return
   - 3 lib_footprint_mismatch — the hand-authored `C33`, `C34`, and
     `U3 (Swarm_M138)` footprints intentionally differ from the
     stock libraries (they carry repair-specific pad/net overrides);
     safe to ignore.
   - 44 silk/mask cosmetic warnings (unchanged from prior revisions).
