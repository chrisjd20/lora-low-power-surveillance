#!/usr/bin/env python3
"""
Phase 18c — Clear tracks + run Freerouting + import SES.

Re-routes the entire board after Phase 18a/b added J4, J5, F1, R24 and
relocated TP4. Reuses the Docker + Freerouting + phase4_import_ses
pipeline established in Phase 4 / Phase 9.

Steps:
    1. Load board.
    2. Delete every PCB_TRACK and PCB_VIA.
    3. Save pre-route snapshot.
    4. Export DSN -> build/warden.dsn.
    5. Run Freerouting (Docker, eclipse-temurin:21-jre) -> build/warden.ses.
    6. Invoke tools/phase4_import_ses.py.
    7. Refill zones (done inside phase4_import_ses).

Run ONCE after phase18_add_expansion.py + phase18_place.py have set up
the schematic, footprints, and /NET-form pad assignments.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pcbnew

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware/warden-apex-master/warden-apex-master.kicad_pcb"
BUILD = ROOT / "build"
FR_JAR = pathlib.Path.home() / ".kicad-mcp/freerouting.jar"


def clear_tracks(board: pcbnew.BOARD) -> int:
    tracks = list(board.Tracks())
    for t in tracks:
        board.Remove(t)
    return len(tracks)


def main() -> int:
    BUILD.mkdir(exist_ok=True)

    board = pcbnew.LoadBoard(str(PCB))
    n = clear_tracks(board)
    print(f"Cleared {n} tracks / vias for re-route.")
    board.Save(str(PCB))

    dsn = BUILD / "warden.dsn"
    ses = BUILD / "warden.ses"
    ses.unlink(missing_ok=True)

    print(f"Exporting DSN -> {dsn}")
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    if not dsn.exists():
        print("DSN export failed; aborting.")
        return 1

    if not FR_JAR.exists():
        print(f"freerouting.jar missing at {FR_JAR}; cannot autoroute.")
        return 1

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{BUILD}:/work",
        "-v", f"{FR_JAR}:/opt/freerouting.jar",
        "-w", "/work",
        "eclipse-temurin:21-jre",
        "java", "-jar", "/opt/freerouting.jar",
        "-de", "/work/warden.dsn",
        "-do", "/work/warden.ses",
        "-mp", "30",
        "-host-mode", "cli",
    ]
    print("Running Freerouting (Docker) …")
    r = subprocess.run(cmd, capture_output=True, text=True)
    # print last ~25 lines of stdout to keep log manageable
    tail = "\n".join(r.stdout.splitlines()[-25:])
    print(tail)
    if r.returncode != 0:
        print(f"freerouting exited {r.returncode}")
        print(r.stderr[-1000:])

    if not ses.exists():
        print("No SES produced; aborting import.")
        return 2

    print("Importing SES via phase4_import_ses.py …")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/phase4_import_ses.py")],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
