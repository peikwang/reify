#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
exec .venv/bin/python -m uvicorn server.main:app --host "${VIBEFORGE_HOST:-0.0.0.0}" --port "${VIBEFORGE_PORT:-12888}"
