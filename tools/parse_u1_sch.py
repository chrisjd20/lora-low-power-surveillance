import re
import sys

data = open('hardware/warden-apex-master/warden-apex-master.kicad_sch').read()

# Find the instance for U1
start = data.find('(property "Reference" "U1"')
if start == -1:
    print("U1 not found")
    sys.exit()

sym_start = data.rfind('(symbol (lib_id', 0, start)
if sym_start == -1:
    print("symbol block not found")
    sys.exit()

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

u1_block = data[sym_start:sym_end]
# Extract all pins connected
pins = re.findall(r'\(pin "[^"]+" "([^"]+)"', u1_block)
print(sorted(pins))

# Also extract no_connect pins to see what is free
ncs = re.findall(r'\(no_connect \(at ([^\)]+)\)\)', data)
print(f"NC pins count: {len(ncs)}")
