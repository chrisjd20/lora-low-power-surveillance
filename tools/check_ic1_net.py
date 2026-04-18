import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
p1 = board.FindFootprintByReference('IC1').FindPadByNumber('1')
print(f"IC1 Pad 1 is: {p1.GetNetname()}")
