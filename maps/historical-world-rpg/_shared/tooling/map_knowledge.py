"""Compile the named region/settlement slice of the scenario map catalogue.

Knowledge needs identity and membership even for settlements without a drawn
map point. Geometry and hidden POIs stay in the existing presentation catalogue.
"""
import json
import re

from scenario_inputs import configuration


def knowledge_catalog(project):
    config = configuration(project)
    world = json.loads((project / config['scenario']['data']).read_text())
    regions = world['regionalGeography']['regions']
    membership = {}
    physical = project / 'physical-maps.json'
    if physical.is_file():
        for row in json.loads(physical.read_text())['physicalMaps']:
            assigned = row['assignments']
            if len(assigned['logicalRegionIds']) == 1:
                for ident in assigned['regionalInstanceIds']:
                    membership[ident] = assigned['logicalRegionIds'][0]
    presentation = project / config['scenario'].get('mapPresentation', 'scenario/maps/world-map.json')
    if presentation.is_file():
        for ident, region in json.loads(presentation.read_text()).get('regionalInstanceRegions', {}).items():
            if ident in membership and membership[ident] != region:
                raise ValueError(f'map catalogue: inconsistent regional membership for {ident}')
            membership[ident] = region
    known = config['scenario'].get('initiallyKnownRegionIds', [])
    ids = {row['id'] for row in regions}
    if set(known) - ids or len(regions) > 64 or len(world['settlements']) > 2048:
        raise ValueError('map catalogue: invalid starting regions or capacity')
    settlements = []
    for row in world['settlements']:
        region = membership.get(row['regionalInstanceId'])
        if region not in ids:
            raise ValueError(f'map catalogue: settlement {row["id"]} has no regional membership')
        settlements.append(dict(id=row['id'], name=row['name'], regionId=region, kind='settlement'))
    records = [*regions, *settlements]
    if len({row['id'] for row in records}) != len(records):
        raise ValueError('map catalogue: duplicate ID')
    for row in records:
        if not re.fullmatch(r'[a-z][a-z0-9_]*', row['id']) or not row['name'].strip():
            raise ValueError('map catalogue: invalid ID or name')
    return dict(version=1, regions=[dict(id=row['id'], name=row['name'], initiallyKnown=row['id'] in known)
                                   for row in regions], settlements=settlements)


def configuration_lines(catalog):
    lines = ['', 'DiscoveryCatalog generatedMapCatalog = null', '',
             'public function scenarioMapCatalog() returns DiscoveryCatalog',
             '\tif generatedMapCatalog == null',
             '\t\tgeneratedMapCatalog = new DiscoveryCatalog()']
    for row in catalog['regions']:
        lines.append('\t\tgeneratedMapCatalog.addRegion(' + ', '.join([
            json.dumps(row['id']), json.dumps(row['name']), str(row['initiallyKnown']).lower()]) + ')')
    for row in catalog['settlements']:
        lines.append('\t\tgeneratedMapCatalog.addSettlement(' + ', '.join(
            json.dumps(row[key], ensure_ascii=False) for key in ('id', 'name', 'regionId')) + ')')
    return lines + ['\treturn generatedMapCatalog', '']
