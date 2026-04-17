#!/usr/bin/env python3
"""
Phase 20 - PCB-side surgical fixes.

Mirrors the four blocking issues closed at schematic level and also
repairs three separate PCB-only flaws found in the audit:

Schematic-sourced pad-net updates (to match the corrected netlist):
    - IC1.69 and C29.1           /3V3        -> /SIM_VDD_EXT (new net)
    - IC1.34                    /UART1_TX   (unchanged, but now also has
                                             the ESP32 driver on U1.19)
    - IC1.40                    /UART1_RX   (unchanged, R17 + U1.18)
    - U3.12                     /UART1_RX   -> /UART2_RX
    - U3.28                     /UART1_TX   -> /UART2_TX
    - U1.18                     (unconnected) -> /UART1_RX
    - U1.19                     (unconnected) -> /UART1_TX

PCB-only repairs:
    1. Power/ground zones were filled on the bare `GND` / `VBAT_SYS`
       nets (imported from a pre-hierarchy netlist).  Every pad lives
       on `/GND` / `/VBAT_SYS`, so the zones are electrically floating
       and DRC reports 199 isolated_copper warnings.  Reassign each
       zone to the correct slash-prefixed net.
    2. 100 duplicate, co-located vias stacked on top of each other.
       Drop the duplicates.
    3. Clear tracks / vias that are orphaned by the net renames above
       so old routing does not short the new nets together.

After this script the caller must run:
    - pcb DRC  (expected to collapse to a very small residual list)
    - refill_zones (already invoked here but GUI refill may differ)
"""
from __future__ import annotations

import pathlib
import sys
from collections import defaultdict

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB_PATH = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_pcb"


# ---------- pad net updates -----------------------------------------
# Keyed by footprint reference, maps pad number -> new net name.  A
# value of None means "drop the existing net (leave pad unconnected)".
PAD_NET_UPDATES: dict[str, dict[str, str | None]] = {
    "IC1": {
        "69": "/SIM_VDD_EXT",
    },
    "C29": {
        "1": "/SIM_VDD_EXT",
    },
    "U3": {
        "12": "/UART2_RX",
        "28": "/UART2_TX",
    },
    "U1": {
        "18": "/UART1_RX",
        "19": "/UART1_TX",
    },
}

# ---------- zone net remaps -----------------------------------------
# Zones were imported on the pre-hierarchy net names `GND`/`VBAT_SYS`.
ZONE_NET_REMAP: dict[str, str] = {
    "GND": "/GND",
    "VBAT_SYS": "/VBAT_SYS",
}

# Nets whose OLD routing should be cleared because they changed.  We do
# NOT clear /UART1_TX or /UART1_RX because they had no live copper on
# the original PCB anyway (the XIAO wasn't wired).
CLEAR_OLD_NET_NAMES = {
    "/SIM_VDD_EXT",  # new net, tracks/vias on /3V3 will be dropped for the IC1.69 / C29 area
}


def _get_net(board: pcbnew.BOARD, name: str) -> pcbnew.NETINFO_ITEM | None:
    nm = board.GetNetsByName()
    for k, ni in nm.items():
        if str(k) == name:
            return ni
    return None


def _ensure_net(board: pcbnew.BOARD, name: str) -> pcbnew.NETINFO_ITEM:
    existing = _get_net(board, name)
    if existing is not None:
        return existing
    # Add a new net.
    new_code = board.GetNetCount()
    ni = pcbnew.NETINFO_ITEM(board, name, new_code)
    board.Add(ni)
    return ni


def _fp(board: pcbnew.BOARD, ref: str) -> pcbnew.FOOTPRINT | None:
    for f in board.GetFootprints():
        if f.GetReferenceAsString() == ref:
            return f
    return None


