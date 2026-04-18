import pcbnew
import math

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

def add_footprint(ref, lib, fp_name, pos, net_map):
    fp = pcbnew.FootprintLoad(lib, fp_name)
    if not fp: return None
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos[0]), pcbnew.FromMM(pos[1])))
    if len(pos) > 2:
        fp.SetOrientation(pcbnew.EDA_ANGLE(pos[2], pcbnew.DEGREES_T))
    for p in fp.Pads():
        net_name = net_map.get(p.GetName())
        if net_name:
            net = board.FindNet(net_name)
            if not net:
                net = pcbnew.NETINFO_ITEM(board, net_name)
                board.Add(net)
            p.SetNet(net)
    board.AddNative(fp)
    return fp

for nn in ['/UART1_TX_1V8', '/UART1_RX_1V8', '/MODEM_PWRKEY_N']:
    if not board.FindNet(nn):
        board.Add(pcbnew.NETINFO_ITEM(board, nn))

# Place them at safe spot X=70..80, Y=75..80
add_footprint('Q4', '/usr/share/kicad/footprints/Package_TO_SOT_SMD.pretty', 'SOT-23', (70, 75), {'1': '/VDD_EXT', '2': '/UART1_TX_1V8', '3': '/UART1_TX'})
add_footprint('Q5', '/usr/share/kicad/footprints/Package_TO_SOT_SMD.pretty', 'SOT-23', (75, 75), {'1': '/VDD_EXT', '2': '/UART1_RX_1V8', '3': '/UART1_RX'})
add_footprint('R25', '/usr/share/kicad/footprints/Resistor_SMD.pretty', 'R_0805_2012Metric', (70, 80), {'1': '/UART1_TX_1V8', '2': '/VDD_EXT'})
add_footprint('R26', '/usr/share/kicad/footprints/Resistor_SMD.pretty', 'R_0805_2012Metric', (73, 80), {'1': '/UART1_TX', '2': '/3V3'})
add_footprint('R27', '/usr/share/kicad/footprints/Resistor_SMD.pretty', 'R_0805_2012Metric', (76, 80), {'1': '/UART1_RX_1V8', '2': '/VDD_EXT'})
add_footprint('R28', '/usr/share/kicad/footprints/Resistor_SMD.pretty', 'R_0805_2012Metric', (79, 80), {'1': '/UART1_RX', '2': '/3V3'})

# Bulk caps
board.FindFootprintByReference('C31').Value().SetText('220uF')
board.FindFootprintByReference('C34').Value().SetText('220uF')

# U5 channels to SIM lines
u5 = board.FindFootprintByReference('U5')
u5.FindPadByNumber('1').SetNet(board.FindNet('/SIM_VDD'))
u5.FindPadByNumber('3').SetNet(board.FindNet('/SIM_DATA'))
u5.FindPadByNumber('4').SetNet(board.FindNet('/SIM_CLK'))
u5.FindPadByNumber('6').SetNet(board.FindNet('/SIM_RST'))

# PWRKEY path
ic1 = board.FindFootprintByReference('IC1')
ic1.FindPadByNumber('39').SetNet(board.FindNet('/MODEM_PWRKEY_N'))
board.FindFootprintByReference('U1').FindPadByNumber('21').SetNet(board.FindNet('/MODEM_PWRKEY_N'))

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print("PCB patched.")
