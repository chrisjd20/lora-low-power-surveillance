import re

data = open('hardware/warden-apex-master/warden-apex-master.kicad_sch').read()
symbols = re.findall(r'\(symbol \(lib_id "warden-custom:SIM7080G"\).*?\(property "Reference" "IC1".*?\)', data, re.DOTALL)
if not symbols:
    # Maybe the entire file is on one line and dotall doesn't match lazily due to backtracking?
    # Let's just find the index of IC1 and search backwards.
    pass

import sys
start = data.find('(property "Reference" "IC1"')
if start == -1:
    print("IC1 not found")
    sys.exit()

sym_start = data.rfind('(symbol (lib_id', 0, start)
if sym_start == -1:
    print("symbol block not found")
    sys.exit()

# rudimentary paren matching
depth = 0
for i in range(sym_start, len(data)):
    if data[i] == '(':
        depth += 1
    elif data[i] == ')':
        depth -= 1
        if depth == 0:
            sym_end = i + 1
            break
else:
    sym_end = len(data)

ic1_block = data[sym_start:sym_end]
pins = re.findall(r'\(pin "[^"]+" "([^"]+)"', ic1_block)
print(sorted(pins))
