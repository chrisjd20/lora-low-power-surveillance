#!/usr/bin/env python3
"""
Generate `create_symbol` argument blobs for the five custom symbols that
live in `hardware/warden-apex-master/symbols/warden-custom.kicad_sym`.

Pin names match the Flux EDIF interface (extracted in research). Pin
numbers are assigned here so each pin is unambiguous. Pin TYPES are
`passive` across the board to keep ERC happy for plug-on modules (these
aren't ICs where we should assert input/output drive direction).

Output: one JSON document per symbol at
    hardware/warden-apex-master/symbols/_generated_{name}.json
The agent then reads each blob and passes it to the KiCAD MCP
`create_symbol` tool verbatim.
"""
from __future__ import annotations
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT  = ROOT / "hardware" / "warden-apex-master" / "symbols"
LIB  = OUT / "warden-custom.kicad_sym"

PITCH = 2.54
PIN_LEN = 2.54


def two_column(pins, pin_type="passive"):
    """
    Arrange `pins` (list of name strings) in two columns inside an
    auto-sized rectangle. Returns (pins_json, rect_json).

    Left column gets pins 1..ceil(N/2); right column gets the rest.
    Body height is chosen so pins align on a 2.54 mm grid; body width is
    fixed (20.32 mm) unless overridden.
    """
    N = len(pins)
    left_n = (N + 1) // 2
    right_n = N - left_n
    rows = max(left_n, right_n)
    body_half_h = PITCH * (rows // 2 + 1)
    body_half_w = 10.16

    def y_for(index_in_col, total):
        top = PITCH * (total - 1) / 2
        return top - index_in_col * PITCH

    pins_json = []
    # left side: angle=180 (wire extends leftwards away from body)
    for i in range(left_n):
        pins_json.append({
            "name": pins[i],
            "number": str(i + 1),
            "type": pin_type,
            "at": {"x": -body_half_w - PIN_LEN, "y": y_for(i, left_n), "angle": 0},
            "length": PIN_LEN,
        })
    # right side: angle=0 (wire extends rightwards); KiCad convention: angle describes wire direction out of body — here the wire endpoint is to the right of body, so angle=180 means the pin BODY is to the right of endpoint? Let me follow the docs:
    # From create_symbol: angle = direction wire extends FROM body.
    #   0   = right  (endpoint at body_right + length; symbol body on left)
    #   180 = left   (endpoint at body_left  - length; symbol body on right)
    # So left-side pins have angle=0 (wire extends RIGHT into body view... wait)
    # Actually re-read: "Pins on left side: at.x = body_left - length, angle=0 (wire goes right)".
    # That means for LEFT-side pins: endpoint is to the LEFT of body, wire
    # visually extends rightward toward body. angle=0.
    # For RIGHT-side pins: endpoint is to the RIGHT of body, wire extends
    # leftward toward body. angle=180.
    for i in range(left_n):
        pins_json[i]["at"]["angle"] = 0  # already set above but make explicit
    for i in range(right_n):
        pins_json.append({
            "name": pins[left_n + i],
            "number": str(left_n + i + 1),
            "type": pin_type,
            "at": {"x": body_half_w + PIN_LEN, "y": y_for(i, right_n), "angle": 180},
            "length": PIN_LEN,
        })

    rect = {
        "x1": -body_half_w,
        "y1": -body_half_h,
        "x2":  body_half_w,
        "y2":  body_half_h,
        "width": 0.254,
        "fill": "background",
    }
    return pins_json, rect


# ---------- XIAO ESP32-S3 Sense (24 pins) ----------------------------------
XIAO_PINS = [
    "TOUCH1_GPIO1_A0_D0",
    "TOUCH2_GPIO2_A1_D1",
    "TOUCH3_GPIO3_A2_D2",
    "TOUCH4_GPIO4_A3_D3",
    "TOUCH5_GPIO5_SDA_A4_D4",
    "TOUCH6_GPIO6_SCL_A5_D5",
    "GPIO43_TX_D6",
    "D7_RX_GPIO44",
    "D8_A8_SCK_GPIO7_TOUCH7",
    "D9_A9_MISO_GPIO8_TOUCH8",
    "D10_A10_MOSI_GPIO9_TOUCH9",
    "3V3",
    "GND",
    "5V",
    "BAT+",
    "BAT-",
    "MTCK",
    "MTDI",
    "MTD0",
    "MTMS",
    "EN",
    "D+",
    "D-",
    "GND",
]
xiao_pins, xiao_rect = two_column(XIAO_PINS)

xiao = {
    "libraryPath": str(LIB),
    "name": "XIAO_ESP32S3_Sense",
    "referencePrefix": "U",
    "description": "Seeed Studio XIAO ESP32-S3 Sense (MPN 113991115). Pin names match Flux EDIF for direct netlist mapping.",
    "keywords": "XIAO ESP32-S3 Sense Seeed module WiFi BLE camera",
    "datasheet": "https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/",
    "footprint": "Module:XIAO_ESP32S3_SENSE",
    "pins": xiao_pins,
    "rectangles": [xiao_rect],
    "overwrite": True,
}

# ---------- SIM7080G (77 pins) ---------------------------------------------
SIM7080G_PINS = [
    "RF_ANT", "GND_12", "GND_11", "GND_6", "PCM_DIN", "NC_1", "GND_3",
    "UART1_CTS", "GND_5", "NC_4", "SIM_VDD", "GPIO3", "PCM_DOUT",
    "UART1_DCD", "NC_5", "GND_8", "SIM_DATA", "GND_13", "UART3_RXD",
    "~SPI_MOSI", "GND_4", "GND_14", "NC_9", "GND_22", "UART3_TXD",
    "SPI_MISO", "GND_16", "GND_15", "I2C_SCL", "PWRKEY", "NETLIGHT",
    "GND_9", "PCM_SYNC", "UART1_RXD", "STATUS", "UART2_TXD", "GND_2",
    "NC_8", "UART1_RTS", "UART1_TXD", "GPIO4", "USB_DP", "USB_DM",
    "GND_21", "GND_10", "GNSS_ANT", "NC_6", "UART2_RXD", "SIM_CLK",
    "GND_23", "NC_3", "ANT_CONTROL1", "USB_VBUS", "SPI_CLK",
    "~USB_BOOT", "GND_19", "GND_1", "GPIO2", "ADC", "UART1_RI",
    "I2C_SDA", "ANT_CONTROL0", "SPI_CS", "SIM_RST", "GND_17", "GND_20",
    "GND_7", "VBAT_1", "VDD_EXT", "NC_7", "NC_2", "GND_18", "GPIO1",
    "UART1_DTR", "PCM_CLK", "GPIO5", "VBAT_2",
]
sim_pins, sim_rect = two_column(SIM7080G_PINS)
sim7080g = {
    "libraryPath": str(LIB),
    "name": "SIM7080G",
    "referencePrefix": "U",
    "description": "SIMCom SIM7080G LTE-M/NB-IoT cellular modem.",
    "keywords": "SIM7080G LTE NB-IoT cellular modem SIMCom",
    "datasheet": "https://www.simcom.com/product/SIM7080G.html",
    "footprint": "Module:LCC-42_SIM7080G",
    "pins": sim_pins,
    "rectangles": [sim_rect],
    "overwrite": True,
}

# ---------- TPS63070 (15 pins) ---------------------------------------------
TPS_PINS = [
    "VOUT_1", "PGND", "PS/S", "VSEL", "L1", "L2", "VIN_2", "VIN_1",
    "EN", "FB2", "FB", "PG", "VAUX", "VOUT_2", "GND",
]
tps_pins, tps_rect = two_column(TPS_PINS)
tps = {
    "libraryPath": str(LIB),
    "name": "TPS63070",
    "referencePrefix": "U",
    "description": "Texas Instruments TPS63070 4.5 V–12 V buck-boost converter, 2 A.",
    "keywords": "TPS63070 buck-boost DCDC regulator TI",
    "datasheet": "https://www.ti.com/lit/ds/symlink/tps63070.pdf",
    "footprint": "Package_DFN_QFN:QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm",
    "pins": tps_pins,
    "rectangles": [tps_rect],
    "overwrite": True,
}

# ---------- Swarm M138 (60 pins) -------------------------------------------
M138_PINS = [
    "VDD_39", "NC_19", "NC_25", "NC_1", "NC_10", "NC_5", "NC_6",
    "GND_15", "GND_29", "NC_33", "NC_31", "UART_TX", "GND_18", "SHIELD",
    "GND_37", "SHIELD_2", "SHIELD_3", "GND_21", "SHIELD_4", "VDD_2",
    "NC_36", "SHIELD_5", "GND_27", "GND_40", "GND_35", "NC_32",
    "GND_50", "UART_RX", "NC_14", "NC_16", "NC_48", "NC_44", "GND_26",
    "SHIELD_6", "VDD_52", "GND_43", "GPIO1", "NC_30", "VDD_41", "NC_7",
    "GND_4", "NC_20", "SHIELD_7", "T/R_OUTPUT", "NC_28", "SHIELD_8",
    "NC_8", "GND_9", "NC_46", "NC_51", "NC_12", "NC_45", "NC_3",
    "NC_49", "NC_47", "NC_23", "GND_34", "NC_38", "NC_24", "NC_22",
]
# Note: the EDIF has 7 duplicate "SHIELD" pins. KiCad requires unique pin
# names; we rename them SHIELD / SHIELD_2..SHIELD_7 for the symbol, and
# account for that in the pin-name translator.
m138_pins, m138_rect = two_column(M138_PINS)
m138 = {
    "libraryPath": str(LIB),
    "name": "Swarm_M138",
    "referencePrefix": "U",
    "description": "Swarm M138 satellite modem (VHF, UART-attached).",
    "keywords": "Swarm M138 satellite modem VHF",
    "datasheet": "https://swarm.space/wp-content/uploads/2023/08/Swarm-M138-Product-Manual.pdf",
    "footprint": "Module:Swarm_M138",
    "pins": m138_pins,
    "rectangles": [m138_rect],
    "overwrite": True,
}

# ---------- SMN-305 Nano-SIM socket (10 pins incl. 3 EP shield tabs) ------
SMN305_PINS = ["VCC", "CLK", "RST", "I/O", "GND", "Vpp", "EP", "EP_2", "EP_3", "EP_4"]
smn_pins, smn_rect = two_column(SMN305_PINS)
smn = {
    "libraryPath": str(LIB),
    "name": "SMN-305_SIM",
    "referencePrefix": "J",
    "description": "XUNPU SMN-305 nano-SIM socket (push-push).",
    "keywords": "SIM nano socket SMN-305",
    "datasheet": "https://lcsc.com/product-detail/Connector-Card-Sockets_XUNPU-SMN-305_C266890.html",
    "footprint": "Connector_Card:Nano_SIM_JAE_SF72S006VBDR2000",
    "pins": smn_pins,
    "rectangles": [smn_rect],
    "overwrite": True,
}

SYMBOLS = {
    "XIAO_ESP32S3_Sense": xiao,
    "SIM7080G": sim7080g,
    "TPS63070": tps,
    "Swarm_M138": m138,
    "SMN-305_SIM": smn,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, args in SYMBOLS.items():
        p = OUT / f"_generated_{name}.json"
        p.write_text(json.dumps(args, indent=2))
        print(f"wrote {p.relative_to(ROOT)}  ({len(args['pins'])} pins)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
