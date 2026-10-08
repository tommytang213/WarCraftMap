"""Physical edge navigation derived from the same raster as packaged WPM.

Connectivity is four-neighbour, movement-specific, and confined to the playable
rectangle. Only components touching the declared edge segment can supply an
arrival. No settlement object or guessed regional spawn participates.
"""
from collections import deque
import math
import struct

CELL = 128.0
TRIGGER_DEPTH = 128.0
ARRIVAL_TOLERANCE = 512.0
CLEARANCE = 32.0
ARRIVAL_DEPTHS = (192.0, 320.0, 448.0)
MOVEMENTS = {0: {1}, 1: {2}, 2: {1, 2}, 3: {1, 2}}


def playable_cells(info: bytes, width: int, height: int):
    """W3I complementary margins delimit the playable part of centered W3E."""
    offset = 28
    for _ in range(4):
        offset = info.index(0, offset) + 1
    left, right, bottom, top = struct.unpack_from('<4i', info, offset + 32)
    if min(left, right, bottom, top) < 0 or left + right >= width or bottom + top >= height:
        raise ValueError('invalid physical playable margins')
    return left, bottom, width - right, height - top


def components(width, height, cells, bounds, movement):
    left, bottom, right, top = bounds
    labels = [0] * len(cells)
    count = 0
    for y in range(bottom, top):
        for x in range(left, right):
            start = y * width + x
            if labels[start] or cells[start] not in MOVEMENTS[movement]:
                continue
            count += 1
            labels[start] = count
            pending = deque([(x, y)])
            while pending:
                px, py = pending.popleft()
                for nx, ny in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                    if left <= nx < right and bottom <= ny < top:
                        index = ny * width + nx
                        if not labels[index] and cells[index] in MOVEMENTS[movement]:
                            labels[index] = count
                            pending.append((nx, ny))
    return labels


def endpoint(width, height, cells, bounds, edge, interval, labels_by_movement=None):
    left, bottom, right, top = bounds
    min_x, min_y = (left-width/2)*CELL, (bottom-height/2)*CELL
    max_x, max_y = (right-width/2)*CELL, (top-height/2)*CELL
    vertical = edge in ('east', 'west')
    low, high = (bottom, top) if vertical else (left, right)
    origin = -height*CELL/2 if vertical else -width*CELL/2
    segment_low = origin + (low + (high-low)*interval[0])*CELL
    segment_high = origin + (low + (high-low)*interval[1])*CELL
    spans = []
    for movement in MOVEMENTS:
        labels = (labels_by_movement or {}).get(movement)
        if labels is None:
            labels = components(width, height, cells, bounds, movement)
        for depth in (0., *ARRIVAL_DEPTHS):
            layer = int(depth // CELL)
            runs = []
            for along in range(low, high):
                if edge == 'west': x, y = left+layer, along
                elif edge == 'east': x, y = right-1-layer, along
                elif edge == 'south': x, y = along, bottom+layer
                else: x, y = along, top-1-layer
                label = labels[y*width+x]
                if label and runs and runs[-1][2] == label and runs[-1][1] == along:
                    runs[-1][1] += 1
                elif label:
                    runs.append([along, along+1, label])
            for start, end, label in runs:
                # Keep arrivals out of ALL edge triggers, including corners.
                margin = CLEARANCE if depth else 0.
                a = max(origin+start*CELL+margin, segment_low,
                        origin+low*CELL+(TRIGGER_DEPTH+CLEARANCE if depth else 0.))
                b = min(origin+end*CELL-margin, segment_high,
                        origin+high*CELL-(TRIGGER_DEPTH+CLEARANCE if depth else 0.))
                if a <= b:
                    spans.append([movement, label, depth, a, b])
    return dict(edge=edge, interval=list(interval), bounds=[min_x, min_y, max_x, max_y], spans=spans)


def resolve(endpoint, position, movement=0, pathable=lambda x, y, movement: True):
    """Headless oracle for the Wurst resolver; saved position is already transformed."""
    if not math.isfinite(position) or not 0 <= position <= 1:
        return None
    min_x, min_y, max_x, max_y = endpoint['bounds']
    edge = endpoint['edge']
    vertical = edge in ('east', 'west')
    low, high = (min_y, max_y) if vertical else (min_x, max_x)
    a, b = endpoint['interval']
    desired = low + (high-low)*(a+(b-a)*position)
    seeds = [(abs(max(start, min(end, desired))-desired), component)
             for kind, component, depth, start, end in endpoint['spans'] if kind == movement and depth == 0]
    if not seeds:
        return None
    distance, component = min(seeds)
    if distance > ARRIVAL_TOLERANCE:
        return None
    best = None
    for kind, connected, depth, start, end in endpoint['spans']:
        if kind != movement or connected != component or depth == 0:
            continue
        closest = max(start, min(end, desired))
        for step in range(33):
            shift = ((step+1)//2)*CLEARANCE * (1 if step % 2 else -1)
            along = closest+shift
            squared = (along-desired)**2 + depth**2
            if start <= along <= end and squared <= ARRIVAL_TOLERANCE**2:
                x = min_x+depth if edge == 'west' else max_x-depth if edge == 'east' else along
                y = min_y+depth if edge == 'south' else max_y-depth if edge == 'north' else along
                if (best is None or squared < best[0]) and pathable(x, y, movement):
                    best = squared, x, y
    return None if best is None else best[1:]


def verify_packaged_navigation(endpoints, map_id, info, pathing, party_navigation=None, recovery=None):
    """Re-prove the generated arrival corridors against the packaged WPM.

    A compiler or packaging step changing pathing must invalidate the proof,
    even when its dimensions and generic file structure remain correct.
    """
    pw, ph = struct.unpack_from('<II', pathing, 8)
    width, height = pw // 4, ph // 4
    cells = []
    values = {0x4e: 0, 0x40: 1, 0x0a: 2}
    for y in range(height):
        for x in range(width):
            pixels = {pathing[16 + (y*4+dy)*pw + x*4+dx] for dy in range(4) for dx in range(4)}
            if len(pixels) != 1 or next(iter(pixels)) not in values:
                raise ValueError('packaged pathing changed a boundary navigation cell')
            cells.append(values[next(iter(pixels))])
    bounds = playable_cells(info, width, height)
    labels = {m: components(width, height, cells, bounds, m) for m in MOVEMENTS}
    for key, authored in endpoints.items():
        if authored['mapId'] != map_id:
            continue
        actual = endpoint(width, height, cells, bounds, authored['edge'], authored['interval'], labels)
        actual['mapId'] = map_id
        if actual != authored:
            raise ValueError(f'packaged pathing disagrees with boundary navigation: {key}')
    if recovery is not None:
        from recovery_navigation import recovery_navigation
        if recovery != recovery_navigation(width, height, cells, bounds):
            raise ValueError('packaged pathing disagrees with recovery navigation')
    if party_navigation is not None:
        from party_locations import navigation
        if party_navigation != navigation(width, height, cells, bounds, labels[0]):
            raise ValueError('packaged pathing disagrees with party navigation')
