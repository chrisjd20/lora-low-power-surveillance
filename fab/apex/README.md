# Warden Apex (Tier 3 — LoRa + BLE/WiFi + Cellular + Satellite)



## Files

- `gerbers/` — 4-layer PCB gerbers + drill (identical across all tiers)
- `warden-apex-master.d356` — IPC-D-356 netlist for bare-board test
- `warden-apex-master-pos.csv` — KiCad P&P, DNP refs filtered out
- `warden-apex-master-pos-jlc.csv` — JLCPCB P&P format
- `warden-apex-master-bom-kicad.csv` — KiCad native BOM
- `warden-apex-master-bom-jlc.csv` — JLCPCB assembly BOM
- `warden-apex-master-bom-full.csv` — enriched BOM with MPN/LCSC/descr

## DNP (0 parts)

*none — fully populated*

## JLCPCB upload

1. Upload `gerbers/` as a zip in the PCB manufacturing form.
2. Enable SMT assembly and upload:
   - P&P: `warden-apex-master-pos-jlc.csv`
   - BOM: `warden-apex-master-bom-jlc.csv`
3. Fill any missing LCSC numbers using the `bom-full.csv` supplement.
