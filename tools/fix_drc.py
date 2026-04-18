import pcbnew
import re

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

with open('hardware/warden-apex-master/drc-report.txt', 'r') as f:
    report = f.read()

# We look for lines like: @(46.9500 mm, 31.9500 mm): Via [/GND] on F.Cu - B.Cu
# Or @(43.4000 mm, 33.6154 mm): Track [/UART1_RX] on F.Cu, length 0.9154 mm
to_remove_coords = []
for line in report.splitlines():
    if line.startswith('    @('):
        m = re.search(r'@\(([\d\.]+) mm, ([\d\.]+) mm\): (Via|Track)', line)
        if m:
            x, y, typ = float(m.group(1)), float(m.group(2)), m.group(3)
            to_remove_coords.append((x, y, typ))

to_remove = []
for track in board.GetTracks():
    pos = track.GetPosition()
    tx, ty = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
    typ = 'Via' if isinstance(track, pcbnew.PCB_VIA) else 'Track'
    
    # check if any coord matches
    for rx, ry, rtyp in to_remove_coords:
        if rtyp == typ and abs(tx - rx) < 0.01 and abs(ty - ry) < 0.01:
            to_remove.append(track)

print(f"Removing {len(to_remove)} offending tracks/vias.")
for t in to_remove:
    board.RemoveNative(t)

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
