# Warden Drone (Tier 1 — LoRa + BLE/WiFi)

Tier 1. LoRa + BLE/WiFi only. Distributed sensor node. ~$35.
No cellular, no satellite, no modem rail, no I2C-UART bridge.
Default solder-jumper config: JP1 OPEN (no modem rail), JP2 OPEN
(SIM holder disconnected), JP3 / JP4 irrelevant (both modems DNP).

## Files

- `gerbers/` — 4-layer PCB gerbers + drill (identical across all tiers)
- `warden-apex-master.d356` — IPC-D-356 netlist for bare-board test
- `warden-apex-master-pos.csv` — KiCad P&P, DNP refs filtered out
- `warden-apex-master-pos-jlc.csv` — JLCPCB P&P format
- `warden-apex-master-bom-kicad.csv` — KiCad native BOM
- `warden-apex-master-bom-jlc.csv` — JLCPCB assembly BOM
- `warden-apex-master-bom-full.csv` — enriched BOM with MPN/LCSC/descr

## DNP (24 parts)

IC1, Card1, J1, D1, U5, C29, U3, U6, X1, C23, C24, C25, C26, C30, C31, Q2, Q3, R16, R18, R19, JP1, JP2, JP3, JP4

## JLCPCB upload

1. Upload `gerbers/` as a zip in the PCB manufacturing form.
2. Enable SMT assembly and upload:
   - P&P: `warden-apex-master-pos-jlc.csv`
   - BOM: `warden-apex-master-bom-jlc.csv`
3. Fill any missing LCSC numbers using the `bom-full.csv` supplement.
