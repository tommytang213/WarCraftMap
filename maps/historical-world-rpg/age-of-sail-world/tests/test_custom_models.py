import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); loaded=importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded
models=module(ROOT/"tooling/build_custom_models.py","build_custom_models")

class CustomModelTests(unittest.TestCase):
    def setUp(self):
        self.source=models.load(); self.imports,self.objects,self.snapshots=models.build(self.source)

    def test_all_high_priority_requirements_are_integrated_without_orphans(self):
        visual=json.loads((ROOT/"scenario/visuals/country-unit-language.json").read_text())
        required={x["entityId"] for x in visual["productionRequirements"] if x["priority"]=="high" and "model" in x["type"]}
        source={x["id"] for x in self.source["models"]}
        self.assertEqual(required,source)
        self.assertEqual(source,{x["entityId"] for x in self.objects})
        self.assertEqual(source,{Path(x["importPath"]).stem for x in self.imports})
        self.assertEqual(len(self.imports),len({x["importPath"].lower() for x in self.imports}))
        for row in self.imports: self.assertTrue((ROOT/"map/AgeOfSailWorld.w3x"/row["importPath"]).is_file())

    def test_generated_mdl_has_supported_complete_structure(self):
        for row in self.source["models"]:
            text=models.mdl(row); vertices,faces=models.geometry(row)
            with self.subTest(model=row["id"]):
                for token in ("FormatVersion 800", "Materials 1", "Geoset {", "PivotPoints 8", "CollisionShape", 'Camera "Portrait"', "ReplaceableId 1"):
                    self.assertIn(token,text)
                self.assertEqual([x[0] for x in models.SEQUENCES],re.findall(r'Anim "([^"]+)"',text))
                self.assertEqual(set(models.ATTACHMENTS),set(re.findall(r'Attachment "([^"]+)"',text)))
                self.assertEqual((40,60),(len(vertices),len(faces)))
                self.assertNotRegex(text,r'Image "[^"]+"')
                object_ids=[int(x) for x in re.findall(r'ObjectId (\d+)',text)]
                self.assertEqual(len(object_ids),len(set(object_ids)))
                self.assertLess(max(object_ids),8)

    def test_provenance_licensing_counts_and_deterministic_exports(self):
        generated=json.loads((ROOT/"scenario/visuals/generated/custom-model-imports.json").read_text())
        self.assertEqual(self.imports,generated["imports"])
        for item in self.imports:
            self.assertEqual("CC0-1.0",item["license"]); self.assertIsNone(item["derivativeOf"])
            self.assertEqual((40,60,0,5),(item["vertices"],item["triangles"],item["textureBytes"],item["animations"]))
        self.assertEqual([models.mdl(x) for x in self.source["models"]],[models.mdl(x) for x in self.source["models"]])

    def test_animation_snapshots_and_preview_cover_every_model(self):
        self.assertEqual({x["id"] for x in self.source["models"]},{x["label"] for x in self.snapshots})
        self.assertTrue(all(set(x["states"])==set(self.source["shared"]["animations"]) for x in self.snapshots))
        preview=(ROOT/"scenario/visuals/generated/custom-model-contact-sheet.svg").read_text()
        for row in self.source["models"]: self.assertIn(row["id"],preview)

    def test_representative_scene_and_archive_budgets(self):
        fixture=json.loads((ROOT/"scenario/visuals/generated/custom-model-scene-fixtures.json").read_text())["fixtures"]
        self.assertEqual({"local_battle","naval","settlement","city_capture","representation_reconstruction","cross_map"},{x["id"] for x in fixture})
        budget=self.source["budgets"]
        for row in fixture:
            self.assertLessEqual(row["activeModels"],budget["activeSceneMaxModels"])
            self.assertLessEqual(row["triangles"],budget["activeSceneMaxTriangles"])
            self.assertLessEqual(row["textureBytes"],budget["activeSceneMaxTextureBytes"])
        size=sum((ROOT/"map/AgeOfSailWorld.w3x"/x["importPath"]).stat().st_size for x in self.imports)
        self.assertLessEqual(size,budget["archiveMaxBytes"])

    def test_validator_rejects_duplicates_unsafe_ids_and_excessive_geometry(self):
        bad=copy.deepcopy(self.source); bad["models"].append(copy.deepcopy(bad["models"][0]))
        with self.assertRaisesRegex(models.ModelError,"unique"): models.validate_source(bad)
        bad=copy.deepcopy(self.source); bad["models"][0]["id"]="../unsafe"
        with self.assertRaisesRegex(models.ModelError,"unsafe"): models.validate_source(bad)
        bad=copy.deepcopy(self.source); bad["budgets"]["modelMaxVertices"]=1
        with self.assertRaisesRegex(models.ModelError,"budget"): models.validate_source(bad)

if __name__=="__main__": unittest.main()
