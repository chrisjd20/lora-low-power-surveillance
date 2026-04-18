import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
ic1 = board.FindFootprintByReference('IC1')

# Correct the swapped nets
p1 = ic1.FindPadByNumber('1')
p1.SetNet(board.FindNet('/UART1_RX_1V8'))

p2 = ic1.FindPadByNumber('2')
p2.SetNet(board.FindNet('/UART1_TX_1V8'))

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print("PCB nets swapped.")
