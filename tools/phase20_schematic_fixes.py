#!/usr/bin/env python3
"""
Phase 20 - Schematic surgical fixes.

Closes four catastrophic schematic-level flaws found in the audit:

1. IC1.69 (SIM7080G VDD_EXT) was tied to /3V3.  VDD_EXT is a 1.8 V
   output from the modem's internal LDO; tying it to 3.3 V short-
   circuits the LDO and can destroy the modem at power-up.  Move
   IC1.69 (and its dedicated decoupler C29) onto a new isolated net
   `SIM_VDD_EXT` so the VDD_EXT rail is left floating with 100 nF of
   decoupling to GND.

2. U3.12 (Swarm M138 UART_TX output) was labelled `UART1_RX`.  When
   stuffed alongside the SIM7080G on the Apex build, two TX outputs
   collided on the same net -- the host-side `UART1_RX` net is driven
   by both `IC1.40 UART1_TXD` and `U3.12 UART_TX`.  Move U3.12 onto
   the satellite UART (`UART2_RX`) so the Swarm reaches the SC16IS740
   via JP4 only.

3. U3.28 (Swarm M138 UART_RX input) was labelled `UART1_TX`.  Both
   modem RX inputs were listening to the same host TX net.  Move to
   `UART2_TX` so JP3 is the only path from the SC16IS740 into the
   Swarm.

4. The ESP32-S3 (U1) had no UART pins wired to either modem.  Add
   host-side labels to U1.7 (GPIO43 / UART0 TX) and U1.8 (GPIO44 /
   UART0 RX) so the XIAO actually reaches the cellular modem on the
   `UART1_*` nets.  (The SC16IS740 bridge is driven via I2C from the
   XIAO, per VARIANTS.md firmware auto-detect, so no UART2 on the
   XIAO is required.)

All edits are done on exact-position `(label ...)` entries in the
schematic text.  Labels are at each pin's connection tip because the
Phase 2 workaround placed them there directly (see PLAN.md Phase 2
"Known MCP server caveat").
"""
from __future__ import annotations

import pathlib
import re
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCH_PATH = ROOT / "hardware" / "warden-apex-master" / "warden-apex-master.kicad_sch"


# -------- fix table --------------------------------------------------
# Each entry is (old_label, new_label, x, y).  We rename the UNIQUE
# `(label "old" (at x y R))` entry at the given coordinate only.
RENAMES: list[tuple[str, str, float, float]] = [
    # IC1.69 VDD_EXT -> new SIM_VDD_EXT net
    ("3V3", "SIM_VDD_EXT", 114.30, 280.67),
    # C29.1 (IC1 VDD_EXT decoupler) -> same new net
    ("3V3", "SIM_VDD_EXT", 215.90, 173.99),
    # U3.12 Swarm UART_TX output -> UART2_RX (goes through JP4 to U6 RX)
    ("UART1_RX", "UART2_RX", 165.10, 245.11),
    # U3.28 Swarm UART_RX input -> UART2_TX (comes through JP3 from U6 TX)
    ("UART1_TX", "UART2_TX", 165.10, 285.75),
]

# No-connect flags that must be removed because the repurposed pins are
# now actively wired.  Each entry is (x, y).
NC_REMOVES: list[tuple[float, float]] = [
    # U1.19 MTD0 was Phase-2 NC; now drives UART1_TX
    (215.90, 153.67),
    # U1.18 MTDI was Phase-2 NC; now receives UART1_RX
    (215.90, 151.13),
]

# New labels to add at pin endpoints.  Each is (name, x, y).
#
# IMPORTANT pin-allocation note: U1 pads 7 and 8 (GPIO43/44, the XIAO's
# stock "D6 TX / D7 RX" header) are already assigned to the I2S audio
# bus (I2S_DOUT / I2S_LRCLK) for the MAX98357A.  We cannot reuse them
# without ripping up the speaker path.  The ESP32-S3 UART matrix is
# fully muxable, so we reuse two otherwise-free JTAG pins:
#
#   MTD0 (pin 19, GPIO40) -> UART1_TX  (host TX to SIM7080 RXD)
#   MTDI (pin 18, GPIO41) -> UART1_RX  (host RX from SIM7080 TXD)
#
# JTAG itself is inaccessible after this but it was never bonded out
# on Warden -- only MTMS was ever reused (for LORA_DIO1 in Phase 2).
ADDS: list[tuple[str, float, float]] = [
    # U1.19 MTD0 -> UART1_TX
    ("UART1_TX", 215.90, 153.67),
    # U1.18 MTDI -> UART1_RX
    ("UART1_RX", 215.90, 151.13),
]


