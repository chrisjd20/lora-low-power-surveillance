import pcbnew
import os

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# Nets that were modified and need their tracks ripped up so Freerouting routes them cleanly
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

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
os.makedirs('build', exist_ok=True)
pcbnew.ExportSpecctraDSN(board, 'build/warden.dsn')
print(f"Removed {len(to_remove)} tracks/vias from modified nets and exported DSN.")
