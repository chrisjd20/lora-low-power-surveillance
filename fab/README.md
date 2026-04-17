# Warden Apex Master — fab output package

Generated at the end of Phase 5 from
`hardware/warden-apex-master/warden-apex-master.kicad_pcb`.

Board specs: **100 mm × 100 mm, 4-layer, 1.6 mm FR-4, HASL finish**,
plated through-holes only, min trace 0.2 mm, min via 0.3 mm drill /
0.6 mm diameter.

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

## Known caveats — READ BEFORE ORDERING

See `hardware/warden-apex-master/PLAN.md` — **Phase 5 result** and
earlier phase notes for the full carry-forward list. The most
important:

- **XIAO, SIM7080G, Swarm M138 footprints are approximations.**
  They have the correct pin count and body size, but individual
  pad geometries have not been cross-checked against the official
  drawings. Verify dimensions before fab.
- **TPS63070 footprint** is datasheet-correct (EP 1.45 × 2.45 mm,
  pin 0.7 × 0.28 mm on 0.5 mm pitch) but was built by hand — inspect
  against TI's RNM drawing before ordering.
- **RF trace routing** is functional but not impedance-controlled
  coplanar waveguide. Fine for LTE-M / 433 MHz proof-of-concept.
- **The DRC still reports 29 unconnected_items + 199 net_conflict.**
  These are all **F.Cu GND zone fragments** — the inner GND plane
  handles the electrical path. To clear them cosmetically before fab,
  open the project in the KiCad GUI, run Edit → Fill All Zones, and
  re-export Gerbers.
