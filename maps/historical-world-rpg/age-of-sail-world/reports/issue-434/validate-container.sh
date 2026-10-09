set -eu
mkdir -p /tmp/issue434
cd /source
# Read-only source, private compilation owned by the image's non-root user.
tar --exclude=.git --exclude=./.agents --exclude=./.aws --exclude=./.codex --exclude=_build --exclude=__pycache__ -cf - maps automation .github AGENTS.md | tar -C /tmp/issue434 -xf -
mkdir -p /tmp/issue434-tools
cp /dependencies/usr/bin/python3.14 /tmp/issue434-tools/python3
export PYTHONHOME=/dependencies/usr

export PATH=/tmp/issue434-tools:/home/wurstuser/.wurst:$PATH
cat > /tmp/issue434-tools/grill <<'GRILL'
#!/bin/sh
set -eu
printf "%s %s\n" "$PWD" "$1" >> /tmp/issue434-tools/progress.log
mkdir -p _build/dependencies
if [ ! -d _build/dependencies/WurstStdlib2 ]; then
  cp -R /dependencies/tmp/issue383-package/age-of-sail-world/_build/compile/_build/dependencies/wurstStdlib2 _build/dependencies/WurstStdlib2
fi
if [ "$1" = install ]; then
  printf '%s\n' "$PWD/_build/dependencies/WurstStdlib2" > wurst.dependencies
  python3 - <<'CORE'
from pathlib import Path
from zipfile import ZipFile
jar=ZipFile('/home/wurstuser/.wurst/grill-cli/grill.jar')
for name in ('common.j','blizzard.j'):
    candidates=[p for p in jar.namelist() if p=='core-jass/v3.0/'+name]
    print(name,candidates)
    Path('_build',name).write_bytes(jar.read(candidates[0]))
CORE
  exit 0
fi
exec /home/wurstuser/.wurst/grill "$@"
GRILL
chmod +x /tmp/issue434-tools/grill
cd /tmp/issue434/maps/historical-world-rpg/age-of-sail-world
case "${1:-tests}" in
  tests) python3 ../_shared/tooling/run_wurst_tests.py package.json ;;
  campaign) python3 ../_shared/tooling/package_wurst_campaign.py physical-maps.json ;;
  framework) python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign ;;
  *) exit 2 ;;
esac
