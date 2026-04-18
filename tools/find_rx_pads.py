import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
net = board.FindNet('/UART1_RX')
if not net:
    print("Net not found")
    sys.exit()

for p in board.GetPads():
    if p.GetNetname() == '/UART1_RX':
        pos = p.GetPosition()
        print(f"Pad {p.GetName()} at {pcbnew.ToMM(pos.x)}, {pcbnew.ToMM(pos.y)}")
