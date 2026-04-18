import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')

# Let's map out occupied areas
occupied = []
for fp in board.GetFootprints():
    bb = fp.GetBoundingBox()
    occupied.append((pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())))

def is_free(x, y, w, h):
    for ox, oy, ow, oh in occupied:
        if x < ox + ow and x + w > ox and y < oy + oh and y + h > oy:
            return False
    return True

# find a 10x10 free area
for y in range(10, 90, 5):
    for x in range(10, 90, 5):
        if is_free(x, y, 10, 10):
            print(f"Free area at X={x}, Y={y}")
