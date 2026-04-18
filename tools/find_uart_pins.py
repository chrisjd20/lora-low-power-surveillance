import re

def get_pins(sym_name):
    with open('hardware/warden-apex-master/symbols/warden-custom.kicad_sym') as f:
        lib = f.read()
    
    m = re.search(r'\(symbol "' + sym_name + r'"(.*?)\n  \)', lib, re.DOTALL)
    if not m: return {}
    
    pins = {}
    for pm in re.finditer(r'\(pin.*?\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(name "([^"]+)".*?\(number "([^"]+)"', m.group(1), re.DOTALL):
        pins[pm.group(5)] = (pm.group(4), float(pm.group(1)), float(pm.group(2)), float(pm.group(3)))
    return pins

print("SIM7080G UART pins:")
sim_pins = get_pins("SIM7080G_1_1")
for num, data in sim_pins.items():
    if 'UART' in data[0] or 'VDD_EXT' in data[0] or 'PWRKEY' in data[0]:
        print(num, data)

print("XIAO UART pins:")
xiao_pins = get_pins("XIAO_ESP32S3_Sense_1_1")
for num, data in xiao_pins.items():
    if 'UART' in data[0] or 'TX' in data[0] or 'RX' in data[0] or 'GPIO40' in data[0] or 'GPIO41' in data[0]:
        print(num, data)
