# Warden Apex Master — Expansion I/O (Phase 18)

Two ports live on the **west edge** of the board, stacked between the
PIR header (`H1`) and the BQ24650 input-cap column (`C15`/`C27`). Both
are reachable through the enclosure window designed for the PIR
ribbon; you can exit with a 14-conductor ribbon or a standard Qwiic
cable without re-routing.

All expansion I/O goes through the I/O expander `U4` (MCP23017, I²C
address `0x20`), so firmware drives loads with a simple register write
and no main-MCU GPIOs are consumed.

Validation refresh (2026-04-18): expansion circuitry remains unchanged after
the final fabrication recovery and still sits on a board that passes
`kicad-cli sch erc --severity-error` and
`kicad-cli pcb drc --schematic-parity --severity-error` with zero errors.

```
West edge (X = 0 mm)
 │
 │  H1   PIR header      Y=34.0 mm   (existing)
 │
 │  J5   Qwiic (4-pin)   Y=48.0 mm   NEW
 │  J4   2×7 header      Y=54.5-69.7 NEW
 │  F1   500 mA polyfuse Y=56.0 mm   NEW (on EXP_VBAT)
 │  R24  10 k pull-up    Y=68.0 mm   NEW (on EXP_IRQ)
 │
 │  C15  BQ24650 Cin     Y=74.0 mm   (existing)
```

## J4 — 2×7 GPIO expansion header (2.54 mm pitch)

Plug-and-play for daughterboards (external lights, relays, extra
sensors) or a 14-way ribbon cable out of the enclosure.

| Pin | Net        | Source          | Notes                                      |
|-----|------------|-----------------|--------------------------------------------|
|  1  | `3V3`      | TPS63070 rail   | 500 mA budget (polyfuse not on this pin)   |
|  2  | `EXP_VBAT` | via F1          | LiFePO₄ ≈3.2 V, fused 500 mA               |
|  3  | `GND`      | plane           |                                            |
|  4  | `I2C_SDA`  | shared bus      | U4 / J5 / daughterboard I²C                |
|  5  | `I2C_SCL`  | shared bus      | U4 / J5 / daughterboard I²C                |
|  6  | `GND`      | plane           |                                            |
|  7  | `EXP_GP1`  | U4 GPA1         | MCP23017 GPIO, push-pull or input          |
|  8  | `EXP_GP2`  | U4 GPA2         |                                            |
|  9  | `EXP_GP3`  | U4 GPA3         |                                            |
| 10  | `EXP_GP4`  | U4 GPA4         |                                            |
| 11  | `EXP_GP5`  | U4 GPA5         |                                            |
| 12  | `EXP_GP6`  | U4 GPA6         |                                            |
| 13  | `GND`      | plane           |                                            |
| 14  | `EXP_IRQ`  | U4 INTA via R24 | Active-low interrupt shared with firmware  |

### Typical uses

- **Motion-triggered external light.** Drive an off-board MOSFET via
  `EXP_GP1..6`; switch a 12 V LED strip from an external supply. Pull
  up to the load's own rail; don't source more than a few mA from
  the MCP23017 directly.
- **Add-on environmental sensors.** Any I²C sensor module that runs
  from 3V3 — SCD41 (CO₂), BME280 (T/RH/P), VEML7700 (lux) — wires to
  J4 pins 1, 3, 4, 5 (3V3 / GND / SDA / SCL). Use J5 if you want the
  0.1 inch-less cable footprint.
- **Low-current actuators.** Small relay coils or opto-isolators that
  pull <200 mA can run from `EXP_VBAT` (pin 2) through F1.

## J5 — Qwiic / STEMMA QT connector (JST-SH, 1 mm pitch)

Standard 4-pin Qwiic pinout for plug-and-play I²C sensors; shares the
same SDA/SCL bus as `J4` and the MCP23017.

| Pin | Net       | Notes                       |
|-----|-----------|-----------------------------|
|  1  | `GND`     |                             |
|  2  | `3V3`     | shared with J4, same budget |
|  3  | `I2C_SDA` | shared                      |
|  4  | `I2C_SCL` | shared                      |

## Power budget

| Rail          | Source         | Daughterboard budget |
|---------------|----------------|----------------------|
| `3V3` (J4.1 / J5.2) | TPS63070 buck-boost | ~500 mA steady (battery-limited) |
| `EXP_VBAT` (J4.2)   | LiFePO₄ via F1       | 500 mA polyfuse trip |

Heavy loads (solenoids, motors, LED strips) should use their own
power source and only tap `EXP_GP*` pins for switching. Keep
continuous `EXP_VBAT` draw below ~300 mA to leave headroom for the
modems.

## Firmware sketch (Arduino / ESP-IDF)

```cpp
#include <Adafruit_MCP23X17.h>
Adafruit_MCP23X17 mcp;

void setup() {
    Wire.begin(47, 48);     // XIAO ESP32-S3 default I²C pins
    mcp.begin_I2C(0x20);
    // GPA0 is reserved for the PIR shim; GPA1..6 are on J4 pins 7..12
    for (uint8_t p = 1; p <= 6; ++p) mcp.pinMode(p, OUTPUT);
    mcp.digitalWrite(1, HIGH);   // EXP_GP1 drives external light MOSFET
}
```

## DRC / validation

- Phase 18 final DRC: **0 violations, 0 unconnected pads**.
- ERC remains at **0 errors** (9 cosmetic `lib_symbol_mismatch`
  warnings on cached symbols — the same set as pre-Phase 18).
- All three assembly tiers (`drone`, `cell_master`, `apex`) populate
  J4 / J5 / F1 / R24 by default — expansion I/O is available on every
  tier without re-spinning fabrication.
