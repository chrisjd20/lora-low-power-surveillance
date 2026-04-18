# Warden Apex Master — Assembly Variants

One board. Three builds. Same gerbers for all tiers.

## Overview

| Tier | Name | Radios | Est. BOM | DNP parts |
|---|---|---|---:|---:|
| 1 | **Drone** | LoRa + BLE/WiFi | ~$35 | 21 |
| 2 | **Cell Master** | LoRa + BLE/WiFi + Cellular (SIM7080G) | ~$55 | 7 |
| 3 | **Apex** | LoRa + BLE/WiFi + Cellular + Satellite (Swarm M138) | ~$95 | 0 |

All three tiers use the same PCB — identical gerbers, drill, IPC-D-356.
Only the BOM and pick-and-place file differ. See [`tools/variants.yaml`](../../tools/variants.yaml)
for the authoritative DNP lists.

Latest validation refresh (2026-04-18):

- `kicad-cli sch erc --severity-error` -> 0 errors
- `kicad-cli pcb drc --schematic-parity --severity-error` -> 0 violations, 0 unconnected, 0 parity issues
- `python3 tools/phase12_variants.py` re-generated all `v3` tier packages under `fab/`
- KiCad-native BOMs are now tier-filtered too (`fab/<tier>/warden-apex-master-bom-kicad.csv`)
- UART1 level-shifter chain (`U7`, `C35`, `C36`, `R25`) is populated on all three tiers

---

## Stuffing tables

Legend:  ● = populate, ○ = DNP (leave empty), ⚫ = solder-bridge closed, ⚪ = solder-bridge open.

### Power / MCU / LoRa (always populated)

| Block | Refdes | Drone | Cell Master | Apex |
|---|---|:---:|:---:|:---:|
| XIAO ESP32-S3 Sense | U1 | ● | ● | ● |
| LoRa Ra-01 | U2 | ● | ● | ● |
| LoRa U.FL | J2 | ● | ● | ● |
| LoRa TVS | D2 | ● | ● | ● |
| MAX98357A audio | IC4 | ● | ● | ● |
| Speaker header | J3 | ● | ● | ● |
| MCP23017 I²C expander | U4 | ● | ● | ● |
| BQ24650 charger | IC2 | ● | ● | ● |
| TPS63070 buck-boost | IC3 | ● | ● | ● |
| LiFePO4 charger inductor | L1 | ● | ● | ● |
| Buck inductor L3 + MOSFET Q1 + RSNS | L3, Q1, RSNS | ● | ● | ● |
| PIR header | H1 | ● | ● | ● |
| MAX98357A ~SD pull-up (100 kΩ) | R23 | ● | ● | ● |
| IC2 V\_IN decoupler (100 nF) | C27 | ● | ● | ● |
| Ra-01 3V3 decoupler (100 nF) | C28 | ● | ● | ● |
| IC3 3V3 bulk (10 µF) | C32 | ● | ● | ● |
| **Phase 19 — charger feedback dividers (all tiers)** |         |     |     |     |
| BQ24650 VFB upper leg (7.15 kΩ, LiFePO4 3.6 V float) | R20 | ● | ● | ● |
| BQ24650 TS  upper leg (10 kΩ, TS safe-window bias) | R21 | ● | ● | ● |
| BQ24650 MPPSET upper leg (100 kΩ, 6 V panel V_IN(REG)=5.25 V) | R22 | ● | ● | ● |
| IC3 VAUX decoupler upsized (100 nF → 1 µF) | C5 | ● | ● | ● |

### Cellular modem block

| Refdes | Drone | Cell Master | Apex |
|---|:---:|:---:|:---:|
| IC1 SIM7080G | ○ | ● | ● |
| Card1 Nano-SIM holder | ○ | ● | ● |
| J1 cellular U.FL | ○ | ● | ● |
| D1 cellular TVS | ○ | ● | ● |
| U5 SRV05-4 TVS array | ○ | ● | ● |
| C29 IC1 SIM\_VDD\_EXT (1.8 V) decoupler (B.Cu) | ○ | ● | ● |
| **JP_SIM_VCC (JP2)** | ⚪ (open) | ⚫ (closed) | ⚫ (closed) |

