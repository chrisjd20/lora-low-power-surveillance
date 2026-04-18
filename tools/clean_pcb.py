import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# 1. Assign IC1 pads 43-77 to /GND
ic1 = board.FindFootprintByReference('IC1')
gnd_net = board.FindNet('/GND')
for p in ic1.Pads():
    if p.GetName().isdigit() and 43 <= int(p.GetName()) <= 77:
        p.SetNet(gnd_net)

# 2. Move Q4, Q5, R25-R28 to a safe spot.
# By inspecting the board, X=85..95, Y=65..75 is somewhat clear, or just Y=50.
# Let's put them at X=20, Y=20 which might be under U1... U1 is at 203, 152 in sch (which is 15-25 mm in PCB?)
# Let's just put them outside the board edge at X=110, Y=50 so Freerouting can route them or we don't care about courtyards for now if it's just a fix. Actually, placing them outside the edge cuts fails DRC.
# Let's put them near U1. U1 is at (17.5, 15.0).
# Let's put them at X=30, Y=20
safe_x, safe_y = 30, 20
for i, ref in enumerate(['Q4', 'Q5', 'R25', 'R26', 'R27', 'R28']):
    fp = board.FindFootprintByReference(ref)
    if fp:
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(safe_x + (i%2)*5), pcbnew.FromMM(safe_y + (i//2)*5)))

# 3. Delete all tracks of the modified nets so Freerouting can route them
nets_to_delete = {
    '/UART1_TX', '/UART1_RX', '/UART1_TX_1V8', '/UART1_RX_1V8',
    '/MODEM_PWRKEY_N', '/SIM_VDD', '/SIM_DATA', '/SIM_CLK', '/SIM_RST'
}

tracks = board.GetTracks()
to_remove = []
for t in tracks:
    if t.GetNetname() in nets_to_delete:
        to_remove.append(t)

for t in to_remove:
    board.RemoveNative(t)

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print("PCB cleaned for routing.")
