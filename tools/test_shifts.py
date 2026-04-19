import pcbnew

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

# IC1 TOP ROW 
set_pos('JP1', -1.0, -8.0) # Move left 1 to clear Q6 
set_pos('Q6', 2.0, -8.0)   # Move right 2 to clear JP1
set_pos('C31', 0.0, -8.0) 
set_pos('TP3', 0.0, -8.0) 
set_pos('U5', 0.0, -8.0) 
set_pos('TP4', 0.0, -8.0) 
set_pos('Q4', 0.0, -8.0) 
set_pos('JP2', 0.0, -8.0) 

# IC1 BOTTOM ROW 
set_pos('Q2', -5.0, 0.0) 
set_pos('TP5', 0.0, 6.0) 
set_pos('C34', 0.0, 6.0) 
set_pos('TP1', 0.0, 6.0) 
set_pos('C22', 0.0, 6.0) 
set_pos('Q5', 8.0, 0.0) 

# L1 overlap fix
for ref in ['L1', 'RSNS', 'R3', 'R5', 'C2', 'C27', 'D3']: 
    set_pos(ref, 0.0, 6.0) # Move down 6 to make room for TP1 moving down 6

# TOP MIDDLE CLUSTER 
for ref in ['R17', 'R10', 'R28', 'R13']:
    set_pos(ref, -10.0, 10.0)

# MIDDLE IO CLUSTER 
set_pos('IC4', -5.0, -5.0)
set_pos('C36', -5.0, -5.0)
set_pos('JP4', -5.0, 5.0)
set_pos('J3', 5.0, 5.0)

# BOTTOM POWER Q1 
set_pos('Q1', -4.0, -4.0)

pcbnew.SaveBoard('/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb', b)
print("Saved final shifts.")
