import pcbnew
import sys
import os

def wipe_routing(board):
    tracks_removed = 0
    zones_removed = 0
    for item in list(board.Tracks()):
        board.RemoveNative(item)
        tracks_removed += 1
    for zone in list(board.Zones()):
        board.RemoveNative(zone)
        zones_removed += 1
    print(f"Removed {tracks_removed} tracks/vias and {zones_removed} zones.")

def main():
    board_path = '/home/admin/github/lora-low-power-surveillance/hardware/warden-apex-master/warden-apex-master.kicad_pcb'
    board = pcbnew.LoadBoard(board_path)
    
    wipe_routing(board)
    
    pcbnew.SaveBoard(board_path, board)
    print("PCB wiped successfully.")

if __name__ == '__main__':
    main()
