"""Compile scenario-owned civic research contracts into reusable domain consumers."""
from datetime import date
import json

RULES = {'transitionDays', 'enactmentBasisPoints', 'upkeepBasisPoints', 'surveyBasisPoints',
         'responseBasisPoints', 'responseDays', 'cooldownDays', 'tradePenaltyBasisPoints', 'baseTaxBasisPoints'}
METRICS = {'civic_reform_diffusion': 'policy', 'epidemic_losses_avoided': 'ability',
           'land_tax_collection_efficiency': 'modifier'}


def annual_tax_capacity(cfg, row):
    roles = set(row.get("roles", []))
    capacity = cfg['normalAnnualCapacityUnits']
    for eligible, key in [('capital' in roles, 'capitalCapacityPermille'),
                          (bool(row.get('port')), 'portCapacityPermille'),
                          (bool(roles & set(cfg['civicRoles']) - {'capital'}), 'tradeCenterCapacityPermille')]:
        if eligible:
            capacity = capacity * cfg[key] // 1000
    annual_tax = capacity * cfg['taxSharePermille'] // 1000
    return annual_tax


def configuration(project, world, settlements, authored, trade_records):
    path = project / 'scenario/progression/civic-governance.json'
    header = '\npublic function configureGeneratedCivic(CivicLedger ledger, CivicResearchEffects research, int day)\n'
    if not path.is_file():
        return header + '\tskip\n', {}, []
    data = json.loads(path.read_text())
    if data.get('schemaVersion') != 1 or set(data['rules']) != RULES:
        raise ValueError('civic governance: invalid schema/rules')
    for key, value in data['rules'].items():
        if type(value) is not int or not 0 < value <= (10000 if 'BasisPoints' in key else 365):
            raise ValueError('civic governance: invalid ' + key)
    if set(data['metrics']) != set(METRICS):
        raise ValueError('civic governance: exact supported metric set required')
    design_path = project / data['designSource']
    designs = json.loads(design_path.read_text())['effects']
    definitions = [x for x in designs if x['metric'] in data['metrics']]
    nodes = {x['id']: x for x in world['technologies'] + world['institutions']}
    identities = set()
    for effect in definitions:
        unlock = effect['unlock']
        pair = (unlock['kind'], unlock['contentId'])
        if (effect['nodeId'] not in nodes or unlock not in nodes[effect['nodeId']]['unlocks']
                or unlock['kind'] != METRICS[effect['metric']] or pair in identities
                or type(effect['bonusBasisPoints']) is not int or not 0 < effect['bonusBasisPoints'] <= 10000):
            raise ValueError('civic governance: invalid exact typed research binding')
        identities.add(pair)
    if len(definitions) != 3:
        raise ValueError('civic governance: missing effect contract')
    from administrative_governance import configuration as administration_configuration
    admin_lines, admin_effects, urban, admin_sources = administration_configuration(project, world)
    from dispatch_contract import configuration as dispatch_configuration
    dispatch_lines, dispatch_effects, dispatch_sources = dispatch_configuration(project, world)
    definitions += admin_effects + dispatch_effects
    q = json.dumps
    lines = [header, *admin_lines, *dispatch_lines]
    for key, value in data['rules'].items():
        lines.append(f'\tledger.{key} = {value}')
    for effect in definitions:
        unlock = effect['unlock']
        lines.append(f'\tresearch.register(new CivicEffect({q(unlock["kind"])}, {q(unlock["contentId"])}, {q(effect["metric"])}, {effect["bonusBasisPoints"]}))')
    cfg = data['districts']
    for key, value in cfg.items():
        if key not in {'civicRoles', 'discussionFirstDate', 'medicalGoodPreference'} and (type(value) is not int or not 0 < value < 1000000):
            raise ValueError('civic governance: invalid district setting ' + key)
    outbreaks = {x['settlementId']: x for x in data['outbreaks']}
    if len(outbreaks) != len(data['outbreaks']) or set(outbreaks) - set(authored):
        raise ValueError('civic governance: duplicate/unknown outbreak district')
    events = {x['id'] for x in world.get('events', [])}
    records = []
    for settlement in settlements:
        ident = settlement['id']
        _, row = authored.get(ident, ('', {}))
        if not row:
            continue
        roles = set(row.get('roles', []))
        annual_tax = annual_tax_capacity(cfg, row)
        # The compiled trade catalogue is authoritative for existing commodities.
        available = [g for g in cfg['medicalGoodPreference'] if any(
            f'runtime.registerMarketProfile({q(ident)},{q(g)},' in line for line in trade_records)]
        medical_good = available[0] if available else cfg['medicalGoodPreference'][0]
        outbreak = outbreaks.get(ident)
        if outbreak and (outbreak['evidenceEventId'] not in events or type(outbreak['durationDays']) is not int
                         or not 0 < outbreak['durationDays'] <= 365 or type(outbreak['diseaseLossPerDay']) is not int
                         or not 0 < outbreak['diseaseLossPerDay'] <= 100):
            raise ValueError('civic governance: invalid outbreak')
        record = dict(id=ident, provinceId=row['provinceId'], annualTax=annual_tax,
                      civicCenter=bool(roles & set(cfg['civicRoles'])), discussionFirstDay=date.fromisoformat(cfg['discussionFirstDate']).toordinal(),
                      discussionPerDay=cfg['discussionPerDay'], outbreakFirstDay=date.fromisoformat(outbreak['firstDate']).toordinal() if outbreak else 0,
                      outbreakDays=outbreak['durationDays'] if outbreak else 0, diseaseLossPerDay=outbreak['diseaseLossPerDay'] if outbreak else 0,
                      medicalGood=medical_good, medicalUnits=cfg['medicalUnits'], tradeCapacity=cfg['dailyTradeCapacityUnits'])
        args = ', '.join(str(v).lower() if isinstance(v, bool) else q(v) if isinstance(v, str) else str(v) for v in record.values())
        records.append(f'\tledger.register(new CivicDistrict({args}), day)')
        if urban:
            percent = urban['urbanPercent'] if roles & set(urban['urbanRoles']) else urban['otherPercent']
            records[-1] += f'\n\tledger.configureAdministration({q(ident)}, {percent})'
    # Keep generated registration functions below compiler complexity limits.
    for start in range(0, len(records), 40):
        lines.append(f'\tconfigureCivicDistricts{start}(ledger, day)')
    for start in range(0, len(records), 40):
        lines.extend([f'\nfunction configureCivicDistricts{start}(CivicLedger ledger, int day)', *records[start:start + 40]])
    return '\n'.join(lines) + '\n', {'rules': data['rules'], 'effects': definitions, 'districtCount': len(records)}, [path, design_path, __import__('pathlib').Path(__file__), *admin_sources, *dispatch_sources]


