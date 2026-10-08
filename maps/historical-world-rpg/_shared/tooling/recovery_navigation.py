"""Map-local recovery components/anchors from the exact packaged terrain raster."""
import json

from boundary_arrival import CELL, MOVEMENTS, components, playable_cells
from party_locations import navigation


def recovery_navigation(width, height, cells, bounds):
    result = []
    for movement in MOVEMENTS:
        labels = components(width, height, cells, bounds, movement)
        data = navigation(width, height, cells, bounds, labels)
        # A cell centre is an explicit generated anchor, never an authored world
        # coordinate. Pick the component cell closest to its centroid. Runtime
        # clearance/pathing must still validate it before any move.
        sums = {}
        for index, label in enumerate(labels):
            if label:
                sx, sy, count = sums.get(label, (0, 0, 0))
                sums[label] = sx + index % width, sy + index // width, count + 1
        best = {}
        for index, label in enumerate(labels):
            if not label:
                continue
            sx, sy, count = sums[label]
            x, y = index % width, index // width
            distance = (x * count - sx) ** 2 + (y * count - sy) ** 2
            if label not in best or distance < best[label][0]:
                best[label] = distance, (x + .5 - width / 2) * CELL, (y + .5 - height / 2) * CELL
        data['anchors'] = [[label, *best[label][1:]] for label in sorted(best)]
        result.append(data)
    if sum(len(data['anchors']) for data in result) > 4096:
        raise ValueError('recovery anchor budget exceeded')
    return result


def campaign_navigation(config, generated):
    from materialize_physical_map import physical_layout
    result = {}
    for physical in config.maps:
        if physical.bootstrap:
            continue
        width, height, cells, _ = physical_layout(generated, physical)
        if height > 1024:
            raise ValueError('recovery navigation row budget exceeded')
        bounds = playable_cells((physical.source_map / 'war3map.w3i').read_bytes(), width, height)
        result[physical.id] = recovery_navigation(width, height, cells, bounds)
    return result


def configuration(maps):
    lines = []
    for index, (map_id, kinds) in enumerate(maps.items()):
        for kind, data in enumerate(kinds):
            lines += [f'function generatedRecoveryNavigation{index}_{kind}(UnstuckRecoveryService service, RecoveryNavigation nav)',
                      f'\tlet grid = new PartyNavigation({json.dumps(map_id)}, {data["minX"]}, {data["minY"]}, {data["width"]}, {data["height"]})']
            lines += [f'\tgrid.rows[{y}] = {json.dumps(row)}' for y, row in enumerate(data['rows'])]
            lines += [f'\tnav.movement[{kind}] = grid']
            for component, x, y in data['anchors']:
                zone = f'{map_id}:{kind}:{component}'
                lines += [f'\tlet anchor{component} = new RecoveryPoint({json.dumps(zone)}, {json.dumps(zone)}, {x}, {y}, true, true)',
                          f'\tanchor{component}.addMovement({kind})', f'\tservice.addPoint(anchor{component})']
            lines.append('')
    lines += ['public function configureRecoveryScenario(UnstuckRecoveryService service, string mapId)',
              '\tservice.clearEntities()',
              '\tfor i = 0 to service.pointCount - 1', '\t\tdestroy service.points[i]',
              '\tservice.pointCount = 0',
              '\tif service.navigation != null',
              '\t\tfor i = 0 to 3', '\t\t\tif service.navigation.movement[i] != null',
              '\t\t\t\tdestroy service.navigation.movement[i]', '\t\tdestroy service.navigation',
              '\tservice.navigation = new RecoveryNavigation(mapId)']
    for index, map_id in enumerate(maps):
        lines += [f'\tif mapId == {json.dumps(map_id)}']
        lines += [f'\t\tgeneratedRecoveryNavigation{index}_{kind}(service, service.navigation)' for kind in range(4)]
    return '\n'.join(lines) + '\n'
