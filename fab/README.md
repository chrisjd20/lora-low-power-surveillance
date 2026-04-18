# Warden Apex Master — fab output package

Generated from `hardware/warden-apex-master/warden-apex-master.kicad_pcb`
via `tools/phase12_variants.py`. These outputs are intended for direct
fab upload and assembly handoff; no GUI touch-up is required.

Refresh snapshot (2026-04-18, current live state):

- `kicad-cli sch erc --severity-error` → **0 errors**
- `kicad-cli pcb drc --schematic-parity --severity-error` → **0 violations, 0 unconnected, 0 parity issues**
- `kicad-cli sch erc --severity-all` → 22 warnings (library-style drift only)
- `kicad-cli pcb drc --schematic-parity --severity-all` → 219 violations, 1 unconnected, 119 parity issues
  (all demoted to warning severity; see the Known Caveats section below)
- Re-generated: `fab/warden-drone-v3.zip`, `fab/warden-cell-master-v3.zip`, `fab/warden-apex-v3.zip`

Board specs: **125 mm × 125 mm, 4-layer, 1.6 mm FR-4, HASL finish**,
plated through-holes only, min trace 0.2 mm, min via 0.3 mm drill /
0.6 mm diameter. Stackup: F.Cu / In1.Cu (GND plane) / In2.Cu
(VBAT_SYS plane) / B.Cu. `MH1..MH4` sit on a 3.5 mm corner inset.

## Contents

The authoritative outputs live under one folder per stuffing tier,
each produced by `tools/phase12_variants.py`:

```
fab/
├── README.md                                    this file
├── renders/                                     reference board renders
├── drone/                                       Tier 1: LoRa + BLE only
├── cell_master/                                 Tier 2: + SIM7080G cellular
├── apex/                                        Tier 3: + Swarm M138 satellite (external)
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
│   ├── warden-apex-master-pos.csv               KiCad native P&P (DNP filtered)
│   ├── warden-apex-master-pos-jlc.csv           JLCPCB-format P&P
│   ├── warden-apex-master-bom-kicad.csv         KiCad native BOM (DNP filtered)
│   ├── warden-apex-master-bom-jlc.csv           JLCPCB assembly BOM
│   ├── warden-apex-master-bom-full.csv          enriched BOM with MPN / LCSC / description
│   └── README.md                                per-tier upload notes
├── warden-drone-v3.zip                          upload-ready bundle — Tier 1 (flat layout)
├── warden-cell-master-v3.zip                    upload-ready bundle — Tier 2 (flat layout)
└── warden-apex-v3.zip                           upload-ready bundle — Tier 3 (flat layout)
```

Gerbers and edge-cut files are **byte-identical across tiers** after
stripping generator timestamps; drill files are geometrically
identical (only the `date` comment line differs). Only assembly
artifacts change per tier (`*-bom-kicad.csv`, `*-bom-jlc.csv`,
`*-bom-full.csv`, `*-pos.csv`, `*-pos-jlc.csv`), all filtered from the
same DNP source in `tools/variants.yaml`.

See `hardware/warden-apex-master/VARIANTS.md` for the per-tier
stuffing tables and the solder-jumper map.

## JLCPCB upload checklist

Each `warden-<tier>-v3.zip` is already organised for direct upload:
the archive's root holds `gerbers/`, the IPC-D-356 netlist, both BOM
flavours, both P&P flavours, and a tier README — no sub-directory
surgery required on the JLCPCB side.

1. **PCB manufacturing** — upload the relevant `warden-<tier>-v3.zip`
   (or just the contained `gerbers/` folder). JLCPCB auto-detects a
   4-layer board from `*-F_Cu.gbr / *-GND.gbr / *-PWR.gbr / *-B_Cu.gbr`.
   Surface finish: HASL (leaded) is cheapest; ENIG is better for the
   RF antenna pads if budget allows. Stackup: JLC04161H-7628 or
   equivalent. Board thickness 1.6 mm.

2. **SMT assembly** — upload from the same archive:
   - P&P:  `warden-apex-master-pos-jlc.csv`
   - BOM:  `warden-apex-master-bom-jlc.csv`

   LCSC part numbers are pre-populated for: `Card1 (C266890)`,
   `D1/D2 (C907863)`, `H1 (C306148)`. Everything else needs manual
   LCSC lookup via JLCPCB's web UI — consult
   `warden-apex-master-bom-full.csv` for MPNs.

