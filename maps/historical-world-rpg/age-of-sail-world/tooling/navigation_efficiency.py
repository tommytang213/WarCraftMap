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
    for r in catalog.routes.values():
        args = [q(r['id']), q(r['mapId']), q(r['knownRegionId']), str(r['days']), str(r['dailyProvisions']), str(r['dailyPositionFindingProvisions'])]
        lines.append('\tcontract.addRoute(new VoyageRoute(' + ', '.join(args) + '))')
    templates = {t['id']: t['warcraftUnitTypeId'] for t in world['militaryRuntimeTemplates']}
    for s in catalog.ships.values():
        lines.append(f'\tcontract.addShip(new VoyageShip({q(s["forceId"])}, \'{templates[s["runtimeTemplateId"]]}\', {q(s["mapId"])}, {s["stationPosition"][0]}., {s["stationPosition"][1]}., {q("|" + "|".join(s["routeIds"]) + "|")}))')
    return '\n'.join(lines + ['\treturn contract', ''])


if __name__ == '__main__':
    catalog, world = build()
    print(json.dumps(dict(catalog=catalog.data, wurst=wurst(catalog, world), sources=[
        'scenario/naval/navigation-efficiency.json', 'tooling/navigation_efficiency.py', 'physical-maps.json'])))
