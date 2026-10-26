set -eu
export JAVA_TOOL_OPTIONS=-Xmx8g
cp -R /source/compile /tmp/compile
cd /tmp/compile
printf '%s  /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar\n' '1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145' | sha256sum -c -
printf '%s\n' /tmp/compile/_build/dependencies/WurstStdlib2 > wurst.dependencies
mkdir -p /tmp/core
(cd /tmp/core && jar xf /home/wurstuser/.wurst/grill-cli/grill.jar core-jass/v3.0/common.j core-jass/v3.0/blizzard.j)
cp /tmp/core/core-jass/v3.0/common.j _build/common.j
cp /tmp/core/core-jass/v3.0/blizzard.j _build/blizzard.j
grill typecheck
grill test
