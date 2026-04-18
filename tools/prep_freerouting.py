import pcbnew
import os

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# 1. Assign dummy nets to unconnected pads so they are exported to DSN
dummy_counter = 0
for fp in board.GetFootprints():
    for p in fp.Pads():
        if not p.GetNetname() or p.GetNetname() == '<no net>':
            dummy_netname = f"/DUMMY_NET_{dummy_counter}"
            dummy_counter += 1
            net = pcbnew.NETINFO_ITEM(board, dummy_netname)
            board.Add(net)
            p.SetNet(net)

# 2. Delete ALL tracks and vias so Freerouting starts fresh
for t in list(board.GetTracks()):
    board.RemoveNative(t)

# 3. Export DSN
os.makedirs('build', exist_ok=True)
pcbnew.ExportSpecctraDSN(board, 'build/warden.dsn')

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print(f"Exported DSN with {dummy_counter} dummy nets.")
