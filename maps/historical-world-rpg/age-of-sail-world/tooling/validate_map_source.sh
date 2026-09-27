#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"

python3 tooling/validate_map_source.py
grill typecheck
./tooling/package_release.sh
