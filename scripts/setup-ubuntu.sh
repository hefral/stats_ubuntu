#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it first: https://docs.astral.sh/uv/"
  exit 1
fi

if [ ! -x /usr/bin/python3 ]; then
  echo "/usr/bin/python3 was not found."
  exit 1
fi

uv venv --python /usr/bin/python3 --system-site-packages --clear .venv
uv sync --active

echo
echo "Ready. Try:"
echo "  uv run stats-ubuntu --debug"
echo "  uv run stats-ubuntu --probe-sensors"
echo "  uv run stats-ubuntu"
