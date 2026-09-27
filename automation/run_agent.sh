#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python3 -m automation.warcraftmap_agent.self_update --repo "$repo_root" "$@"
exec python3 -m automation.warcraftmap_agent.worker --repo "$repo_root" "$@"
