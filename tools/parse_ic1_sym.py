import sys
data = open('hardware/warden-apex-master/warden-apex-master.kicad_sch').read()

start = data.find('(symbol "SIM7080G"')
if start == -1:
    print("SIM7080G not found")
    sys.exit()

depth = 0
for i in range(start, len(data)):
    if data[i] == '(':
        depth += 1
    elif data[i] == ')':
        depth -= 1
        if depth == 0:
            sym_end = i + 1
            break
else:
    sym_end = len(data)

sym_block = data[start:sym_end]

import re
pins = re.findall(r'\(pin ([a-z_]+) [a-z]+ \(at [^\)]+\) \(length [^\)]+\) \(name "([^"]+)" \(effects [^\)]+\)\) \(number "([^"]+)"', sym_block)
print(pins)
