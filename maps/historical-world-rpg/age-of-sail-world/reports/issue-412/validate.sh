set -eu
# Run as wurstuser in the pinned image after making Python available there.
# /source is a read-only bind mount. Every build write is container-private.
validation_mode=${1:-tests}
validation_root="/tmp/recovery-$validation_mode/maps/historical-world-rpg"
for directory in _shared age-of-sail-world conformance-campaign; do
  mkdir -p "$validation_root/$directory"
  tar -C "/source/maps/historical-world-rpg/$directory" --exclude=./_build --exclude=./.wurst --exclude=__pycache__ -cf - . |
    tar -C "$validation_root/$directory" -xf -
done
cd "$validation_root/age-of-sail-world"
export PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin
case "$validation_mode" in
  tests) python3 ../_shared/tooling/run_wurst_tests.py package.json ;;
  campaign) ./tooling/package_campaign.sh ;;
  framework) python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign ;;
  *) exit 2 ;;
esac