# Deliberately limited to #548's two supplied findings. Survey and administrative
# bindings have independent evidence requirements and cannot close here.
CLOSURE_EFFECTS = {
    ('policy', 'progression_abolitionist_public_sphere'):
        ('abolitionist_public_sphere', 'civic_reform_diffusion', 500),
    ('ability', 'epidemic_control'):
        ('anatomy_and_medicine', 'epidemic_losses_avoided', 2500),
}
REQUIRED_TESTS = {
    'civicRegisteredResearchAndActionsChargeOnlyTheExactAuthoritativeBills',
    'civicActionsRejectOccupationMissingInstitutionsSuppliesAndCooldownAtomically',
    'civicSaveMigrationCaptureAndFailedRestorePreserveLocalAuthorityWithoutReplay',
    'civicQuarantineBudgetCannotBeBypassedBySplitTransactionsAndSurvivesReload',
    'civicPlayerAndAiUseIdenticalActionsAndActiveAbstractReplayArithmetic',
    'civicSurveyUsesExactRelativeCollectionAndPolicyNeedsActualLocalDiscussion',
    'civicPolicyMatchedControlProvesOptionalTransitionFundedDiffusionAndRenewal',
    'civicPolicyAndResponseRequireCurrentLocalJurisdictionAndMedicalStock',
    'civicResponseMatchedControlProvesActualLossesBillsThroughputAndCooldown',
}
ROLLBACK_TEST = 'wurst/CampaignLoadTransactionTests.wurst:lateLoadFailureRestoresCivicPolicyResponseAndActualResourcesAtomically'
COMMON_PROBES = {'civic_registration', 'research', 'dispatch', 'administrative_action',
                 'administrative_advance', 'administrative_pay', 'civic_clock'}
COMPARATIVE_PATHS = {
    ('policy', 'progression_abolitionist_public_sphere'):
        ('civic_policy', 'civicPolicyMatchedControlProvesOptionalTransitionFundedDiffusionAndRenewal',
         COMMON_PROBES | {'civic_diffusion'}),
    ('ability', 'epidemic_control'):
        ('epidemic_response', 'civicResponseMatchedControlProvesActualLossesBillsThroughputAndCooldown',
         COMMON_PROBES | {'civic_disease', 'civic_trade_budget', 'civic_trade_commit'}),
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """Recognize only current pinned execution, actual calls and asserted outcomes.

    Full discovery, source/input hashes and transcript verification are required;
    a focused development run or a declared binding alone cannot close a finding.
    """
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/CivicGovernanceTests.wurst:'
        passed = {r['id'] for r in execution['tests'] if r['status'] == 'pass'}
        if not ({prefix + name for name in REQUIRED_TESTS} | {ROLLBACK_TEST}) <= passed:
            return set()
        world = json.loads((project / 'scenario/world/world.json').read_text())
        authored_districts = {row['id']: (path.stem, row)
                             for path in (project / 'scenario/settlements').glob('*-1450.json')
                             for row in json.loads(path.read_text())['settlements']}
        _, catalog, _ = configuration(project, world, [], authored_districts, [])
        authored = {(e['unlock']['kind'], e['unlock']['contentId']):
                    (e['nodeId'], e['metric'], e['bonusBasisPoints']) for e in catalog['effects']}
        observed = execution['productionCoverage']['tests']
        return {pair for pair, (system, name, probes) in COMPARATIVE_PATHS.items()
                if authored.get(pair) == CLOSURE_EFFECTS[pair]
                and prefix + name in coverage.get(system, [])
                and probes <= set(observed.get(prefix + name, []))}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
