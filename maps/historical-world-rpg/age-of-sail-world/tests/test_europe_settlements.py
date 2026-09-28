import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from europe_settlements import SettlementContentError, local_position, project, validate
from settlement import RecordingSettlementAdapter, SettlementRuntime


class EuropeSettlementTests(unittest.TestCase):
    def setUp(self):
        self.source_path = ROOT / "scenario/settlements/europe-1450.json"
        self.source = json.loads(self.source_path.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def test_complete_authority_and_projection(self):
        source, politics, geography, world, positions = validate()
        self.assertEqual((72, 30, 3), (len(source["settlements"]), sum("port" in s for s in source["settlements"]), len(source["transitions"])))
        projected = project(source, politics, geography, world, positions)
        self.assertEqual(projected, project(copy.deepcopy(source), politics, geography, world, positions))
        self.assertEqual({s["id"] for s in source["settlements"]}, {s["id"] for s in projected["settlements"]})

    def test_inland_port_invalid_position_and_overlap_are_rejected(self):
        cases = []
        inland = copy.deepcopy(self.source); next(s for s in inland["settlements"] if s["id"] == "paris")["port"] = {"maritimeZoneId":"english_channel","access":"coastal"}; cases.append((inland, "invalid port access"))
        outside = copy.deepcopy(self.source); next(s for s in outside["settlements"] if s["id"] == "london")["sourcePosition"] = [1000,1000]; cases.append((outside, "outside local bounds"))
        overlap = copy.deepcopy(self.source); a=next(s for s in overlap["settlements"] if s["id"]=="london"); b=next(s for s in overlap["settlements"] if s["id"]=="dover"); b["sourcePosition"]=a["sourcePosition"]; cases.append((overlap,"overlap"))
        with tempfile.TemporaryDirectory() as tmp:
            for index,(candidate,pattern) in enumerate(cases):
                path=Path(tmp)/f"case_{index}.json"; path.write_text(json.dumps(candidate))
                with self.subTest(pattern=pattern), self.assertRaisesRegex(SettlementContentError, pattern): validate(path)

    def test_regional_activation_retirement_capture_and_reconstruction_preserve_state(self):
        adapter=RecordingSettlementAdapter(); runtime=SettlementRuntime(self.world,adapter)
        regional=sorted(s["id"] for s in self.world["settlements"] if s["regionalInstanceId"]=="europe_italy_central_med")
        self.assertEqual(tuple(regional), runtime.activate_region("europe_italy_central_med"))
        runtime.update("venice",controllerPolityId="milan"); runtime.set_service_available("venice","market",False)
        saved=runtime.snapshot()
        self.assertEqual(tuple(regional), runtime.retire_region("europe_italy_central_med"))
        self.assertFalse(any(runtime.require(ident).represented for ident in regional))
        replacement=SettlementRuntime(self.world,RecordingSettlementAdapter()); replacement.restore(saved,reconstruct=True)
        self.assertEqual("milan",replacement.require("venice").controller_polity_id)
        self.assertFalse(replacement.require("venice").services["market"])
        self.assertTrue(replacement.require("venice").represented)

    def test_land_and_sea_reachability(self):
        zones={z["id"]:z for z in self.world["navigationZones"]}
        def reached(start,kind):
            seen=set(); pending=[start]
            while pending:
                current=pending.pop()
                if current in seen: continue
                seen.add(current); pending.extend(zones[current]["connections"].get(kind,[]))
            return seen
        land={s["navigationZoneId"] for s in self.world["settlements"]}
        sea={s["portAccess"]["maritimeZoneId"] for s in self.world["settlements"] if "portAccess" in s}
        self.assertTrue(land <= reached(next(iter(land)),"land"))
        self.assertTrue(sea <= reached(next(iter(sea)),"naval"))


if __name__ == "__main__": unittest.main()
