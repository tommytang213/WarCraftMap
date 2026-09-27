#!/usr/bin/env bash
set -euo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if command -v python3 >/dev/null 2>&1; then
  python_executable=python3
elif command -v python >/dev/null 2>&1; then
  python_executable=python
else
  echo "packaging failed: required tool 'python3' (or 'python') was not found on PATH" >&2
  exit 1
fi

exec "$python_executable" "$project_root/tooling/package_release.py"
