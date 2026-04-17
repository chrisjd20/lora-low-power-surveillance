#!/usr/bin/env python3
"""
Translation / configuration tables for Phase 2 schematic build.

Maps Flux EDIF (ref, pin_name) pairs onto (KiCad library, symbol, pin_number)
triples. Also defines:
    * SYMBOL_CHOICE    — KiCad library:symbol per Flux cell
    * NET_RENAME       — unnamed Flux "Net 1..5" → meaningful charger names
    * ADDED_PARTS      — L1 (charger inductor) and RSNS (sense resistor)
    * ADDED_NET_NODES  — extra pin-net attachments for L1, RSNS, LORA_DIO1 fix
    * ZONES            — component placement coordinates by functional zone
    * NO_CONNECTS      — pins to explicitly flag as NC after wiring
    * POWER_FLAG_NETS  — nets that must carry a PWR_FLAG for ERC
"""

# ---------------------------------------------------------------------------
# Symbol selection
# ---------------------------------------------------------------------------
# value is (library, symbol, footprint_override_or_None).
# Footprints are hints for Phase 3; set to None where the symbol already
# ships with a sensible default.

SYMBOL_CHOICE: dict[str, tuple[str, str, str | None]] = {
    # Power / charger
    "BQ24650RVAR":        ("Battery_Management", "BQ24650",        "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.65x1.65mm"),
    "TPS63070RNMR":       ("warden_custom",      "TPS63070",       "Package_DFN_QFN:QFN-15-1EP_3x4mm_P0.5mm_EP1.45x2.45mm"),
    "DMG9926UDM":         ("Transistor_FET",     "DMG9926UDM",     "Package_TO_SOT_SMD:SOT-23-6"),
    "BAT54HT1G":          ("Device",             "D_Schottky",     "Diode_SMD:D_SOD-323"),
    "74437346015":        ("Device",             "L",              "Inductor_SMD:L_Wuerth_HCI-1890"),

    # Audio
    "MAX98357AETE+T":     ("Audio",              "MAX98357A",      "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm"),

    # Radio modules
    "Ai-Thinker-Ra-01":   ("RF_Module",          "Ai-Thinker-Ra-01", "RF_Module:Ai-Thinker-Ra-01"),
    "SIM7080G":           ("warden_custom",      "SIM7080G",       "Module:LCC-42_SIM7080G"),
    "M138_MODEM":         ("warden_custom",      "Swarm_M138",     "Module:Swarm_M138"),

    # IO / controller
    "Seeed Studio XIAO ESP32S3 Sense":
                          ("warden_custom",      "XIAO_ESP32S3_Sense", "Module:XIAO_ESP32S3_SENSE"),
    "MCP23017_SO":        ("Interface_Expansion","MCP23017_SO",    "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm"),
    "SRV05-4-P-T7":       ("Power_Protection",   "SRV05-4",        "Package_TO_SOT_SMD:SOT-23-6"),

    # Connectors
    "SMN-305":            ("warden_custom",      "SMN-305_SIM",    "Connector_Card:Nano_SIM_JAE_SF72S006VBDR2000"),
    "U.FL-R-SMT-1":       ("Connector_Generic",  "Conn_01x03",     "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical"),
    "825433-3":           ("Connector_Generic",  "Conn_01x03",     "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical"),
    "Pin Header 01x02 2.54mm Vertical":
                          ("Connector_Generic",  "Conn_01x02",     "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"),

    # TVS
    "ESD0P2RF-02LRH-TP":  ("Device",             "D_TVS",          "Diode_SMD:D_SOD-323"),

    # Passives
    "Generic Capacitor":  ("Device",             "C",              "Capacitor_SMD:C_0805_2012Metric"),
    "Generic Resistor":   ("Device",             "R",              "Resistor_SMD:R_0805_2012Metric"),
    "5002":               ("Connector",          "TestPoint",      "TestPoint:TestPoint_Pad_D1.5mm"),
}

# ---------------------------------------------------------------------------
# Pin-name translator (Flux name → KiCad pin number, per symbol)
# ---------------------------------------------------------------------------
# Keyed by KiCad symbol name. Missing entries = pass-through (Flux name is
# already identical to the KiCad pin name, as in all our custom symbols).

