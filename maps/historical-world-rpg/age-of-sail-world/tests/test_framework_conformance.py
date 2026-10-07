"""One content/packaging contract for every registered framework consumer.

Compiler execution is separately mandatory in CI; the synthetic packager below
tests orchestration and binary inspections, not Wurst gameplay execution.
"""
import hashlib
import copy
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest

CATEGORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CATEGORY / "_shared/tooling"))
from audit_framework_boundary import audit
from framework_conformance import mutate_content
from package_wurst_map import _assemble, generate, load_config, run_execution_tests, verify_generated
from package_wurst_campaign import (_localize_runtime, build_campaign, inspect_campaign,
                                    load_campaign_config, validate_campaign)
from materialize_physical_map import materialize
from validate_world import validate
from player_items import PlayerItemError, validate_catalog
from scenario_inputs import catalogue_paths
from test_campaign_packaging import FAKE_GRILL
from wurst_execution_fixture import allow_synthetic_compiler
from integration_evidence import verify_execution_coverage
from requirement_traceability import execution_results


def copy_category(destination):
    for name in ("_shared", "age-of-sail-world", "conformance-campaign"):
        shutil.copytree(CATEGORY / name, destination / name, symlinks=True,
                        ignore=shutil.ignore_patterns("_build", ".wurst", "__pycache__", "reports"))
    shutil.copy2(CATEGORY / "framework-scenarios.json", destination)


