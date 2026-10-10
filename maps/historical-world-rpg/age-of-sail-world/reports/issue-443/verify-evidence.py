#!/usr/bin/env python3
"""Verify issue 443's scoped live-order receipts and diagnostic registrations."""
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

REQUIREMENTS = ('ROAD-0048.01', 'REQ-0233.01', 'REQ-0234.01')


def order_registrations(payload, expected):
    """Follow the pinned optimizer's event/trigger aliases into real calls.

    Wurst's native wrappers inline guards and temporary argument assignments.
    A diagnostic string mentioning an event or function is not registration.
    """
    code = trace.lua_code_mask(payload['script'])
    match = re.search(r'^function (WarcraftMilitaryOrderNatives_\w*_install)\([^\n]*\n(.*?)(?=^function |\Z)', code, re.M | re.S)
    assert match, 'Missing production order installer'
    calls = trace.compiled_calls(payload)
    assert any(call.startswith('dispatch_MilitaryOrderNatives_install(') for call in calls), 'Installer has no dispatch call'
    assert re.search(r'WarcraftMilitaryOrderNatives\.MilitaryOrderNatives_install\s*=\s*' + match[1] + r'\b', code), 'Production installer is not bound to dispatch'
    assert any(call.startswith('installMilitaryOrderEvents(') and 'WarcraftMilitaryOrderNatives_new_' in call for call in calls), 'Startup does not install the production native port'
    events, aliases, registered = {}, {}, []
    attached = False
    listener = None
    for line in match[2].splitlines():
        assignment = re.fullmatch(r'\s*(\w+)\s*=\s*(\w+)\s*', line)
        if assignment:
            left, right = assignment.groups()
            if right in expected:
                events[left] = right
            else:
                events.pop(left, None)
            aliases[left] = aliases.get(right, right)
        creation = re.fullmatch(r'\s*(\w+)\s*=\s*CreateTrigger\(\)\s*', line)
        if creation:
            listener = creation[1]
            aliases[listener] = listener
        call = re.fullmatch(r'\s*TriggerRegisterPlayerUnitEvent\((\w+),\s*\w+,\s*(\w+),\s*nil\)\s*', line)
        if call:
            assert listener and aliases.get(call[1]) == listener, line
            registered.append(events[call[2]])
        attachment = re.fullmatch(r'\s*TriggerAddAction\((\w+),\s*(\w+)\)\s*', line)
        if attachment:
            assert listener and aliases.get(attachment[1]) == listener, line
            assert aliases.get(attachment[2]) == '__wurst_callback_bridge_militaryOrderEvent', line
            attached = True
    assert registered == expected, registered
    assert attached, 'Order callback is not attached'
    return registered


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
    rows = {row['id']: row for row in full['requirements']}
    assert all(rows[ident]['status'] == 'fail' for ident in REQUIREMENTS), 'Order persistence alone cannot close compound obligations'
    downstream = ('REQ-0300.01', 'ROAD-0062.01')
    assert all(rows[ident]['status'] == 'fail' for ident in downstream), 'Physical remote command remains independent'
    mappings = copy.deepcopy(trace.load(scenario.DIRECTORY / 'mappings.json'))
    for ident in REQUIREMENTS:
        mappings['requirements'][ident] = rows[ident]['mapping']['liveOrders']
    maps = [{'id': row['id'], 'packagePath': row['packagePath'],
             'bootstrap': row.get('bootstrap', False), '_self': [row['id']], **row['assignments']}
            for row in trace.load(PROJECT / 'physical-maps.json')['physicalMaps']]
    scoped = trace.audit(PROJECT, trace.load(scenario.DIRECTORY / 'requirements.json'), mappings,
                         trace.load(scenario.DIRECTORY / 'catalogues.json'), maps,
                         artifact=args.artifact, evidence=evidence, transcript=transcript, revision=revision,
                         authority_documents=('docs/DESIGN_LOCK.md', 'docs/ROADMAP.md'))
    checks = {row['id']: row for row in scoped['requirements'] if row['id'] in REQUIREMENTS}
    assert all(row['status'] == 'pass' for row in checks.values()), [
        row for row in scoped['blockers'] if row['id'] in REQUIREMENTS]
    _, payloads, errors = trace.inspect_artifact(args.artifact, maps)
    assert not errors, errors
    registrations = {}
    patterns = mappings['requirements'][REQUIREMENTS[0]]['artifact']['callPatterns']
    for physical in maps:
        payload = payloads[physical['id']]
        assert json.loads(payload['members']['runtime/build-identity.json']) == identity, physical['id']
        if physical['bootstrap']:
            continue
        calls = trace.compiled_calls(payload)
        registrations[physical['id']] = {
            'nativeEvents': order_registrations(payload, mappings['requirements'][REQUIREMENTS[0]]['artifact']['nativeEvents']),
            'calls': {pattern: next(call for call in calls if re.match(pattern, call)) for pattern in patterns}}
    assert not full['candidateReady'] and full['blockerCount'] > 0
    result = {**identity, 'status': 'pass', 'requirements': list(REQUIREMENTS),
              'scope': 'Live army/fleet order and local position persistence only',
              'wholeRequirementStatus': 'fail', 'receipts': 12,
              'artifactSha256': full['artifact']['sha256'],
              'executionLogSha256': evidence['logSha256'],
              'compiledRegistrations': registrations, 'candidateReady': False,
              'remainingPublicationBlockers': full['blockerCount'],
              'downstreamObligations': list(downstream), 'realClientExecuted': False,
              'releaseStatus': 'blocked_pending_remote_transport_and_native_launch'}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'scoped-evidence.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS: live order callbacks, saves, reconstruction and compiled registrations; unrelated blockers retained')


if __name__ == '__main__':
    main()