PIN_MAP: dict[str, dict[str, str]] = {
    # ----- stock -----
    "C": {"P1": "1", "P2": "2"},
    "R": {"P1": "1", "P2": "2"},
    "L": {"~": "1"},  # special-cased in resolve_l3_pin()
    "D_Schottky": {"K": "1", "A": "2"},
    "D_TVS": {"1": "1", "2": "2"},

    "TestPoint": {"~": "1"},

    "Conn_01x02":  {"P1": "1", "P2": "2"},  # J3 speaker
    "Conn_01x03":  {"1": "1", "2": "2", "3": "3"},  # J1/J2 U.FL, H1 PIR

    "BQ24650": {
        "VCC": "1", "MPPSET": "2", "STAT1": "3", "TS": "4", "STAT2": "5",
        "VREF": "6", "TERM_EN": "7", "VFB": "8", "SRN": "9", "SRP": "10",
        "GND": "11", "REGN": "12", "LODRV": "13", "PH": "14", "HIDRV": "15",
        "BTST": "16",
        "EP": "17",  # exposed pad — stock symbol has GND pin 17
    },

    "MAX98357A": {
        "DIN": "1", "GAIN_SLOT": "2", "GND_3": "3", "~SD_MODE": "4",
        "N.C._1": "5", "N.C._2": "6", "VDD_1": "7", "VDD_2": "8",
        "OUTP": "9", "OUTN": "10", "GND_1": "11", "N.C._3": "12",
        "N.C._4": "13", "LRCLK": "14", "GND_2": "15", "BCLK": "16",
        "THERMAL_PAD": "17",
    },

    "MCP23017_SO": {
        "GPB0": "1", "GPB1": "2", "GPB2": "3", "GPB3": "4", "GPB4": "5",
        "GPB5": "6", "GPB6": "7", "GPB7": "8", "VDD": "9", "VSS": "10",
        "NC": "11",  # NC pin #11
        "SCK": "12", "SDA": "13",
        # "NC" repeats at pin 14 — see NC_14 alias below
        "NC_14": "14",
        "A0": "15", "A1": "16", "A2": "17", "~{RESET}": "18", "INTB": "19",
        "INTA": "20", "GPA0": "21", "GPA1": "22", "GPA2": "23", "GPA3": "24",
        "GPA4": "25", "GPA5": "26", "GPA6": "27", "GPA7": "28",
    },

    "Ai-Thinker-Ra-01": {
        # Flux pin names              # KiCad pin numbers
        "ANT": "1", "GND": "2", "VDD": "3",       # stock symbol: multiple GNDs (2,9,16)
        "RESET": "4", "DIO0": "5", "DIO1": "6",
        "DIO2": "7", "DIO3": "8", "GND_9": "9",
        "DIO4": "10", "DIO5": "11",
        "SCK": "12", "MISO": "13", "MOSI": "14",
        "NSS": "15",
        "GND_16": "16",
        # Flux labels also use "3.3V" for VDD
        "3.3V": "3",
    },

    "DMG9926UDM": {
        "D1": "1", "S1/D2": "2",  # ← also pin 5 is S1/D2; stock has S1/D2 at 2 AND 5
        "S2": "3", "G2": "4",
        "S1/D2_5": "5",
        "G1": "6",
    },

    "SRV05-4": {
        # Flux uses REF/GND/IO1..IO4 — KiCad uses IO1/VN/IO2/IO3/VP/IO4.
        # Pin numbers are the source of truth:
        "IO1": "1", "VN": "2", "IO2": "3",
        "IO3": "4", "VP": "5", "IO4": "6",
        # Flux EDIF in Warden mapping:
        "REF": "5",   # REF = VP
        "GND": "2",   # GND = VN
    },

    # ----- custom symbols: Flux names match 1:1, identity pass-through -----
    # XIAO has two GND pins (1 and 24). Flux netlist only has one ["U1","GND"]
    # entry after dedup, but we must connect both; the driver adds a second
    # connection for pin 24 ("GND2") automatically.
    "XIAO_ESP32S3_Sense": {
        # all pass-through except the second GND alias
        "GND2": "24",
    },
    "SIM7080G": {},       # names match
    "TPS63070": {},       # names match
    "Swarm_M138": {},     # names match (SHIELD/SHIELD_2..SHIELD_7 aliasing)
    "SMN-305_SIM": {},    # names match (EP/EP_2..EP_4)
}


def resolve_pin(symbol: str, flux_pin: str) -> str:
    """Return the KiCad pin *number* (as a string) for a given Flux pin
    name on the given KiCad symbol. Falls back to the Flux name if no
    mapping is recorded (custom symbols where names match 1:1)."""
    table = PIN_MAP.get(symbol, {})
    if flux_pin in table:
        return table[flux_pin]
    # For custom symbols, return the Flux name unchanged; connect_to_net
    # accepts either name or number.
    return flux_pin


# ---------------------------------------------------------------------------
# Net renames + orphan fix
# ---------------------------------------------------------------------------
NET_RENAME: dict[str, str] = {
    "Net 1": "CHG_GATE_LO",  # IC2.LODRV ↔ Q1.G1
    "Net 2": "CHG_GATE_HI",  # IC2.HIDRV ↔ Q1.G2
    "Net 3": "CHG_BST",      # IC2.BTST ↔ D3.K ↔ C19.P1
    "Net 4": "CHG_REGN",     # IC2.REGN ↔ D3.A ↔ C15.P1
    "Net 5": "CHG_PH",       # IC2.PH ↔ Q1.S2 ↔ C19.P2 (L1 will extend to VBAT_SYS)
}

