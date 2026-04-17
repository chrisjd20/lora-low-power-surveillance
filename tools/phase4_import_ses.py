#!/usr/bin/env python3
"""
Direct Specctra SES → KiCad PCB applier.

`pcbnew.ImportSpecctraSES` returns False for our board (unclear why — the
SES looks well-formed and Freerouting produced it successfully). Rather
than debug the C++ importer, this script parses the SES file ourselves
and adds `PCB_TRACK` / `PCB_VIA` objects directly via the pcbnew Python
API.

SES units: resolution declared per file (we read it). Typical `um 10`
means each integer coordinate is 0.1 µm. Y axis in SES is negated
relative to KiCad.
"""
from __future__ import annotations
import pathlib
import re
import sys
import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB  = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
SES  = ROOT / "build/warden.ses"


# s-expression tokenizer + simple parser -----------------------------------
def tokenize(text: str):
    pos = 0
    while pos < len(text):
        c = text[pos]
        if c.isspace():
            pos += 1
        elif c == '(':
            yield '('
            pos += 1
        elif c == ')':
            yield ')'
            pos += 1
        elif c == '"':
            end = text.find('"', pos + 1)
            yield text[pos:end+1]
            pos = end + 1
        else:
            end = pos
            while end < len(text) and not text[end].isspace() and text[end] not in '()':
                end += 1
            yield text[pos:end]
            pos = end


def parse(text: str):
    toks = list(tokenize(text))
    i = 0
    def r():
        nonlocal i
        t = toks[i]; i += 1
        if t == '(':
            out = []
            while toks[i] != ')':
                out.append(r())
            i += 1  # eat )
            return out
        return t
    return r()


def find(tree, head):
    if isinstance(tree, list):
        for c in tree:
            if isinstance(c, list) and c and c[0] == head:
                yield c


def walk(tree):
    if isinstance(tree, list):
        yield tree
        for c in tree:
            yield from walk(c)


def main() -> int:
    board = pcbnew.LoadBoard(str(PCB))
    netinfo = board.GetNetInfo()
    nets_by_name = netinfo.NetsByName()
    layer_ids = {
        "F.Cu":   board.GetLayerID("F.Cu"),
        "B.Cu":   board.GetLayerID("B.Cu"),
        "In1.Cu": board.GetLayerID("In1.Cu"),
        "In2.Cu": board.GetLayerID("In2.Cu"),
    }

    text = SES.read_text()
    # strip "(session" wrapper
    tree = parse(text)
    # Find resolution
    res_um = 10.0  # default
    for r in walk(tree):
        if isinstance(r, list) and r and r[0] == "resolution" and len(r) >= 3:
            units = r[1]
            value = float(r[2])
            if units == "um":
                res_um = value
            break
    print(f"SES resolution: 1 unit = {1/res_um} um")

    # Helper: SES integer -> nm for pcbnew VECTOR2I (1 IU = 1 nm)
    def ses_to_nm(x_str: str) -> int:
        return int(float(x_str) * 1000.0 / res_um)  # SES_unit -> um -> nm

    added_wires = 0
    added_vias  = 0
    skipped     = 0

    for net_block in walk(tree):
        if not (isinstance(net_block, list) and net_block and net_block[0] == "net"):
            continue
        if len(net_block) < 2:
            continue
        net_name = net_block[1].strip('"')
        if not nets_by_name.has_key(net_name):
            skipped += 1
            continue
        net = nets_by_name[net_name]

        # Extract wires and vias (direct children only)
        for child in net_block[2:]:
            if not isinstance(child, list):
                continue
            head = child[0]
            if head == "wire":
                # (wire (path LAYER WIDTH X1 Y1 X2 Y2 ...))
                for path in find(child, "path"):
                    if len(path) < 7:
                        continue
                    layer_name = path[1].strip('"')
                    # Freerouting sometimes emits "signal" or uppercase "F.Cu"; map robustly
                    layer_id = layer_ids.get(layer_name)
                    if layer_id is None:
                        # Try case fold
                        for k, v in layer_ids.items():
                            if k.lower() == layer_name.lower():
                                layer_id = v; break
                    if layer_id is None:
                        continue
                    width_nm = ses_to_nm(path[2])
                    coords = path[3:]
                    # coords are alternating X Y, add a track segment between each pair
                    points = []
                    for j in range(0, len(coords), 2):
                        if j + 1 >= len(coords):
                            break
                        x = ses_to_nm(coords[j])
                        y = -ses_to_nm(coords[j + 1])  # SES Y is negated
                        points.append((x, y))
                    for (x1, y1), (x2, y2) in zip(points, points[1:]):
                        tr = pcbnew.PCB_TRACK(board)
                        tr.SetStart(pcbnew.VECTOR2I(x1, y1))
                        tr.SetEnd(pcbnew.VECTOR2I(x2, y2))
                        tr.SetWidth(width_nm)
                        tr.SetLayer(layer_id)
                        tr.SetNet(net)
                        board.Add(tr)
                        added_wires += 1
            elif head == "via":
                # (via "Name" X Y)
                if len(child) < 4:
                    continue
                x = ses_to_nm(child[2])
                y = -ses_to_nm(child[3])
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(x, y))
                # Pull diameter / drill from name if present "Via[0-3]_600:300_um"
                m = re.search(r"(\d+):(\d+)", child[1] if child[1] else "")
                if m:
                    diam_um = int(m.group(1))
                    drill_um = int(m.group(2))
                    via.SetWidth(int(diam_um * 1000))
                    via.SetDrill(int(drill_um * 1000))
                else:
                    via.SetWidth(int(600 * 1000))
                    via.SetDrill(int(300 * 1000))
                via.SetLayerPair(layer_ids["F.Cu"], layer_ids["B.Cu"])
                via.SetNet(net)
                board.Add(via)
                added_vias += 1

    # Re-fill zones
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(str(PCB))
    print(f"added {added_wires} wires + {added_vias} vias, {skipped} nets skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
