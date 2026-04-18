import re

def get_pins(sym_name):
    with open('hardware/warden-apex-master/symbols/warden-custom.kicad_sym') as f:
        lib = f.read()
    
    m = re.search(r'\(symbol "' + sym_name + r'"(.*?)\n  \)', lib, re.DOTALL)
    if not m: return {}
    
    pins = {}
    for pm in re.finditer(r'\(pin.*?\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(number "([^"]+)"', m.group(1), re.DOTALL):
        pins[pm.group(4)] = (float(pm.group(1)), float(pm.group(2)), float(pm.group(3)))
    return pins

print("SIM7080G pins:")
sim_pins = get_pins("SIM7080G_1_1")
for p in ['39', '41', '42']:
    print(p, sim_pins.get(p))

print("XIAO pins:")
xiao_pins = get_pins("XIAO_ESP32S3_Sense_1_1")
for p in ['1', '2', '3', '4', '5', '6', '7', '8', '21']:
    print(p, xiao_pins.get(p))
