#!/bin/sh
set -eu
if ! command -v python3 >/dev/null; then
  apt-get update > /tmp/apt-update.log 2>&1
  apt-get install -y --no-install-recommends python3 > /tmp/apt-install.log 2>&1
fi
su -s /bin/sh wurstuser -c '
set -eu
mkdir -p /tmp/issue444
cd /source
# All writes and compilation occur in this private, unprivileged copy.
tar --exclude=./.git --exclude=*/_build -cf - . | tar -C /tmp/issue444 -xf -
cd /tmp/issue444/maps/historical-world-rpg/age-of-sail-world
export PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin
python3 tooling/package_campaign.py > /tmp/issue444/campaign.log 2>&1 || { tail -45 /tmp/issue444/campaign.log; exit 1; }
python3 reports/issue-444/verify-evidence.py --artifact _build/release/AgeOfSailWorldCampaign.w3n --execution-dir _build/wurst-tests --output-dir _build/issue444-evidence > /tmp/issue444/evidence.log 2>&1 || { tail -35 /tmp/issue444/evidence.log; exit 1; }
python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign > /tmp/issue444/framework.log 2>&1 || { tail -35 /tmp/issue444/framework.log; exit 1; }
tail -3 /tmp/issue444/campaign.log
tail -3 /tmp/issue444/evidence.log
tail -3 /tmp/issue444/framework.log
'
