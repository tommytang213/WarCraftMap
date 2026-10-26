set -eu
export JAVA_TOOL_OPTIONS=-Xmx4g
for variant in original mutated; do
cp -R /source/$variant-build/compile /tmp/$variant
cd /tmp/$variant
printf '%s  /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar\n' '1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145' | sha256sum -c -
sha256sum -c inputs.sha256
printf '%s\n' /tmp/$variant/_build/dependencies/WurstStdlib2 > wurst.dependencies
grill typecheck
grill test
sha256sum -c inputs.sha256
done