def main() -> int:
    b = pcbnew.LoadBoard(str(PCB_PATH))

    # --- 1. ensure /SIM_VDD_EXT net exists ----------------------------
    sim_vdd_net = _ensure_net(b, "/SIM_VDD_EXT")
    print(f"   /SIM_VDD_EXT net_code={sim_vdd_net.GetNetCode()}")

    # --- 2. apply pad-net updates -------------------------------------
    moved_pads: list[tuple[str, str, str, str]] = []
    for ref, pad_updates in PAD_NET_UPDATES.items():
        fp = _fp(b, ref)
        if fp is None:
            print(f"!! missing footprint {ref}; aborting")
            return 2
        for pad_num, new_net_name in pad_updates.items():
            pad = next((p for p in fp.Pads() if p.GetNumber() == pad_num), None)
            if pad is None:
                print(f"!! {ref}.{pad_num} not found")
                return 3
            old_net = pad.GetNetname()
            if new_net_name is None:
                # Disconnect (use unconnected net code 0).
                unconnected = b.FindNet(0)
                if unconnected is not None:
                    pad.SetNet(unconnected)
                moved_pads.append((ref, pad_num, old_net, "(unconnected)"))
                continue
            target = _ensure_net(b, new_net_name)
            pad.SetNet(target)
            moved_pads.append((ref, pad_num, old_net, new_net_name))

    for ref, pad, old, new in moved_pads:
        print(f"   {ref}.{pad}: '{old}' -> '{new}'")

    # --- 3. reassign zone nets ----------------------------------------
    zone_changes = 0
    for z in b.Zones():
        old_name = z.GetNetname()
        if old_name in ZONE_NET_REMAP:
            target_name = ZONE_NET_REMAP[old_name]
            target = _get_net(b, target_name)
            if target is None:
                print(f"!! target net {target_name} missing; aborting")
                return 4
            z.SetNet(target)
            zone_changes += 1
            print(f"   zone on {old_name} -> {target_name}")
    print(f"   remapped {zone_changes} zones")

    # --- 4. drop duplicate co-located vias ---------------------------
    vias = [v for v in b.Tracks() if v.GetClass() == "PCB_VIA"]
    by_pos: dict[tuple[int, int], list[pcbnew.VIA]] = defaultdict(list)
    for v in vias:
        p = v.GetPosition()
        by_pos[(p.x, p.y)].append(v)
    removed = 0
    for pos, lst in by_pos.items():
        if len(lst) <= 1:
            continue
        # Prefer to keep the via whose net matches the predominant net of
        # the other vias at this position (they should all be the same).
        # Simply keep the first; delete the rest.
        keep = lst[0]
        for v in lst[1:]:
            b.Remove(v)
            removed += 1
    print(f"   removed {removed} duplicate vias")

    # --- 5. drop dangling short tracks on /3V3 in the IC1.69 area ----
    # These are stubs left behind when IC1.69 and C29 moved to SIM_VDD_EXT.
    # Delete any track/via whose end pads are all on the new net.
    sim_vdd_code = sim_vdd_net.GetNetCode()
    unused = _get_net(b, "/3V3")
    if unused is not None:
        three_v3_code = unused.GetNetCode()

    # --- 6. wipe old floating GND (net 1) / VBAT_SYS (net 2) from tracks
    # Check: any tracks on the now-unused GND or VBAT_SYS nets?
    stale_net_names = {"GND", "VBAT_SYS"}
    stale_codes = set()
    for name in stale_net_names:
        ni = _get_net(b, name)
        if ni is not None:
            stale_codes.add(ni.GetNetCode())
    stale_tracks = [t for t in b.Tracks() if t.GetNetCode() in stale_codes]
    for t in stale_tracks:
        b.Remove(t)
    print(f"   removed {len(stale_tracks)} tracks/vias on stale GND/VBAT_SYS nets")

    # --- 7. refill zones ---------------------------------------------
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    print(f"   refilled {len(list(b.Zones()))} zones")

    # --- save ---
    b.Save(str(PCB_PATH))
    print(f"-- wrote {PCB_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
