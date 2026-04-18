#!/usr/bin/env python3
"""
One-shot power-distribution repair for warden-apex-master.kicad_pcb.

Phase A re-audit found:
  * Every POWER_HI / POWER_3V3 / CHARGER_SW net is routed at 0.2 mm even
    though netclass widths are 0.6 / 0.4 / 0.5 mm. The autorouter ran with
    default widths and was never re-run with netclass enforcement.
  * /GND has 3 vias for 164 pads -> the F.Cu / In1.Cu / B.Cu GND zones
    are essentially detached from each other.
  * /VBAT_SYS has 2 vias for 18 pads -> the dedicated In2.Cu (PWR) plane
    is barely tied to the VBAT_SYS pads.

This script:
  1. Bumps every track on a power net to its netclass width, then iterates
     DRC and reverts any widened track that creates a clearance error,
     stepping the width down 0.6 -> 0.5 -> 0.4 -> 0.3 -> 0.25 -> 0.2 until
     DRC is clean for that track.
  2. Stitches every VBAT_SYS SMD pad with a via that taps the In2.Cu plane.
  3. Drops a coarse GND via grid across the board to bond F.Cu/In1.Cu/B.Cu
     GND zones, skipping any cell that would collide with existing copper
     or sit outside the Edge.Cuts.
  4. Refills zones and re-runs DRC to confirm the board is still clean
     (all severities reported, but only `error`-class violations are
     treated as blocking).

Run from the repo root:
    python3 tools/fix_power_rails.py
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
from collections import defaultdict
from typing import Iterable

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
PRO = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pro"
DRC_REPORT = ROOT / "build/fix_power_rails_drc.json"

# Trace width steps to try, largest first; final fallback is 0.20 mm.
WIDTH_STEPS_MM = [0.60, 0.50, 0.40, 0.30, 0.25, 0.20]


def mm(v_nm: int) -> float:
    return pcbnew.ToMM(v_nm)


def to_nm(v_mm: float) -> int:
    return pcbnew.FromMM(v_mm)


def load_netclass_targets() -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    """Pull netclass -> {track_width, via_diameter, via_drill, clearance}
    in mm, plus the per-net `/NetName -> classname` assignments."""
    pro = json.loads(PRO.read_text())
    classes = {c["name"]: c for c in pro["net_settings"]["classes"]}
    assignments_raw = pro["net_settings"].get("netclass_assignments", {}) or {}
    # Each net maps to a list with a single classname in this project.
    net_to_class: dict[str, str] = {}
    for net, names in assignments_raw.items():
        if names:
            net_to_class[net] = names[0]
    return classes, net_to_class


def power_target_width(net_name: str, net_to_class: dict[str, str],
                       classes: dict) -> float | None:
    """Return target track width (mm) for nets in a power netclass, or None
    if the netclass should not be widened by this script."""
    nc_name = net_to_class.get(net_name, "Default")
    if nc_name in ("POWER_HI", "POWER_3V3", "CHARGER_SW"):
        return classes[nc_name]["track_width"]
    return None


def build_via(board, net, x_nm, y_nm, diameter_mm, drill_mm,
              top="F.Cu", bottom="B.Cu") -> "pcbnew.PCB_VIA":
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(x_nm, y_nm))
    via.SetWidth(to_nm(diameter_mm))
    via.SetDrill(to_nm(drill_mm))
    via.SetLayerPair(board.GetLayerID(top), board.GetLayerID(bottom))
    via.SetNet(net)
    board.Add(via)
    return via


def _seg_point_dist2(px, py, sx, sy, ex, ey):
    """Squared distance from point (px,py) to segment (sx,sy)-(ex,ey)."""
    dx = ex - sx
    dy = ey - sy
    if dx == 0 and dy == 0:
        return (px - sx) ** 2 + (py - sy) ** 2
    t = ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)
    if t < 0:
        t = 0.0
    elif t > 1:
        t = 1.0
    qx = sx + t * dx
    qy = sy + t * dy
    return (px - qx) ** 2 + (py - qy) ** 2


def collect_pad_via_hazards(board):
    """Return (cx, cy, radius_nm, netcode) for every pad and via on the
    board. Pads are bloated by their full diagonal half-extent so that
    rectangular pads are conservatively bounded."""
    haz = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            r = (max(pad.GetSizeX(), pad.GetSizeY()) // 2) + to_nm(0.10)
            haz.append((p.x, p.y, r, pad.GetNetCode()))
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            haz.append((p.x, p.y, t.GetWidth() // 2 + to_nm(0.10), t.GetNetCode()))
    return haz


def collect_track_segments(board):
    """Return [(sx, sy, ex, ey, half_w_nm, netcode)] for every track segment."""
    segs = []
    for t in list(board.GetTracks()):
        if t.GetClass() in ("PCB_TRACK", "PCB_ARC"):
            segs.append((t.GetStartX(), t.GetStartY(),
                         t.GetEndX(), t.GetEndY(),
                         t.GetWidth() // 2,
                         t.GetNetCode()))
    return segs


def via_clear_at(x, y, via_radius_nm, clearance_nm,
                 pad_via_haz, track_segs, my_netcode):
    """True if a via centered at (x,y) on `my_netcode` clears every other
    net's geometry by at least `clearance_nm`."""
    # Pads / vias
    for hx, hy, hr, hnet in pad_via_haz:
        if hnet == my_netcode:
            continue
        need = via_radius_nm + hr + clearance_nm
        if (x - hx) ** 2 + (y - hy) ** 2 < need * need:
            return False
    # Track segments
    for sx, sy, ex, ey, hw, hnet in track_segs:
        if hnet == my_netcode:
            continue
        need = via_radius_nm + hw + clearance_nm
        if _seg_point_dist2(x, y, sx, sy, ex, ey) < need * need:
            return False
    return True


