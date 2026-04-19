import math
from itertools import product
import pcbnew

BOARD_PATH = "/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb"
BOARD_MARGIN_MM = 2.0
COLLISION_CLEARANCE_MM = 1.2
CLUSTER_GRID_STEP_MM = 3.0

EDGE_PLACEMENTS = {
    # ref: (side, desired_axis_position_mm, angle_deg)
    "U1": ("top", 47.5, 180),      # XIAO USB-C faces outward
    "J4": ("bottom", 25.0, 0),
    "J5": ("bottom", 47.5, 0),
    "H1": ("bottom", 70.0, 0),
    "J1": ("left", 42.0, 90),
    "J2": ("right", 42.0, 270),
}

MAIN_ICS = {
    "U1": "MCU",
    "IC1": "CELL",
    "U2": "LORA",
    "IC2": "POWER",
    "IC3": "POWER",
    "L1": "POWER",
    "U3": "SWARM",
    "U4": "IO",
    "U6": "IO",
    "IC4": "IO",
}

IGNORE_NETS = {"/GND", "GND", "/3V3", "/VBAT_SYS"}


def mm_to_iu(mm):
    return int(round(mm * 1e6))


def iu_to_mm(iu):
    return iu / 1e6


def rect_intersects(a, b, clearance=0.0):
    return not (
        (a[2] + clearance) <= b[0]
        or (b[2] + clearance) <= a[0]
        or (a[3] + clearance) <= b[1]
        or (b[3] + clearance) <= a[1]
    )


def get_pads_rect_mm(fp):
    pads = list(fp.Pads())
    if not pads:
        bb = fp.GetBoundingBox()
        return (
            iu_to_mm(bb.GetX()),
            iu_to_mm(bb.GetY()),
            iu_to_mm(bb.GetRight()),
            iu_to_mm(bb.GetBottom()),
        )
    minx = min(iu_to_mm(p.GetBoundingBox().GetX()) for p in pads)
    miny = min(iu_to_mm(p.GetBoundingBox().GetY()) for p in pads)
    maxx = max(iu_to_mm(p.GetBoundingBox().GetRight()) for p in pads)
    maxy = max(iu_to_mm(p.GetBoundingBox().GetBottom()) for p in pads)
    return (minx, miny, maxx, maxy)


def get_nets(fp):
    nets = set()
    for pad in fp.Pads():
        net = pad.GetNetname()
        if net and net not in IGNORE_NETS:
            nets.add(net)
    return nets


def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def point_inside_region(rect, region, margin=0.0):
    return (
        rect[0] >= region[0] + margin
        and rect[1] >= region[1] + margin
        and rect[2] <= region[2] - margin
        and rect[3] <= region[3] - margin
    )


def nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM):
    rect = get_pads_rect_mm(fp)
    dx = 0.0
    dy = 0.0
    if rect[0] < board_rect[0] + margin:
        dx += (board_rect[0] + margin - rect[0])
    if rect[2] > board_rect[2] - margin:
        dx -= (rect[2] - (board_rect[2] - margin))
    if rect[1] < board_rect[1] + margin:
        dy += (board_rect[1] + margin - rect[1])
    if rect[3] > board_rect[3] - margin:
        dy -= (rect[3] - (board_rect[3] - margin))
    if abs(dx) > 1e-6 or abs(dy) > 1e-6:
        p = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(p.x + mm_to_iu(dx), p.y + mm_to_iu(dy)))


def find_global_slot(fp, board_rect, placed_rects):
    bx1, by1, bx2, by2 = board_rect
    xs = []
    ys = []
    x = bx1 + 8.0
    while x <= bx2 - 8.0:
        xs.append(x)
        x += CLUSTER_GRID_STEP_MM
    y = by1 + 8.0
    while y <= by2 - 8.0:
        ys.append(y)
        y += CLUSTER_GRID_STEP_MM

    cx = (bx1 + bx2) / 2.0
    cy = (by1 + by2) / 2.0
    candidates = sorted(product(xs, ys), key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    for px, py in candidates:
        fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(px), mm_to_iu(py)))
        nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
        rect = get_pads_rect_mm(fp)
        if any(rect_intersects(rect, r, COLLISION_CLEARANCE_MM) for r in placed_rects):
            continue
        if not point_inside_region(rect, board_rect, margin=BOARD_MARGIN_MM):
            continue
        return rect
    return None


