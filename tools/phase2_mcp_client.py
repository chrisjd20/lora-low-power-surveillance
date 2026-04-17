#!/usr/bin/env python3
"""
Persistent stdio client for the KiCAD MCP server. Keeps one server
subprocess alive across many tool calls, then exits cleanly.

Usage as a library:
    from phase2_mcp_client import McpSession
    with McpSession() as s:
        r = s.call("check_kicad_ui", {})
        s.call("add_schematic_component", {...})

Usage as a CLI:
    python3 tools/phase2_mcp_client.py run <batch.json>
        where batch.json is [{"tool": "...", "args": {...}}, ...]
    python3 tools/phase2_mcp_client.py call <tool> <args.json>
"""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys
import time
from contextlib import contextmanager

ROOT = pathlib.Path(__file__).resolve().parents[1]
MCP = ROOT / "tools" / "KiCAD-MCP-Server" / "dist" / "index.js"


class McpSession:
    def __init__(self, log_level: str = "error"):
        env = os.environ.copy()
        env.setdefault("KICAD_PYTHON", "/usr/bin/python3")
        env.setdefault("PYTHONPATH", "/usr/lib/python3/dist-packages")
        env.setdefault("LOG_LEVEL", log_level)
        self.proc = subprocess.Popen(
            ["node", str(MCP)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )
        self._next_id = 1
        # Initialize handshake
        self._send({
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "phase2", "version": "1"},
            },
        })
        self._read(self._next_id)
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read(self, expected_id, timeout=60.0):
        start = time.time()
        while time.time() - start < timeout:
            line = self.proc.stdout.readline()
            if not line:
                time.sleep(0.02)
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if msg.get("id") == expected_id:
                return msg
        raise TimeoutError(f"no reply for id {expected_id}")

    def call(self, tool: str, args: dict, timeout: float = 120.0) -> dict:
        self._next_id += 1
        rid = self._next_id
        self._send({
            "jsonrpc": "2.0",
            "id": rid,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        })
        reply = self._read(rid, timeout=timeout)
        if reply.get("error"):
            return {"success": False, "error": reply["error"]}
        content = (reply.get("result") or {}).get("content") or []
        for item in content:
            if item.get("type") == "text":
                text = item["text"]
                try:
                    parsed = json.loads(text)
                    return parsed
                except Exception:
                    # Plain-text response: treat as success unless it
                    # clearly signals an error.
                    lower = text.lower()
                    if any(w in lower for w in ("error", "failed", "exception", "cannot", "not found")):
                        return {"success": False, "raw": text}
                    return {"success": True, "raw": text}
        return {"success": False, "raw": reply}

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def run_batch(path: pathlib.Path, stop_on_error: bool = False) -> int:
    calls = json.loads(path.read_text())
    ok = 0
    fail = 0
    with McpSession() as s:
        for i, c in enumerate(calls):
            tool = c["tool"]
            args = c["args"]
            r = s.call(tool, args)
            if r.get("success") is False:
                fail += 1
                label = c.get("label") or f"{tool}#{i}"
                print(f"[FAIL {i:4d}] {label}: {json.dumps(r)[:240]}")
                if stop_on_error:
                    break
            else:
                ok += 1
                if (i + 1) % 25 == 0:
                    print(f"[ok {i+1}/{len(calls)}]")
    print(f"done. ok={ok} fail={fail} total={len(calls)}")
    return 0 if fail == 0 else 1


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: phase2_mcp_client.py {run <batch.json>|call <tool> <args.json>}", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "run":
        return run_batch(pathlib.Path(sys.argv[2]),
                         stop_on_error=("--stop" in sys.argv))
    if cmd == "call":
        tool = sys.argv[2]
        args = json.loads(pathlib.Path(sys.argv[3]).read_text())
        with McpSession() as s:
            r = s.call(tool, args)
            print(json.dumps(r, indent=2))
            return 0 if r.get("success", True) else 1
    print(f"unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
