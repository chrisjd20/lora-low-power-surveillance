import re

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch') as f:
    sch = f.read()

m = re.search(r'\(symbol "Power_Protection:SRV05-4"(.*?)\n    \)', sch, re.DOTALL)
if m:
    for pm in re.finditer(r'\(pin.*?\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(number "([^"]+)"', m.group(1), re.DOTALL):
        print(pm.group(4), float(pm.group(1)), float(pm.group(2)), float(pm.group(3)))
else:
    print("Symbol not found in cache")
