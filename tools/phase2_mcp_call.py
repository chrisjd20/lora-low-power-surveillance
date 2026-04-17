#!/usr/bin/env python3
"""
Thin stdio client for the KiCAD MCP server. Reads a JSON argument blob
from a file, calls a named tool on the server, prints the response.

Usage:
    python3 tools/phase2_mcp_call.py <toolName> <argsJsonPath>
    python3 tools/phase2_mcp_call.py <toolName> --args '<inline_json>'
"""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MCP  = ROOT / "tools" / "KiCAD-MCP-Server" / "dist" / "index.js"


def call(tool: str, args: dict) -> dict:
    env = os.environ.copy()
    env.setdefault("KICAD_PYTHON", "/usr/bin/python3")
    env.setdefault("PYTHONPATH", "/usr/lib/python3/dist-packages")
    env.setdefault("LOG_LEVEL", "error")  # quiet

    p = subprocess.Popen(
        ["node", str(MCP)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    def send(obj):
        p.stdin.write(json.dumps(obj) + "\n")
        p.stdin.flush()

    def read_reply(expected_id):
        while True:
            line = p.stdout.readline()
            if not line:
                return None
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if msg.get("id") == expected_id:
                return msg

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "phase2", "version": "1"}}})
    read_reply(1)
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": tool, "arguments": args}})
    reply = read_reply(2)
    try:
        p.stdin.close()
    except Exception:
        pass
    try:
        p.terminate()
        p.wait(timeout=5)
    except Exception:
        p.kill()
    return reply or {"error": "no reply"}


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: phase2_mcp_call.py <toolName> <argsJsonPath|--args JSON>", file=sys.stderr)
        return 2
    tool = sys.argv[1]
    spec = sys.argv[2]
    if spec == "--args":
        if len(sys.argv) < 4:
            print("need JSON after --args", file=sys.stderr)
            return 2
        args = json.loads(sys.argv[3])
    else:
        args = json.loads(pathlib.Path(spec).read_text())
    reply = call(tool, args)
    print(json.dumps(reply, indent=2))
    # Return non-zero if the reply contains an error
    if reply.get("error"):
        return 1
    res = reply.get("result", {})
    content = res.get("content") if isinstance(res, dict) else None
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    body = json.loads(item.get("text", "{}"))
                    if body.get("success") is False:
                        return 1
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
