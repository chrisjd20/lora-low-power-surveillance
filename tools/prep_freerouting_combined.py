import pcbnew
import os

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# Assign dummy nets to unconnected pads so Freerouting respects them
dummy_counter = 0
for fp in board.GetFootprints():
    for p in fp.Pads():
        if not p.GetNetname() or p.GetNetname() == '<no net>':
            dummy_netname = f"/DUMMY_NET_{dummy_counter}"
            dummy_counter += 1
            net = pcbnew.NETINFO_ITEM(board, dummy_netname)
            board.Add(net)
            p.SetNet(net)

# Nets to rip up
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
print("Prepared combined DSN.")
