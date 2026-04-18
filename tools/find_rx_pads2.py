import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

for p in board.GetPads():
    if p.GetNetname() == '/UART1_RX':
        pos = p.GetPosition()
        for fp in board.GetFootprints():
            if fp.GetBoundingBox().Contains(pos):
                ref = fp.GetReference()
                break
        print(f"Pad {p.GetName()} of {ref} at {pcbnew.ToMM(pos.x)}, {pcbnew.ToMM(pos.y)}")
