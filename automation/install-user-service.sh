#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
config_dir=${XDG_CONFIG_HOME:-"$HOME/.config"}
unit_dir="$config_dir/systemd/user"
env_file="$config_dir/warcraftmap-agent.env"

if command -v loginctl >/dev/null 2>&1; then
  linger=$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)
  if [[ "$linger" != "yes" ]]; then
    echo "ERROR: systemd user lingering is disabled for $USER." >&2
    echo "Run: sudo loginctl enable-linger $USER" >&2
    echo "Then rerun this installer." >&2
    exit 3
  fi
fi

mkdir -p "$unit_dir"
escaped_root=${repo_root//\\/\\\\}
escaped_root=${escaped_root//&/\\&}
escaped_root=${escaped_root//|/\\|}
sed "s|@REPO_ROOT@|$escaped_root|g" \
  "$repo_root/automation/systemd/warcraftmap-agent.service.in" \
  > "$unit_dir/warcraftmap-agent.service"
install -m 0644 "$repo_root/automation/systemd/warcraftmap-agent.timer" \
  "$unit_dir/warcraftmap-agent.timer"
if [[ ! -e "$env_file" ]]; then
  install -m 0600 "$repo_root/automation/warcraftmap-agent.env.example" "$env_file"
fi
systemctl --user daemon-reload
systemctl --user enable --now warcraftmap-agent.timer
echo "Installed. Preview selection with: $repo_root/automation/run_agent.sh --dry-run"
