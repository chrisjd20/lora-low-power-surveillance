import pcbnew

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

dummy_counter = 0
for fp in board.GetFootprints():
    for p in fp.Pads():
        if not p.GetNetname() or p.GetNetname() == '<no net>':
            dummy_netname = f"/DUMMY_NET_{dummy_counter}"
            dummy_counter += 1
            net = pcbnew.NETINFO_ITEM(board, dummy_netname)
            board.Add(net)
            p.SetNet(net)

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print(f"Assigned {dummy_counter} dummy nets to unconnected pads.")
