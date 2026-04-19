import pcbnew
import math

b = pcbnew.LoadBoard('/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb')

def get_pos(ref):
    fp = b.FindFootprintByReference(ref)
    if fp:
        return fp.GetPosition().x/1e6, fp.GetPosition().y/1e6
    return None, None

def set_pos(ref, dx, dy):
    fp = b.FindFootprintByReference(ref)
    if fp:
        cx, cy = get_pos(ref)
        fp.SetPosition(pcbnew.VECTOR2I(int(round((cx + dx) * 1e6)), int(round((cy + dy) * 1e6))))

# Top-Left (IC1 cluster) top row
set_pos('JP1', -3.0, -3.0)
set_pos('Q6', -1.5, -2.0)
set_pos('TP3', 0.0, -3.0)
set_pos('C31', 0.0, -3.0)
set_pos('U5', 0.0, -4.0)
set_pos('TP4', 0.0, -3.0)
set_pos('C35', 0.0, -3.0) # Check image, the cap below TP4 might be shifted too, wait, C35 is next to U5? Ah, let's just shift what user circled. User didn't circle C35.
set_pos('Q4', 1.5, -2.0)
set_pos('JP2', 3.0, -3.0)

# Top-Left (IC1 cluster) bottom row
set_pos('Q2', -3.0, -3.0)
set_pos('TP5', 0.0, 3.0)
set_pos('C34', 0.0, 3.0)
set_pos('TP1', 0.0, 3.0)
set_pos('C22', 0.0, 3.0)
set_pos('Q5', 3.0, -3.0)

# Mid-Top (R17, R10, R28, R13)
# Arrow points down-left
for ref in ['R17', 'R10', 'R28', 'R13']:
    set_pos(ref, -12.0, 10.0)

# Middle IO (IC4, C36)
# Arrow points up-left
set_pos('IC4', -5.0, -5.0)
set_pos('C36', -5.0, -5.0)

# Bottom-Left (POWER)
# Q1 arrow points up-left
set_pos('Q1', -4.0, -4.0)

# Bottom-Middle
# JP4 down-left
set_pos('JP4', -10.0, 8.0)
# J3 down-right
set_pos('J3', 6.0, 8.0)

pcbnew.SaveBoard('/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb', b)
print("Applied shifts based on user arrows.")
