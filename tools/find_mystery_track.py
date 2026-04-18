import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
for t in board.GetTracks():
    pos = t.GetPosition()
    if abs(pcbnew.ToMM(pos.x) - 43.4) < 0.5 and abs(pcbnew.ToMM(pos.y) - 33.6) < 0.5:
        print(f"Track near 43.4, 33.6 is on net: {t.GetNetname()}")
