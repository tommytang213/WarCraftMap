#!/usr/bin/env python3
"""Verify real compiled set registrations, including optimizer constructor aliases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT.parent / '_shared/engine')]
from integration_evidence import source_identity
from player_items import equipment_set_definitions
from requirement_traceability import lua_code_mask
from warcraft_campaign import MpqReader


def compiled_sets(script):
    body = re.search(r'(?ms)^function configureGeneratedRpg\([^\n]+\).*?(?=^function |\Z)', script)
    assert body, 'compiled scenario configuration is missing'
    script = body[0]
    objects, found = {}, {}
    variable = r'(?:__wurst_locals\[\d+\]|\w+)'
    literal = r'"(?:[^"\\]|\\.)*"'
    kinds = r'(EquipmentSet|EquipmentSetPiece|EquipmentSetThreshold)'
    for raw, masked in zip(script.splitlines(), lua_code_mask(script).splitlines()):
        raw, masked = raw.strip(), masked.strip()
        new = re.fullmatch(rf'({variable})\s*=\s*{kinds}:create\d+\(\)', masked)
        ctor = re.fullmatch(rf'({variable})\s*=\s*{kinds}_new_\2\(({literal})(?:, (\d+), ({literal}))?(?:, {literal})?\)', raw)
        if new or ctor:
            match = new or ctor
            kind = match[2]
            value = {'kind': kind}
            if kind == 'EquipmentSet':
                value.update(pieces=[], thresholds=[], allowDuplicatePieces=False)
            elif kind == 'EquipmentSetPiece':
                value.update(itemTypeIds=[], equipmentSlotTypes=[])
            else:
                value.update(effectIds=[], replacesThresholdIds=[])
            if ctor:
                value['id'] = json.loads(ctor[3])
                if kind == 'EquipmentSetThreshold':
                    value.update(pieceCount=int(ctor[4]), tierPolicy=json.loads(ctor[5]))
            objects[match[1]] = value
            continue
        alias = re.fullmatch(rf'({variable})\s*=\s*({variable})', masked)
        if alias and alias[2] in objects:
            objects[alias[1]] = objects[alias[2]]
        field = re.fullmatch(rf'{kinds}_(id|pieceCount|tierPolicy|allowDuplicatePieces)_storage\[({variable})\]\s*=\s*({literal}|\d+|true|false)', raw)
        if field and field[3] in objects and (field[2] != 'pieceCount' or field[1] == 'EquipmentSetThreshold'):
            objects[field[3]][field[2]] = json.loads(field[4])
        call = re.fullmatch(rf'{kinds}_\1_add(Item|Slot|Effect|Replacement|Piece|Threshold)\(({variable}),\s*({literal}|{variable})(?:,\s*{literal})?\)', raw)
        if call:
            assert call[3] in objects, raw
            field = {'Item': 'itemTypeIds', 'Slot': 'equipmentSlotTypes', 'Effect': 'effectIds',
                     'Replacement': 'replacesThresholdIds', 'Piece': 'pieces', 'Threshold': 'thresholds'}[call[2]]
            target = call[4]
            objects[call[3]][field].append(json.loads(target) if target.startswith('"') else objects[target])
        register = re.fullmatch(rf'PlayerInventory_PlayerInventory_registerSet\([^,]+,\s*({variable})(?:,\s*{literal})?\)', raw)
        if register:
            value = objects[register[1]]
            assert value['id'] not in found, 'duplicate compiled set registration'
            found[value['id']] = value
    def strip_kind(value):
        if isinstance(value, dict):
            return {key: strip_kind(item) for key, item in value.items() if key != 'kind'}
        if isinstance(value, list):
            return [strip_kind(item) for item in value]
        return value
    return strip_kind(found)


def inspect(archive):
    mpq = MpqReader(archive)
    script_bytes = mpq.read('war3map.lua')
    script = script_bytes.decode()
    runtime = json.loads(mpq.read('runtime/scenario-runtime.json'))
    identity = json.loads(mpq.read('runtime/build-identity.json'))
    assert identity == source_identity(PROJECT, identity['sourceRevision']), 'source mismatch'
    catalogue = json.loads((PROJECT / 'scenario/inventory/player-use-catalog.json').read_text())
    definitions = equipment_set_definitions(catalogue)
    assert runtime['inventory'] == catalogue
    assert runtime['equipmentSetDefinitions'] == definitions
    pieces = {row['id']: row for row in definitions['equipmentSetPieces']}
    expected = {row['id']: {key: value for key, value in row.items() if key != 'pieceIds'} |
                {'pieces': [pieces[ident] for ident in row['pieceIds']]} for row in definitions['equipmentSets']}
    actual = compiled_sets(script)
    assert actual == expected, {ident: (expected.get(ident), actual.get(ident))
                                for ident in expected.keys() | actual.keys() if expected.get(ident) != actual.get(ident)}
    # Negative controls must fail actual executable-definition comparison.
    dropped = re.sub(r'^[ \t]*EquipmentSet_EquipmentSet_addThreshold\([^\n]+\)[ \t]*$', '', script, count=1, flags=re.M)
    assert compiled_sets(dropped) != expected, 'dropped compiled tier was not detected'
    changed = re.sub(r'(EquipmentSetThreshold_EquipmentSetThreshold_addEffect\([^,]+,\s*)"set_mobility"', r'\1"lost_identity"', script, count=1)
    assert compiled_sets(changed) != expected, 'lost compiled effect identity was not detected'
    for command in ('equip', 'unequip', 'inventory'):
        assert re.search(r'\bCommandRegistry_CommandRegistry_register\([^,\n]+,\s*"' + command + '",', script), command
    assert re.search(r'\bCommandRegistry_CommandRegistry_register\([^,\n]+,\s*"inventory",\s*"equipment,items",', script)
    assert 'Set gameplay effects pending binding.' in script
    return {'status': 'pass', 'sourceIdentity': identity,
            'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'luaSha256': hashlib.sha256(script_bytes).hexdigest(),
            'sets': len(actual), 'thresholds': sum(len(row['thresholds']) for row in actual.values()),
            'setsWithMiddleTiers': sum(len(row['thresholds']) > 2 for row in actual.values()),
            'effectReferences': sum(len(tier['effectIds']) for row in actual.values() for tier in row['thresholds']),
            'negativeControls': ['dropped_compiled_threshold', 'lost_compiled_effect_identity'],
            'gameplayEffects': 'blocked_pending_gameplay_effect_bindings',
            'nativeClient': 'not_run', 'releaseReady': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive), indent=2, sort_keys=True) + '\n')
