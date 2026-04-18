# Warden Apex Master — fab output package

Generated from `hardware/warden-apex-master/warden-apex-master.kicad_pcb`
after the **Phase 22 power-rail / ground-stitch hardening** (see
`hardware/warden-apex-master/PLAN.md` § Phase 22), which widened 346
under-sized power-net segments on `POWER_HI`/`POWER_3V3`/`CHARGER_SW`
to their netclass targets and added a 171-via F.Cu↔In1.Cu↔B.Cu
ground stitch grid, on top of the Phase 21 routing-completion sweep
and the Phase 20 universal-PCB recovery. The outputs in this folder
are ready to upload to JLCPCB (or any equivalent fab) as-is — no
manual routing pass is required.

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

**1. Phase 20/21 SIM7080 repair (applied, no action required).**
The `LCC-42_SIM7080G` symbol's pin-to-name mapping was corrected in
Phase 20 (77 pins rewritten to match SIMCom SIM7080G datasheet V1.04),
every `IC1` pad on the PCB was re-mapped to the correct net, 83
mis-routed legacy traces around IC1 were purged, and two local-VBAT
decouplers were added to IC1 pad 34:

   | Ref | Value | Footprint | Placement         | Role              |
   |-----|-------|-----------|-------------------|-------------------|
   | C33 | 100 nF | 0805     | 43.0,50.2  rot 90 | IC1 HF decoupling |
   | C34 | 47 µF  | 1206     | 46.5,50.5  rot 90 | IC1 bulk reservoir |

Both sit on `/MODEM_VBAT_SW` (POWER_HI netclass, 0.6 mm trace) and fan
out directly to IC1 pad 34 (VBAT). All ~60 unused SIM7080 pads are
intentionally tied to `/GND` with `zone_connect 2` thermal relief so
the GND pour contacts them rather than shorting through the fill.
These changes are already baked into the `.kicad_pcb` and reflected in
every file in this folder.

**2. Routing complete + power-rail hardening — no manual finish needed.**
Phase 21 closed every remaining open net (`/CELL_RF`,
`/SIM_{VDD,VDD_EXT,CLK,RST,DATA}`, `/UART1_{TX,RX}`, `/UART2_{TX,RX}`,
`/MODEM_VBAT_SW`), fixed the starved-thermal on `J4.6/GND`, and
cleaned up dangling vias. Phase 22 then widened every routed power
rail to the netclass target (`POWER_HI` 0.40 mm, `POWER_3V3` 0.30 mm,
`CHARGER_SW` 0.40 mm), added a deliberate 171-via GND stitching grid
across F.Cu / In1.Cu / B.Cu, and dropped the last missing F.Cu↔B.Cu
transition via on `/GND` at `(21.20, 78.68)`. The board now passes
`--severity-error` DRC with zero unconnected items and zero
schematic-parity errors. `/CELL_RF` remains on the `RF_50OHM`
netclass, kept short, but is not a fully tuned coplanar waveguide —
see caveat 4.

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

**5. DRC snapshot (as shipped).**

`kicad-cli pcb drc --schematic-parity --severity-error` on the
as-fabricated board reports:

   - 0 errors
   - 0 unconnected items
   - 0 schematic-parity errors

At full severity (warnings included), the remaining items are all
intentional / cosmetic:

   - ~44 silk_over_copper + silk_overlap — silkscreen touches on
     tight passive clusters; reference designators remain readable.
   - 3 lib_footprint_mismatch — the hand-authored `C33`, `C34`, and
     `U3 (Swarm_M138)` footprints intentionally differ from the stock
     libraries because they carry repair-specific pad/net overrides.
   - 52 schematic-parity warnings (`net_conflict`,
     `footprint_symbol_mismatch`) covering the same repair-era
     library mismatches and power-symbol silkscreen-vs-net labels;
     none represent an electrical defect.