def place_edge_component(fp, board_rect, side, desired_axis, angle_deg, placed_rects):
    fp.SetOrientation(pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T))
    fp.SetLayer(pcbnew.F_Cu)
    fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(0.0), mm_to_iu(0.0)))
    width = get_pads_rect_mm(fp)[2] - get_pads_rect_mm(fp)[0]
    height = get_pads_rect_mm(fp)[3] - get_pads_rect_mm(fp)[1]
    half_w, half_h = width / 2.0, height / 2.0

    bx1, by1, bx2, by2 = board_rect
    min_cx = bx1 + BOARD_MARGIN_MM + half_w
    max_cx = bx2 - BOARD_MARGIN_MM - half_w
    min_cy = by1 + BOARD_MARGIN_MM + half_h
    max_cy = by2 - BOARD_MARGIN_MM - half_h

    if side == "top":
        cx = clamp(desired_axis, min_cx, max_cx)
        cy = min_cy
        axis_candidates = [cx + step for step in [0, -4, 4, -8, 8, -12, 12, -16, 16]]
        for test_cx in axis_candidates:
            test_cx = clamp(test_cx, min_cx, max_cx)
            fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(test_cx), mm_to_iu(cy)))
            nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
            rect = get_pads_rect_mm(fp)
            if all(not rect_intersects(rect, r, COLLISION_CLEARANCE_MM) for r in placed_rects):
                placed_rects.append(rect)
                return
        nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
        placed_rects.append(get_pads_rect_mm(fp))
        return

    if side == "bottom":
        cx = clamp(desired_axis, min_cx, max_cx)
        cy = max_cy
        axis_candidates = [cx + step for step in [0, -4, 4, -8, 8, -12, 12, -16, 16]]
        for test_cx in axis_candidates:
            test_cx = clamp(test_cx, min_cx, max_cx)
            fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(test_cx), mm_to_iu(cy)))
            nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
            rect = get_pads_rect_mm(fp)
            if all(not rect_intersects(rect, r, COLLISION_CLEARANCE_MM) for r in placed_rects):
                placed_rects.append(rect)
                return
        nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
        placed_rects.append(get_pads_rect_mm(fp))
        return

    if side == "left":
        cx = min_cx
        cy = clamp(desired_axis, min_cy, max_cy)
        axis_candidates = [cy + step for step in [0, -4, 4, -8, 8, -12, 12, -16, 16]]
        for test_cy in axis_candidates:
            test_cy = clamp(test_cy, min_cy, max_cy)
            fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(cx), mm_to_iu(test_cy)))
            nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
            rect = get_pads_rect_mm(fp)
            if all(not rect_intersects(rect, r, COLLISION_CLEARANCE_MM) for r in placed_rects):
                placed_rects.append(rect)
                return
        nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
        placed_rects.append(get_pads_rect_mm(fp))
        return

    if side == "right":
        cx = max_cx
        cy = clamp(desired_axis, min_cy, max_cy)
        axis_candidates = [cy + step for step in [0, -4, 4, -8, 8, -12, 12, -16, 16]]
        for test_cy in axis_candidates:
            test_cy = clamp(test_cy, min_cy, max_cy)
            fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(cx), mm_to_iu(test_cy)))
            nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
            rect = get_pads_rect_mm(fp)
            if all(not rect_intersects(rect, r, COLLISION_CLEARANCE_MM) for r in placed_rects):
                placed_rects.append(rect)
                return
        nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
        placed_rects.append(get_pads_rect_mm(fp))
        return


def get_cluster_regions(board_rect):
    bx1, by1, bx2, by2 = board_rect
    left = bx1 + 8.0
    right = bx2 - 8.0
    top = by1 + 20.0
    bottom = by2 - 20.0
    width = right - left
    height = bottom - top
    col = width / 3.0
    row = height / 2.0

    # Add small gutters between regions for breathing room.
    gx = 1.0
    gy = 2.0
    return {
        "CELL": (left + gx, top + gy, left + col - gx, top + row - gy),
        "MCU": (left + col + gx, top + gy, left + 2 * col - gx, top + row - gy),
        "LORA": (left + 2 * col + gx, top + gy, right - gx, top + row - gy),
        "POWER": (left + gx, top + row + gy, left + col - gx, bottom - gy),
        "IO": (left + col + gx, top + row + gy, left + 2 * col - gx, bottom - gy),
        "SWARM": (left + 2 * col + gx, top + row + gy, right - gx, bottom - gy),
    }


