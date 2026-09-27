#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1

python3 maps/historical-world-rpg/_shared/tooling/validate_world.py \
  maps/historical-world-rpg/age-of-sail-world/scenario/world/world.json
python3 maps/historical-world-rpg/age-of-sail-world/tooling/validate_map_source.py
python3 -m unittest discover -s maps/historical-world-rpg/age-of-sail-world/tests -p 'test_*.py'
python3 -m unittest discover -s automation/tests -p 'test_*.py'

case "${WARCRAFTMAP_WURST_CHECK:-required}" in
  skip)
    echo "WARNING: Wurst typecheck skipped by explicit WARCRAFTMAP_WURST_CHECK=skip"
    ;;
  required)
    if command -v grill >/dev/null 2>&1; then
      (cd maps/historical-world-rpg/age-of-sail-world && grill install && grill typecheck && grill build map/AgeOfSailWorld.w3x)
    elif command -v docker >/dev/null 2>&1; then
      docker run --rm \
        --entrypoint /bin/sh \
        -v "$repo_root:/source:ro" \
        frotty/wurstscript:latest \
        -lc '
          set -eu
          mkdir /tmp/age-of-sail-world
          cd /source/maps/historical-world-rpg/age-of-sail-world
          tar --exclude=./_build -cf - . | tar -C /tmp/age-of-sail-world -xf -
          cd /tmp/age-of-sail-world
          grill install wurstscript
          grill install
          grill typecheck
          grill build map/AgeOfSailWorld.w3x
        '
    else
      echo "ERROR: Wurst validation requires grill or Docker." >&2
      exit 1
    fi
    ;;
  *)
    echo "ERROR: WARCRAFTMAP_WURST_CHECK must be required or skip" >&2
    exit 2
    ;;
esac
