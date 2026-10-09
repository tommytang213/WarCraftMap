#!/usr/bin/env python3
"""Verify only the equipment research eligibility portion of REQ-0076.01."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/tooling')]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity
from wurst_execution import source_revision


def compiled_equipment(payload):
    """Read the pinned optimizer's inlined constructors and real mutator calls.

    Follow each freshly allocated item's local aliases through its literal ID,
    all prerequisite calls and inventory registration. Mask comments/diagnostic
    strings before recognizing executable statements; those cannot be evidence.
    """
    found, aliases = {}, set()
    ident = None
    literal = r'"(?:[^"\\]|\\.)*"'
    for raw, code in zip(payload['script'].splitlines(), trace.lua_code_mask(payload['script']).splitlines()):
        raw, code = raw.strip(), code.strip()
        create = re.fullmatch(r'(\w+)\s*=\s*RpgItem:create\d+\(\)', code)
        if create:
            assert ident is None, 'Item was not registered before the next allocation'
            aliases = {create[1]}
        alias = re.fullmatch(r'(\w+)\s*=\s*(\w+)', code)
        if alias and alias[2] in aliases:
            aliases.add(alias[1])
        if code.startswith('RpgItem_id_storage['):
            match = re.fullmatch(r'RpgItem_id_storage\[(\w+)\]\s*=\s*(' + literal + ')', raw)
            if match and json.loads(match[2]):
                assert match[1] in aliases, 'Literal identity must belong to the allocated item'
                ident = json.loads(match[2])
                assert ident not in found, ident
                found[ident] = {'technologyIds': [], 'institutionIds': []}
        if code.startswith(('RpgItem_RpgItem_addTechnology(', 'RpgItem_RpgItem_addInstitution(')):
            match = re.fullmatch(r'RpgItem_RpgItem_add(Technology|Institution)\((\w+),\s*(' + literal +
                                 r')(?:,\s*' + literal + r')?\)', raw)
            assert match and ident is not None and match[2] in aliases, raw
            field = 'technologyIds' if match[1] == 'Technology' else 'institutionIds'
            found[ident][field].append(json.loads(match[3]))
        if code.startswith('PlayerInventory_PlayerInventory_registerItem('):
            match = re.fullmatch(r'PlayerInventory_PlayerInventory_registerItem\([^,]+,\s*(\w+)(?:,\s*' + literal + r')?\)', raw)
            assert match and ident is not None and match[1] in aliases, raw
            ident, aliases = None, set()
    assert ident is None, 'Final item was never registered'
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--execution-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-revision')
    args = parser.parse_args()
    revision = source_revision(PROJECT, args.source_revision)
    identity = source_identity(PROJECT, revision)
    evidence = trace.load(args.execution_dir / 'results.json')
    transcript = (args.execution_dir / 'execution.log').read_bytes()
    full = scenario.build_report(args.artifact, evidence, transcript, revision)
    scenario.write_report(full, args.output_dir / 'requirement-traceability')
    assert not full['executionErrors'], full['executionErrors']
    requirement = next(row for row in full['requirements'] if row['id'] == 'REQ-0076.01')
    assert requirement['status'] == 'fail', 'Equipment tests cannot close merchant availability'
    dependency = next(row for row in full['dependencies'] if row['id'] == 'DEP-equipment-technology-trade')
    assert dependency['status'] == 'fail', 'Broader progression/trade integration remains incomplete'
    scope = requirement['mapping']['equipmentEligibility']
    mappings = trace.load(scenario.DIRECTORY / 'mappings.json')
    mappings = copy.deepcopy(mappings)
    mappings['requirements']['REQ-0076.01'] = scope
    maps = [{'id': row['id'], 'packagePath': row['packagePath'],
             'bootstrap': row.get('bootstrap', False), '_self': [row['id']], **row['assignments']}
            for row in trace.load(PROJECT / 'physical-maps.json')['physicalMaps']]
    # Reuse the receipt, source, registration, persistence and artifact checks on
    # the nested equipment-only mapping. Never publish this as a full-obligation
    # pass: the canonical report above retains every unrelated requirement gap.
    scoped = trace.audit(PROJECT, trace.load(scenario.DIRECTORY / 'requirements.json'), mappings,
                         trace.load(scenario.DIRECTORY / 'catalogues.json'), maps,
                         artifact=args.artifact, evidence=evidence, transcript=transcript, revision=revision,
                         authority_documents=('docs/DESIGN_LOCK.md', 'docs/ROADMAP.md'))
    checks = next(row for row in scoped['requirements'] if row['id'] == 'REQ-0076.01')
    assert checks['status'] == 'pass', [row for row in scoped['blockers'] if row['id'] == 'REQ-0076.01']
    _, payloads, errors = trace.inspect_artifact(args.artifact, maps)
    assert not errors, errors
    catalogue = trace.load(PROJECT / 'scenario/inventory/player-use-catalog.json')
    expected = {row['id']: {field: row['requirements'].get(field, [])
                           for field in ('technologyIds', 'institutionIds')}
                for row in catalogue['items']}
    registrations = {}
    for physical in maps:
        payload = payloads[physical['id']]
        assert json.loads(payload['members']['runtime/build-identity.json']) == identity, physical['id']
        if physical['bootstrap']:
            continue
        assert payload['runtime']['inventory'] == catalogue, physical['id']
        actual = compiled_equipment(payload)
        assert actual == expected, (physical['id'], {ident: (expected.get(ident), actual.get(ident))
               for ident in expected.keys() | actual.keys() if expected.get(ident) != actual.get(ident)})
        calls = trace.compiled_calls(payload)
        registrations[physical['id']] = {
            'completeItems': len(actual),
            'technologyRequirements': sum(len(row['technologyIds']) for row in actual.values()),
            'institutionRequirements': sum(len(row['institutionIds']) for row in actual.values()),
            'calls': {pattern: next(call for call in calls if re.match(pattern, call))
                      for pattern in scope['artifact']['callPatterns']}}
    assert not full['candidateReady'] and full['blockerCount'] > 0
    result = {**identity, 'status': 'pass', 'requirement': 'REQ-0076.01',
              'scope': 'Equipment research eligibility only', 'wholeRequirementStatus': 'fail',
              'artifactSha256': full['artifact']['sha256'], 'tests': scope['tests'],
              'compiledEquipment': registrations, 'candidateReady': False,
              'remainingPublicationBlockers': full['blockerCount'], 'realClientExecuted': False,
              'releaseStatus': 'blocked_pending_real_forsaken_kingdom_launch_smoke'}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'scoped-evidence.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS: equipment prerequisite sets, command receipts, saves and compiled registrations; unrelated blockers retained')


if __name__ == '__main__':
    main()
