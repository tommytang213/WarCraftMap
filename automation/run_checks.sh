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
      maps/historical-world-rpg/age-of-sail-world/tooling/package_release.sh
    elif command -v docker >/dev/null 2>&1; then
      docker run --rm \
        --user root \
        -v "$repo_root:/source:ro" \
        frotty/wurstscript:latest \
        /bin/sh -lc '
          set -eu
          apt-get update
          apt-get install -y --no-install-recommends python3
          cp -R /source/maps/historical-world-rpg/age-of-sail-world /tmp/age-of-sail-world
          cp -R /source/maps/historical-world-rpg/_shared /tmp/_shared
          chown -R wurstuser:wurstuser /tmp/age-of-sail-world /tmp/_shared
          cd /tmp/age-of-sail-world
          su -s /bin/sh wurstuser -c "/home/wurstuser/.wurst/grill install wurstscript && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh"
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
