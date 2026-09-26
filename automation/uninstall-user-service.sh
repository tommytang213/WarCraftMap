#!/usr/bin/env bash
set -euo pipefail

config_dir=${XDG_CONFIG_HOME:-"$HOME/.config"}
unit_dir="$config_dir/systemd/user"
systemctl --user disable --now warcraftmap-agent.timer 2>/dev/null || true
rm -f "$unit_dir/warcraftmap-agent.service" "$unit_dir/warcraftmap-agent.timer"
systemctl --user daemon-reload
echo "Removed the user service and timer. Configuration and state were preserved."
echo "After review, they may be removed manually from:"
echo "  $config_dir/warcraftmap-agent.env"
echo "  ${XDG_STATE_HOME:-"$HOME/.local/state"}/warcraftmap-agent"
