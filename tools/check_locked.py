import pcbnew

board = pcbnew.LoadBoard('hardware/warden-apex-master/warden-apex-master.kicad_pcb')
locked_vias = [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA) and t.IsLocked()]
print(f"Locked vias: {len(locked_vias)}")
