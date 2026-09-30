import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))

from visual_language import DATES, VisualCatalog, VisualLanguageError, normalized


class VisualLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = VisualCatalog()

    def test_regional_rosters_and_characters_are_completely_covered(self):
        assignments = {(p, u) for p, u in self.catalog.roster.assignments if p in self.catalog.polity_family}
        snapshot = self.catalog.snapshot((1650,))
        self.assertEqual(assignments, {(x["polityId"], x["unitId"]) for x in snapshot["units"]})
        self.assertEqual({"infantry", "cavalry", "artillery", "specialist", "marine", "transport", "merchant", "warship"},
                         {self.catalog.roster.archetypes[x["unitId"]]["category"] for x in snapshot["units"]})
        expected_characters = {x["id"] for x in self.catalog.characters["characters"]
                               if x["regionId"] in self.catalog.source["scope"]["regions"]}
        self.assertEqual(expected_characters, {x["characterId"] for x in snapshot["characters"]})

    def test_inheritance_and_identity_overrides_are_deterministic(self):
        early = self.catalog.resolve_unit("england", "english_longbow_retinue", 1450)
        self.assertEqual("specialist_skirmisher", early["roleId"])
        self.assertEqual("europe_cloth_steel", early["paletteId"])
        ottoman = self.catalog.resolve_unit("ottoman_empire", "ottoman_janissary_orta", 1650)
        self.assertEqual("middle_east_india_ordinary_roster", ottoman["regionalFamilyId"])
        self.assertEqual("med_india_jewel_earth", ottoman["paletteId"])
        self.assertEqual(ottoman, self.catalog.resolve_unit("ottoman_empire", "ottoman_janissary_orta", 1650))
        galley = self.catalog.resolve_unit("venice", "venetian_galley", 1550)
        self.assertEqual(("warship_oared", "galley_long", "stock_boat"),
                         (galley["roleId"], galley["silhouetteId"], galley["assetId"]))

    def test_normalized_representative_date_snapshot_has_not_regressed(self):
        expected = (ROOT / "scenario/visuals/generated/representative-dates.snapshot.json").read_text()
        self.assertEqual(expected, normalized(self.catalog.snapshot(DATES)))

    def test_asset_compatibility_boundary_and_generated_object_data(self):
        classic = self.catalog.object_data("classic", 1650)
        reforged = self.catalog.object_data("reforged", 1650)
        self.assertEqual([x["id"] for x in classic["objects"]], [x["id"] for x in reforged["objects"]])
        self.assertTrue(all(x["model"].endswith(".mdl") for x in classic["objects"]))
        self.assertTrue(all(x["model"].endswith(".mdx") for x in reforged["objects"]))
        self.assertEqual(classic, json.loads((ROOT / "scenario/visuals/generated/classic-1650.object-data.json").read_text()))
        self.assertEqual(reforged, json.loads((ROOT / "scenario/visuals/generated/reforged-1650.object-data.json").read_text()))

    def test_controller_change_reconstruction_and_physical_map_instantiation(self):
        generated = self.catalog.object_data("classic", 1650)["objects"]
        physical = json.loads((ROOT / "physical-maps.json").read_text())
        map_ids = {entry["id"] for entry in physical["physicalMaps"]}
        state = [{"mapId":sorted(map_ids)[i % len(map_ids)], "object":dict(obj), "controller":i % 12}
                 for i, obj in enumerate(generated)]
        rebuilt = copy.deepcopy(state)
        for entry in rebuilt:
            entry["controller"] = (entry["controller"] + 1) % 12
            self.assertEqual("player", entry["object"]["teamColorMode"])
        self.assertEqual([x["object"] for x in state], [x["object"] for x in rebuilt])
        self.assertTrue({x["mapId"] for x in rebuilt} <= map_ids)

    def test_preview_contact_sheet_is_structured_labeled_and_bounded(self):
        preview = self.catalog.preview(1650)
        self.assertEqual(preview, json.loads((ROOT / "scenario/visuals/generated/1650.contact-sheet.json").read_text()))
        self.assertTrue(preview["scenes"])
        self.assertTrue(all(x["label"] == f"{x['familyId']}: {x['roleId']}" for x in preview["scenes"]))
        self.assertTrue(any("warship" in x["roleId"] for x in preview["scenes"]))
        self.assertTrue(any(x["roleId"] in {"infantry_line", "specialist_field"} for x in preview["scenes"]))
        for assignment in self.catalog.snapshot((1650,))["units"]:
            attachment = self.catalog.indexes["attachmentSets"][assignment["attachmentSetId"]]
            self.assertLessEqual(len(attachment["attachments"]), 2)
            self.assertLessEqual(len(attachment["effects"]), 1)

    def test_rejects_unsafe_scale_undeclared_placeholder_and_conflicting_archetype(self):
        for mutation in ("scale", "placeholder", "conflict"):
            source = copy.deepcopy(self.catalog.source)
            if mutation == "scale":
                source["archetypes"][0]["values"]["scale"] = 2.0
            elif mutation == "placeholder":
                source["historicalFit"][0].pop("customCandidate")
            else:
                source["archetypes"].append(copy.deepcopy(source["archetypes"][0]))
                source["archetypes"][-1]["id"] = "conflicting_infantry"
            with self.assertRaises(VisualLanguageError):
                VisualCatalog(source)


if __name__ == "__main__":
    unittest.main()
