"""Compare compiled research definitions with every authoritative graph node."""
import json
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
        cls.expected = {
            row["id"]: {"kind": kind, "prerequisites": row["prerequisiteIds"],
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
