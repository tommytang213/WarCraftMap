#!/usr/bin/env python3
"""Read actual optimized Lua item registrations, not just the embedded catalogue."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'tests'), str(PROJECT.parent / '_shared/tooling')]
from test_item_definitions import expected_items
from integration_evidence import source_identity
from requirement_traceability import lua_code_mask
from warcraft_campaign import MpqReader

LITERAL = r'"(?:[^"\\]|\\.)*"'
VARIABLE = r'(?:__wurst_locals\d*\[\d+\]|\w+)'


def compiled_items(script):
    body = re.search(r'(?ms)^function configureGeneratedRpg\([^\n]*\).*?(?=^function |\Z)', script)
    assert body, 'compiled scenario registration is missing'
    objects, found = {}, {}
    for raw, masked in zip(body[0].splitlines(), lua_code_mask(body[0]).splitlines()):
        raw, masked = raw.strip(), masked.strip()
        new = re.fullmatch(rf'({VARIABLE}) = RpgItem_new_RpgItem\((.*?)\)', raw)
        if new:
            args = json.loads('[' + new[2] + ']')
            ident, name, slot, rarity, level = args[:5]
            objects[new[1]] = dict(id=ident, name=name, slot=slot, rarity=rarity, itemLevel=level,
                                  majorStats={}, effectIds=[], conditionalEffects=[],
                                  technologyIds=[], institutionIds=[])
            continue
        alias = re.fullmatch(rf'({VARIABLE}) = ({VARIABLE})', masked)
        if alias and alias[2] in objects:
            objects[alias[1]] = objects[alias[2]]
        field = re.fullmatch(rf'RpgItem_(\w+)_storage\[({VARIABLE})\] = ({LITERAL}|-?\d+|true|false)', raw)
        if field and field[2] in objects:
            objects[field[2]][field[1]] = json.loads(field[3])
        call = re.fullmatch(rf'(?:{VARIABLE} = )?RpgItem_RpgItem_add(Stat|Effect|ConditionalEffect|Technology|Institution)\(({VARIABLE}), (.*?)\)', raw)
        if call:
            assert call[2] in objects, raw
            value = objects[call[2]]
            args = json.loads('[' + call[3] + ']')
            if call[1] == 'Stat':
                assert args[0] not in value['majorStats'], 'duplicate compiled stat'
                value['majorStats'][args[0]] = args[1]
            elif call[1] == 'ConditionalEffect':
                descriptor = json.loads(args[2])
                assert descriptor['id'] == args[0] and descriptor['condition'] == args[1]
                value['conditionalEffects'].append(descriptor)
            else:
                field = {'Effect': 'effectIds', 'Technology': 'technologyIds', 'Institution': 'institutionIds'}[call[1]]
                value[field].append(args[0])
        register = re.fullmatch(rf'PlayerInventory_PlayerInventory_registerItem\([^,]+, ({VARIABLE})(?:, {LITERAL})?\)', raw)
        if register:
            value = objects[register[1]]
            assert value['id'] not in found, 'duplicate compiled item registration'
            # Display text is checked by the production command tests; structured
            # metadata below must independently survive optimization.
            value.pop('requirementsText', None)
            found[value['id']] = value
    return found


def inspect(archive):
    mpq = MpqReader(archive)
    script_bytes = mpq.read('war3map.lua')
    script = script_bytes.decode()
    runtime = json.loads(mpq.read('runtime/scenario-runtime.json'))
    identity = json.loads(mpq.read('runtime/build-identity.json'))
    assert identity == source_identity(PROJECT, identity['sourceRevision']), 'source identity mismatch'
    catalogue = json.loads((PROJECT / 'scenario/inventory/player-use-catalog.json').read_text())
    assert runtime['inventory'] == catalogue
    expected = expected_items(catalogue)
    actual = compiled_items(script)
    differences = {key: {'expected': expected.get(key), 'actual': actual.get(key)}
                   for key in expected.keys() | actual.keys() if expected.get(key) != actual.get(key)}
    assert not differences, json.dumps(differences, indent=2)[:12000]
    negatives = []
    for method in ('Stat', 'Effect', 'ConditionalEffect'):
        broken, count = re.subn(rf'^[ \t]*RpgItem_RpgItem_add{method}\([^\n]+\)[ \t]*$', '', script, count=1, flags=re.M)
        assert count == 1 and compiled_items(broken) != expected, f'lost {method} was not detected'
        negatives.append('dropped_compiled_' + method)
    # A descriptor argument in a constructor is insufficient if its storage is
    # optimized away. The live layer fingerprint reads the complete descriptor.
    for field in ('ItemConditionalEffect_descriptor_storage', 'RpgItem_provenance_storage',
                  'RpgItem_requirements_storage', 'EquipmentItemLayer_definitionFingerprint_storage'):
        assert len(re.findall(r'\b' + field + r'(?:_local\d*)?\[', lua_code_mask(script))) > 1, field
    assert 'applyPower' not in lua_code_mask(script)
    for command in ('equip', 'unequip', 'inventory'):
        assert re.search(r'\bCommandRegistry_CommandRegistry_register\([^,\n]+,\s*"' + command + '",', script)
    assert 'Item stat and effect gameplay bonuses unavailable.' in script
    return {
        'status': 'pass', 'sourceIdentity': identity,
        'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'luaSha256': hashlib.sha256(script_bytes).hexdigest(),
        'items': len(actual), 'majorStats': sum(len(row['majorStats']) for row in actual.values()),
        'effectIds': sum(len(row['effectIds']) for row in actual.values()),
        'conditionalDescriptors': sum(len(row['conditionalEffects']) for row in actual.values()),
        'afghanPulwar': actual['afghan_pulwar']['majorStats'], 'negativeControls': negatives,
        'gameplayBindings': 'blocked_pending_item_gameplay_bindings',
        'nativeClient': 'not_run', 'releaseReady': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive), indent=2, sort_keys=True) + '\n')
