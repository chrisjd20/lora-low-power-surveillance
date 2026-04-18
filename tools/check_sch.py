import re
with open('hardware/warden-apex-master/warden-apex-master.kicad_sch', 'r') as f:
    data = f.read()

ic1_match = re.search(r'\(symbol \(lib_id "warden-custom:SIM7080G"\) \(at [^\)]+\).*?\(property "Reference" "IC1".*?\n\s*\)', data, re.DOTALL | re.MULTILINE)
if ic1_match:
    print("Found IC1 in schematic")
    pins = re.findall(r'\(pin "[^"]+" "(.*?)"', ic1_match.group(0))
    print(sorted(pins))
else:
    print("IC1 not found")
