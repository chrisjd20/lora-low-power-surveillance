#!/usr/bin/env python3
"""
Extract a clean, normalized netlist from Flux's EDIF 2.0 export.

Flux encodes wires as tiny pseudo-instances with names like
    "IC4 OUTN - J3 P2"
that reference a generic "Net Portal" or "Ground" cell. The authoritative
connectivity lives later in the file inside `(Net NAME (joined (portRef ...)))`
blocks. We parse those blocks, drop all references back into Net Portal /
Ground pseudo-instances, and keep only the real (designator, pin) endpoints.

Output:  hardware/warden-apex-master/flux-netlist.json
    {
      "components": [ { "ref": "IC2", "cell": "BQ24650RVAR" }, ... ],
      "nets":       [ { "name": "3V3", "nodes": [["IC3","VOUT_2"], ...] }, ... ],
      "stats":      { "components": N, "nets": M, "nodes": K }
    }
"""
from __future__ import annotations
import json
import pathlib
import sys

try:
    import sexpdata
except ImportError:
    sys.exit("pip install sexpdata first")


ROOT = pathlib.Path(__file__).resolve().parents[1]
EDIF = ROOT / "flux-archive" / "chrisjd20-warden-apex-master.edif"
OUT  = ROOT / "hardware" / "warden-apex-master" / "flux-netlist.json"


def sym_name(x) -> str:
    """Get the printable name from a Symbol / str / bytes leaf."""
    if isinstance(x, sexpdata.Symbol):
        return x.value()
    if isinstance(x, (str, bytes)):
        return x.decode() if isinstance(x, bytes) else x
    return str(x)


def find(node, head):
    """Iterate direct children whose first element == head (case-insensitive)."""
    if not isinstance(node, list):
        return
    for child in node:
        if isinstance(child, list) and child and sym_name(child[0]).lower() == head.lower():
            yield child


def walk(node):
    """Depth-first walk, yielding every list node."""
    if isinstance(node, list):
        yield node
        for c in node:
            yield from walk(c)


def main() -> int:
    src = EDIF.read_text(encoding="utf-8")
    tree = sexpdata.loads(src)

    # --- Index every cell's pin list so we can filter out pseudo-instances ---
    #     A cell is a real part iff it has >=3 pins OR isn't Net Portal / Ground.
    pseudo_cells = {"net portal", "ground"}
    real_cells: dict[str, list[str]] = {}

    for lib in find(tree, "library"):
        for cell in find(lib, "cell"):
            if len(cell) < 2:
                continue
            cname = sym_name(cell[1])
            if cname.lower() in pseudo_cells:
                continue
            pins: list[str] = []
            for view in find(cell, "view"):
                for iface in find(view, "interface"):
                    for port in find(iface, "port"):
                        if len(port) >= 2:
                            pins.append(sym_name(port[1]))
            real_cells[cname] = pins

    # --- Walk the top design cell for instances (components) ---
    components: dict[str, str] = {}
    pseudo_instances: set[str] = set()

    for cell in walk(tree):
        if not (isinstance(cell, list) and cell and sym_name(cell[0]).lower() == "instance"):
            continue
        if len(cell) < 2:
            continue
        inst_name = sym_name(cell[1])
        # cellRef lives inside (viewRef schematic (cellRef NAME ...))
        cell_ref = None
        for vref in walk(cell):
            if isinstance(vref, list) and vref and sym_name(vref[0]).lower() == "cellref":
                if len(vref) >= 2:
                    cell_ref = sym_name(vref[1])
                    break
        if cell_ref is None:
            continue
        if cell_ref.lower() in pseudo_cells:
            pseudo_instances.add(inst_name)
        else:
            # Real component: instance name is the refdes (L3, C19, IC2, R15, ...)
            # Some duplicates possible across libraries; keep first.
            if inst_name not in components:
                components[inst_name] = cell_ref

    # --- Extract (Net NAME (joined (portRef PIN (instanceRef REF)) ... )) ---
    nets: list[dict] = []
    for node in walk(tree):
        if not (isinstance(node, list) and node and sym_name(node[0]) == "Net"):
            continue
        if len(node) < 2:
            continue
        net_name = sym_name(node[1])
        joined = None
        for child in node[2:]:
            if isinstance(child, list) and child and sym_name(child[0]).lower() == "joined":
                joined = child
                break
        if joined is None:
            continue

        seen: set[tuple[str, str]] = set()
        nodes: list[tuple[str, str]] = []
        for pr in joined[1:]:
            if not (isinstance(pr, list) and pr and sym_name(pr[0]).lower() == "portref"):
                continue
            if len(pr) < 3:
                continue
            pin = sym_name(pr[1])
            iref = pr[2]
            if not (isinstance(iref, list) and iref and sym_name(iref[0]).lower() == "instanceref"):
                continue
            ref = sym_name(iref[1]) if len(iref) >= 2 else ""
            if ref in pseudo_instances or ref not in components:
                continue  # drop Net Portal / Ground pseudo-components
            key = (ref, pin)
            if key in seen:
                continue
            seen.add(key)
            nodes.append(key)

        if nodes:
            nets.append({"name": net_name, "nodes": nodes})

    # GND is special: Flux uses Ground pseudo-components to attach pins to GND
    # rather than listing them in a (Net GND) entry. We recover them by
    # inspecting every Ground instance's **name**, which follows the pattern
    # "<REF1> <PIN1> - <REF2> <PIN2>" or similar. Easier path: read back the
    # instance names that reference cellRef Ground.
    gnd_pins: list[tuple[str, str]] = []
    for cell in walk(tree):
        if not (isinstance(cell, list) and cell and sym_name(cell[0]).lower() == "instance"):
            continue
        if len(cell) < 2:
            continue
        inst_name = sym_name(cell[1])
        cref = None
        for vref in walk(cell):
            if isinstance(vref, list) and vref and sym_name(vref[0]).lower() == "cellref":
                if len(vref) >= 2:
                    cref = sym_name(vref[1])
                    break
        if (cref or "").lower() != "ground":
            continue
        # parse "REF1 PIN1 - REF2 PIN2" (pins may contain underscores/digits)
        for side in inst_name.split(" - "):
            toks = side.strip().split(" ", 1)
            if len(toks) == 2 and toks[0] in components:
                gnd_pins.append((toks[0], toks[1]))

    # Merge gnd pins into the (Net GND ...) entry (or create one).
    gnd_net = next((n for n in nets if n["name"] == "GND"), None)
    if gnd_net is None:
        gnd_net = {"name": "GND", "nodes": []}
        nets.insert(0, gnd_net)
    existing = {tuple(n) for n in gnd_net["nodes"]}
    for node in gnd_pins:
        if node not in existing:
            gnd_net["nodes"].append(list(node))
            existing.add(node)

    # Normalize list-of-tuple nodes to list-of-list for JSON.
    for n in nets:
        n["nodes"] = [list(x) if not isinstance(x, list) else x for x in n["nodes"]]

    out = {
        "source": str(EDIF.relative_to(ROOT)),
        "components": [
            {"ref": r, "cell": c} for r, c in sorted(components.items())
        ],
        "nets": sorted(nets, key=lambda n: n["name"]),
        "stats": {
            "components": len(components),
            "nets": len(nets),
            "nodes": sum(len(n["nodes"]) for n in nets),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  components: {out['stats']['components']}")
    print(f"  nets:       {out['stats']['nets']}")
    print(f"  nodes:      {out['stats']['nodes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