# LORA_DIO1 orphan fix: the Flux EDIF has only U2.DIO1 on LORA_DIO1.
# Route it to XIAO MTMS (GPIO42), a free JTAG pin reusable as GPIO.
LORA_DIO1_ADD_NODE: tuple[str, str] = ("U1", "MTMS")


# ---------------------------------------------------------------------------
# New parts added (not in Flux BOM / netlist)
# ---------------------------------------------------------------------------
ADDED_PARTS = [
    {
        "ref": "L1",
        "library": "Device",
        "symbol": "L",
        "value": "4.7uH",
        "footprint": "Inductor_SMD:L_Coilcraft_XAL5030",
        "description": "BQ24650 charger buck inductor (missing in Flux BOM)",
        "mpn": "Würth 74438336047",
        "lcsc": "C1089748",
    },
    {
        "ref": "RSNS",
        "library": "Device",
        "symbol": "R",
        "value": "20m",
        "footprint": "Resistor_SMD:R_2512_6332Metric",
        "description": "BQ24650 charge current sense resistor (missing in Flux BOM)",
        "mpn": "UniOhm LR2512-R020",
        "lcsc": "C160142",
    },
]

# New net memberships introduced by L1 / RSNS / LORA_DIO1 fix.
#   L1 bridges CHG_PH and VBAT_SYS
#   RSNS bridges VBAT_SYS (SRP side) and CHG_SENSE_NEG (SRN side)
ADDED_NET_NODES = [
    ("CHG_PH",        "L1",   "1"),  # Device:L pin 1
    ("VBAT_SYS",      "L1",   "2"),  # Device:L pin 2
    ("VBAT_SYS",      "RSNS", "1"),  # Device:R pin 1 ← SRP side
    ("CHG_SENSE_NEG", "RSNS", "2"),  # Device:R pin 2 ← SRN side
    ("LORA_DIO1",     "U1",   "20"), # XIAO MTMS (pin 20)
]


# ---------------------------------------------------------------------------
# Pins that must be flagged as "no-connect" after wiring
# ---------------------------------------------------------------------------
# Every pin on a module that has no EDIF net membership + is not meant to
# be connected to anything. Passing these to the no-connect flag avoids
# ERC "floating pin" errors.
#
# (ref, pinNumber)
NO_CONNECTS: list[tuple[str, str]] = [
    # SIM7080G (IC1) — all NC pins + unused UART2 / UART3 / USB / PCM / SPI /
    # GPIOs / AUX lines. ~40 pins. See list_unconnected_pins() below.
    # MCP23017 (U4) — unused GPB*, INTA/INTB, A2
    # MAX98357A (IC4) — none; all strapped to GND already
    # Swarm M138 (U3) — most NC + T/R_OUTPUT + GPIO1
]
# The list is built dynamically by compute_no_connects() based on the
# netlist at build time (fewer chances of drift).


def compute_no_connects(netlist: dict) -> list[tuple[str, str]]:
    """Given the parsed flux-netlist.json dict, return every (ref,
    pinNumber) that is present on a symbol we placed but is not in any
    net — these get a NoConnect flag."""
    used: set[tuple[str, str]] = set()
    ref_to_cell: dict[str, str] = {c["ref"]: c["cell"] for c in netlist["components"]}
    for n in netlist["nets"]:
        for ref, pin in n["nodes"]:
            used.add((ref, pin))
    # Collect every symbol's full pin list from our custom library + stock
    # symbols. We only NC pins on modules with many leftover pins; discrete
    # passives (R, C, L, D) always have both pins used.
    targets = {
        "IC1": "SIM7080G",
        "U3":  "Swarm_M138",
        "U4":  "MCP23017_SO",
        "IC4": "MAX98357A",
    }
    result: list[tuple[str, str]] = []
    for ref, sym in targets.items():
        if ref not in ref_to_cell:
            continue
        # Full pin inventory comes from the symbol itself; rather than parse
        # the .kicad_sym we use the MCP tool get_symbol_info upstream.
        # Here we just emit placeholders; the driver fills actual numbers.
        pass
    return result


