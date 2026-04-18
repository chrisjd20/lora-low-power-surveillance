#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_FILE="$SCRIPT_DIR/hardware/warden-apex-master/warden-apex-master.kicad_pro"
LOG_FILE="/tmp/warden-kicad-launch.log"

if ! command -v kicad >/dev/null 2>&1; then
  echo "KiCad is not installed in this WSL environment." >&2
  exit 1
fi

if [[ ! -f "$PROJECT_FILE" ]]; then
  echo "KiCad project not found: $PROJECT_FILE" >&2
  exit 1
fi

# WSLg usually provides WAYLAND_DISPLAY. Older X server setups often need DISPLAY=:0.
if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  export DISPLAY=:0
fi

nohup kicad "$PROJECT_FILE" >"$LOG_FILE" 2>&1 &

echo "Launching KiCad for:"
echo "  $PROJECT_FILE"
echo "Log: $LOG_FILE"
