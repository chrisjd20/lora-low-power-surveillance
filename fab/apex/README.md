# Warden Apex (Tier 3 — LoRa + BLE/WiFi + Cellular + Satellite)

Tier 3. LoRa + BLE/WiFi + Cellular + Satellite. Full global fallback. ~$95.
Default solder-jumper config: JP1 OPEN (Q2 gates modem rail under firmware),
JP2 CLOSED (SIM VCC connected), JP3 CLOSED (SC16→Swarm TX),
JP4 CLOSED (Swarm→SC16 RX).

The Swarm M138 (U3) and its dedicated decouplers (C30, C31) are DNP on
every tier (including Apex) because the committed `warden_custom:Swarm_M138`
land pattern does not match the real 51.0 x 30.0 mm mPCIe module. The
on-board SC16IS740 I2C-UART bridge (U6), crystal (X1, C23, C24), U6
decouplers (C25, C26), and the Swarm UART jumpers (JP3/JP4) ARE populated
on Apex and expose the Swarm interface on the expansion header for an
external Swarm breakout daughterboard.

## Files

- `gerbers/` — 4-layer PCB gerbers + drill (identical across all tiers)
- `warden-apex-master.d356` — IPC-D-356 netlist for bare-board test
- `warden-apex-master-pos.csv` — KiCad P&P, DNP refs filtered out
- `warden-apex-master-pos-jlc.csv` — JLCPCB P&P format
- `warden-apex-master-bom-kicad.csv` — KiCad native BOM
- `warden-apex-master-bom-jlc.csv` — JLCPCB assembly BOM
- `warden-apex-master-bom-full.csv` — enriched BOM with MPN/LCSC/descr

## DNP (3 parts)

U3, C30, C31

## JLCPCB upload

1. Upload `gerbers/` as a zip in the PCB manufacturing form.
2. Enable SMT assembly and upload:
   - P&P: `warden-apex-master-pos-jlc.csv`
   - BOM: `warden-apex-master-bom-jlc.csv`
3. Fill any missing LCSC numbers using the `bom-full.csv` supplement.
