data = open('hardware/warden-apex-master/symbols/warden-custom.kicad_sym').read()
start = data.find('(symbol "SIM7080G"')
import sys
if start == -1: sys.exit()
import re
sym_block = data[start:start+10000] # roughly
pins = re.findall(r'\(pin ([a-z_]+) [a-z]+ \(at [^\)]+\) \(length [^\)]+\) \(name "([^"]+)" \(effects [^\)]+\)\) \(number "([^"]+)"', sym_block)
for p in pins:
    print(p)
