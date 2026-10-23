"""Project approved agricultural effects and authored local economy predicates.

Only grain-producing hinterlands farm. Other grain markets can build storage.
Quantities compress actual seed, tools, labor and local market tax capacity;
settlement count is never a multiplier on a polity's historical resources.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def validate_rules(rules):
    if rules.get('schemaVersion')!=1:
        raise ValueError('Unsupported agriculture contract schema')
    for key,value in rules.items():
        if isinstance(value,int) and (type(value) is not int or value<1 or value>100000):
            raise ValueError(f'Invalid agricultural quantity: {key}')
    for key in ('policyCostBp','policyUpkeepBp','granaryCostBp','granarySpoilageReductionBp',
                'tenureTaxBp','tenureUnrestBp','enclosureUnrestBp','societyFarmBp',
                'seedFractionBp','spoilageBp','normalTaxOnGrossBp','laborOnTaxBp'):
        if type(rules.get(key)) is not int or not 1<=rules[key]<=10000:
            raise ValueError(f'Invalid agricultural basis points: {key}')
    if rules['storageStockMultiplier']>16 or rules['maximumKnowledge']>1000:
        raise ValueError('Agriculture support budget exceeds its domain range')


def build(project=ROOT):
    project=Path(project)
    rules=json.loads((project/'scenario/progression/agriculture.json').read_text())
    validate_rules(rules)
    design=json.loads((project/rules['designSource']).read_text())
    world=json.loads((project/'scenario/world/world.json').read_text())
    nodes={x['id']:x for x in world['technologies']+world['institutions']}
    effects=[]
    for row in design['effects']:
        if row['family']!='agriculture':
            continue
        node=nodes[row['nodeId']]
        kind,content=row['unlock']['kind'],row['unlock']['contentId']
        if {'kind':kind,'contentId':content} not in node['unlocks']:
            raise ValueError('Agricultural entitlement no longer matches authored research')
        building=kind=='building'
        tenure=content=='land_tenure_reform'
        enclosure=content=='enclosure'
        effects.append(dict(description=row['rules'],nodeId=row['nodeId'],kind=kind,contentId=content,metric=row['metric'],bonus=row['bonusBasisPoints'],
            secondary=rules['granarySpoilageReductionBp'] if building else rules['tenureTaxBp'] if tenure else rules['societyFarmBp'] if not enclosure else 0,
            unrest=rules['tenureUnrestBp'] if tenure else rules['enclosureUnrestBp'] if enclosure else 0,
            unrestDays=rules['enclosureUnrestDays'] if enclosure else 0,
            costBp=rules['granaryCostBp'] if building else rules['policyCostBp'],upkeepBp=0 if building else rules['policyUpkeepBp'],
            duration=rules['granaryDurationDays'] if building else rules['policyDurationDays'],materialCost=rules['constructionMaterials'] if building else 0,
            earliestYear=node['timeCost']['preferredYear']))
    if len(effects)!=4:
        raise ValueError('Expected the four approved agricultural contracts')
    rules["agriculturalNodes"]="~"+"~".join(x["id"] for x in world["technologies"] if x["branchId"]=="agricultural")+"~"
    return rules,effects


def effect_lines(rules,effects):
    q=json.dumps
    lines=[f'\truntime.stapleId={q(rules["stapleGoodId"])}',f'\truntime.farmEquipmentId={q(rules["equipmentGoodId"])}']
    lines += [f'\truntime.agriculture.materialName={q(rules["constructionGoodId"])}', f'\truntime.constructionGoodId={q(rules["constructionGoodId"])}',f'\truntime.agriculture.agriculturalNodes={q(rules["agriculturalNodes"])}', f'\truntime.agriculture.knowledgePerSeedBp={rules["knowledgePerSeedBp"]}', f'\truntime.agriculture.maximumKnowledge={rules["maximumKnowledge"]}']
    for row in effects:
        args=[q(row[k]) for k in ('nodeId','kind','contentId','metric')]+[str(row[k]) for k in ('bonus','secondary','unrest','unrestDays','costBp','upkeepBp','duration','materialCost','earliestYear')]
        lines.append('\truntime.agriculture.addEffect(new AgricultureEffect('+','.join(args)+').described('+q(row['description'])+'))')
    return lines


# Closure requires independent production comparisons as well as the migration,
# replay and negative cases. Runtime labels and generated definitions are only
# recognition metadata; they are never release evidence.
COMPARATIVE_TESTS = {
    'agriculturalGranaryCapacityBeatsMatchedControlAfterPaidNinetyDays',
    'agriculturalGranarySpoilageBeatsMatchedControlWithoutFarming',
    'agriculturalTenureHarvestAndTaxBeatMatchedElectedControl',
    'agriculturalEnclosureHarvestSeparatesEfficiencyFromTwoYearUnrest',
    'agriculturalSocietiesSeparateDiffusionAndConditionalFarmOutput',
}
REQUIRED_TESTS = COMPARATIVE_TESTS | {
    'agriculturalProductionRegistrationConnectsResearchClockAndMarkets',
    'registeredAgriculturalResearchAndActionsDebitOnceAndRespectPrerequisites',
    'agriculturalAnnualConsumerUsesExactInputsSpoilageTaxAndEarnedDiffusion',
    'agriculturalRejectionsUseCurrentControlSupplyOfficeEquipmentAndNetwork',
    'agriculturalSaveMigrationFailedLoadAndCaptureRetainDurableSources',
    'agriculturalAbstractReplayMatchesActiveDaysAndDuplicatesNeverStack',
    'unsupportedFarmsProduceNoKnowledgeOrExtraOutputAndUnpaidUpkeepSuspends',
    'granaryConstructionConsumesDeliveredMaterialsAndTheirCostBasis',
    'agriculturalLateCampaignLoadRollbackRestoresPaidProjectsResourcesAndClock',
    'allFourAgriculturalOptionsHaveIdenticalControllerRulesAndOutcomes',
    'researchAloneNeverStartsOrganizationsAndLastToolSupportsTheSameHarvestTax',
    'agriculturalWrongKindsMissingSeedLaborAndTaxLiquidityNeverCreateBenefits',
}
PRODUCTION_PROBES = {
    'agriculture_definitions', 'agriculture_registration', 'dispatch', 'research',
    'agriculture_layers', 'agriculture_action', 'agriculture_clock',
    'agriculture_advance', 'agriculture_pay', 'agriculture_harvest',
    'agriculture_tax', 'agriculture_storage',
}


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        verify_execution_coverage(execution, execution_log, project, revision)
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()
    prefix = 'wurst/AgricultureTests.wurst:'
    passed = {r['id'][len(prefix):] for r in execution['tests']
              if r['status'] == 'pass' and r['id'].startswith(prefix)}
    probes = execution.get('productionCoverage', {}).get('tests', {})
    if not REQUIRED_TESTS <= passed:
        return set()
    for name in COMPARATIVE_TESTS:
        required = PRODUCTION_PROBES | ({'agriculture_adoption'} if 'Societies' in name else set())
        if not required <= set(probes.get(prefix + name, [])):
            return set()
    wiring = {'domains', 'agriculture_definitions', 'agriculture_layers',
              'agriculture_clock', 'agriculture_advance', 'agriculture_storage'}
    if not wiring <= set(probes.get(prefix + 'agriculturalProductionRegistrationConnectsResearchClockAndMarkets', [])):
        return set()
    _, effects = build(project)
    return {(e['kind'], e['contentId']) for e in effects}


if __name__=='__main__':
    rules,effects=build()
    print(json.dumps(dict(rules=rules,effects=effects,wurst=effect_lines(rules,effects),sources=['scenario/progression/agriculture.json','scenario/progression/gameplay-effect-design.json','scenario/progression/catalog.json','tooling/agriculture_catalog.py'])))
