import pcbnew
import math

BOARD_PATH = '/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb'
board = pcbnew.LoadBoard(BOARD_PATH)

def mm2iu(v): return int(round(v*1e6))
def iu2mm(v): return v/1e6

def get_pos(ref):
    fp = board.FindFootprintByReference(ref)
    if fp:
        p = fp.GetPosition()
        return iu2mm(p.x), iu2mm(p.y)
    return None, None

def set_pos(ref, x, y, ang=None):
    fp = board.FindFootprintByReference(ref)
    if fp:
        fp.SetPosition(pcbnew.VECTOR2I(mm2iu(x), mm2iu(y)))
        if ang is not None:
            fp.SetOrientation(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))

# --- MANUAL SHIFTS BASED ON RED ARROWS ---
# J1: move down along left edge
j1x, j1y = get_pos('J1')
if j1x is not None: set_pos('J1', j1x, j1y + 15)

# Card1 (SMN-305): move up-right into open space
c1x, c1y = get_pos('Card1')
if c1x is not None: set_pos('Card1', c1x + 12, c1y - 12)

# J3: move down-right
j3x, j3y = get_pos('J3')
if j3x is not None: set_pos('J3', j3x + 6, j3y + 6)

# R18, R19: move down-right
r18x, r18y = get_pos('R18')
if r18x is not None: set_pos('R18', r18x + 5, r18y + 5)
r19x, r19y = get_pos('R19')
if r19x is not None: set_pos('R19', r19x + 5, r19y + 5)

# --- CLUSTER ALIGNMENT ---
# Find all small components
major_refs = {'U1', 'U2', 'U3', 'IC1', 'IC2', 'IC3', 'U4', 'U5', 'U6', 'IC4', 'Card1', 'L1', 'J1', 'J2', 'J3', 'J4', 'J5', 'H1', 'R18', 'R19', 'X1'}
fps = [fp for fp in board.GetFootprints() if not fp.GetReference().startswith('MH') and fp.GetReference() not in major_refs]

centers = {
    'IC1': get_pos('IC1'),
    'POWER': ((get_pos('IC2')[0] + get_pos('IC3')[0])/2, (get_pos('IC2')[1] + get_pos('IC3')[1])/2),
    'IO': get_pos('U4')
}

clusters = {'IC1': [], 'POWER': [], 'IO': []}
for fp in fps:
    ref = fp.GetReference()
    pos = (iu2mm(fp.GetPosition().x), iu2mm(fp.GetPosition().y))
    best_c = None
    best_d = float('inf')
    for c, cp in centers.items():
        d = math.hypot(pos[0]-cp[0], pos[1]-cp[1])
        if d < best_d:
            best_d = d
            best_c = c
    if best_d < 35:
        clusters[best_c].append(fp)

def snap_to_90(angle):
    # snap to 0, 90, 180, 270
    normalized = angle % 360
    return round(normalized / 90.0) * 90.0

def arrange_grid(cluster_fps, cx, cy, exclude_radius=14.0, grid_step=3.5):
    if not cluster_fps: return
    # Generate a grid of points
    points = []
    for dx in range(-8, 9):
        for dy in range(-8, 9):
            x = cx + dx * grid_step
            y = cy + dy * grid_step
            d = math.hypot(dx * grid_step, dy * grid_step)
            # Must be outside exclude_radius and inside board
            if d >= exclude_radius and 5 < x < 120 and 5 < y < 120:
                points.append((x, y))
    
    # Sort points by distance from center (inner to outer)
    points.sort(key=lambda p: math.hypot(p[0]-cx, p[1]-cy))
    
    # Sort footprints by their current angle around center to minimize criss-crossing
    def fp_angle(fp):
        x, y = iu2mm(fp.GetPosition().x), iu2mm(fp.GetPosition().y)
        return math.atan2(y - cy, x - cx)
        
    cluster_fps.sort(key=fp_angle)
    
    # For each footprint, place it on the most appropriate grid point
    # We match them by angle. Sort points by angle as well for the first N points
    n = len(cluster_fps)
    used_points = points[:n]
    used_points.sort(key=lambda p: math.atan2(p[1]-cy, p[0]-cx))
    
    for i, fp in enumerate(cluster_fps):
        px, py = used_points[i]
        ang = fp.GetOrientation().AsDegrees()
        # snap angle to 0 or 90 depending on which way looks cleaner, or just keep current snapped to 90
        new_ang = snap_to_90(ang)
        fp.SetPosition(pcbnew.VECTOR2I(mm2iu(px), mm2iu(py)))
        fp.SetOrientation(pcbnew.EDA_ANGLE(new_ang, pcbnew.DEGREES_T))

# Arrange IC1 cluster
ic1_x, ic1y = centers['IC1']
arrange_grid(clusters['IC1'], ic1_x, ic1y, exclude_radius=15.0, grid_step=3.0)

# Arrange POWER cluster (IC2, IC3, L1)
px, py = centers['POWER']
arrange_grid(clusters['POWER'], px, py, exclude_radius=14.0, grid_step=3.0)

# Arrange IO cluster (U4)
iox, ioy = centers['IO']
arrange_grid(clusters['IO'], iox, ioy, exclude_radius=12.0, grid_step=3.0)

# Ensure L1 is aligned cleanly in POWER cluster
l1_fp = board.FindFootprintByReference('L1')
if l1_fp:
    # L1 is currently at 10.95, 79.5. Let's snap it to grid
    set_pos('L1', 11.0, 79.5)

zf=pcbnew.ZONE_FILLER(board)
zf.Fill(list(board.Zones()))
pcbnew.SaveBoard(BOARD_PATH, board)
print("Aligned clusters to grid perfectly and moved specified components.")
