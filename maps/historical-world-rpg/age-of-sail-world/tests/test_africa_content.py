import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from africa_content import AfricaContentError, project, validate
from settlement import RecordingSettlementAdapter, SettlementRuntime


class AfricaContentTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "scenario/settlements/africa-1450.json"
        self.source = json.loads(self.path.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def candidate(self, value):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "candidate.json"
        path.write_text(json.dumps(value))
        return directory, path

    def test_complete_authority_and_deterministic_projection(self):
        source, politics, geography, positions = validate()
        self.assertEqual((30, 11, 12, 3), (len(source["settlements"]), sum("port" in x for x in source["settlements"]), len(source["tradeRoutes"]), len(source["transitions"])))
        projected = project(source, politics, geography, positions, self.world)
        self.assertEqual(projected, project(copy.deepcopy(source), politics, geography, positions, self.world))
        selected = [x for x in projected["settlements"] if x.get("regionalInstanceId") == "africa_mainland"]
        self.assertEqual({x["id"] for x in source["settlements"]}, {x["id"] for x in selected})
        cores = {x["id"] for x in projected["cityCores"]}; layouts = {x["id"] for x in projected["defenseLayouts"]}
        for settlement in selected:
            self.assertTrue(settlement["capturable"])
            self.assertTrue(settlement["civilianFacilitiesInvulnerable"])
            self.assertIn(settlement["cityCoreId"], cores)
            self.assertIn(settlement["defenseLayoutId"], layouts)

    def test_port_topology_and_inland_maritime_routes_are_rejected(self):
        inland = copy.deepcopy(self.source)
        next(x for x in inland["settlements"] if x["id"] == "cairo")["port"] = {"maritimeZoneId":"mediterranean_navigation","access":"coastal"}
        directory, path = self.candidate(inland)
        with directory, self.assertRaisesRegex(AfricaContentError, "invalid port access"): validate(path)
        route = copy.deepcopy(self.source)
        route["tradeRoutes"].append({"id":"invalid_inland_shipping","fromSettlementId":"cairo","toSettlementId":"gao","kind":"maritime","contract":"settlement_trade_endpoint"})
        directory, path = self.candidate(route)
        with directory, self.assertRaisesRegex(AfricaContentError, "inland maritime route"): validate(path)

    def test_placement_overlap_bounds_and_entry_clearance_are_rejected(self):
        outside = copy.deepcopy(self.source); next(x for x in outside["settlements"] if x["id"] == "fez")["position"] = [101, 88]
        overlap = copy.deepcopy(self.source); next(x for x in overlap["settlements"] if x["id"] == "fez")["position"] = next(x for x in overlap["settlements"] if x["id"] == "ceuta")["position"]
        blocked = copy.deepcopy(self.source); next(x for x in blocked["settlements"] if x["id"] == "fez")["position"] = [50, 95]
        for candidate, message in ((outside,"outside local bounds"),(overlap,"overlap"),(blocked,"obstructs entry anchor")):
            directory, path = self.candidate(candidate)
            with self.subTest(message=message), directory, self.assertRaisesRegex(AfricaContentError, message): validate(path)

    def test_trans_saharan_endpoints_and_boundary_reachability(self):
        required = set(self.source["requiredTransSaharanEndpoints"])
        edges = [(x["fromSettlementId"],x["toSettlementId"]) for x in self.source["tradeRoutes"] if x["kind"] == "trans_saharan"]
        seen, pending = set(), [next(iter(required))]
        while pending:
            current = pending.pop()
            if current in seen: continue
            seen.add(current); pending.extend(b if a == current else a for a,b in edges if a == current or b == current)
        self.assertTrue(required <= seen)
        self.assertEqual({"europe","middle_east_india","americas_caribbean"}, {x["neighborRegionId"] for x in self.source["transitions"]})

    def test_activation_retirement_capture_reconstruction_and_save_restore(self):
        runtime = SettlementRuntime(self.world, RecordingSettlementAdapter())
        regional = sorted(x["id"] for x in self.world["settlements"] if x.get("regionalInstanceId") == "africa_mainland")
        self.assertEqual(tuple(regional), runtime.activate_region("africa_mainland"))
        runtime.update("timbuktu", controllerPolityId="songhai")
        runtime.set_service_available("timbuktu", "market", False)
        saved = runtime.snapshot()
        self.assertEqual(tuple(regional), runtime.retire_region("africa_mainland"))
        replacement = SettlementRuntime(self.world, RecordingSettlementAdapter())
        replacement.restore(saved, reconstruct=True)
        self.assertEqual("songhai", replacement.require("timbuktu").controller_polity_id)
        self.assertFalse(replacement.require("timbuktu").services["market"])
        self.assertTrue(replacement.require("timbuktu").represented)


if __name__ == "__main__": unittest.main()
