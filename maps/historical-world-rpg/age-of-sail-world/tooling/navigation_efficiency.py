"""Compile the bounded navigation contract and its executable definitions."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '_shared/engine'))
from voyage_navigation import VoyageCatalog


def build(project=ROOT):
    project = Path(project)
    world = json.loads((project / 'scenario/world/world.json').read_text())
    data = json.loads((project / 'scenario/naval/navigation-efficiency.json').read_text())
    catalog = VoyageCatalog(data, world)
    science = json.loads((project / 'scenario/progression/science-exploration.json').read_text())
    sites = {s['id']: s for s in science['sites']}
    catalog.commissioning = sites
    for source in catalog.sources.values():
        if source['equipmentSiteId']:
            site = sites.get(source['equipmentSiteId'])
            if not site or site.get('commissioningOnly') is not True or site['capability'] != 'coastal_chart_bearings' or site['forceId'] not in catalog.ships or not catalog.ships[site['forceId']]['coastalBearingCapable']:
                raise ValueError('navigation requires compatible paid coastal commissioning')
    physical = json.loads((project / 'physical-maps.json').read_text())
    maps = {m['id']: m for m in physical['physicalMaps']}
    for route in catalog.routes.values():
        if route['mapId'] not in maps or route['knownRegionId'] not in maps[route['mapId']]['assignments']['logicalRegionIds']:
            raise ValueError('voyage route is outside its physical map')
    return catalog, world


def wurst(catalog, world):
    q = json.dumps
    lines = ['public function createGeneratedVoyageContract() returns VoyageContract',
             f'\tlet contract = new VoyageContract({q(catalog.kind)}, {q(catalog.content)}, {catalog.reduction}, {catalog.equipment_cost})']
    for source in catalog.sources.values():
        args = [q(source['id']), q(source['entitlement']['kind']), q(source['entitlement']['contentId']), str(source['reductionBasisPoints']), q(source['equipmentSiteId']), q(source['qualification'])]
        lines.append('\tcontract.addSource(new VoyageSource(' + ', '.join(args) + '))')
        lines.append(f'\tcontract.source({q(source["id"])}).inspection = {q(inspection(catalog, source))}')
    for route_index, r in enumerate(catalog.routes.values()):
        args = [q(r['id']), q(r['mapId']), q(r['knownRegionId']), str(r['days']), str(r['dailyProvisions']), str(r['dailyPositionFindingProvisions'])]
        lines.append(f'\tlet route{route_index} = new VoyageRoute(' + ', '.join(args) + ')')
        lines.append(f'\troute{route_index}.coastalBearingDays = ' + q(''.join('1' if x else '0' for x in r['coastalBearingDays'])))
        lines.append(f'\tcontract.addRoute(route{route_index})')
    templates = {t['id']: t['warcraftUnitTypeId'] for t in world['militaryRuntimeTemplates']}
    for s in catalog.ships.values():
        lines.append(f'\tcontract.addShip(new VoyageShip({q(s["forceId"])}, \'{templates[s["runtimeTemplateId"]]}\', {q(s["mapId"])}, {s["stationPosition"][0]}., {s["stationPosition"][1]}., {q("|" + "|".join(s["routeIds"]) + "|")}))')
        lines.append(f'\tcontract.ship({q(s["forceId"])}).coastalBearingCapable = {str(s["coastalBearingCapable"]).lower()}')
    return '\n'.join(lines + ['\treturn contract', ''])


COASTAL_UNLOCK = ('modifier', 'progression_coastal_triangulation')
COASTAL_COMPARISON = 'coastalOnlyRegisteredVoyageCommits92For100OverheadAgainstMatchedControl'
COASTAL_TESTS = {
    COASTAL_COMPARISON,
    'coastalAndCelestialComposeOnceInCommonBucketAcrossResumeAndDuplicateGrants',
    'coastalRejectsMissingInputsEquipmentUnsupportedSegmentsAndOverlappingWork',
    'coastalPlayerAiActiveInactiveCaptureInterruptAndDestructionConserveProvisions',
    'coastalLegacyMigrationAndMalformedSourceRecordsPreserveCelestialReservation',
    'coastalFailedCampaignLoadRollsBackEquipmentPaymentsProvisionsAndFractions',
}
COASTAL_PROBES = {'research', 'dispatch', 'science_registration', 'science_action',
                  'science_pay', 'voyage_registration', 'voyage_start',
                  'voyage_qualify', 'voyage_advance', 'voyage_resolve', 'voyage_commit'}


def inspection(catalog, source):
    text = (f"{source['reductionBasisPoints']} bp reduction of position-finding provision overhead only; "
            "reserve full undiscounted voyage provisions. No change to food, weather losses, hull damage, time or discovery. "
            "Requires current-controller research and compatible purchased equipment. ")
    if source['equipmentSiteId']:
        kit = catalog.commissioning[source['equipmentSiteId']]
        text += (f"Practical coastal bearings/charts on authored shoreline days only; not later precision instruments. "
                 f"/science equip {kit['id']}: {kit['equipmentCost']} treasury minor units + "
                 f"{kit['equipmentUnits']} {kit['good']}, {kit['equipmentDays']} preparation days at {kit['settlementId']}; "
                 f"requires {kit['prerequisite']}, local access and control. No overlapping voyage or science work. ")
    else:
        text += f"Astronomical observation kit: /voyage-kit FORCE install, {catalog.equipment_cost} money. "
    return text + "Research grants no kit or geography; independent eligible navigation sources add once before shared rounding."


def consumers(catalog):
    return [dict(nodeId=s['id'], kind=s['entitlement']['kind'],
                 contentId=s['entitlement']['contentId'],
                 metric='position_finding_provision_overhead',
                 reductionBasisPoints=s['reductionBasisPoints'],
                 equipmentSiteId=s['equipmentSiteId'], qualification=s['qualification'], inspection=inspection(catalog, s),
                 runtimeConsumer='MilitarySettlementRuntime.resolveVoyages/VoyageContract.resolveSources')
            for s in catalog.sources.values()]


def verified_bindings(project, execution=None, execution_log=None, revision=None):
    """Closure requires the exact identity and complete pinned current-source evidence."""
    if execution is None or execution_log is None or revision is None:
        return set()
    from integration_evidence import verify_execution_coverage
    from wurst_execution import WurstExecutionError
    try:
        coverage = verify_execution_coverage(execution, execution_log, project, revision)
        prefix = 'wurst/CoastalNavigationTests.wurst:'
        passed = {r['id'] for r in execution['tests'] if r['status'] == 'pass'}
        comparison = prefix + COASTAL_COMPARISON
        if (not {prefix + name for name in COASTAL_TESTS} <= passed
                or comparison not in coverage.get('coastal_navigation', [])
                or not COASTAL_PROBES <= set(execution['productionCoverage']['tests'].get(comparison, []))):
            return set()
        catalog, _ = build(project)
        coastal = [s for s in catalog.sources.values() if s['id'] == 'coastal_triangulation'
                   or s['entitlement'] == dict(zip(('kind', 'contentId'), COASTAL_UNLOCK))]
        if len(coastal) != 1 or coastal[0] != dict(
                id='coastal_triangulation', entitlement={'kind': COASTAL_UNLOCK[0], 'contentId': COASTAL_UNLOCK[1]},
                reductionBasisPoints=800, equipmentSiteId='channel_coastal_bearing_kit', qualification='coastal_bearings'):
            return set()
        science = json.loads((Path(project) / 'scenario/progression/science-exploration.json').read_text())
        sites = [s for s in science['sites'] if s['id'] == coastal[0]['equipmentSiteId']]
        if len(sites) != 1 or any(type(sites[0][k]) is not type(v) or sites[0][k] != v for k, v in dict(
                equipmentCost=120, equipmentUnits=2, equipmentDays=7, good='cloth',
                prerequisite='pilot_books', commissioningOnly=True).items()):
            return set()
        return {COASTAL_UNLOCK}
    except (WurstExecutionError, ValueError, OSError, KeyError, TypeError, AttributeError):
        return set()


if __name__ == '__main__':
    catalog, world = build()
    print(json.dumps(dict(catalog=catalog.data, consumers=consumers(catalog), wurst=wurst(catalog, world), sources=[
        'scenario/naval/navigation-efficiency.json', 'scenario/progression/science-exploration.json', 'tooling/navigation_efficiency.py', 'physical-maps.json'])))