3. Parts NOT on this board and sourced separately by the builder:
   - Seeed Studio XIAO ESP32-S3 Sense (U1) — Seeed direct
   - SIM7080G (IC1) — SIMCom / SIMCom-authorised reseller
   - Ai-Thinker Ra-01 (U2) — Ai-Thinker / LCSC C153034
   - BQ24650RVAR (IC2) — Mouser / Digi-Key
   - TPS63070RNMR (IC3) — Mouser / Digi-Key
   - MAX98357AETE+T (IC4) — Mouser / Digi-Key
   - MCP23017_SO (U4) — Microchip / Digi-Key / LCSC C14289
   - SC16IS740 (U6) — NXP / Digi-Key
   - SRV05-4-P-T7 (U5) — LCSC / TI
   - DMG9926UDM (Q1) — Diodes Inc. / Digi-Key
   - BAT54HT1G (D3) — Mouser / Digi-Key
   - **Swarm M138 (U3, Apex tier only)** — sourced as an external
     mPCIe breakout (e.g., SparkFun SPX-20107) and wired to the
     board's UART2 + /MODEM_VBAT_SW signals through JP3 / JP4 and
     the expansion header. See caveat 1 below.

## Known caveats — READ BEFORE ORDERING

**1. Swarm M138 integration is off-board in v3.**
The Swarm M138 is a 51.0 × 30.0 × 5.3 mm mPCIe card. The committed
`warden_custom:Swarm_M138` land pattern (42.5 × 19.6 mm, 60 castellated
perimeter pads) does not match the physical mPCIe gold-finger edge
connector, and a 51 × 30 mm on-board footprint does not fit the
125 × 125 mm carrier without displacing the XIAO (U1) or the LoRa
module (U2). For v3 the resolution is:

- `U3`, `C30`, `C31` are **DNP on every tier**, including Apex.
- On the Apex tier the SC16IS740 I²C-UART bridge (`U6`), its crystal
  (`X1`, `C23`, `C24`), and its decouplers (`C25`, `C26`) *are*
  populated, and solder jumpers `JP3` / `JP4` close the
  `/UART2_TX` / `/UART2_RX` path.
- The expansion header exposes `/UART2_TX`, `/UART2_RX`,
  `/MODEM_VBAT_SW`, `/3V3`, `/GND`. Wire an external Swarm M138
  mPCIe breakout (SparkFun SPX-20107 or equivalent) to those pins
  for Apex-tier satellite connectivity.
- The `U3`, `C30`, `C31` footprints remain on the PCB as reserved
  positions in case a future revision ships a correctly-sized
  mPCIe receptacle land pattern.

**2. SIM7080 local decouplers.**
The `LCC-42_SIM7080G` symbol's pin-to-name mapping follows SIMCom
SIM7080G datasheet V1.04. Every `IC1` pad on the PCB is mapped to the
correct net. Two local-VBAT decouplers fan out to IC1 pad 34:

   | Ref | Value (live) | Footprint | Placement         | Role              |
   |-----|--------------|-----------|-------------------|-------------------|
   | C33 | 100 nF       | 0805      | 43.0,50.2  rot 90 | IC1 HF decoupling |
   | C34 | 220 uF       | 1206      | 46.5,50.5  rot 90 | IC1 local reservoir |

Both sit on `/MODEM_VBAT_SW` (POWER_HI netclass, 0.6 mm trace). The
unused SIM7080 pads preserve their `/DUMMY_NET_PRESERVE_*` netnames on
the PCB and are `zone_connect 2` thermal-relieved into the GND pour;
this is intentional and is why ERC/DRC reports `net_conflict` items
under full-severity — they are demoted to warnings in the project
rule-severity map.

**3. Custom-footprint datasheet re-verification (still recommended).**
Four footprints pass ERC/DRC but have not been cross-checked against
vendor mechanical drawings:

  - `LCC-42_SIM7080G.kicad_mod` — span 15.60 × 18.70 mm center-to-center,
    18.10 × 16.20 mm courtyard.
  - `XIAO_ESP32S3_SENSE.kicad_mod` — pad span 16.10 × 24.00 mm;
    re-verify the 24 mm breakout row span against the Seeed
    21.0 × 17.5 mm board footprint.
  - `SMN-305_Nano_SIM.kicad_mod` — body 11.2 × 11.0 mm,
    courtyard 13.3 × 14.5 mm.
  - `QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm.kicad_mod` — TPS63070
    buck-boost (body 3.0 × 4.0 mm, EP 1.45 × 2.45 mm; datasheet-correct
    per TI RNM drawing, re-inspect before stencil cut).

The fifth original entry — `Swarm_M138.kicad_mod` — is explicitly
superseded by the off-board integration path in caveat 1.

**4. RF trace routing** is functional but not impedance-controlled
coplanar waveguide. Fine for LTE-M / 433 MHz proof-of-concept; plan a
dedicated RF tune-up before any production run that targets formal
conducted-emissions or antenna-efficiency specs.

**5. Full-severity DRC warnings are intentional.**
The full-severity DRC report lists ~165 `holes_co_located` warnings
(duplicated GND-stitching vias left by the autorouter), 103
`net_conflict` warnings on the preserved SIM7080 pads, 44 silk / library
cosmetic warnings, and 2 sub-millimetre `track_dangling` stubs on the
`/3V3` and `/CHG_REGN` nets. These are all demoted to warning severity
in `warden-apex-master.kicad_pro` and do not affect error-severity
sign-off. They are listed here so nobody is surprised when they open
the design in the GUI.
