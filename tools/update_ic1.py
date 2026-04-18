import pcbnew
import sys

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
ic1 = board.FindFootprintByReference('IC1')
if not ic1:
    print("IC1 not found")
    sys.exit(1)

# load the library footprint
fp_lib = pcbnew.FootprintLoad('hardware/warden-apex-master/footprints/warden-custom.pretty', 'LCC-42_SIM7080G')
if not fp_lib:
    print("Library footprint not found")
    sys.exit(1)

# we need to replace ic1 with fp_lib but keep its position and orientation
fp_lib.SetPosition(ic1.GetPosition())
fp_lib.SetOrientation(ic1.GetOrientation())
fp_lib.SetReference(ic1.GetReference())
fp_lib.SetLayer(ic1.GetLayer())

# We must preserve the net assignments of pads that already existed
nets = {}
for p in ic1.Pads():
    nets[p.GetName()] = p.GetNet()

for p in fp_lib.Pads():
    if p.GetName() in nets:
        p.SetNet(nets[p.GetName()])

board.RemoveNative(ic1)
board.AddNative(fp_lib)

board.Save('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
print("Updated IC1 on board.")
