# Private container entrypoint; /source is always read-only.
set -eu
apt-get update
apt-get install -y --no-install-recommends python3
mkdir -p /tmp/historical-world-rpg/age-of-sail-world
mkdir -p /tmp/historical-world-rpg/_shared
mkdir -p /tmp/historical-world-rpg/conformance-campaign
cd /source/maps/historical-world-rpg/age-of-sail-world
tar --exclude=./_build -cf - . | tar -C /tmp/historical-world-rpg/age-of-sail-world -xf -
cd /source/maps/historical-world-rpg/_shared
tar -cf - . | tar -C /tmp/historical-world-rpg/_shared -xf -
cd /source/maps/historical-world-rpg/conformance-campaign
tar --exclude=./_build -cf - . | tar -C /tmp/historical-world-rpg/conformance-campaign -xf -
chown -R wurstuser:wurstuser /tmp/historical-world-rpg
validation_status=0
su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg/age-of-sail-world && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh" || validation_status=$?
if [ "$validation_status" -eq 0 ]; then
  su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin python3 _shared/tooling/validate_framework_fixture.py conformance-campaign" || validation_status=$?
fi
if [ "$validation_status" -ne 0 ]; then
  # The private container owns these logs. Include them in the worker output
  # before removal so interpreter failures remain diagnosable.
  for execution_log in \
    /tmp/historical-world-rpg/age-of-sail-world/_build/wurst-tests/execution.log \
    /tmp/historical-world-rpg/conformance-campaign/_build/wurst-tests/execution.log \
    /tmp/historical-world-rpg/conformance-campaign/_build/mutation/campaign/_build/wurst-tests/execution.log
  do
    if [ -f "$execution_log" ]; then
      cat "$execution_log" || true
    fi
  done
fi
if [ "$validation_status" -eq 0 ]; then
  python3 /source/maps/historical-world-rpg/_shared/tooling/execution_transport.py \
    stage /tmp/historical-world-rpg/age-of-sail-world /tmp/wurst-evidence \
    --source-revision "$SOURCE_REVISION"
fi
exit "$validation_status"
