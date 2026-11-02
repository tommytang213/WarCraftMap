"""Generate land-party membership from the same raster as boundary arrivals."""
import json
from itertools import groupby

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


def configure_rows(receiver, rows):
    """Keep repeated raster rows as bounded loops instead of expanded Lua writes.

    This changes only executable initialization, not the raster or its component
    labels. Short runs stay explicit so loop overhead cannot grow the payload.
    """
    lines = []
    for row, entries in groupby(enumerate(rows), key=lambda entry: entry[1]):
        indices = [index for index, _ in entries]
        if len(indices) >= 4:
            lines += [f'\tfor row = {indices[0]} to {indices[-1]}',
                      f'\t\t{receiver}.rows[row] = {json.dumps(row)}']
        else:
            lines += [f'\t{receiver}.rows[{index}] = {json.dumps(row)}' for index in indices]
    return lines


def configuration(maps):
    lines = []
    for index, (map_id, data) in enumerate(maps.items()):
        lines += [f'function generatedPartyNavigation{index}() returns PartyNavigation',
                  f'\tlet nav = new PartyNavigation({json.dumps(map_id)}, {data["minX"]}, {data["minY"]}, {data["width"]}, {data["height"]})']
        lines += configure_rows('nav', data['rows'])
        lines += ['\treturn nav', '']
    lines.append('public function configureGeneratedPartyNavigation(PlayableCampaignState state)')
    for index, map_id in enumerate(maps):
        lines += [f'\tif state.loadedPhysicalMap == {json.dumps(map_id)}',
                  f'\t\tstate.partyNavigation = generatedPartyNavigation{index}()']
    if not maps:
        lines.append('\tskip')
    return '\n'.join(lines) + '\n'