def repair_missing_layer_transition_vias(board, classes) -> int:
    """The autorouter occasionally terminates two same-net tracks on
    opposite copper layers at the exact same point without dropping a
    via. Find every such coincidence and add a via."""
    fixed = 0
    f_cu = board.GetLayerID("F.Cu")
    b_cu = board.GetLayerID("B.Cu")
    via_d = classes["GND"]["via_diameter"]
    via_drill = classes["GND"]["via_drill"]
    via_r = to_nm(via_d) // 2
    clearance_nm = to_nm(0.20) + to_nm(0.05)
    pad_via_haz = collect_pad_via_hazards(board)
    track_segs = collect_track_segments(board)
    # Index F.Cu and B.Cu endpoints by snapped position per net
    snap = 50_000  # 50 µm grid
    f_endpoints: dict[tuple[int, int, int], list] = {}
    b_endpoints: dict[tuple[int, int, int], list] = {}
    tracks = [t for t in list(board.GetTracks())
              if t.GetClass() in ("PCB_TRACK", "PCB_ARC")]
    for t in tracks:
        nc = t.GetNetCode()
        for px, py in ((t.GetStartX(), t.GetStartY()),
                       (t.GetEndX(),   t.GetEndY())):
            key = (nc, (px + snap // 2) // snap, (py + snap // 2) // snap)
            if t.GetLayer() == f_cu:
                f_endpoints.setdefault(key, []).append((t, px, py))
            elif t.GetLayer() == b_cu:
                b_endpoints.setdefault(key, []).append((t, px, py))
    # For each F endpoint that has a B endpoint on the same net at the
    # same snapped position AND no same-net via nearby, drop a via.
    # `same_net_vias` must look only at *vias* (not pads) since a pad
    # ending a track does not bridge layers.
    same_net_vias: dict[int, list[tuple[int, int]]] = {}
    for tr in list(board.GetTracks()):
        if tr.GetClass() != "PCB_VIA":
            continue
        p = tr.GetPosition()
        same_net_vias.setdefault(tr.GetNetCode(), []).append((p.x, p.y))
    # Plated through-hole pads do bridge layers; treat them like vias too.
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                p = pad.GetPosition()
                same_net_vias.setdefault(pad.GetNetCode(), []).append((p.x, p.y))
    placed: set[tuple[int, int, int]] = set()
    overlap_keys = [k for k in f_endpoints if k in b_endpoints]
    print(f"  [transition-via] {len(overlap_keys)} F/B overlapping endpoints across nets")
    skipped_nearby = 0
    skipped_clear = 0
    for key in overlap_keys:
        if key in placed:
            continue
        nc = key[0]
        f_items = f_endpoints[key]
        f_t, fx, fy = f_items[0]
        x, y = fx, fy
        # Only skip if an *actual* same-net via/PTH already sits on this
        # endpoint (tolerance 10 µm). KiCad's DRC treats near-but-not-
        # touching vias as unconnected, so we must still drop a via when
        # the existing one is more than a hair away.
        nearby = same_net_vias.get(nc, [])
        if any((vx - x) ** 2 + (vy - y) ** 2 < (to_nm(0.010)) ** 2
                for vx, vy in nearby):
            skipped_nearby += 1
            continue
        # Build a set of offsets: (0,0) is the ideal; then nudge along
        # each participating track toward its other endpoint to find a
        # clear spot while remaining *on* that track. Offsets are small
        # multiples of 0.10 mm.
        nudges = [(0, 0)]
        for layer_items in (f_items, b_endpoints.get(key, [])):
            for trk, tx, ty in layer_items:
                # Compute the unit vector from (tx,ty) -> other end.
                ox = trk.GetStartX() if (trk.GetEndX(), trk.GetEndY()) == (tx, ty) else trk.GetEndX()
                oy = trk.GetStartY() if (trk.GetEndX(), trk.GetEndY()) == (tx, ty) else trk.GetEndY()
                dx, dy = ox - tx, oy - ty
                ln = (dx * dx + dy * dy) ** 0.5
                if ln < 1:
                    continue
                ux, uy = dx / ln, dy / ln
                for step_um in (100, 200, 300, 400, 500):
                    nudges.append((int(ux * step_um * 1000), int(uy * step_um * 1000)))
        # Try netclass via, fall back to min via that still satisfies the
        # board's 0.3 mm min hole rule.
        placed_here = False
        for nudge_x, nudge_y in nudges:
            if placed_here:
                break
            px, py = x + nudge_x, y + nudge_y
            for cand_d, cand_drill in ((via_d, via_drill), (0.6, 0.3)):
                cand_r = to_nm(cand_d) // 2
                if via_clear_at(px, py, cand_r, clearance_nm,
                                pad_via_haz, track_segs, nc):
                    net = f_t.GetNet()
                    build_via(board, net, px, py, cand_d, cand_drill,
                              top="F.Cu", bottom="B.Cu")
                    pad_via_haz.append((px, py, cand_r + to_nm(0.10), nc))
                    same_net_vias.setdefault(nc, []).append((px, py))
                    placed.add(key)
                    fixed += 1
                    placed_here = True
                    break
        if not placed_here:
            skipped_clear += 1
    print(f"  [transition-via] skipped {skipped_nearby} near existing via/PTH, {skipped_clear} no clearance")
    return fixed


def repair_degenerate_layer_transitions(board, classes) -> int:
    """The autorouter occasionally emits a zero-length track on the bottom
    layer instead of a via where two same-net tracks change layer. Find
    every zero-length track that coincides with the endpoint of an
    opposite-layer track on the same net and replace it with a via."""
    fixed = 0
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    by_endpoint: dict[tuple[int, int], list] = {}
    for t in tracks:
        by_endpoint.setdefault((t.GetStartX(), t.GetStartY()), []).append(t)
        if (t.GetStartX(), t.GetStartY()) != (t.GetEndX(), t.GetEndY()):
            by_endpoint.setdefault((t.GetEndX(), t.GetEndY()), []).append(t)
    f_cu = board.GetLayerID("F.Cu")
    b_cu = board.GetLayerID("B.Cu")
    via_d = classes["GND"]["via_diameter"]
    via_drill = classes["GND"]["via_drill"]
    pad_via_haz = collect_pad_via_hazards(board)
    track_segs = collect_track_segments(board)
    via_r = to_nm(via_d) // 2
    clearance_nm = to_nm(0.20) + to_nm(0.05)
    for t in list(tracks):
        # Treat <1 um as zero-length (autorouter snap noise)
        dx = t.GetEndX() - t.GetStartX()
        dy = t.GetEndY() - t.GetStartY()
        if dx * dx + dy * dy >= 1_000_000:  # >= 1um sqr
            continue
        x, y = t.GetStartX(), t.GetStartY()
        layer = t.GetLayer()
        layer = t.GetLayer()
        # Look for any same-net track on the *other* copper layer that
        # touches this point (within 50 um snap).
        sister = []
        for s in tracks:
            if s is t or s.GetNetCode() != t.GetNetCode():
                continue
            if s.GetLayer() == layer:
                continue
            for ax, ay in ((s.GetStartX(), s.GetStartY()),
                           (s.GetEndX(),   s.GetEndY())):
                if (ax - x) ** 2 + (ay - y) ** 2 < 2_500_000_000:  # 50 um
                    sister.append(s)
                    break
        if not sister:
            board.Remove(t)
            continue
        # Already a same-net via nearby? Just remove the stub.
        existing_via = False
        for hx, hy, hr, hnet in pad_via_haz:
            if hnet != t.GetNetCode():
                continue
            if (hx - x) ** 2 + (hy - y) ** 2 < (to_nm(0.4)) ** 2:
                existing_via = True
                break
        if existing_via:
            board.Remove(t)
            continue
        net = t.GetNet()
        if not via_clear_at(x, y, via_r, clearance_nm,
                            pad_via_haz, track_segs, t.GetNetCode()):
            board.Remove(t)
            continue
        build_via(board, net, x, y, via_d, via_drill, top="F.Cu", bottom="B.Cu")
        board.Remove(t)
        pad_via_haz.append((x, y, via_r + to_nm(0.10), t.GetNetCode()))
        fixed += 1
    return fixed


def add_vbat_pad_vias(board, classes) -> int:
    """Drop a via right next to every VBAT_SYS SMD pad so the pad can
    actually reach the In2.Cu (PWR) plane. Skips pads with an existing
    via within 0.6 mm or where no clear spot exists nearby."""
    code = board.GetNetcodeFromNetname("/VBAT_SYS")
    if code < 0:
        return 0
    net = board.GetNetInfo().GetNetItem(code)
    via_d = classes["POWER_HI"]["via_diameter"]
    via_drill = classes["POWER_HI"]["via_drill"]
    via_r = to_nm(via_d) // 2
    clearance_nm = to_nm(0.20) + to_nm(0.05)  # netclass clearance + safety
    pad_via_haz = collect_pad_via_hazards(board)
    track_segs = collect_track_segments(board)
    existing_vbat_vias = [(p[0], p[1]) for p in pad_via_haz if p[3] == code]
    added = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != code:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            cx, cy = pad.GetPosition().x, pad.GetPosition().y
            if any((cx - vx) ** 2 + (cy - vy) ** 2 < to_nm(0.6) ** 2
                    for vx, vy in existing_vbat_vias):
                continue
            half_x = pad.GetSizeX() // 2
            half_y = pad.GetSizeY() // 2
            # Try via-on-pad first; pad is large enough for KiCad to merge
            # them. Then fall back to perimeter offsets.
            offsets = [(0, 0)]
            if via_r * 2 < min(pad.GetSizeX(), pad.GetSizeY()):
                # Center stack works only if via fits inside the pad.
                pass
            else:
                offsets = []
            offsets += [
                (half_x + via_r + to_nm(0.20), 0),
                (-half_x - via_r - to_nm(0.20), 0),
                (0, half_y + via_r + to_nm(0.20)),
                (0, -half_y - via_r - to_nm(0.20)),
                (half_x + via_r + to_nm(0.20), half_y + via_r + to_nm(0.20)),
                (-half_x - via_r - to_nm(0.20), half_y + via_r + to_nm(0.20)),
                (half_x + via_r + to_nm(0.20), -half_y - via_r - to_nm(0.20)),
                (-half_x - via_r - to_nm(0.20), -half_y - via_r - to_nm(0.20)),
            ]
            for dx, dy in offsets:
                vx, vy = cx + dx, cy + dy
                if via_clear_at(vx, vy, via_r, clearance_nm,
                                pad_via_haz, track_segs, code):
                    build_via(board, net, vx, vy, via_d, via_drill)
                    existing_vbat_vias.append((vx, vy))
                    pad_via_haz.append((vx, vy, via_r + to_nm(0.10), code))
                    added += 1
                    break
    return added


def add_gnd_stitch_grid(board, classes,
                        spacing_mm: float = 6.0,
                        margin_mm: float = 2.0) -> int:
    """Drop a coarse GND via grid across the board, skipping any cell that
    collides with existing copper / pads / vias of *another* net.

    Stagger every other row by half a step to densify coverage without
    inflating via count."""
    code = board.GetNetcodeFromNetname("/GND")
    if code < 0:
        return 0
    net = board.GetNetInfo().GetNetItem(code)
    via_d = classes["GND"]["via_diameter"]
    via_drill = classes["GND"]["via_drill"]
    via_r = to_nm(via_d) // 2
    clearance_nm = to_nm(0.20) + to_nm(0.05)  # netclass + safety
    pad_via_haz = collect_pad_via_hazards(board)
    track_segs = collect_track_segments(board)
    bb = board.GetBoardEdgesBoundingBox()
    x_lo = bb.GetX() + to_nm(margin_mm)
    x_hi = bb.GetRight() - to_nm(margin_mm)
    y_lo = bb.GetY() + to_nm(margin_mm)
    y_hi = bb.GetBottom() - to_nm(margin_mm)
    step = to_nm(spacing_mm)
    half_step = step // 2
    added = 0
    row = 0
    y = y_lo
    while y <= y_hi:
        x = x_lo + (half_step if row & 1 else 0)
        while x <= x_hi:
            if via_clear_at(x, y, via_r, clearance_nm,
                            pad_via_haz, track_segs, code):
                build_via(board, net, x, y, via_d, via_drill)
                pad_via_haz.append((x, y, via_r + to_nm(0.10), code))
                added += 1
            x += step
        y += step
        row += 1
    return added


def widen_power_tracks(board, classes, net_to_class) -> tuple[int, int]:
    """Bump every power-netclass track to its netclass width.

    Returns (widened, untouched). DRC-driven backoff is performed by
    `iterate_drc_backoff` after this pass."""
    widened = 0
    untouched = 0
    for t in list(board.GetTracks()):
        if t.GetClass() not in ("PCB_TRACK", "PCB_ARC"):
            continue
        net = t.GetNet()
        if net is None:
            continue
        target = power_target_width(net.GetNetname(), net_to_class, classes)
        if target is None:
            untouched += 1
            continue
        cur_mm = mm(t.GetWidth())
        if cur_mm + 1e-6 < target:
            t.SetWidth(to_nm(target))
            widened += 1
        else:
            untouched += 1
    return widened, untouched


def run_drc(board) -> dict:
    """Run DRC via kicad-cli and return parsed JSON. Saves the board first."""
    DRC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    board.Save(str(PCB))
    subprocess.run([
        "kicad-cli", "pcb", "drc",
        "--schematic-parity",
        "--severity-all",
        "--units", "mm",
        "--format", "json",
        "--output", str(DRC_REPORT),
        str(PCB),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads(DRC_REPORT.read_text())


def iterate_drc_backoff(board, classes, net_to_class, max_passes: int = 12) -> tuple[int, dict]:
    """Iterate: run DRC, find clearance / shorting violations on widened
    power tracks (or stitch vias we just placed), drop width to the next
    step (or remove the via), repeat until DRC clean for error severity."""
    backoffs = 0
    removed_vias = 0
    last_drc = run_drc(board)
    for pass_n in range(max_passes):
        violations = last_drc.get("violations", [])
        clearance_errors = [
            v for v in violations
            if v.get("type") in ("clearance", "shorting_items",
                                  "copper_edge_clearance", "tracks_crossing")
            and v.get("severity") == "error"
        ]
        if not clearance_errors:
            print(f"  [drc] pass {pass_n}: clean (errors={sum(1 for v in violations if v['severity']=='error')})")
            return backoffs, last_drc
        print(f"  [drc] pass {pass_n}: {len(clearance_errors)} clearance/shorting errors")

        targets: list[tuple[int, int]] = []
        for v in clearance_errors:
            for item in v.get("items", []):
                pos = item.get("pos") or {}
                if "x" in pos and "y" in pos:
                    targets.append((to_nm(pos["x"]), to_nm(pos["y"])))
        tol_track = to_nm(0.4)
        tol_via = to_nm(0.6)
        tol_t2 = tol_track * tol_track
        tol_v2 = tol_via * tol_via

        backoff_this_pass = 0
        # First pass: widen-back tracks
        for t in list(board.GetTracks()):
            if t.GetClass() not in ("PCB_TRACK", "PCB_ARC"):
                continue
            net = t.GetNet()
            if net is None:
                continue
            if power_target_width(net.GetNetname(), net_to_class, classes) is None:
                continue
            cur_mm = mm(t.GetWidth())
            if cur_mm <= 0.20 + 1e-6:
                continue
            sx, sy, ex, ey = t.GetStartX(), t.GetStartY(), t.GetEndX(), t.GetEndY()
            hit = False
            for tx, ty in targets:
                if _seg_point_dist2(tx, ty, sx, sy, ex, ey) <= tol_t2:
                    hit = True
                    break
            if not hit:
                continue
            for w in WIDTH_STEPS_MM:
                if w + 1e-6 < cur_mm:
                    t.SetWidth(to_nm(w))
                    backoff_this_pass += 1
                    break

        # Second pass: drop GND/VBAT stitch vias whose center sits within
        # `tol_via` of a violation centroid. We only remove vias whose net
        # is GND or VBAT_SYS to avoid yanking real circuit vias.
        gnd_code = board.GetNetcodeFromNetname("/GND")
        vbat_code = board.GetNetcodeFromNetname("/VBAT_SYS")
        modem_code = board.GetNetcodeFromNetname("/MODEM_VBAT_SW")
        to_remove = []
        for t in list(board.GetTracks()):
            if t.GetClass() != "PCB_VIA":
                continue
            if t.GetNetCode() not in (gnd_code, vbat_code, modem_code):
                continue
            vx, vy = t.GetPosition().x, t.GetPosition().y
            for tx, ty in targets:
                if (vx - tx) ** 2 + (vy - ty) ** 2 <= tol_v2:
                    to_remove.append(t)
                    break
        for t in to_remove:
            board.Remove(t)
            removed_vias += 1

        backoffs += backoff_this_pass
        if backoff_this_pass == 0 and not to_remove:
            print(f"  [warn] pass {pass_n+1}: {len(clearance_errors)} errors but no fix matched -- giving up")
            return backoffs, last_drc
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        last_drc = run_drc(board)
    return backoffs, last_drc


def remove_orphan_vias(board) -> int:
    """Remove the GND stitch vias we just placed if they ended up sitting
    inside a non-GND net's keep-out (defensive). The DRC pass will tell us
    via dangling errors; if found, drop them."""
    return 0  # placeholder hook; current grid filter is generous


def main() -> int:
    print(f"[fix_power_rails] loading {PCB.name}")
    classes, net_to_class = load_netclass_targets()
    board = pcbnew.LoadBoard(str(PCB))

    widened, untouched = widen_power_tracks(board, classes, net_to_class)
    print(f"[fix_power_rails] widened {widened} power-net segments (left {untouched} alone)")

    vbat_added = add_vbat_pad_vias(board, classes)
    print(f"[fix_power_rails] added {vbat_added} VBAT_SYS pad-stitch vias to In2.Cu plane")

    gnd_added = add_gnd_stitch_grid(board, classes, spacing_mm=6.0, margin_mm=2.0)
    print(f"[fix_power_rails] added {gnd_added} GND stitch vias")

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    print("[fix_power_rails] iterating DRC + back-off ...")
    backoffs, drc = iterate_drc_backoff(board, classes, net_to_class, max_passes=12)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(PCB))

    # Re-load fresh; close any layer-transition gaps the autorouter forgot
    # to via-stitch. Done on a clean LoadBoard to avoid SWIG iterator
    # corruption from prior mutations.
    board2 = pcbnew.LoadBoard(str(PCB))
    via_fixed = repair_missing_layer_transition_vias(board2, classes)
    deg_fixed = repair_degenerate_layer_transitions(board2, classes)
    pcbnew.ZONE_FILLER(board2).Fill(board2.Zones())
    board2.Save(str(PCB))
    print(f"[fix_power_rails] added {via_fixed} missing layer-transition vias, removed {deg_fixed} degenerate stubs")
    drc = run_drc(board2)

    err = sum(1 for v in drc.get("violations", []) if v.get("severity") == "error")
    warn = sum(1 for v in drc.get("violations", []) if v.get("severity") == "warning")
    parity = drc.get("schematic_parity_violations", [])
    unconn = drc.get("unconnected_items", [])
    print(f"[fix_power_rails] backoffs={backoffs}  drc_errors={err}  drc_warnings={warn}  parity={len(parity)}  unconnected={len(unconn)}")
    if err:
        print("[fix_power_rails] WARNING: DRC errors remain; see", DRC_REPORT)
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
