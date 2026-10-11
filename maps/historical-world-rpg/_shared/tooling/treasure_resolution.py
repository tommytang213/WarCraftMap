"""Emit authored treasure choices and physical bindings, never campaign choices."""
import copy
import json

from treasures import validate_catalog


def definitions(catalog, locations):
    if not catalog:
        return {}
    validate_catalog(catalog)
    result = copy.deepcopy(catalog)
    physical = {row['id']: row for row in locations if row['kind'] == 'treasure'}
    for candidate in result['candidateLocations']:
        target = physical.get(candidate['id'])
        if target is None or not target['movements']:
            raise ValueError(f"treasure {candidate['id']}: no compatible physical/navigation binding")
        candidate['placement'] = copy.deepcopy(target)
    # This is migration metadata ONLY. v2-v6 stored no location; retain exactly
    # what the old packager exposed. Never use this field for a new campaign.
    for treasure in result['treasures']:
        treasure['legacyLocationId'] = treasure.get('legacyCandidateLocationId', '')
    return result


def configuration(catalog):
    q = json.dumps
    lines = ['public function configureGeneratedTreasures(TreasureRuntime runtime)']
    if not catalog:
        return '\n'.join(lines + ['\tskip']) + '\n'
    candidates = {row['id']: row for row in catalog['candidateLocations']}
    pools = {row['id']: row for row in catalog['rewardPools']}
    clues = {row['id']: row for row in catalog['clues']}
    precisions = {'region': 1, 'approximate': 2, 'narrowed': 3, 'exact': 4}
    def ids(values):
        return ''.join('|' + value + '|' for value in values)
    for index, row in enumerate(catalog['treasures']):
        d, t = f'td{index}', f't{index}'
        lines += [f'\tlet {d} = new TreasureDefinition({q(row["id"])})',
                  f'\t{d}.unique = {str(row["kind"] == "unique").lower()}',
                  f'\t{d}.anchorRegions = {q(ids(row.get("anchorRegionIds", [])))}',
                  f'\t{d}.families = {q(ids(row.get("locationFamilies", [])))}',
                  f'\t{d}.legacyLocationId = {q(row["legacyLocationId"])}',
                  f'\t{d}.fallbackId = {q(row.get("fallbackCandidateId", ""))}']
        candidate_ids = list(row['candidateLocationIds'])
        if row.get('fallbackCandidateId') and row['fallbackCandidateId'] not in candidate_ids:
            candidate_ids.append(row['fallbackCandidateId'])
        for ci, cid in enumerate(candidate_ids):
            c = candidates[cid]; v = f'c{index}_{ci}'; binding = c['placement']
            args = [c['id'], c['regionId'], c['regionalInstanceId'], binding['mapId'], c['terrainId'], c['navigationZoneId'], c.get('locationFamily', '')]
            lines.append(f'\tlet {v} = new TreasureCandidate(' + ', '.join(map(q, args)) + ')')
            fields = dict(weight=c.get('weight', 1), clearance=float(c['clearance']), accessible=c['accessible'],
                          shared=c.get('allowSharedPlacement', False), placementValid=True, inactivePolicy=c['inactiveRegionPolicy'],
                          x=float(binding['world'][0]), y=float(binding['world'][1]), fallbackOnly=cid not in row['candidateLocationIds'])
            lines.extend(f'\t{v}.{key} = {q(value)}' for key, value in fields.items())
            lines.append(f'\t{d}.add({v})')
        for clue_index, clue_id in enumerate(row.get('clueIds', [])):
            lines.append(f'\t{d}.cluePrecisions[{clue_index}] = {precisions[clues[clue_id]["precision"]]}')
        for entry in pools[row['rewardPoolId']]['entries']:
            lines.append(f'\t{d}.rewards.add({q(entry["id"])}, {entry["weight"]})')
        for field, prop in [('guardIds', 'guards'), ('hazardIds', 'hazards'), ('encounterIds', 'encounters')]:
            lines.extend(f'\t{d}.{prop}.add({q(value)}, 1)' for value in row.get(field, []))
        lines += [f'\tlet {t} = new RuntimeTreasure({q(row["id"])}, "", "")',
                  f'\t{t}.definition = {d}', f'\t{t}.clueCount = {len(row.get("clueIds", []))}', f'\truntime.register({t})']
    return '\n'.join(lines) + '\n'
