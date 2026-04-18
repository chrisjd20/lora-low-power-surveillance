import pcbnew
import os

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

for ref in ['C35', 'C36', 'U7', 'R25_old']:
    fp = board.FindFootprintByReference(ref)
    if fp:
        board.RemoveNative(fp)

dummy_counter = 0
for fp in board.GetFootprints():
    for p in fp.Pads():
        if not p.GetNetname() or p.GetNetname() == '<no net>':
            dummy_netname = f"/DUMMY_NET_PRESERVE_{dummy_counter}"
            dummy_counter += 1
            net = pcbnew.NETINFO_ITEM(board, dummy_netname)
            board.Add(net)
            p.SetNet(net)

c15 = board.FindFootprintByReference('C15')
if c15:
    c15.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(14.0), pcbnew.FromMM(83.0)))

ic1 = board.FindFootprintByReference('IC1')
if ic1:
    gnd_net = board.FindNet('/GND')
    for p in ic1.Pads():
        if p.GetName().isdigit() and 43 <= int(p.GetName()) <= 77:
            p.SetNet(gnd_net)

nets_to_delete = {
    '/UART1_TX', '/UART1_RX', '/UART1_TX_1V8', '/UART1_RX_1V8',
    '/MODEM_PWRKEY_N', '/SIM_VDD', '/SIM_DATA', '/SIM_CLK', '/SIM_RST'
}

# Find all pads of new/moved components
new_pads = []
for ref in ['Q4', 'Q5', 'R25', 'R26', 'R27', 'R28', 'C15']:
    fp = board.FindFootprintByReference(ref)
    if fp:
        for p in fp.Pads():
            new_pads.append(p)

to_remove = []
for t in board.GetTracks():
    if t.GetNetname() in nets_to_delete:
        to_remove.append(t)
        continue
    
    # Check if track bounding box intersects new pads
    t_box = t.GetBoundingBox()
    for p in new_pads:
        # expand pad box slightly
        p_box = p.GetBoundingBox()
        p_box.Inflate(pcbnew.FromMM(0.5))
        if t_box.Intersects(p_box):
            to_remove.append(t)
            break

for t in to_remove:
    board.RemoveNative(t)

os.makedirs('build', exist_ok=True)
pcbnew.ExportSpecctraDSN(board, 'build/warden.dsn')
board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print(f"Prepared DSN. Removed {len(to_remove)} tracks/vias.")
