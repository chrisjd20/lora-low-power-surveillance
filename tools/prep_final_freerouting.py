import pcbnew
import os

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# 1. Delete C35, C36, U7 (from previous translator chain)
for ref in ['C35', 'C36', 'U7', 'R25_old']:
    fp = board.FindFootprintByReference(ref)
    if fp:
        board.RemoveNative(fp)

# 2. Move C15 to X=14.0, Y=78.5 (Left of IC2)
c15 = board.FindFootprintByReference('C15')
if c15:
    c15.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(14.0), pcbnew.FromMM(78.5)))

# 3. Assign dummy nets to unconnected pads to prevent vias being routed through them
dummy_counter = 0
for fp in board.GetFootprints():
    for p in fp.Pads():
        if not p.GetNetname() or p.GetNetname() == '<no net>':
            dummy_netname = f"/DUMMY_NET_FIN_{dummy_counter}"
            dummy_counter += 1
            net = pcbnew.NETINFO_ITEM(board, dummy_netname)
            board.Add(net)
            p.SetNet(net)

# 4. Remove all tracks so we can re-route cleanly
for t in list(board.GetTracks()):
    board.RemoveNative(t)

# 5. Export DSN
os.makedirs('build', exist_ok=True)
pcbnew.ExportSpecctraDSN(board, 'build/warden.dsn')

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print("Prepared final freerouting DSN.")
