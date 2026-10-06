"""Generate land-party membership from the same raster as boundary arrivals."""
import json

from boundary_arrival import CELL, components, playable_cells


def navigation(width, height, cells, bounds, labels=None):
    labels = components(width, height, cells, bounds, 0) if labels is None else labels
    rows = []
    for y in range(height):
        runs = []
        for x in range(width):
            component = labels[y * width + x]
            if runs and runs[-1][1] == component:
                runs[-1][0] = x + 1
            else:
                runs.append([x + 1, component])
        rows.append(''.join(f'{end}:{component},' for end, component in runs))
    return dict(width=width, height=height, minX=-width * CELL / 2,
                minY=-height * CELL / 2, rows=rows)


def campaign_navigation(config, generated):
    from materialize_physical_map import physical_layout
    result = {}
    for physical in config.maps:
        if physical.bootstrap:
            continue
        width, height, cells, _ = physical_layout(generated, physical)
        if height > 1024:
            raise ValueError('party navigation row budget exceeded')
        bounds = playable_cells((physical.source_map / 'war3map.w3i').read_bytes(), width, height)
        result[physical.id] = navigation(width, height, cells, bounds)
    return result


def configuration(maps):
    lines = []
    for index, (map_id, data) in enumerate(maps.items()):
        lines += [f'function generatedPartyNavigation{index}() returns PartyNavigation',
                  f'\tlet nav = new PartyNavigation({json.dumps(map_id)}, {data["minX"]}, {data["minY"]}, {data["width"]}, {data["height"]})']
        lines += [f'\tnav.rows[{y}] = {json.dumps(row)}' for y, row in enumerate(data['rows'])]
        lines += ['\treturn nav', '']
    lines.append('public function configureGeneratedPartyNavigation(PlayableCampaignState state)')
    for index, map_id in enumerate(maps):
        lines += [f'\tif state.loadedPhysicalMap == {json.dumps(map_id)}',
                  f'\t\tstate.partyNavigation = generatedPartyNavigation{index}()']
    if not maps:
        lines.append('\tskip')
    return '\n'.join(lines) + '\n'