class FrameworkConformanceTests(unittest.TestCase):
    def test_execution_evidence_accepts_shared_contract_and_instrumented_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            category = Path(tmp)
            copy_category(category)
            for name in ("age-of-sail-world", "conformance-campaign"):
                with self.subTest(scenario=name):
                    project = category / name
                    fake = project / "fake-grill"
                    fake.write_text(FAKE_GRILL)
                    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
                    allow_synthetic_compiler(self, fake)
                    report = run_execution_tests(load_config(project / "package.json"), str(fake))
                    log = (project / "_build/wurst-tests/execution.log").read_bytes()
                    revision = report["sourceRevision"]
                    verify_execution_coverage(report, log, project, revision)
                    results, errors = execution_results(project, report, log, revision)
                    self.assertEqual([], errors)
                    self.assertEqual({row["id"] for row in report["tests"]}, set(results))
                    contract = category / "_shared/wurst-tests/FrameworkConformanceTests.wurst"
                    original = contract.read_bytes()
                    contract.write_bytes(original + b"\n// changed after execution\n")
                    with self.assertRaisesRegex(ValueError, "source identity"):
                        verify_execution_coverage(report, log, project, revision)
                    self.assertTrue(execution_results(project, report, log, revision)[1])
                    contract.write_bytes(original)

    def test_inventory_boundary_uses_each_scenarios_commodity_catalogue(self):
        for name in ("age-of-sail-world", "conformance-campaign"):
            with self.subTest(scenario=name):
                project = CATEGORY / name
                data = json.loads(catalogue_paths(project)["inventory"].read_text())
                goods = json.loads((project / "scenario/economy/global-goods.json").read_text())
                ids = {row["id"] for row in goods["goods"]}
                validate_catalog(data, bulk_good_ids=ids)
                broken = copy.deepcopy(data)
                broken["items"][0]["id"] = goods["goods"][0]["id"]
                with self.assertRaisesRegex(PlayerItemError, "bulk good"):
                    validate_catalog(broken, bulk_good_ids=ids)

    def test_shared_content_and_physical_adapters_for_every_campaign(self):
        registry = json.loads((CATEGORY / "framework-scenarios.json").read_text())
        for row in registry["scenarios"]:
            with self.subTest(scenario=row["directory"]), tempfile.TemporaryDirectory() as tmp:
                project = CATEGORY / row["directory"]
                config = load_config(project / "package.json")
                validate(config.scenario_file)
                campaign = load_campaign_config(project / "physical-maps.json")
                world = validate_campaign(campaign)
                vector = json.loads((project / "conformance.json").read_text())
                self.assertIn(vector["hero"], {x["id"] for x in world["characters"]})
                self.assertIn(vector["quest"], {x["id"] for x in world["quests"]})
                inventory = json.loads(catalogue_paths(project)["inventory"].read_text())
                self.assertIn(vector["item"], {x["id"] for x in inventory["items"]})
                self.assertEqual((CATEGORY / "age-of-sail-world/wurst_run.args").read_bytes(),
                                 (project / "wurst_run.args").read_bytes())
                terrain_hashes = set()
                for physical in campaign.maps:
                    if physical.id not in {vector["sourceMap"], vector["destinationMap"], campaign.bootstrap_map_id}:
                        continue
                    root = Path(tmp) / physical.id
                    generated = root / "generated"
                    generate(config, generated)
                    _localize_runtime(campaign, world, physical, generated)
                    verify_generated(config, generated)
                    compile_root = _assemble(config, root, generated, physical.terrain_ids, include_tests=False)
                    settings = (compile_root / "wurst/ScenarioSettings.wurst").read_text()
                    self.assertIn(f'SCENARIO_BOOTSTRAP_MAP_ID = "{campaign.bootstrap_map_id}"', settings)
                    map_dir = compile_root / "map" / config.source_map.name
                    runtime = json.loads((generated / "scenario-runtime.json").read_text())
                    result = materialize(project, map_dir, generated, physical, runtime)
                    if not physical.bootstrap:
                        terrain_hashes.add(hashlib.sha256((map_dir / "war3map.w3e").read_bytes()).hexdigest())
                        self.assertTrue(result["terrain"]["width"])
                    # Canonical Warcraft mechanism bytes, independent of content.
                    for source in (CATEGORY / "_shared/wurst").glob("*.wurst"):
                        self.assertEqual(source.read_bytes(), (compile_root / "wurst" / source.name).read_bytes())
                self.assertEqual(2, len(terrain_hashes))

    def test_fixture_packages_through_campaign_orchestrator_and_mutates_only_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            category = Path(tmp)
            copy_category(category)
            project = category / "conformance-campaign"
            mutant = category / "mutated-campaign"
            before = {str(p.relative_to(category / "_shared")): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (category / "_shared").rglob("*") if p.is_file()}
            mutate_content(project, mutant)
            outputs = []
            for source in (project, mutant):
                validate(source / "scenario/world/world.json")
                fake = source / "fake-grill"
                # Include generated settings, as the real compiler does.
                fake.write_text(FAKE_GRILL.replace("generated + bootstrap", "generated + bootstrap + (root / 'wurst/ScenarioSettings.wurst').read_text()"))
                fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
                allow_synthetic_compiler(self, fake)
                output = build_campaign(source / "physical-maps.json", grill=str(fake))
                inspect_campaign(load_campaign_config(source / "physical-maps.json"), output)
                self.assertTrue(output.is_file())
                generated = source / "_build/wurst-tests/generated/ScenarioData.wurst"
                outputs.append(generated.read_text())
                vector = json.loads((source / "conformance.json").read_text())
                goods = json.loads((source / "scenario/economy/global-goods.json").read_text())
                expected_price = next(row["basePriceMinor"] for row in goods["goods"] if row["id"] == vector["good"])
                contract = (source / "_build/wurst-tests/compile/wurst/ConformanceData.wurst").read_text()
                self.assertIn(f'CONTRACT_ITEM = "{vector["item"]}"', contract)
                self.assertIn(f"CONTRACT_GOOD_BASE_PRICE = {expected_price}\n", contract)
                self.assertIn("test", (source / "_build/wurst-tests/commands.txt").read_text().splitlines())
                for physical in load_campaign_config(source / "physical-maps.json").maps:
                    self.assertIn("typecheck", (source / "_build/maps" / physical.id / "commands.txt").read_text().splitlines())
            self.assertNotEqual(outputs[0], outputs[1])
            self.assertIn('"reed_runner"', outputs[0])
            self.assertIn('"marsh_runner"', outputs[1])
            self.assertNotIn('"reed_runner"', outputs[1])
            original_goods = json.loads((project / "scenario/economy/global-goods.json").read_text())
            mutant_goods = json.loads((mutant / "scenario/economy/global-goods.json").read_text())
            self.assertEqual(original_goods["goods"][0]["basePriceMinor"] * 3, mutant_goods["goods"][0]["basePriceMinor"])
            after = {str(p.relative_to(category / "_shared")): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (category / "_shared").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
            self.assertEqual(before, after)

    def test_boundary_rejects_literals_branches_and_renamed_forks(self):
        with tempfile.TemporaryDirectory() as tmp:
            category = Path(tmp)
            copy_category(category)
            self.assertEqual([], audit(category))
            injected = category / "_shared/engine/injected.py"
            for code in ('POLITY = "england"', 'CITY = "Lisbon"', 'GOOD = "grain"',
                         'POLITY = "\\x65ngland"', 'POLITY = ("eng" "land")',
                         'HERO = "leonardo_da_vinci"', 'QUEST = "quest_leonardo_codex"',
                         'FORMAT = "age_of_sail_visual_language_v1"',
                         'if scenario_name == "Age of Sail":\n    pass',
                         'if scenario_id == "reed_union":\n    pass',
                         'if event == "reed_market_day":\n    pass',
                         'if physical_map == "reed_selector":\n    pass',
                         'if campaign == "conformance-campaign":\n    pass',
                         'if campaign == "Reed and Stone":\n    pass',
                         'if release == "ReedConformance":\n    pass',
                         'if polity.startswith("reed_"):\n    pass',
                         'if hero == "marsh_runner":\n    pass'):
                with self.subTest(code=code):
                    injected.write_text(code)
                    self.assertTrue(any("scenario literal" in error for error in audit(category)))
            injected.unlink()
            nested = category / "_shared/engine/nested/branch.py"
            nested.parent.mkdir()
            nested.write_text('if polity == "england":\n    pass')
            self.assertTrue(any("scenario literal" in error for error in audit(category)))
            nested.unlink()
            branch = category / "_shared/wurst/PrivateBranch.wurst"
            branch.write_text('package PrivateBranch\npublic function accept(string polity) returns boolean\n\treturn polity == "reed_union"\n')
            self.assertTrue(any("scenario literal" in error for error in audit(category)))
            branch.write_text('package PrivateBranch\npublic function accept(string polity) returns boolean\n\treturn polity == "\\u0065ngland"\n')
            self.assertTrue(any("scenario literal" in error for error in audit(category)))
            branch.unlink()
            # A renamed, slightly changed copy is still a private mechanism.
            source = category / "_shared/engine/trade.py"
            fork = category / "age-of-sail-world/tooling/alternate_exchange.py"
            for prefix in ("", "import collections\n", "import collections\nPRIVATE_VERSION = 2\n"):
                with self.subTest(fork_prefix=prefix):
                    fork.write_text(prefix + source.read_text().replace("TradeError", "PrivateTradeError"))
                    self.assertTrue(any("copied/forked" in error for error in audit(category)))
            fork.unlink()
            fixture_code = category / "conformance-campaign/wurst/PrivateRules.wurst"
            fixture_code.write_text("package PrivateRules\npublic function specialCase() returns int\n\treturn 1\n")
            self.assertTrue(any("content-only" in error for error in audit(category)))
            fixture_code.unlink()
            disguised = category / "conformance-campaign/wurst/tests/PrivateRules.wurst"
            disguised.parent.mkdir()
            disguised.write_text("package PrivateRules\npublic function specialCase() returns int\n\treturn 1\n")
            self.assertTrue(any("content-only" in error for error in audit(category)))

    def test_assembly_refuses_a_scenario_shadow_of_a_shared_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            category = Path(tmp)
            copy_category(category)
            project = category / "conformance-campaign"
            (project / "wurst/PlayableTrade.wurst").write_text("package PlayableTrade\n")
            config = load_config(project / "package.json")
            generate(config, project / "_build/generated")
            with self.assertRaisesRegex(RuntimeError, "forks shared"):
                _assemble(config, project / "_build", project / "_build/generated")


if __name__ == "__main__":
    unittest.main()
