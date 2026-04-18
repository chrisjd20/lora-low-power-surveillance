import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print("Net /UART1_RX_1V8 exists:", board.FindNet('/UART1_RX_1V8') is not None)
print("Pad 2 of Q5 net:", board.FindFootprintByReference('Q5').FindPadByNumber('2').GetNetname())
