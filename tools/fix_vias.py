import pcbnew

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
ic1 = board.FindFootprintByReference('IC1')
bbox = ic1.GetBoundingBox()

# Delete any via that falls inside IC1 bounding box unless it connects to a /GND pad of IC1 specifically
to_remove = []
for track in board.GetTracks():
    if isinstance(track, pcbnew.PCB_VIA):
        if bbox.Contains(track.GetPosition()):
            # check if it intersects a non-GND pad
            for pad in ic1.Pads():
                if pad.GetNetname() != '/GND' and pad.GetBoundingBox().Contains(track.GetPosition()):
                    to_remove.append(track)
                    break

for v in to_remove:
    board.RemoveNative(v)

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print(f"Removed {len(to_remove)} offending vias under IC1.")
