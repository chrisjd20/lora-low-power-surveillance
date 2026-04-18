import sys
import uuid

def gen_uuid():
    return str(uuid.uuid4())

def make_label(name, x, y):
    return f'(label "{name}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))'

def make_symbol(ref, val, lib_id, footprint, x, y, uid):
    return f'''(symbol (lib_id "{lib_id}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid}")
  (property "Reference" "{ref}" (at {x} {y-2.54} 0) (effects (font (size 1.27 1.27))))
  (property "Value" "{val}" (at {x} {y+2.54} 0) (effects (font (size 1.27 1.27))))
  (property "Footprint" "{footprint}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (property "Datasheet" "~" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (instances (project "project" (path "/" (reference "{ref}") (unit 1))))
)'''

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch', 'r') as f:
    sch = f.read()

sch = sch.strip()
if sch.endswith(')'):
    sch = sch[:-1]

items = []
items.append(make_label("MODEM_PWRKEY_N", 88.9, 279.4))
items.append(make_label("MODEM_PWRKEY_N", 215.9, 158.75))

items.append(make_label("SIM_VDD", 139.7, 251.46))
items.append(make_label("SIM_DATA", 139.7, 256.54))
items.append(make_label("SIM_CLK", 165.1, 251.46))
items.append(make_label("SIM_RST", 165.1, 256.54))

items.append(make_symbol("Q4", "2N7002", "Transistor_FET:2N7002", "Package_TO_SOT_SMD:SOT-23", 300, 200, gen_uuid()))
items.append(make_label("VDD_EXT", 294.92, 200.0))
items.append(make_label("UART1_TX_1V8", 302.54, 205.08))
items.append(make_label("UART1_TX", 302.54, 194.92))

items.append(make_symbol("Q5", "2N7002", "Transistor_FET:2N7002", "Package_TO_SOT_SMD:SOT-23", 320, 200, gen_uuid()))
items.append(make_label("VDD_EXT", 314.92, 200.0))
items.append(make_label("UART1_RX_1V8", 322.54, 205.08))
items.append(make_label("UART1_RX", 322.54, 194.92))

items.append(make_symbol("R25", "10k", "Device:R", "Resistor_SMD:R_0805_2012Metric", 300, 215, gen_uuid()))
items.append(make_label("UART1_TX_1V8", 300.0, 211.19))
items.append(make_label("VDD_EXT", 300.0, 218.81))

items.append(make_symbol("R26", "10k", "Device:R", "Resistor_SMD:R_0805_2012Metric", 300, 185, gen_uuid()))
items.append(make_label("UART1_TX", 300.0, 181.19))
items.append(make_label("3V3", 300.0, 188.81))

items.append(make_symbol("R27", "10k", "Device:R", "Resistor_SMD:R_0805_2012Metric", 320, 215, gen_uuid()))
items.append(make_label("UART1_RX_1V8", 320.0, 211.19))
items.append(make_label("VDD_EXT", 320.0, 218.81))

items.append(make_symbol("R28", "10k", "Device:R", "Resistor_SMD:R_0805_2012Metric", 320, 185, gen_uuid()))
items.append(make_label("UART1_RX", 320.0, 181.19))
items.append(make_label("3V3", 320.0, 188.81))

sch += "\n  " + "\n  ".join(items) + "\n)"

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch', 'w') as f:
    f.write(sch)
    
print("Schematic patched.")
