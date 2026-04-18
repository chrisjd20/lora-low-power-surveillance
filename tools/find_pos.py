import re

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch') as f:
    data = f.read()

# We need to find the placement (at X Y R) of IC1 and U1
ic1_match = re.search(r'\(symbol \(lib_id "warden-custom:SIM7080G"\).*?\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(property "Reference" "IC1"', data)
if ic1_match:
    ic1_x, ic1_y, ic1_r = map(float, ic1_match.groups())
    print(f"IC1 at: {ic1_x}, {ic1_y}, rot: {ic1_r}")

u1_match = re.search(r'\(symbol \(lib_id "warden-custom:XIAO_ESP32S3_Sense"\).*?\(at ([-\d\.]+) ([-\d\.]+) ([-\d\.]+)\).*?\(property "Reference" "U1"', data)
if u1_match:
    u1_x, u1_y, u1_r = map(float, u1_match.groups())
    print(f"U1 at: {u1_x}, {u1_y}, rot: {u1_r}")

# To connect a net, we just add a (label "/MODEM_PWRKEY_N" (at X Y R) (effects (font (size 1.27 1.27)) (justify left bottom)))
# We must find the exact X,Y where the pin lands.
