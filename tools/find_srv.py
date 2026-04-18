import re
try:
    with open('/usr/share/kicad/symbols/Power_Protection.kicad_sym') as f:
        lib = f.read()
    m = re.search(r'\(symbol "SRV05-4"(.*?)\n  \)', lib, re.DOTALL)
    if m:
        for pm in re.finditer(r'\(pin.*?\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(number "([^"]+)"', m.group(1), re.DOTALL):
            print(pm.group(4), float(pm.group(1)), float(pm.group(2)), float(pm.group(3)))
except Exception as e:
    print(e)
