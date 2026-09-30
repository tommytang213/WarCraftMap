import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


CATEGORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = CATEGORY_ROOT / "_shared" / "tooling" / "validate_world.py"
WORLD_PATH = Path(__file__).resolve().parents[1] / "scenario" / "world" / "world.json"
CYCLIC_RESEARCH_PATH = Path(__file__).resolve().parent / "fixtures" / "cyclic_research.json"

spec = importlib.util.spec_from_file_location("validate_world", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def add_character_fixture(data):
    data["traits"] = [{"id": "steadfast", "name": "Steadfast", "description": "Keeps faith under pressure."}] + data.get("traits", [])
    data["skills"] = [{"id": "navigation_fixture", "name": "Navigation Fixture", "description": "Plans and follows routes."}] + data.get("skills", [])
    data["professions"] = [{"id": "navigator_fixture", "name": "Navigator Fixture", "description": "A professional navigator."}] + data.get("professions", [])
    data["personalQuests"] = [{
        "id": "prove_the_route", "title": "Prove the Route",
        "summary": "Resolve a personal obligation.", "characterId": "companion_alpha"
    }] + data.get("personalQuests", [])
    data["characters"] = [
        {
            "id": "companion_alpha", "displayName": "Companion Alpha",
            "biography": "Scenario-defined character display data.",
            "traitIds": ["steadfast"], "skills": [{"skillId": "navigation_fixture", "rating": 60}],
            "professionIds": ["navigator_fixture"], "personalQuestIds": ["prove_the_route"],
            "loyalty": {"score": 25, "permanentState": "none"}
        },
        {
            "id": "companion_beta", "displayName": "Companion Beta",
            "biography": "A second scenario-defined character.",
            "traitIds": [], "skills": [], "professionIds": [], "personalQuestIds": [],
            "loyalty": {"score": 0, "permanentState": "oathbound"}
        }
    ] + data.get("characters", [])
    data["relationshipThresholds"] = [{
        "id": "trusted_companions", "scope": "companion_relationship",
        "minimum": 50, "maximum": 100,
        "consequences": [{"kind": "buff", "contentId": "trusted_companion_synergy"}]
    }] + data.get("relationshipThresholds", [])
    data["companionRelationships"] = [{
        "id": "alpha_beta_relation", "characterAId": "companion_alpha",
        "characterBId": "companion_beta", "score": 10
    }] + data.get("companionRelationships", [])
    return data


class WorldContractTests(unittest.TestCase):
    def test_current_world_is_valid(self):
        validator.validate(WORLD_PATH)

    def test_duplicate_ids_are_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["settlements"].append(dict(data["settlements"][0]))
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_broken_cross_reference_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["provinces"][0]["settlementIds"] = ["nonexistent_city"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def assert_valid_data(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def assert_invalid_data(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_duplicate_military_ids_are_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["strategicUnits"].append(dict(data["strategicUnits"][0]))
        self.assert_invalid_data(data)

    def test_broken_army_membership_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["armies"][0]["formationUnitIds"] = ["missing_formation"]
        self.assert_invalid_data(data)

    def test_fleet_cannot_contain_a_formation(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["fleets"][0]["shipUnitIds"] = ["english_guard_formation"]
        self.assert_invalid_data(data)

    def test_broken_commander_reference_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["armies"][0]["commanderOfficerId"] = "missing_officer"
        self.assert_invalid_data(data)

    def test_runtime_metadata_must_match_instantiation_state(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["strategicUnits"][0]["runtimeInstantiation"]["activeObjectCount"] = 1
        self.assert_invalid_data(data)

    def test_native_food_is_not_part_of_strategic_contract(self):
        schema_path = CATEGORY_ROOT / "_shared" / "contracts" / "military.schema.json"
        schema_text = schema_path.read_text(encoding="utf-8").lower()
        self.assertNotIn('"food"', schema_text)

    def test_character_contract_fixture_is_valid(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)
        try:
            validator.validate(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_character_ranges_are_rejected(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["characters"][0]["loyalty"]["score"] = 101
        self.assert_invalid_data(data)
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["characters"][0]["skills"][0]["rating"] = -1
        self.assert_invalid_data(data)
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["companionRelationships"][0]["score"] = -101
        self.assert_invalid_data(data)

    def test_duplicate_character_ids_are_rejected(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["characters"].append(dict(data["characters"][0]))
        self.assert_invalid_data(data)

    def test_duplicate_companion_pairs_are_rejected_regardless_of_order(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["companionRelationships"].append({
            "id": "beta_alpha_relation", "characterAId": "companion_beta",
            "characterBId": "companion_alpha", "score": 20
        })
        self.assert_invalid_data(data)

    def test_broken_character_references_are_rejected(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["companionRelationships"][0]["characterBId"] = "missing_character"
        self.assert_invalid_data(data)
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["personalQuests"][0]["characterId"] = "missing_character"
        self.assert_invalid_data(data)

    def test_invalid_permanent_state_transitions_are_rejected(self):
        with self.assertRaises(validator.ValidationError):
            validator.validate_permanent_state_transition("oathbound", "none")
        with self.assertRaises(validator.ValidationError):
            validator.validate_permanent_state_transition("oathbound", "oathbound")
        with self.assertRaises(validator.ValidationError):
            validator.validate_permanent_state_transition("none", "none")

    def test_oathbound_may_be_entered_once(self):
        validator.validate_permanent_state_transition("none", "oathbound")

    def test_threshold_range_must_be_ordered(self):
        data = add_character_fixture(json.loads(WORLD_PATH.read_text(encoding="utf-8")))
        data["relationshipThresholds"][0]["minimum"] = 75
        data["relationshipThresholds"][0]["maximum"] = 50
        self.assert_invalid_data(data)


    def test_cross_tree_prerequisite_is_valid(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        node = next(x for x in data["technologies"] if x["id"] == "flintlock_drill")
        self.assertIn("military_fiscal_state", node["prerequisiteIds"])
        validator.validate(WORLD_PATH)

    def test_duplicate_research_ids_are_rejected_across_node_kinds(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        duplicate = dict(data["technologies"][0])
        data["institutions"].append(duplicate)
        self.assert_invalid_data(data)

    def test_missing_research_prerequisite_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["technologies"][1]["prerequisiteIds"] = ["missing_research"]
        self.assert_invalid_data(data)

    def test_deliberately_cyclic_fixture_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        fixture = json.loads(CYCLIC_RESEARCH_PATH.read_text(encoding="utf-8"))
        data.update(fixture)
        self.assert_invalid_data(data)

    def test_unreachable_research_node_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["researchBranches"][0]["entryNodeIds"] = ["standardized_charts"]
        self.assert_invalid_data(data)

    def test_ahead_of_time_research_has_finite_cost_not_a_lock(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        node = next(x for x in data["technologies"] if x["id"] == "standardized_charts")
        cost = node["timeCost"]
        self.assertGreater(cost["aheadOfTimeCostMultiplier"], 1)
        self.assertGreaterEqual(cost["additionalMultiplierPerYearAhead"], 0)
        self.assertNotIn("earliestYear", data["technologies"][1])

    def test_polity_state_and_uneven_province_adoption_are_valid(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        by_province = {x["provinceId"]:x for x in data["provinceAdoptionStates"]}
        london = {x["nodeId"]:x["level"] for x in by_province["greater_london"]["adoption"]}
        kent = {x["nodeId"]:x["level"] for x in by_province["kent"]["adoption"]}
        self.assertNotEqual(london["professional_bureaucracy"], kent["professional_bureaucracy"])
        validator.validate(WORLD_PATH)


    def test_scenario_defines_native_names_with_generic_tiers(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        french = next(style for style in data["titleStyles"] if style["id"] == "french_king")
        self.assertEqual("Roi", french["nativeName"])
        self.assertEqual("King", french["genericName"])
        self.assertEqual("king", french["rankTier"])

    def test_lower_rank_may_be_granted_by_sovereign(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["titleGrants"].append({
            "id": "duchy_of_kent", "titleStyleId": "english_duke",
            "holder": {"kind": "polity", "id": "england"},
            "allegiancePolityId": "england", "sovereign": False,
            "grantorTitleId": "crown_of_england"
        })
        self.assert_valid_data(data)

    def test_empire_may_grant_subordinate_king_rank(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["titleStyles"].extend([
            {"id": "imperial_emperor", "polityId": "england", "rankTier": "emperor", "nativeName": "Emperor", "genericName": "Emperor"},
            {"id": "subordinate_king", "polityId": "england", "rankTier": "king", "nativeName": "King", "genericName": "King"}
        ])
        data["titleGrants"].extend([
            {"id": "imperial_crown", "titleStyleId": "imperial_emperor", "holder": {"kind": "polity", "id": "england"}, "allegiancePolityId": "england", "sovereign": True},
            {"id": "subordinate_crown", "titleStyleId": "subordinate_king", "holder": {"kind": "polity", "id": "england"}, "allegiancePolityId": "england", "sovereign": False, "grantorTitleId": "imperial_crown"}
        ])
        self.assert_valid_data(data)

    def test_equal_or_higher_rank_grant_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["titleGrants"].append({
            "id": "second_english_crown", "titleStyleId": "english_king",
            "holder": {"kind": "polity", "id": "england"},
            "allegiancePolityId": "england", "sovereign": False,
            "grantorTitleId": "crown_of_england"
        })
        self.assert_invalid_data(data)

    def test_title_hierarchy_cycle_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["titleGrants"][0]["sovereign"] = False
        data["titleGrants"][0]["grantorTitleId"] = "crown_of_england"
        self.assert_invalid_data(data)

    def test_broken_territorial_reference_is_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["territorialHoldings"][0]["territory"]["id"] = "missing_province"
        self.assert_invalid_data(data)

    def test_broken_and_cyclic_overlord_references_are_rejected(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["territorialHoldings"][1]["overlordHoldingId"] = "missing_holding"
        self.assert_invalid_data(data)
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        data["territorialHoldings"][0]["overlordHoldingId"] = "holding_kent"
        data["territorialHoldings"][1]["overlordHoldingId"] = "holding_greater_london"
        data["territorialHoldings"][1]["overlordTaxRatePercent"] = 5
        data["territorialHoldings"][0]["overlordTaxRatePercent"] = 5
        self.assert_invalid_data(data)

    def test_independent_holding_has_no_overlord_tax_but_has_upkeep(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        independent = data["territorialHoldings"][0]
        self.assertNotIn("overlordHoldingId", independent)
        self.assertEqual(0, independent["overlordTaxRatePercent"])
        self.assertGreater(independent["upkeepRatePercent"], 0)
        independent["overlordTaxRatePercent"] = 1
        self.assert_invalid_data(data)

    def test_ownership_control_governance_sovereignty_and_autonomy_are_separate(self):
        holding = json.loads(WORLD_PATH.read_text(encoding="utf-8"))["territorialHoldings"][0]
        self.assertIn("legalOwner", holding)
        self.assertIn("controllerPolityId", holding)
        self.assertIn("governingPolityId", holding)
        self.assertIn("sovereignPolityId", holding)
        self.assertIn("autonomyPercent", holding)

    def test_allegiance_can_change_to_any_referenced_polity(self):
        data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        polities = {item["id"]: item for item in data["polities"]}
        validator.validate_allegiance_transition("england", "france", polities, validator.fail)
        with self.assertRaises(validator.ValidationError):
            validator.validate_allegiance_transition("england", "england", polities, validator.fail)


if __name__ == "__main__":
    unittest.main()
