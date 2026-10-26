"""Compile optional scenario-owned communications into the paid survey consumer."""
import json
from pathlib import Path

METRIC = 'remote_survey_dispatch_time_reduction'


def configuration(project, world):
    path = project / 'scenario/progression/dispatch-contract.json'
    if not path.exists():
        return [], [], []
    data = json.loads(path.read_text())
    nodes = {n['id']: n for n in world['technologies']}
    effect = data['effect']
    node = nodes.get(data['nodeId'], {})
    relay = nodes.get(data['relayNodeId'], {})
    if (data['schemaVersion'] != 1 or effect['nodeId'] != node.get('id')
            or effect['unlock'] not in node.get('unlocks', [])
            or effect['unlock']['kind'] != 'modifier' or effect['metric'] != METRIC
            or data['relayUnlock'] not in relay.get('unlocks', [])
            or relay.get('id') not in node.get('prerequisiteIds', [])
            or type(effect['bonusBasisPoints']) is not int or not 0 < effect['bonusBasisPoints'] <= 1000
            or type(data['operatingBasisPoints']) is not int or not 0 < data['operatingBasisPoints'] <= 100):
        raise ValueError('dispatch contract: invalid bounded effect, relay prerequisite or bill')
    settlements = {s['id'] for s in world['settlements']}
    links = data['relayLinks']
    identities = {(x['originId'], x['recipientId']) for x in links}
    if (not 0 < len(links) <= 64 or len(identities) != len(links)
            or any(a == b or a not in settlements or b not in settlements for a, b in identities)):
        raise ValueError('dispatch contract: duplicate or invalid geographic relay')
    q = json.dumps
    lines = [f'\tledger.dispatchRelayKind = {q(data["relayUnlock"]["kind"])}',
             f'\tledger.dispatchRelayContent = {q(data["relayUnlock"]["contentId"])}',
             f'\tledger.dispatchOperatingBasisPoints = {data["operatingBasisPoints"]}']
    lines += [f'\tledger.addDispatchLink({q(x["originId"])}, {q(x["recipientId"])})' for x in links]
    return lines, [effect], [path, Path(__file__)]


REQUIRED_TESTS = {
    'dispatchRegisteredResearchAndSurveyBeatMatchedControlWithExactBills',
    'dispatchMissingRelayTechnologyAccessAndRemoteJurisdictionRemoveEarlyCompletion',
    'dispatchRejectedCommandsAndDuplicateOrdersPreserveAuthority',
    'dispatchStaleAccessAndControllerTransferReevaluateAtCompletion',
    'dispatchActiveAbstractReplaySaveReconstructionAndLegacyDeadlineAgree',
    'dispatchFailedCampaignLoadRollsBackPendingOrderResearchAndBills',
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """A resolver/registration alone cannot close a release consumer finding."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError):
        return set()
    prefix = 'wurst/DispatchTests.wurst:'
    passed = {r['id'][len(prefix):] for r in execution['tests']
              if r['status'] == 'pass' and r['id'].startswith(prefix)}
    if (not REQUIRED_TESTS <= passed or prefix + 'dispatchRegisteredResearchAndSurveyBeatMatchedControlWithExactBills'
            not in coverage.get('dispatch_contract', [])):
        return set()
    world = json.loads((project / 'scenario/world/world.json').read_text())
    _, effects, _ = configuration(project, world)
    return {(e['unlock']['kind'], e['unlock']['contentId']) for e in effects}


def verify_registration(project, world, source, catalog):
    """Reject executable/network edits even if generated file hashes are resealed."""
    lines, effects, _ = configuration(project, world)
    expected = lines + [f'\tresearch.register(new CivicEffect({json.dumps(e["unlock"]["kind"])}, '
                         f'{json.dumps(e["unlock"]["contentId"])}, {json.dumps(e["metric"])}, '
                         f'{e["bonusBasisPoints"]}))' for e in effects]
    actual = [line for line in source.splitlines() if line.startswith((
        '\tledger.dispatchRelay', '\tledger.dispatchOperating', '\tledger.addDispatchLink('))
        or (line.startswith('\tresearch.register(new CivicEffect(') and json.dumps(METRIC) in line)]
    if (actual != expected or [e for e in catalog.get('effects', []) if e['metric'] == METRIC] != effects):
        raise ValueError('dispatch contract: executable or runtime registration differs from scenario')
