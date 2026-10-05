#!/bin/sh
set -eu
# /source is always read-only. Everything installed/generated lives in this
# disposable container; no ownership or permission operations target /source.
if ! command -v python3 >/dev/null; then
  apt-get update
  apt-get install -y --no-install-recommends python3
fi
rm -rf /tmp/issue371
mkdir -p /tmp/issue371
cd /source
tar --exclude=_build --exclude=__pycache__ -cf - maps | tar -C /tmp/issue371 -xf -
chown -R wurstuser:wurstuser /tmp/issue371
su -s /bin/sh wurstuser -c 'cd /tmp/issue371/maps/historical-world-rpg/age-of-sail-world && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh'