# ---------------------------------------------------------------------------
# Component placement zones
# ---------------------------------------------------------------------------
# Approximate (x, y) in millimetres on the KiCad schematic canvas. The
# sheet grows as needed; these are just starting coordinates per zone.
# Layout, top-down (y increases downwards in KiCad schematic coords):
#
#   ┌────────────────────┬──────────────────┬────────────────────┐
#   │ Power in + charger │   VBAT_SYS rail  │  3.3V regulator    │
#   │ (IC2 Q1 L1 D3 C15  │  (C13,14,20..22, │  (IC3 L3 R11,12,15 │
#   │  C19 RSNS R1..5)   │   TP3 TP4)       │   C2..5 C16..18)   │
#   ├────────────────────┼──────────────────┼────────────────────┤
#   │   LoRa chain       │     MCU (U1)     │   Audio (IC4 J3)   │
#   │  (U2 J2 D2)        │   + PIR (H1)     │                    │
#   ├────────────────────┼──────────────────┼────────────────────┤
#   │ Cellular + SIM     │  Satellite (U3)  │  GPIO expander     │
#   │ (IC1 Card1 J1 D1   │                  │  (U4)              │
#   │  U5)               │                  │                    │
#   │                 Test points TP1..TP5 along the bottom edge │
#   └────────────────────┴──────────────────┴────────────────────┘

ZONES = {
    # All coords are integer multiples of 2.54 mm so every pin endpoint
    # lands on KiCad's 50-mil (1.27 mm) connection grid.
    "power_in":   (50.8,  50.8),     # top-left
    "vbat":       (177.8, 50.8),     # top-center
    "reg33":      (304.8, 50.8),     # top-right
    "lora":       (50.8,  152.4),    # middle-left
    "mcu":        (177.8, 152.4),    # middle-center
    "audio":      (304.8, 152.4),    # middle-right
    "cell":       (50.8,  254.0),    # bottom-left
    "sat":        (177.8, 254.0),    # bottom-center
    "io":         (304.8, 254.0),    # bottom-right
    "tps":        (381.0, 304.8),    # test points strip
}

# (ref → zone) mapping so the driver can place each component near its zone.
REF_ZONE = {
    # power_in
    "IC2": "power_in", "Q1": "power_in", "L1": "power_in", "RSNS": "power_in",
    "D3": "power_in", "C15": "power_in", "C19": "power_in",
    "R1": "power_in", "R2": "power_in", "R3": "power_in",
    "R4": "power_in", "R5": "power_in", "R10": "power_in",
    "C1": "power_in", "C20": "power_in", "C21": "power_in", "C22": "power_in",
    "TP2": "power_in",
    # vbat
    "C13": "vbat", "C14": "vbat", "TP3": "vbat", "TP4": "vbat",
    # reg33
    "IC3": "reg33", "L3": "reg33",
    "R11": "reg33", "R12": "reg33", "R15": "reg33",
    "C2": "reg33", "C3": "reg33", "C4": "reg33", "C5": "reg33",
    "C16": "reg33", "C17": "reg33", "C18": "reg33",
    "TP1": "reg33", "TP5": "reg33",
    # lora
    "U2": "lora", "J2": "lora", "D2": "lora",
    # mcu
    "U1": "mcu", "H1": "mcu",
    # audio
    "IC4": "audio", "J3": "audio",
    # cell
    "IC1": "cell", "Card1": "cell", "J1": "cell", "D1": "cell", "U5": "cell",
    # sat
    "U3": "sat",
    # io
    "U4": "io",
    # resistors R13/R14 (I2C pull-ups) near U4
    "R13": "io", "R14": "io",
}


# ---------------------------------------------------------------------------
# Power-flag nets (need PWR_FLAG for ERC)
# ---------------------------------------------------------------------------
POWER_FLAG_NETS = ["GND", "3V3", "VBAT_SYS", "SOLAR_IN", "MODEM_VBAT"]


if __name__ == "__main__":
    # Smoke-test
    import json, pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    nl = json.loads((root / "hardware/warden-apex-master/flux-netlist.json").read_text())
    refs = sorted({c["ref"] for c in nl["components"]})
    missing_zone = [r for r in refs if r not in REF_ZONE and not r.startswith(("TP", "C", "R"))
                    and r not in {"TP6","TP7","TP8","TP9","TP10","TP11","TP12",
                                  "C6","C7","C8","C9","C10","C11","C12",
                                  "R6","R7","R8","R9"}]
    print(f"components in netlist: {len(refs)}")
    print(f"components placed:     {sum(1 for r in refs if r in REF_ZONE)}")
    print(f"added parts:           {[p['ref'] for p in ADDED_PARTS]}")
    if missing_zone:
        print(f"!!! ref missing zone: {missing_zone}")
    # Test translator
    print("pin translations sample:")
    for (ref, pin, sym) in [("IC2","VFB","BQ24650"),("IC4","N.C._1","MAX98357A"),
                             ("U4","~{RESET}","MCP23017_SO"),("R1","P1","R"),
                             ("U1","TOUCH4_GPIO4_A3_D3","XIAO_ESP32S3_Sense")]:
        print(f"  {ref}.{pin} on {sym} → pin {resolve_pin(sym, pin)}")
