#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1

# A failed attempt must never leave an earlier passing run available to planning.
if [ "${WARCRAFTMAP_WURST_CHECK:-required}" = required ]; then
  python3 maps/historical-world-rpg/_shared/tooling/execution_transport.py \
    invalidate maps/historical-world-rpg/age-of-sail-world
  trap 'validation_status=$?; trap - EXIT; if [ "$validation_status" -ne 0 ]; then
    python3 maps/historical-world-rpg/_shared/tooling/execution_transport.py \
      invalidate maps/historical-world-rpg/age-of-sail-world || true
  fi; exit "$validation_status"' EXIT
fi

python3 maps/historical-world-rpg/_shared/tooling/audit_framework_boundary.py
python3 maps/historical-world-rpg/_shared/tooling/validate_world.py \
  maps/historical-world-rpg/conformance-campaign/scenario/world/world.json
python3 maps/historical-world-rpg/_shared/tooling/validate_world.py \
  maps/historical-world-rpg/age-of-sail-world/scenario/world/world.json
python3 maps/historical-world-rpg/age-of-sail-world/tooling/europe_geography.py
python3 maps/historical-world-rpg/age-of-sail-world/tooling/validate_map_source.py
python3 maps/historical-world-rpg/age-of-sail-world/tooling/requirement_traceability_audit.py --check
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
      python3 automation/container_validation.py --source-revision "$SOURCE_REVISION"
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
