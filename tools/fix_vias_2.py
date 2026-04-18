import pcbnew
board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

def pad_poly(pad):
    return pad.GetEffectivePolygon()

to_remove = []
for track in board.GetTracks():
    if isinstance(track, pcbnew.PCB_VIA):
        via_pos = track.GetPosition()
        via_radius = track.GetWidth() // 2
        # check overlap with any pad that is not GND
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() != track.GetNetname() and pad.GetNetname() != '/GND':
                    # very rough check: distance from via center to pad center < via_radius + pad_size/2
                    dist = (via_pos - pad.GetPosition()).EuclideanNorm()
                    if dist < via_radius + max(pad.GetSize().x, pad.GetSize().y)//2:
                        to_remove.append(track)
                        break
            if track in to_remove:
                break

for v in to_remove:
    board.RemoveNative(v)

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print(f"Removed {len(to_remove)} offending vias.")
