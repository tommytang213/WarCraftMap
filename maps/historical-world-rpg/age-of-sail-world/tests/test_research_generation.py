"""Compare compiled research definitions with every authoritative graph node."""
import json
import copy
from decimal import Decimal
from dataclasses import replace
from pathlib import Path
import re
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from package_wurst_map import generate, load_config, research_time_cost, PackagingError


def generated_research(source):
    definitions = {}
    for match in re.finditer(
        r'let (technology\d+)=new RuntimeTechnology\("([^"]+)".*?'
        r'runtime\.technologies\.register\(\1\)', source, re.S
    ):
        variable, node_id = match.group(1, 2)
        body = match[0]
        if node_id in definitions:
            raise AssertionError(f"duplicate generated research ID: {node_id}")
        definitions[node_id] = {
            "kind": re.search(rf'{variable}\.kind="([^"]+)"', body)[1],
            "prerequisites": re.findall(rf'{variable}\.addPrerequisite\("([^"]+)"\)', body),
            "timeCost": re.search(r'RuntimeTechnology\("[^"]+","[^"]+",(-?\d+),"([^"]+)","([^"]+)","([^"]+)"\)', body).groups(),
            "unlocks": re.findall(rf'{variable}\.addUnlock\("([^"]+)","([^"]+)","([^"]+)"\)', body),
            "unlockCount": int(re.search(rf'{variable}\.expectedUnlockCount=(\d+)', body)[1]),
        }
    return definitions


class ResearchGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.config = load_config(PROJECT / "package.json")
        generated = Path(cls.temp.name) / "generated"
        generate(cls.config, generated)
        cls.source = (generated / "ScenarioData.wurst").read_text(encoding="utf-8")
        world = json.loads(cls.config.scenario_file.read_text(encoding="utf-8"))
        cls.world = world
        cls.runtime = json.loads((generated / 'scenario-runtime.json').read_text())
        cls.expected = {
            row["id"]: {"kind": kind, "prerequisites": row["prerequisiteIds"],
                        "unlocks": [(row["id"], u["kind"], u["contentId"]) for u in row["unlocks"]],
                        "unlockCount": len(row["unlocks"]),
                        "timeCost": tuple(str(row["timeCost"][key]) for key in
                            ("preferredYear", "baseCost", "aheadOfTimeCostMultiplier", "additionalMultiplierPerYearAhead"))}
            for kind, records in (("technology", world["technologies"]),
                                  ("institution", world["institutions"]))
            for row in records
        }

    def assert_complete(self, source):
        actual = generated_research(source)
        self.assertEqual(set(self.expected), set(actual))
        for node_id, expected in self.expected.items():
            self.assertEqual(expected, actual[node_id], node_id)

    def test_all_authored_prerequisites_and_stable_ids_are_generated_in_order(self):
        self.assert_complete(self.source)
        self.assertEqual(
            ["trace_italienne", "military_fiscal_state"],
            generated_research(self.source)["flintlock_drill"]["prerequisites"],
        )

    def test_first_prerequisite_only_fixture_is_rejected(self):
        seen = set()

        def truncate(match):
            variable = match[1]
            if variable in seen:
                return ""
            seen.add(variable)
            return match[0]

        # Reproduce the old generator's [0] data loss on the full authored graph.
        fixture = re.sub(r'\t(technology\d+)\.addPrerequisite\("[^"]+"\)\n',
                         truncate, self.source)
        with self.assertRaises(AssertionError):
            self.assert_complete(fixture)
        actual = generated_research(fixture)
        missing = {node_id for node_id, expected in self.expected.items()
                   if actual[node_id] != expected}
        self.assertEqual({node_id for node_id, row in self.expected.items()
                          if len(row["prerequisites"]) > 1}, missing)
        self.assertIn("flintlock_drill", missing)
        self.assertIn("scientific_societies", missing)

    def test_repeated_generation_is_byte_identical(self):
        generated = Path(self.temp.name) / "again"
        generate(self.config, generated)
        self.assertEqual(self.source, (generated / "ScenarioData.wurst").read_text(encoding="utf-8"))

    def test_all_220_typed_unlocks_and_13_multi_unlock_nodes_are_retained(self):
        self.assert_complete(self.source)
        expected = [entry for row in self.expected.values() for entry in row['unlocks']]
        self.assertEqual(220, len(expected))
        self.assertEqual(13, sum(row['unlockCount'] > 1 for row in self.expected.values()))
        self.assertEqual(expected, [(u['nodeId'], u['kind'], u['contentId'])
                                   for u in self.runtime['researchUnlockDefinitions']])
        self.assertEqual(self.runtime['researchIntegrationBlockers'], [
            dict(nodeId=n, kind=k, contentId=c, bindingStatus='unbound', reason='missing_gameplay_consumer')
            for n, k, c in expected if (k, c) not in {('modifier', 'army_discipline'),
                ('modifier', 'progression_campaign_bakeries'), ('modifier', 'progression_canal_logistics'),
                ('modifier', 'progression_celestial_navigation'), ('modifier', 'progression_cast_cannon'),
                ('modifier', 'progression_auction_markets'), ('modifier', 'progression_bill_of_exchange_networks'),
                ('modifier', 'progression_brokerage_houses'), ('modifier', 'progression_canal_tolls_finance'), ('unit', 'ship_of_the_line'),
                ('modifier', 'progression_careening_stations'), ('modifier', 'progression_carronade_batteries'),
                ('modifier', 'progression_carvel_hull_construction'), ('modifier', 'progression_blast_furnace_practice'),
                ('modifier', 'progression_boring_mills'), ('modifier', 'progression_central_banking'),
                ('policy', 'progression_central_bank_institution'),
                ('modifier', 'progression_chancery_archives'),
                ('policy', 'progression_chartered_municipalities')}])
        self.assertNotIn('effectMagnitude', self.source)

    def test_logistics_depots_use_materialized_service_positions_and_land_connectivity(self):
        import re
        anchors = {r['id']: r for r in self.runtime['interactionLocations'] if r['kind'] == 'settlement'}
        catalog = self.runtime['armyFoodLogistics']
        self.assertEqual(set(catalog['foodSiteIds']) - set(catalog['unreachableDepotIds']), {d['id'] for d in catalog['depots']})
        for depot in catalog['depots']:
            self.assertEqual(anchors[depot['id']]['world'], depot['servicePosition'])
            self.assertLessEqual(sum((a-b)**2 for a,b in zip(depot['servicePosition'], [depot['x'], depot['y']])), catalog['food']['approachRadius'] ** 2)
            self.assertEqual(anchors[depot['id']]['mapId'], depot['mapId'])
            grid = self.runtime['partyNavigation'][depot['mapId']]
            x = int((depot['x'] - grid['minX']) // 128)
            y = int((depot['y'] - grid['minY']) // 128)
            self.assertTrue(0 <= x < grid['width'] and 0 <= y < grid['height'], depot['id'])
            component = next(int(label) for end, label in re.findall(r'(\d+):(\d+),', grid['rows'][y]) if x < int(end))
            self.assertGreater(component, 0, depot['id'])
        self.assertTrue(catalog['depots'])
        self.assertIn('yangzhou', {d['id'] for d in catalog['depots']})
        self.assertIn('generatedLogisticsNavigation', self.source)
        self.assertIn('configureGeneratedLogisticsNavigation(ledger)', self.source)

    def test_production_adapter_cannot_substitute_native_food_capacity(self):
        bootstrap=(PROJECT.parent / '_shared/wurst/Bootstrap.wurst').read_text()
        effects=(PROJECT.parent / '_shared/wurst/ResearchEntitlements.wurst').read_text()
        self.assertIn('new WarcraftRpgRuntime(new UnboundResearchEffects())',bootstrap)
        self.assertNotIn('PLAYER_STATE_RESOURCE_FOOD_CAP',bootstrap+effects)
        self.assertNotIn('SetPlayerState',effects)
        self.assertIn('return RESEARCH_UNBOUND',effects)

    def test_dropped_unlocks_kinds_provenance_and_order_are_detected(self):
        pattern = r'\t(technology\d+)\.addUnlock\("[^"]+","[^"]+","[^"]+"\)\n'
        seen = set()
        def truncate(match):
            if match[1] in seen: return ''
            seen.add(match[1]); return match[0]
        dropped = re.sub(pattern, truncate, self.source)
        actual = generated_research(dropped)
        self.assertEqual({n for n, r in self.expected.items() if r['unlockCount'] > 1},
                         {n for n, r in actual.items() if r != self.expected[n]})
        mass = re.findall(r'[^\n]*\.addUnlock\("mass_army_logistics",[^\n]*\n', self.source)
        self.assertEqual(3, len(mass))
        for fixture in (dropped,
            self.source.replace('"policy","mass_conscription"', '"modifier","mass_conscription"'),
            self.source.replace('addUnlock("mass_army_logistics",', 'addUnlock("lost_node",'),
            self.source.replace(''.join(mass), ''.join(reversed(mass)))):
            with self.assertRaises(AssertionError): self.assert_complete(fixture)

    def test_malformed_research_references_reject_before_generation(self):
        mutations = [
            lambda w: w['technologies'][0].update(unlocks=None),
            lambda w: w['technologies'][0]['unlocks'][0].pop('kind'),
            lambda w: w['technologies'][0]['unlocks'][0].update(kind='food'),
            lambda w: w['technologies'][0]['unlocks'][0].update(contentId=''),
            lambda w: w['technologies'][0]['unlocks'][0].update(contentId='bad,id'),
            lambda w: w['technologies'][0]['unlocks'][0].update(magnitude=1),
            lambda w: w['technologies'][0]['unlocks'].append(w['technologies'][0]['unlocks'][0]),
            lambda w: w['technologies'][0].update(unlocks=[dict(kind='unit',contentId=f'unit_{i}') for i in range(65)]),
            lambda w: w['technologies'][0].update(prerequisiteIds=['missing_node']),
            lambda w: w['technologies'].append(w['technologies'][0]),
            lambda w: w['institutions'][0].update(id=w['technologies'][0]['id']),
        ]
        for index, mutate in enumerate(mutations):
            world = copy.deepcopy(self.world); mutate(world)
            source = Path(self.temp.name) / 'invalid-world.json'; source.write_text(json.dumps(world))
            target = Path(self.temp.name) / f'invalid-{index}'
            with self.subTest(index=index), self.assertRaises(PackagingError):
                generate(replace(self.config, scenario_file=source), target)
            self.assertFalse(target.exists())

    def test_exact_fractional_tokens_survive_generation_for_both_kinds(self):
        world = json.loads(self.config.scenario_file.read_text())
        for kind in ("technologies", "institutions"):
            world[kind][0]["timeCost"] = dict(preferredYear=1500, baseCost=1.23456789,
                aheadOfTimeCostMultiplier=1.125, additionalMultiplierPerYearAhead=0.0000005)
        # A token that cannot round-trip through a binary float.
        text = json.dumps(world).replace('1.23456789', '1.234567890123456789012345678')
        source = Path(self.temp.name) / 'fractional-world.json'
        source.write_text(text)
        generated = Path(self.temp.name) / 'fractional'
        generate(replace(self.config, scenario_file=source), generated)
        actual = generated_research((generated / 'ScenarioData.wurst').read_text())
        for kind in ("technologies", "institutions"):
            self.assertEqual(actual[world[kind][0]['id']]['timeCost'],
                ('1500', '1.234567890123456789012345678', '1.125', '0.0000005'))

    def test_generation_rejects_invalid_or_unrepresentable_costs(self):
        valid = dict(preferredYear=1500, baseCost=1, aheadOfTimeCostMultiplier=8,
                     additionalMultiplierPerYearAhead=0.08)
        for field, value in [('baseCost', 0), ('baseCost', True), ('baseCost', float('inf')),
                ('baseCost', Decimal('0.0000009')), ('baseCost', Decimal('1.2345678901234567890123456789')),
                ('aheadOfTimeCostMultiplier', Decimal('0.999')), ('additionalMultiplierPerYearAhead', -1),
                ('additionalMultiplierPerYearAhead', Decimal('1e-29')), ('preferredYear', 2**31),
                ('preferredYear', 1450.5), ('preferredYear', True)]:
            with self.subTest(field=field, value=value), self.assertRaises(PackagingError):
                research_time_cost({**valid, field: value}, 'fixture')
        for field in valid:
            with self.subTest(missing=field), self.assertRaises(PackagingError):
                research_time_cost({k: v for k, v in valid.items() if k != field}, 'fixture')
