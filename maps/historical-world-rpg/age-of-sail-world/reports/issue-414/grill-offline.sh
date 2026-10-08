#!/usr/bin/env bash
set -euo pipefail
issue_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export JAVA_TOOL_OPTIONS="-Duser.home=$issue_tools/pinned-home -Xmx4g"
if [[ "${1:-}" == install ]]; then
  mkdir -p _build/dependencies
  cp -a "$issue_tools/wurst-stdlib" _build/dependencies/WurstStdlib2
  "$issue_tools/pinned-home/.wurst/grill" typecheck
  exit 0
fi
export JAVA_TOOL_OPTIONS="-Duser.home=$issue_tools/pinned-home -Xmx4g"
exec "$issue_tools/pinned-home/.wurst/grill" "$@"
