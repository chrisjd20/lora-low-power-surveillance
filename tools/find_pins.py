import re

with open('hardware/warden-apex-master/symbols/warden-custom.kicad_sym') as f:
    lib = f.read()

def get_pin_coords(sym_name, pin_num):
    m = re.search(r'\(symbol "' + sym_name + r'".*?\(pin\b[^\)]+\bline\s+\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(number "' + pin_num + r'".*?\)', lib, re.DOTALL)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    return None

print("SIM7080G Pin 39 (PWRKEY):", get_pin_coords("SIM7080G_1_1", "39"))
# U1 is XIAO_ESP32S3_Sense
for i in range(1, 25):
    coords = get_pin_coords("XIAO_ESP32S3_Sense_1_1", str(i))
    if coords:
        print(f"XIAO Pin {i}: {coords}")
