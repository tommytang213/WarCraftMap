import hashlib
import importlib.util
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); loaded=importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded); return loaded
icons=module(ROOT/"tooling/build_custom_2d.py","build_custom_2d")
matrix_builder=module(ROOT/"tooling/build_asset_matrix.py","custom_2d_matrix")

class Custom2DAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)/"out"; self.manifest=icons.build(self.output)

    def test_every_high_priority_2d_gap_has_one_stable_import(self):
        high={(x["entityKind"],x["entityId"]) for x in matrix_builder.build()["mappings"]
              if x["classification"]=="custom_icon_texture_candidate" and x["replacementPriority"]<=2}
        uses={(use.split(":",1)[0],use.split(":",1)[1]) for row in self.manifest["assets"] for use in row["uses"]}
        self.assertEqual(high,uses)
        self.assertEqual(16,len(self.manifest["assets"]))
        self.assertEqual(16,len({x["importPath"].casefold() for x in self.manifest["assets"]}))
        self.assertEqual(16,len({x["derivativeSha256"] for x in self.manifest["assets"]}))

    def test_tga_metadata_hashes_and_objective_readability_are_valid(self):
        referenced=set()
        for row in self.manifest["assets"]:
            path=self.output/"imports"/Path(row["importPath"].replace("\\","/"))
            referenced.add(path.resolve())
            raw=path.read_bytes(); header=struct.unpack("<BBBHHBHHHHBB",raw[:18])
            self.assertEqual((2,64,64,32),(header[2],header[8],header[9],header[10]))
            self.assertEqual(16402,len(raw)); self.assertEqual(hashlib.sha256(raw).hexdigest(),row["derivativeSha256"])
            self.assertGreaterEqual(row["metrics32"]["luminanceRange"],70)
            self.assertLessEqual(row["metrics32"]["borderOpaquePixels"],124)
            self.assertGreater(row["metrics32"]["transparentPixels"],0)
            self.assertEqual({"none","none_command_icons"},{row["compression"],row["mipmapPolicy"]})
            self.assertEqual("CC0-1.0",row["license"])
        actual={p.resolve() for p in (self.output/"imports").rglob("*.tga")}
        self.assertEqual(referenced,actual,"missing or orphaned imports")

    def test_clean_conversions_are_byte_identical_and_contact_sheet_is_labelled(self):
        first={p.relative_to(self.output):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.rglob("*") if p.is_file()}
        shutil.rmtree(self.output); icons.build(self.output)
        second={p.relative_to(self.output):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(first,second)
        sheet=(self.output/"contact-sheet.svg").read_text()
        for row in self.manifest["assets"]: self.assertIn(row["id"],sheet)
        self.assertIn("32px",sheet)

    def test_rejects_duplicate_missing_and_malformed_sources(self):
        source=json.loads(icons.SOURCE.read_text())
        broken=json.loads(json.dumps(source)); broken["assets"][1]["id"]=broken["assets"][0]["id"]
        with self.assertRaisesRegex(icons.AssetError,"16 unique"): icons.validate_source(broken)
        broken=json.loads(json.dumps(source)); broken["assets"].pop()
        with self.assertRaisesRegex(icons.AssetError,"16 unique"): icons.validate_source(broken)
        broken=json.loads(json.dumps(source)); broken["assets"][0]["palette"]="unknown"
        with self.assertRaisesRegex(icons.AssetError,"invalid palette"): icons.validate_source(broken)

    def test_remaining_placeholders_are_explicitly_routed(self):
        work=self.manifest["remainingWork"]
        self.assertEqual(3,work["lowerPriority2D"]["priority"])
        self.assertTrue(work["customModelLane"] and work["soundLane"] and work["interfaceLane"])

if __name__=="__main__": unittest.main()