def _fmt_coord(v: float) -> str:
    """KiCad uses mixed decimal precision.  Try common forms so the
    regex we build matches the text as-is."""
    # KiCad typically writes "114.3" not "114.30".
    s1 = f"{v:g}"
    s2 = f"{v:.2f}"
    s3 = f"{v:.1f}"
    return s1, s2, s3


def _find_label(data: str, name: str, x: float, y: float) -> tuple[int, int] | None:
    """Return the (start, end) span of a single `(label "name" (at X Y R)
    ...)` item whose coordinates match."""
    xs = _fmt_coord(x)
    ys = _fmt_coord(y)
    # Build a pattern that matches any (start/end) coordinate formatting.
    x_alt = "|".join(re.escape(s) for s in set(xs))
    y_alt = "|".join(re.escape(s) for s in set(ys))
    pat = re.compile(
        r"\(label\s+\"" + re.escape(name) + r"\"\s+\(at\s+(?:" + x_alt + r")\s+(?:" + y_alt + r")\s+\d+\)"
        r"\s*\(effects\s+\(font\s+\(size\s+[\d.]+\s+[\d.]+\)\)\s+\(justify\s+\w+\s+\w+\)\)"
        r"\s*\(uuid\s+\"[0-9a-f-]+\"\)\s*\)",
        re.S,
    )
    m = pat.search(data)
    if not m:
        return None
    return m.span()


def _label_block(name: str, x: float, y: float, rot: int = 0) -> str:
    u = uuid.uuid4()
    return (
        f'(label "{name}" (at {x:g} {y:g} {rot})\n'
        f"\t\t(effects (font (size 1.27 1.27)) (justify left bottom))\n"
        f'\t\t(uuid "{u}")\n'
        f"\t)"
    )


def main() -> int:
    data = SCH_PATH.read_text()
    orig_len = len(data)

    # 1) Renames.
    for old, new, x, y in RENAMES:
        span = _find_label(data, old, x, y)
        if span is None:
            print(f"!! rename FAILED: no '{old}' label at ({x}, {y}) -- aborting")
            return 2
        block = data[span[0] : span[1]]
        # Change just the name string.
        new_block = block.replace(f'"{old}"', f'"{new}"', 1)
        data = data[: span[0]] + new_block + data[span[1] :]
        print(f"   renamed label at ({x}, {y}): '{old}' -> '{new}'")

    # 2) Remove no-connect flags that are now actively wired.
    for x, y in NC_REMOVES:
        xa = "|".join(re.escape(s) for s in set(_fmt_coord(x)))
        ya = "|".join(re.escape(s) for s in set(_fmt_coord(y)))
        pat = re.compile(
            r"\s*\(no_connect\s+\(at\s+(?:" + xa + r")\s+(?:" + ya + r")\)\s+\(uuid\s+\"[0-9a-f-]+\"\)\s*\)",
            re.S,
        )
        m = pat.search(data)
        if m is None:
            print(f"   no_connect at ({x}, {y}) already absent -- skip")
            continue
        data = data[: m.start()] + data[m.end() :]
        print(f"   removed no_connect at ({x}, {y})")

    # 3) Adds.
    # We insert each new label block just before the schematic `(sheet_instances`
    # / `(symbol_instances` footer to keep structure valid.  Conveniently,
    # labels already exist in the file, so we just append after the last label.
    # Find the `\n)` at end of file (closing of kicad_sch).
    for name, x, y in ADDS:
        # Guard against double-add if script is re-run.
        existing = _find_label(data, name, x, y)
        if existing is not None:
            print(f"   label '{name}' at ({x}, {y}) already exists -- skip")
            continue
        # Find a good insertion point: after the last `(label ...)` uuid line.
        uuids = list(re.finditer(r"\(label\s+\"[^\"]+\"[^\n]*\n[^\n]*\n[^\n]*\(uuid\s+\"[0-9a-f-]+\"\)\s*\)", data))
        if not uuids:
            # fallback: insert before the last closing paren of the file
            last_label_end = data.rfind(")")
        else:
            last_label_end = uuids[-1].end()
        block = "\n\t" + _label_block(name, x, y, rot=0)
        data = data[:last_label_end] + block + data[last_label_end:]
        print(f"   added label at ({x}, {y}): '{name}'")

    SCH_PATH.write_text(data)
    print(f"-- wrote {SCH_PATH.name}: {orig_len} -> {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
