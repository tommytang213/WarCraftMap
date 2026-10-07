#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1

python3 maps/historical-world-rpg/_shared/tooling/audit_framework_boundary.py
python3 maps/historical-world-rpg/_shared/tooling/validate_world.py \
  maps/historical-world-rpg/conformance-campaign/scenario/world/world.json
python3 maps/historical-world-rpg/_shared/tooling/validate_world.py \
  maps/historical-world-rpg/age-of-sail-world/scenario/world/world.json
python3 maps/historical-world-rpg/age-of-sail-world/tooling/europe_geography.py
python3 maps/historical-world-rpg/age-of-sail-world/tooling/validate_map_source.py
python3 -m unittest discover -s maps/historical-world-rpg/age-of-sail-world/tests -p 'test_*.py'
python3 -m unittest discover -s automation/tests -p 'test_*.py'

case "${WARCRAFTMAP_WURST_CHECK:-required}" in
  skip)
    echo "WARNING: Wurst typecheck and execution skipped by explicit WARCRAFTMAP_WURST_CHECK=skip"
    ;;
  required)
    export SOURCE_REVISION
    SOURCE_REVISION=$(git rev-parse HEAD)
    if command -v grill >/dev/null 2>&1; then
      (cd maps/historical-world-rpg/age-of-sail-world && ./tooling/package_release.sh)
      python3 maps/historical-world-rpg/_shared/tooling/validate_framework_fixture.py \
        maps/historical-world-rpg/conformance-campaign
    elif command -v docker >/dev/null 2>&1; then
      docker run --rm \
        --user root \
        --entrypoint /bin/sh \
        -e SOURCE_REVISION \
        -e WURST_IMAGE=frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a \
        -v "$repo_root:/source:ro" \
        frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a \
        -lc '
          set -eu
          apt-get update
          apt-get install -y --no-install-recommends python3
          mkdir -p /tmp/historical-world-rpg/age-of-sail-world
          mkdir -p /tmp/historical-world-rpg/_shared
          mkdir -p /tmp/historical-world-rpg/conformance-campaign
          cd /source/maps/historical-world-rpg/age-of-sail-world
          tar --exclude=./_build -cf - . | tar -C /tmp/historical-world-rpg/age-of-sail-world -xf -
          cd /source/maps/historical-world-rpg/_shared
          tar -cf - . | tar -C /tmp/historical-world-rpg/_shared -xf -
          cd /source/maps/historical-world-rpg/conformance-campaign
          tar --exclude=./_build -cf - . | tar -C /tmp/historical-world-rpg/conformance-campaign -xf -
          chown -R wurstuser:wurstuser /tmp/historical-world-rpg
          validation_status=0
          su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg/age-of-sail-world && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh" || validation_status=$?
          if [ "$validation_status" -eq 0 ]; then
            su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin python3 _shared/tooling/validate_framework_fixture.py conformance-campaign" || validation_status=$?
          fi
          if [ "$validation_status" -ne 0 ]; then
            # The --rm container owns these logs. Include them in the worker output
            # before removal so interpreter failures remain diagnosable.
            for execution_log in \
              /tmp/historical-world-rpg/age-of-sail-world/_build/wurst-tests/execution.log \
              /tmp/historical-world-rpg/conformance-campaign/_build/wurst-tests/execution.log \
              /tmp/historical-world-rpg/conformance-campaign/_build/mutation/campaign/_build/wurst-tests/execution.log
            do
              if [ -f "$execution_log" ]; then
                cat "$execution_log" || true
              fi
            done
          fi
          exit "$validation_status"
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