### Satellite modem block

| Refdes | Drone | Cell Master | Apex |
|---|:---:|:---:|:---:|
| U3 Swarm M138 | ○ | ○ | ● |
| U6 SC16IS740 I²C-UART bridge | ○ | ○ | ● |
| X1 14.7456 MHz crystal | ○ | ○ | ● |
| C23 / C24 crystal load caps | ○ | ○ | ● |
| C25 / C26 U6 decouplers | ○ | ○ | ● |
| R18 / R19 UART2 pull-downs (Swarm/U6 path) | ○ | ○ | ● |
| C30 Swarm V\_BAT HF decoupler | ○ | ○ | ● |
| C31 Swarm V\_BAT bulk (47 µF / 1206) | ○ | ○ | ● |
| **JP_SAT_UART_TX (JP3)** | ⚪ | ⚪ | ⚫ |
| **JP_SAT_UART_RX (JP4)** | ⚪ | ⚪ | ⚫ |

### Modem power rail (Q2/Q3/R16 load switch)

| Refdes | Drone | Cell Master | Apex |
|---|:---:|:---:|:---:|
| Q2 P-MOSFET AO3401A | ○ | ● | ● |
| Q3 N-MOSFET 2N7002 | ○ | ● | ● |
| R16 100 kΩ gate pull-up | ○ | ● | ● |
| R17 UART1\_RX pull-down (always populated) | ● | ● | ● |
| U7 + C35/C36 + R25 UART1 level-shifter chain | ● | ● | ● |
| **JP_MODEM_RAIL (JP1)** | ⚪ | ⚪ | ⚪ |

The modem rail is gated by **MODEM_EN** (MCP23017 GPB0). Firmware drives
it HIGH after detecting a modem. JP1 exists as a bypass option if a
builder prefers a hard-wired rail and wants to omit Q2/Q3 entirely — close
JP1 and DNP Q2/Q3/R16. Default is firmware-controlled gating.

> **Phase 20 note:** `UART1` is dedicated to the cellular modem and
> routes through XIAO pins `GPIO40` (U1.19, TX) and `GPIO41` (U1.18, RX).
> These pins previously carried the boot-strap JTAG signals; Phase 20
> explicitly repurposes them and removes their `no_connect` flags.
> `R17` is the `UART1_RX` pull-down that keeps U1.18 quiet when the SIM
> isn't driving. It is populated on every tier because it is benign on
> Drone and required on Cell Master / Apex.
> Phase 23 adds `U7` (`TXS0102`) with `C35/C36/R25` so UART1 is translated
> between XIAO 3V3 I/O and SIM7080G 1V8 I/O on every tier.

### Expansion I/O (always populated)

All three tiers ship with the expansion port populated so daughter-boards
remain plug-and-play across the lineup. Full pinout, power budget, and
firmware snippets live in [`EXPANSION.md`](EXPANSION.md).

| Refdes | Purpose | Drone | Cell Master | Apex |
|---|---|:---:|:---:|:---:|
| J4 | 2×7 GPIO expansion header (2.54 mm) | ● | ● | ● |
| J5 | Qwiic / STEMMA QT I²C connector (JST-SH) | ● | ● | ● |
| F1 | 500 mA polyfuse on `EXP_VBAT` (J4 pin 2) | ● | ● | ● |
| R24 | 10 kΩ pull-up on `EXP_IRQ` (J4 pin 14) | ● | ● | ● |

The header exposes 8 MCP23017 GPIOs + shared I²C (SDA/SCL, 3V3, GND,
fused VBAT, IRQ). None of the XIAO's native pins are consumed — any
daughter-board can be added without firmware rework on the main MCU.

---

## Solder-jumper map

All four jumpers use footprint `Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm`
placed on the front copper.

| Ref | Name | Default | Purpose |
|---|---|:---:|---|
| JP1 | JP_MODEM_RAIL | OPEN | Short to bypass Q_MODEM (use only if Q2/Q3/R16 DNP). |
| JP2 | JP_SIM_VCC   | CLOSED when SIM holder populated | Breaks SIM_VDD between SIM7080G and Nano-SIM cage. Open on Drone to prevent leakage through Card1's detect pin. |
| JP3 | JP_SAT_UART_TX | CLOSED when Swarm populated | Routes SC16IS740 TX → Swarm RX. |
| JP4 | JP_SAT_UART_RX | CLOSED when Swarm populated | Routes Swarm TX → SC16IS740 RX. |

