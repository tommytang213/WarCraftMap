#!/usr/bin/env bash
set -euo pipefail
issue_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:- -Xmx6g} -Duser.home=$issue_tools/home/wurstuser"
if [[ "${1:-}" == install ]]; then
  mkdir -p _build/dependencies
  cp -a "$issue_tools/wurst-stdlib" _build/dependencies/WurstStdlib2
  "$issue_tools/home/wurstuser/.wurst/grill" typecheck
  exit 0
fi
exec "$issue_tools/home/wurstuser/.wurst/grill" "$@"
