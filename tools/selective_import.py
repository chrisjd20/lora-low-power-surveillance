import pcbnew
import os

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# We must delete the exact same tracks that were routed by freerouting so we can REPLACE them
nets_to_delete = {
    '/UART1_TX', '/UART1_RX', '/UART1_TX_1V8', '/UART1_RX_1V8',
    '/MODEM_PWRKEY_N', '/SIM_VDD', '/SIM_DATA', '/SIM_CLK', '/SIM_RST'
}

to_remove = []
for t in board.GetTracks():
    if t.GetNetname() in nets_to_delete:
        to_remove.append(t)

for t in to_remove:
    board.RemoveNative(t)

# Now import the SES
import sys
sys.path.append('tools')
import phase4_import_ses
phase4_import_ses.PCB = 'hardware/warden-apex-master/warden-apex-master.kicad_pcb'
phase4_import_ses.main()

print("Selective SES import done.")
