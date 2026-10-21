"""Reproduce PR #543's regional payload gate with normal production assembly.

Usage from the scenario directory: python3 reports/issue-524/prepare-regional.py
PATH_TO_CACHED_WURST_STDLIB [PHYSICAL_MAP_ID]
This is a single-map diagnostic, not full-suite or campaign release evidence.
"""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from integration_evidence import source_identity
from materialize_physical_map import materialize
from package_wurst_campaign import load_campaign_config, validate_campaign, _localize_runtime, _validate_budget
from package_wurst_map import load_config, generate, verify_generated, _assemble

campaign = load_campaign_config(project / 'physical-maps.json')
map_id = sys.argv[2] if len(sys.argv) > 2 else 'europe_west'
physical = next(p for p in campaign.maps if p.id == map_id)
assert not physical.bootstrap, 'Use the minimal bootstrap assembly for selector maps'
base = load_config(campaign.map_config_path)
config = replace(base, source_map=physical.source_map, manifest=physical.source_manifest)
root = project / '_build/issue-524-regional' / map_id
if root.exists():
    shutil.rmtree(root)
generated = root / 'generated'
generate(config, generated)
_localize_runtime(campaign, validate_campaign(campaign), physical, generated)
verify_generated(config, generated)
_validate_budget(config, physical, generated)
compile_root = _assemble(config, root, generated, physical.terrain_ids, include_tests=False)
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project, text=True).strip()
identity = source_identity(project, revision)
(compile_root / 'map' / config.source_map.name / 'runtime/build-identity.json').write_text(json.dumps(identity, sort_keys=True) + '\n')
runtime = json.loads((generated / 'scenario-runtime.json').read_text())
materialize(project, compile_root / 'map' / config.source_map.name, generated, physical, runtime)
(compile_root / '_build/dependencies').mkdir(parents=True)
shutil.copytree(sys.argv[1], compile_root / '_build/dependencies/WurstStdlib2')
(root / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
print(compile_root, flush=True)
