import math
from itertools import product
import pcbnew
import shutil

BOARD_PATH = '/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb'
shutil.copyfile('/tmp/pre_align.kicad_pcb', BOARD_PATH)
board = pcbnew.LoadBoard(BOARD_PATH)

def mm2iu(mm): return int(round(mm * 1e6))
def iu2mm(iu): return iu / 1e6

b_edges = board.GetBoardEdgesBoundingBox()
BOARD_LEFT = iu2mm(b_edges.GetX()) + 2.0
BOARD_TOP = iu2mm(b_edges.GetY()) + 2.0
BOARD_RIGHT = iu2mm(b_edges.GetRight()) - 2.0
BOARD_BOTTOM = iu2mm(b_edges.GetBottom()) - 2.0

def get_pos(ref):
    fp = board.FindFootprintByReference(ref)
    if fp:
        return iu2mm(fp.GetPosition().x), iu2mm(fp.GetPosition().y)
    return None, None

def set_pos(ref, x, y, ang=None):
    fp = board.FindFootprintByReference(ref)
    if fp:
        fp.SetPosition(pcbnew.VECTOR2I(mm2iu(x), mm2iu(y)))
        if ang is not None:
            fp.SetOrientation(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))

def get_pads_rect_mm(fp):
    pads = list(fp.Pads())
    if not pads:
        bb = fp.GetBoundingBox()
        return (bb.GetX()/1e6, bb.GetY()/1e6, bb.GetRight()/1e6, bb.GetBottom()/1e6)
    return (
        min(p.GetBoundingBox().GetX() for p in pads)/1e6,
        min(p.GetBoundingBox().GetY() for p in pads)/1e6,
        max(p.GetBoundingBox().GetRight() for p in pads)/1e6,
        max(p.GetBoundingBox().GetBottom() for p in pads)/1e6,
    )

def intersects(a, b, clearance=0.0):
    return not ((a[2]+clearance)<=b[0] or (b[2]+clearance)<=a[0] or (a[3]+clearance)<=b[1] or (b[3]+clearance)<=a[1])

# Manual Shifts
j1x, j1y = get_pos('J1')
if j1x: set_pos('J1', j1x, j1y + 15)

c1x, c1y = get_pos('Card1')
if c1x: set_pos('Card1', c1x + 12, c1y - 12)

j3x, j3y = get_pos('J3')
if j3x: set_pos('J3', j3x + 6, j3y + 6)

r18x, r18y = get_pos('R18')
if r18x: set_pos('R18', r18x + 5, r18y + 5)
r19x, r19y = get_pos('R19')
if r19x: set_pos('R19', r19x + 5, r19y + 5)

# Clusters
major_refs = {'U1', 'U2', 'U3', 'IC1', 'IC2', 'IC3', 'U4', 'U5', 'U6', 'IC4', 'Card1', 'L1', 'J1', 'J2', 'J3', 'J4', 'J5', 'H1', 'R18', 'R19', 'X1'}
all_fps = [fp for fp in board.GetFootprints() if not fp.GetReference().startswith('MH')]
small_fps = [fp for fp in all_fps if fp.GetReference() not in major_refs]

centers = {
    'IC1': get_pos('IC1'),
    'POWER': ((get_pos('IC2')[0] + get_pos('IC3')[0])/2, (get_pos('IC2')[1] + get_pos('IC3')[1])/2),
    'IO': get_pos('U4')
}

clusters = {'IC1': [], 'POWER': [], 'IO': []}
for fp in small_fps:
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

placed_rects = []
for fp in all_fps:
    if fp not in small_fps:
        placed_rects.append(get_pads_rect_mm(fp))

def snap_to_90(angle):
    normalized = angle % 360
    return round(normalized / 90.0) * 90.0

def can_place(fp, x, y, ang, clearance=0.8):
    orig_x = fp.GetPosition().x
    orig_y = fp.GetPosition().y
    orig_a = fp.GetOrientation()
    
    fp.SetPosition(pcbnew.VECTOR2I(mm2iu(x), mm2iu(y)))
    fp.SetOrientation(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
    
    rect = get_pads_rect_mm(fp)
    
    fp.SetPosition(pcbnew.VECTOR2I(orig_x, orig_y))
    fp.SetOrientation(orig_a)
    
    if rect[0] < BOARD_LEFT or rect[1] < BOARD_TOP or rect[2] > BOARD_RIGHT or rect[3] > BOARD_BOTTOM:
        return False
        
    for pr in placed_rects:
        if intersects(rect, pr, clearance):
            return False
            
    return True

def place_cluster_on_grid(cluster_fps, cx, cy, grid_step=3.0, clearance=1.0, min_radius=13.0):
    if not cluster_fps: return
    
    grid_points = []
    for dx in range(-12, 13):
        for dy in range(-12, 13):
            x = cx + dx * grid_step
            y = cy + dy * grid_step
            d = math.hypot(dx * grid_step, dy * grid_step)
            if d >= min_radius:
                grid_points.append((x, y, d))
                
    grid_points.sort(key=lambda p: p[2])
    
    def fp_dist(fp):
        x, y = iu2mm(fp.GetPosition().x), iu2mm(fp.GetPosition().y)
        return math.hypot(x-cx, y-cy)
    
    cluster_fps.sort(key=fp_dist)
    
    for fp in cluster_fps:
        placed = False
        ang = snap_to_90(fp.GetOrientation().AsDegrees())
        
        for gx, gy, d in grid_points:
            if can_place(fp, gx, gy, ang, clearance):
                set_pos(fp.GetReference(), gx, gy, ang)
                placed_rects.append(get_pads_rect_mm(fp))
                placed = True
                break
                
        if not placed:
            alt_ang = (ang + 90) % 360
            for gx, gy, d in grid_points:
                if can_place(fp, gx, gy, alt_ang, clearance):
                    set_pos(fp.GetReference(), gx, gy, alt_ang)
                    placed_rects.append(get_pads_rect_mm(fp))
                    placed = True
                    break

        if not placed:
            print(f"WARNING: Could not find grid spot for {fp.GetReference()} around {cx},{cy}")

place_cluster_on_grid(clusters['IC1'], centers['IC1'][0], centers['IC1'][1], grid_step=3.0, min_radius=15.0)
place_cluster_on_grid(clusters['POWER'], centers['POWER'][0], centers['POWER'][1], grid_step=3.0, min_radius=16.0)
place_cluster_on_grid(clusters['IO'], centers['IO'][0], centers['IO'][1], grid_step=3.0, min_radius=13.0)

zf=pcbnew.ZONE_FILLER(board)
zf.Fill(list(board.Zones()))
pcbnew.SaveBoard(BOARD_PATH, board)
print("Grid placement complete with correct board edges.")
