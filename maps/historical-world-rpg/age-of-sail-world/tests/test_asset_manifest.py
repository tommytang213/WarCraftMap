import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / "_shared"

def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path); loaded=importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded

assets=module(SHARED/"tooling/validate_assets.py","validate_assets")
builder=module(ROOT/"tooling/build_asset_matrix.py","build_asset_matrix")

class AssetManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest=assets.load(SHARED/"assets/warcraft-3.0-stock.json")
        self.matrix=assets.load(ROOT/"scenario/visuals/historical-fit.json")

    def rejected_manifest(self, edit, text):
        data=copy.deepcopy(self.manifest); edit(data)
        with self.assertRaisesRegex(assets.AssetValidationError,text): assets.validate_manifest(data)

    def test_catalogue_and_all_classifications_validate(self):
        catalogue=assets.validate_manifest(self.manifest)
        rows=assets.validate_matrix(self.matrix,catalogue)
        self.assertEqual(17,len(catalogue))
        self.assertEqual(603 + 1,len(rows))
        self.assertEqual(assets.CLASSES,{x["classification"] for x in rows})

    def test_matrix_is_deterministically_generated_from_current_scenario(self):
        self.assertEqual(builder.build(),self.matrix)
        refs={(x["entityKind"],x["entityId"]) for x in self.matrix["mappings"]}
        for required in (("runtime_template","foot_company_runtime"),("ship","armed_sailing_hull"),("character","yi_sun_sin"),("settlement","london"),("equipment","naval_ordnance"),("treasure","treasure_ming_voyage_register"),("ability","broadside"),("effect","broadside_impact"),("terrain_feature","rhine"),("ui_concept","inventory_slot")):
            self.assertIn(required,refs)

    def test_reports_are_deterministic_and_grouped(self):
        report, unresolved=assets.coverage(self.matrix["mappings"])
        self.assertIn("europe",report); self.assertIn("global",report)
        self.assertTrue(all(set(x)=={"region","polity","entityKind","entityId","replacementPriority","classification"} for x in unresolved))
        reports=ROOT/"scenario/visuals/reports"
        self.assertEqual(json.loads((reports/"coverage.json").read_text()),report)
        self.assertEqual(json.loads((reports/"unresolved.json").read_text()),unresolved)
        resolved=json.loads((reports/"resolved-manifest.json").read_text())
        self.assertEqual(604,len(resolved))
        self.assertEqual({"entityKind","entityId","classification","assetId","locator"},set(resolved[0]))
        self.assertTrue(all(x["locator"] is not None or x["classification"]=="intentionally_invisible_data_only" for x in resolved))

    def test_rejects_every_catalogue_rejection_class(self):
        self.rejected_manifest(lambda d:d["assets"][0].update(kind="sprite"),"invalid asset kind")
        self.rejected_manifest(lambda d:d["assets"][0].update(locator={}),"missing path or ID")
        self.rejected_manifest(lambda d:d["assets"][0].update(renderers=["future"]),"unsupported renderer")
        self.rejected_manifest(lambda d:d["assets"].append(copy.deepcopy(d["assets"][0])),"duplicate asset IDs")
        self.rejected_manifest(lambda d:d["assets"][0]["relationships"].update(iconAssetId="absent"),"broken iconAssetId")
        self.rejected_manifest(lambda d:d["assets"][0].update(provenance={"origin":"external","source":"unknown"}),"undocumented external provenance")

    def test_rejects_every_variation_constraint(self):
        catalogue=assets.validate_manifest(self.manifest)
        cases=(("renderers",["future"],"renderer"),("scale",9,"scale"),("tint",True,"tint"),("attachments",["head"],"attachment"),("animations",["swim"],"animation"),("footprint",{"width":9,"height":9},"footprint"))
        base=next(x for x in self.matrix["mappings"] if x["candidateAssetId"]=="terrain_lordaeron_summer")
        for field,value,message in cases:
            row=copy.deepcopy(base); row["permittedVariation"][field]=value
            bad={"format":"historical_fit_matrix_v1","mappings":[row]}
            with self.subTest(field=field), self.assertRaisesRegex(assets.AssetValidationError,message): assets.validate_matrix(bad,catalogue)

if __name__ == "__main__": unittest.main()
