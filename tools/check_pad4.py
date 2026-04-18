import pcbnew

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
ic1 = board.FindFootprintByReference('IC1')
pad4 = ic1.FindPadByNumber('4')
print("Pad 4 netname:", pad4.GetNetname())
