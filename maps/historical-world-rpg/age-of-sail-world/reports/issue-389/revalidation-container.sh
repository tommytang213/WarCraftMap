set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3
mkdir -p /tmp/historical-world-rpg/age-of-sail-world /tmp/historical-world-rpg/_shared
cd /source/maps/historical-world-rpg/age-of-sail-world
tar --exclude=./_build --exclude=__pycache__ -cf - . | tar -C /tmp/historical-world-rpg/age-of-sail-world -xf -
cd /source/maps/historical-world-rpg/_shared
tar --exclude=__pycache__ -cf - . | tar -C /tmp/historical-world-rpg/_shared -xf -
chown -R wurstuser:wurstuser /tmp/historical-world-rpg
mkdir -p /tmp/issue-389-bin
cat > /tmp/issue-389-bin/grill <<'GRILL'
#!/bin/bash
set -o pipefail
if [ "$1" = test ]; then
  /home/wurstuser/.wurst/grill "$@" 2>&1 | tee /tmp/issue-389-wurst-progress.log
else
  exec /home/wurstuser/.wurst/grill "$@"
fi
GRILL
chmod 755 /tmp/issue-389-bin/grill
trap 'if test -f /tmp/historical-world-rpg/age-of-sail-world/_build/wurst-tests/execution.log; then cat /tmp/historical-world-rpg/age-of-sail-world/_build/wurst-tests/execution.log; fi' EXIT
su -s /bin/sh wurstuser -c 'cd /tmp/historical-world-rpg/age-of-sail-world && PATH=/tmp/issue-389-bin:/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh'
