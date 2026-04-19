import math
import pcbnew

BOARD_PATH = '/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb'
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

major_refs = {
    'U1', 'U2', 'U3', 'IC1', 'IC2', 'IC3', 'U4', 'U5', 'U6', 'IC4', 'Card1', 'L1',
    'J1', 'J2', 'J3', 'J4', 'J5', 'H1', 'R18', 'R19', 'X1',
    'Q2', 'Q6', 'Q4', 'Q5', 'JP1', 'JP2' # Locking these newly padded components
}
all_fps = [fp for fp in board.GetFootprints() if not fp.GetReference().startswith('MH')]
small_fps = [fp for fp in all_fps if fp.GetReference() not in major_refs]

centers = {'IC1': get_pos('IC1')}
clusters = {'IC1': []}

for fp in small_fps:
    # Only group small passives around IC1 (x < 45, y < 60)
    pos = (iu2mm(fp.GetPosition().x), iu2mm(fp.GetPosition().y))
    if pos[0] > 45 or pos[1] > 60:
        continue
    
    clusters['IC1'].append(fp)

placed_rects = []
for fp in all_fps:
    if fp not in clusters['IC1']:
        placed_rects.append(get_pads_rect_mm(fp))

def snap_to_90(angle):
    normalized = angle % 360
    return round(normalized / 90.0) * 90.0

def can_place(fp, x, y, ang, clearance=1.0):
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

def place_cluster_on_square_grid(cluster_fps, cx, cy, grid_step_x=4.0, grid_step_y=4.0, clearance=1.0, min_dist=12.0):
    if not cluster_fps: return
    
    grid_points = []
    # Create rectangular grid of points
    for r in range(1, 10):
        # Top and bottom rows
        for dx in range(-r, r+1):
            for dy in [-r, r]:
                x = cx + dx * grid_step_x
                y = cy + dy * grid_step_y
                if math.hypot(dx * grid_step_x, dy * grid_step_y) >= min_dist:
                    grid_points.append((x, y, max(abs(dx), abs(dy))))
        # Left and right columns
        for dy in range(-r+1, r):
            for dx in [-r, r]:
                x = cx + dx * grid_step_x
                y = cy + dy * grid_step_y
                if math.hypot(dx * grid_step_x, dy * grid_step_y) >= min_dist:
                    grid_points.append((x, y, max(abs(dx), abs(dy))))
                
    grid_points.sort(key=lambda p: (p[2], math.hypot(p[0]-cx, p[1]-cy)))
    
    unique_gp = []
    seen = set()
    for p in grid_points:
        if (p[0], p[1]) not in seen:
            seen.add((p[0], p[1]))
            unique_gp.append(p)
            
    def fp_area(fp):
        r = get_pads_rect_mm(fp)
        return (r[2]-r[0])*(r[3]-r[1])
    
    cluster_fps.sort(key=fp_area, reverse=True)
    
    for fp in cluster_fps:
        placed = False
        ang = snap_to_90(fp.GetOrientation().AsDegrees())
        
        for gx, gy, _ in unique_gp:
            if can_place(fp, gx, gy, ang, clearance):
                set_pos(fp.GetReference(), gx, gy, ang)
                placed_rects.append(get_pads_rect_mm(fp))
                placed = True
                break
                
        if not placed:
            alt_ang = (ang + 90) % 360
            for gx, gy, _ in unique_gp:
                if can_place(fp, gx, gy, alt_ang, clearance):
                    set_pos(fp.GetReference(), gx, gy, alt_ang)
                    placed_rects.append(get_pads_rect_mm(fp))
                    placed = True
                    break

        if not placed:
            print(f"WARNING: Could not find grid spot for {fp.GetReference()} around {cx},{cy}")

place_cluster_on_square_grid(clusters['IC1'], centers['IC1'][0], centers['IC1'][1], grid_step_x=4.0, grid_step_y=4.0, min_dist=15.0)

zf=pcbnew.ZONE_FILLER(board)
zf.Fill(list(board.Zones()))
pcbnew.SaveBoard(BOARD_PATH, board)
print("Repacked IC1 small components around the newly padded major components.")