---

## Firmware auto-detect

The ESP32-S3 probes the hardware at boot:

```c
bool has_io_expander  = i2c_ack(0x20);   // MCP23017 on I2C
bool has_sc16is740    = i2c_ack(0x48);   // SC16IS740 I2C-UART bridge
bool has_cellular     = probe_at_cmd(UART1, "AT", 300);     // SIM7080G on UART1
bool has_satellite    = has_sc16is740 &&
                        probe_at_cmd_over_bridge("$CS", 500);  // Swarm via U6

if (has_cellular) gpio_set_level(MODEM_EN, 1);  // via MCP GPB0

const char* tier = "Drone";
if (has_cellular && has_satellite) tier = "Apex";
else if (has_cellular)             tier = "Cell Master";
ESP_LOGI("boot", "Warden Tier: %s", tier);
```

---

## JLCPCB upload instructions (per tier)

1. **Gerbers** (same for all tiers): upload `fab/<tier>/gerbers/` zipped,
   or use `fab/warden-<tier>-v3.zip`.
2. **SMT assembly** for that tier:
   - P&P: `warden-apex-master-pos-jlc.csv`
   - BOM: `warden-apex-master-bom-jlc.csv`
3. Fill any missing LCSC part numbers using `warden-apex-master-bom-full.csv`.

---

## Pre-fab QA checklist

Before hitting the JLCPCB "Submit" button:

- [ ] Open the `.kicad_pcb` in KiCad 9 GUI. Edit → Fill All Zones.
- [ ] Verify rendered top/bottom images look clean (no silk on pads, no
      exposed unrouted copper). Current reference renders live in
      `fab/renders/pcb-top.png` / `pcb-bottom.png`.
- [ ] Confirm `kicad-cli pcb drc --schematic-parity --severity-error`
      reports **0 violations, 0 unconnected pads, 0 footprint errors**.
      The Phase 21 fabrication-readiness sweep closed every remaining
      open net (`/CELL_RF`, `/SIM_*`, `/UART1_*`, `/UART2_*`,
      `/MODEM_VBAT_SW`), the starved-thermal on `J4.6/GND`, and the
      mis-placed `/VBAT_SYS` via; Phase 22 then widened 346 power-rail
      segments to their `POWER_HI`/`POWER_3V3`/`CHARGER_SW` netclass
      targets and added a 171-via F.Cu↔In1.Cu↔B.Cu ground-stitch grid.
      No manual routing is required before fab. Full-severity DRC
      still emits cosmetic silk-overlap and `lib_footprint_mismatch`
      warnings on `C33`/`C34`/`U3`; these are intentional and safe.
- [ ] Verify the three custom footprints (XIAO, SIM7080G, Swarm M138)
      against the vendor mechanical drawing one more time.
- [ ] Verify the expansion port headers (J4 2×7 + J5 Qwiic) are placed
      on the west edge with the keepout/silk arrow for pin 1 visible,
      and that F1 + R24 silk references stay outside the pad areas.
- [ ] Order the Drone v2 first as a proof-run, then Cell Master and Apex
      from the same gerbers.
- [ ] **Phase 19 tuning**: R20/R21/R22 values assume LiFePO4 3.6 V float
      and a 6 V (~5 V MPP) solar panel. If using a different chemistry
      or panel, re-tune per the BQ24650 datasheet:
      V_FLOAT = 2.1 * (1 + R20/R1) with R1 = 10 kΩ;
      V_IN(REG) = 5 * 2.1 * R2 / (R22 + R2) with R2 = 100 kΩ.
      No routing change required — only component value swaps.
- [ ] TS pin (R3 + R21) biases charger to "room temp" with fixed
      resistors. Replace R3 (10 kΩ) with a 10 kΩ NTC thermistor in
      thermal contact with the battery pack to enable real
      over-temperature charge protection (optional).
