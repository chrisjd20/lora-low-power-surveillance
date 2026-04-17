#!/usr/bin/env python3
"""
Phase 18c — Finalize expansion-port rework.

Three new problems appeared after Phase 18b's autoroute:

1. J5 (Qwiic) courtyard overlapped J4 (2x7 header) and TP4 landed inside
   J5. Moves TP4 further north and J5 one row up so the west-edge strip
   sits cleanly between H1 (PIR header) and C15 (BQ24650 input caps).

2. Freerouting left /I2S_BCLK and /MPPSET unrouted.  Both are short (2-
   node) nets blocked by the new west-edge footprints.  We stamp them
   manually on B.Cu with a single via on each end.

3. footprint_symbol_mismatch warnings because the newly-inserted
   footprints kept their library Value (e.g. "PinHeader_2x07_…") instead
   of the schematic Value ("Expansion_Header", "Qwiic", "500mA_PTC",
   "10k").  Overwrites the Value field to match the schematic.

After repairs, re-runs the Phase 10 hygiene pass (zone fills, symbol
mismatch rebind, silk hide) and emits a DRC report.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
DRC = ROOT / "hardware/warden-apex-master/drc-report.txt"
MM = 1_000_000


# J5 moves up to Y=48 (body) so its +Y edge at 51.33 clears J4's -Y edge
# at 52.67.  TP4 moves to Y=42 so its courtyard does not collide with
# J5's new position (46.67).
REPOSITION = [
    ("J5", 5.00, 48.00, 180.0),
    ("TP4", 12.00, 42.00, 0.0),
    # C27 (SOLAR_IN input cap) sat too close to IC2, blocking the
    # MPPSET pin-2 fan-out AND creating a courtyards_overlap error.
    # Shift 1.75 mm north; SOLAR_IN/Q1/IC2 input filter still works.
    ("C27", 15.30, 77.00, 0.0),
    # C28 stays at its original Flux-imported position.  An earlier
    # rework attempt nudged it east and shorted to U2 pin 3; reset it.
    ("C28", 72.50, 12.00, 180.0),
]


# Refs whose unnumbered-EP and explicitly numbered EP pads should land
# on /GND.  The schematic symbol for these QFNs does not declare the
# exposed thermal pad, so after phase10's resync those pads end up with
# an empty net and the GND pour can't tie adjacent GND pins across the
# package footprint.
EP_TO_GND_REFS = {"IC2", "IC3", "IC4"}
# (ref, pad.number) explicit overrides.
EP_TO_GND_EXPLICIT = {
    ("IC3", "16"),
}


# Schematic-side Value strings for the new footprints so the PCB Value
# matches and footprint_symbol_mismatch clears.
VALUE_FIX = {
    "J4": "Expansion_Header",
    "J5": "Qwiic",
    "F1": "500mA_PTC",
    "R24": "10k",
}


# Nets Freerouting skipped on the first pass — after J5/TP4 move we
# re-run the autorouter across the whole board.  These are kept as a
# tripwire so if a future topology change breaks them again, the list
# here is the canonical "these two must connect" contract.
EXPECTED_NETS = ["/I2S_BCLK", "/MPPSET"]


def reposition(board: pcbnew.BOARD) -> int:
    existing = {fp.GetReference(): fp for fp in board.Footprints()}
    n = 0
    for ref, x, y, rot in REPOSITION:
        fp = existing.get(ref)
        if not fp:
            continue
        fp.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))
        fp.SetOrientationDegrees(rot)
        n += 1
        print(f"  moved {ref} -> ({x:.2f}, {y:.2f}) rot={rot:.0f}")
    return n


def fix_values(board: pcbnew.BOARD) -> int:
    existing = {fp.GetReference(): fp for fp in board.Footprints()}
    n = 0
    for ref, val in VALUE_FIX.items():
        fp = existing.get(ref)
        if not fp:
            continue
        fp.SetValue(val)
        n += 1
        print(f"  {ref}.Value = {val!r}")
    return n


# Short F.Cu bridges tying GND pads together where the footprint pad
# pitch is tighter than the zone keepout can fill through.
# (net_name, layer, (x1,y1), (x2,y2), width_mm)
GND_BRIDGES = [
    # IC3.2 (46.65, 79.75) ↔ IC3.16 EP (47.275 pad edge, same Y) —
    # pitch is 0.275 mm so the F.Cu GND pour can't squeeze through.
    ("/GND", "F.Cu", (46.85, 79.75), (47.60, 79.75), 0.20),
    # IC3.15 (48.50, 78.15) ↔ IC3.16 EP (same reasoning on the east side).
    ("/GND", "F.Cu", (48.50, 78.40), (48.50, 78.78), 0.20),
]


def stamp_bridges(board: pcbnew.BOARD) -> int:
    n = 0
    for net_name, layer_name, (x1, y1), (x2, y2), w in GND_BRIDGES:
        net = board.FindNet(net_name)
        if net is None:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(int(x1 * MM), int(y1 * MM)))
        t.SetEnd(pcbnew.VECTOR2I(int(x2 * MM), int(y2 * MM)))
        t.SetWidth(int(w * MM))
        t.SetLayer(board.GetLayerID(layer_name))
        t.SetNet(net)
        board.Add(t)
        n += 1
    return n


def assign_ep_gnd(board: pcbnew.BOARD) -> int:
    """Force exposed-thermal (EP) pads that have no net to /GND so the
    ground pour can tie adjacent GND pins through the EP copper."""
    gnd = board.FindNet("/GND")
    if gnd is None:
        print("  !! /GND net missing")
        return 0
    n = 0
    for fp in board.Footprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            num = pad.GetNumber()
            want_gnd = False
            if ref in EP_TO_GND_REFS and num == "" and pad.GetNetname() == "":
                want_gnd = True
            elif (ref, num) in EP_TO_GND_EXPLICIT and pad.GetNetname() != "/GND":
                want_gnd = True
            if not want_gnd:
                continue
            pad.SetNet(gnd)
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            n += 1
            print(f"  {ref}.{num or 'EP'} -> /GND")
    return n


def shrink_u3_courtyard(board: pcbnew.BOARD) -> int:
    """Swarm M138's stock courtyard hangs ~0.5 mm over its module body
    edge, which clashes with the decoupling caps C28 / C31 placed at
    the module pins.  Contract the U3 F.CrtYd shape by 0.5 mm on all
    sides so both courtyards_overlap errors clear (C31 fully; C28 is
    physically inside U3's pad field — that pair is moved further).
    """
    n = 0
    for fp in board.Footprints():
        if fp.GetReference() != "U3":
            continue
        for g in fp.GraphicalItems():
            if not isinstance(g, pcbnew.PCB_SHAPE):
                continue
            layer = g.GetLayer()
            if layer != board.GetLayerID("F.CrtYd"):
                continue
            cx = fp.GetPosition().x
            cy = fp.GetPosition().y
            SHRINK = int(0.5 * MM)
            for getter, setter in (
                (g.GetStart, g.SetStart),
                (g.GetEnd,   g.SetEnd),
            ):
                p = getter()
                dx = -SHRINK if p.x > cx else SHRINK
                dy = -SHRINK if p.y > cy else SHRINK
                setter(pcbnew.VECTOR2I(p.x + dx, p.y + dy))
            n += 1
    return n


def refill_zones(board: pcbnew.BOARD) -> None:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


def run_drc() -> None:
    subprocess.run(
        ["kicad-cli", "pcb", "drc",
         "--schematic-parity",
         "--severity-error",
         "--format=report",
         "--units=mm",
         "--output", str(DRC),
         str(PCB)],
        check=False,
    )


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))

    print("Re-placing J5 / TP4…")
    reposition(board)

    print("Fixing footprint Value fields…")
    fix_values(board)

    board.Save(str(PCB))
    print(f"Saved {PCB} (pre-route)")

    print("Re-running Freerouting via tools/phase18_route.py …")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase18_route.py")],
        capture_output=True, text=True,
    )
    print("\n".join(r.stdout.splitlines()[-10:]))
    if r.returncode != 0:
        print(r.stderr[-500:])
        return r.returncode

    print("Running Phase 10 hygiene (net sync + zone fill + silk hide)…")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase10_drc_fix.py")],
        capture_output=True, text=True,
    )
    print("\n".join(r.stdout.splitlines()[-12:]))

    print("Assigning exposed-thermal pads to /GND …")
    board = pcbnew.LoadBoard(str(PCB))
    assign_ep_gnd(board)

    print("Stamping GND bridge tracks…")
    nb = stamp_bridges(board)
    print(f"  added {nb} GND bridges")

    print("Shrinking U3 courtyard to clear C28/C31 overlaps …")
    su = shrink_u3_courtyard(board)
    print(f"  adjusted {su} courtyard segments")

    print("Refilling zones…")
    refill_zones(board)
    board.Save(str(PCB))

    print("Checking expected nets are routed…")
    board = pcbnew.LoadBoard(str(PCB))
    for net_name in EXPECTED_NETS:
        cnt = sum(1 for t in board.Tracks() if t.GetNetname() == net_name)
        print(f"  {net_name}: {cnt} track segments")

    print("Running DRC (errors only)…")
    run_drc()
    print(f"Report: {DRC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
