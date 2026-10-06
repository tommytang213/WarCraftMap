set -eu
# Pass the read-only source assembled by package_wurst_map.generate/_assemble.
# All edits and dependency/build writes below are container-private.
cp -R "${1:?assembled compile root is required}" /tmp/full
cd /tmp/full
/home/wurstuser/.wurst/grill install
sha256sum /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar
cp -R /tmp/full /tmp/startup
cp -R /tmp/full /tmp/remaining
for source in /tmp/startup/wurst/*.wurst; do
  case "$source" in
    */CampaignStartupTests.wurst) ;;
    *) sed -i 's/@test //g' "$source" ;;
  esac
done
sed -i 's/@test //g' /tmp/remaining/wurst/CampaignStartupTests.wurst
cd /tmp/startup
/home/wurstuser/.wurst/grill test
cd /tmp/remaining
/home/wurstuser/.wurst/grill test
cd /tmp/full
/home/wurstuser/.wurst/grill build map/AgeOfSailWorld.w3x
