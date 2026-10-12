#!/usr/bin/env bash
set -euo pipefail
issue_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:- -Xmx6g} -Duser.home=$issue_tools/home/wurstuser"
if [[ "${1:-}" == install ]]; then
  mkdir -p _build/dependencies
  if [[ ! -d _build/dependencies/WurstStdlib2 ]]; then
    cp -a "$issue_tools/wurst-stdlib" _build/dependencies/WurstStdlib2
  fi
  printf '%s\n' "$PWD/_build/dependencies/WurstStdlib2" > wurst.dependencies
  python3 - "$issue_tools/home/wurstuser/.wurst/grill-cli/grill.jar" <<'PY'
from pathlib import Path
import sys
from zipfile import ZipFile
with ZipFile(sys.argv[1]) as archive:
    for name in ('common.j', 'blizzard.j'):
        Path('_build', name).write_bytes(archive.read('core-jass/v3.0/' + name))
PY
  exit 0
fi
exec "$issue_tools/home/wurstuser/.wurst/grill" "$@"
