"""Compile scenario predicates against the existing, inherited unit roster."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '_shared/engine'))
from combat_effects import CombatCatalogue, verify_executable_bindings
from validate_unit_roster import load_catalog


def build(project=ROOT):
    project = Path(project)
    data = json.loads((project / 'scenario/combat-effect-bindings.json').read_text())
    traditions = json.loads((project / 'scenario/military-traditions.json').read_text())
    world = json.loads((project / 'scenario/world/world.json').read_text())
    catalog = CombatCatalogue(data, traditions, load_catalog(), world)
    return catalog


def wurst(catalog):
    def quote(value):
        return json.dumps(value, ensure_ascii=True)
    lines = ['public function createGeneratedCombatBindings() returns CombatBindings',
             '\tlet bindings = new CombatBindings()']
    for row in catalog.attributes.values():
        lines.append(f'\tbindings.addAttribute({quote(row["id"])}, {quote(row["categoryId"])}, {quote(row["attackId"] or "")}, {quote(row["stat"] or "")})')
    for row in catalog.research_effects.values():
        args = [row['sourceId'], row['entitlement']['kind'], row['entitlement']['contentId'], row['recipient']['kind'], row['recipient']['categoryId'], row['stat'], str(row['basisPoints']), row['description']]
        if row['recipient']['kind'] == 'weapon_attack':
            args = [row['sourceId'], row['entitlement']['kind'], row['entitlement']['contentId'], row['recipient']['categoryId'], row['recipient']['attackId'], str(row['basisPoints']), row['description']]
            lines.append('\tbindings.addResearchAttack(' + ', '.join(map(quote, args)) + ')')
            for profile in catalog.profiles.values():
                if (any(a['id'] == row['recipient']['attackId'] and a['categoryId'] == row['recipient']['categoryId'] for a in profile['attacks'])
                        and set(profile['weaponIds']) & set(row['recipient']['weaponIds'])):
                    lines.append('\tbindings.addResearchWeapon(' + quote(row['sourceId']) + ', ' + quote(profile['id']) + ')')
        else:
            lines.append('\tbindings.addResearch(' + ', '.join(map(quote, args)) + ')')
    for index, row in enumerate(catalog.effects.values()):
        lines.append(f'\tlet effect{index} = bindings.addEffect({quote(row["id"])}, {quote(row["sourceId"])}, {quote(row["categoryId"])}, {quote(row["description"])})')
        for contribution in row['contributions']:
            lines.append(f'\teffect{index}.contributions.replace({quote(row["sourceId"])}, {quote(contribution["attackId"])}, {quote(contribution["stat"])}, new ExactRational("{contribution["basisPoints"]}", "1", "1"))')
    profiles = list(catalog.profiles.values())
    for start in range(0, len(profiles), 40):
        lines.append(f'\tcombatProfiles{start}(bindings)')
    lines += ['\treturn bindings', '']
    for start in range(0, len(profiles), 40):
        lines.append(f'function combatProfiles{start}(CombatBindings bindings)')
        for row in profiles[start:start + 40]:
            attack = row['attacks'][0] if row['attacks'] else dict(categoryId='', id='', nativeAttack='')
            lines.append(f'\tbindings.addProfile({quote(row["id"])}, \'{row["unitTypeId"]}\', {row["kind"]}, {quote(attack["categoryId"])}, {quote(attack["id"])}, {quote(attack["nativeAttack"])})')
        lines.append('')
    return '\n'.join(lines)


def verify(source, catalog):
    # Compare every executable binding, including native predicates and all
    # numerical contributions, not only a retained JSON catalogue.
    verify_executable_bindings(source, wurst(catalog))


if __name__ == '__main__':
    catalog = build()
    sources = ['scenario/combat-effect-bindings.json', 'scenario/military-traditions.json',
               'tooling/combat_effect_catalog.py', 'tooling/validate_unit_roster.py']
    sources += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'scenario/rosters').glob('*.json'))]
    print(json.dumps(dict(catalog=catalog.data, profiles=list(catalog.profiles.values()),
                          wurst=wurst(catalog), sources=sources)))