def pack_cluster(region, fps, placed_rects, board_rect):
    if not fps:
        return

    cx = (region[0] + region[2]) / 2.0
    cy = (region[1] + region[3]) / 2.0

    def sort_key(fp):
        ref = fp.GetReference()
        is_main = ref in MAIN_ICS
        rect = get_pads_rect_mm(fp)
        area = (rect[2] - rect[0]) * (rect[3] - rect[1])
        return (not is_main, -area)

    fps_sorted = sorted(fps, key=sort_key)

    xs = []
    ys = []
    x = region[0] + 2.0
    while x <= region[2] - 2.0:
        xs.append(x)
        x += CLUSTER_GRID_STEP_MM
    y = region[1] + 2.0
    while y <= region[3] - 2.0:
        ys.append(y)
        y += CLUSTER_GRID_STEP_MM

    candidates = sorted(product(xs, ys), key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)

    for fp in fps_sorted:
        fp.SetLayer(pcbnew.F_Cu)
        placed = False
        for px, py in candidates:
            fp.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
            fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(px), mm_to_iu(py)))
            rect = get_pads_rect_mm(fp)
            if not point_inside_region(rect, region, margin=0.3):
                continue
            if any(rect_intersects(rect, r, COLLISION_CLEARANCE_MM) for r in placed_rects):
                continue
            placed_rects.append(rect)
            placed = True
            break

        if not placed:
            # Fallback: keep trying with reduced clearance.
            for px, py in candidates:
                fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(px), mm_to_iu(py)))
                rect = get_pads_rect_mm(fp)
                if not point_inside_region(rect, region, margin=0.1):
                    continue
                if any(rect_intersects(rect, r, 0.2) for r in placed_rects):
                    continue
                placed_rects.append(rect)
                placed = True
                break

        if not placed:
            # Final fallback: search global free area.
            rect = find_global_slot(fp, board_rect, placed_rects)
            if rect is None:
                fp.SetPosition(pcbnew.VECTOR2I(mm_to_iu(cx), mm_to_iu(cy)))
                nudge_inside_board(fp, board_rect, margin=BOARD_MARGIN_MM)
                rect = get_pads_rect_mm(fp)
            placed_rects.append(rect)


def validate(board, board_rect):
    fps = [fp for fp in board.GetFootprints() if not fp.GetReference().startswith("MH")]
    out = []
    for fp in fps:
        rect = get_pads_rect_mm(fp)
        if not point_inside_region(rect, board_rect, margin=0.0):
            out.append(fp.GetReference())
    overlaps = []
    for i, a in enumerate(fps):
        ra = get_pads_rect_mm(a)
        for b in fps[i + 1 :]:
            rb = get_pads_rect_mm(b)
            if rect_intersects(ra, rb, 0.0):
                overlaps.append((a.GetReference(), b.GetReference()))
    return out, overlaps


def main():
    board = pcbnew.LoadBoard(BOARD_PATH)
    edge = board.GetBoardEdgesBoundingBox()
    board_rect = (
        iu_to_mm(edge.GetX()),
        iu_to_mm(edge.GetY()),
        iu_to_mm(edge.GetRight()),
        iu_to_mm(edge.GetBottom()),
    )

    for fp in board.GetFootprints():
        if fp.GetReference().startswith("MH"):
            continue
        fp.SetLayer(pcbnew.F_Cu)

    ic_nets = {cluster: set() for cluster in get_cluster_regions(board_rect).keys()}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in MAIN_ICS:
            ic_nets[MAIN_ICS[ref]].update(get_nets(fp))

    clusters = {cluster: [] for cluster in get_cluster_regions(board_rect).keys()}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("MH") or ref in EDGE_PLACEMENTS:
            continue
        if ref in MAIN_ICS:
            clusters[MAIN_ICS[ref]].append(fp)
            continue
        fp_nets = get_nets(fp)
        best_cluster = "MCU"
        best_score = -1
        for cluster, nets in ic_nets.items():
            score = len(fp_nets.intersection(nets))
            if score > best_score:
                best_score = score
                best_cluster = cluster
        clusters[best_cluster].append(fp)

    placed_rects = []

    # Place edge-critical components first.
    edge_order = ["U1", "J4", "J5", "H1", "J1", "J2"]
    for ref in edge_order:
        fp = board.FindFootprintByReference(ref)
        if not fp:
            continue
        side, axis, angle = EDGE_PLACEMENTS[ref]
        place_edge_component(fp, board_rect, side, axis, angle, placed_rects)

    # Pack clusters into interior regions.
    regions = get_cluster_regions(board_rect)
    cluster_order = ["CELL", "LORA", "POWER", "IO", "SWARM", "MCU"]
    for cluster in cluster_order:
        pack_cluster(regions[cluster], clusters[cluster], placed_rects, board_rect)

    pcbnew.SaveBoard(BOARD_PATH, board)

    # Quick validation report.
    out, overlaps = validate(board, board_rect)
    print("Algorithmic placement pass 2 completed.")
    print(f"Off-board footprints: {len(out)}")
    if out:
        print("  " + ", ".join(sorted(out)))
    print(f"Pad-overlap pairs: {len(overlaps)}")
    if overlaps:
        print("  " + ", ".join(f"{a}-{b}" for a, b in overlaps[:30]))


if __name__ == "__main__":
    main()
