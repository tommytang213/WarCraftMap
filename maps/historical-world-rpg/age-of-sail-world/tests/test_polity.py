import copy, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from polity import PolityError, PolityRuntime
WORLD_PATH=ROOT/"scenario"/"world"/"world.json"
class PolityRuntimeTests(unittest.TestCase):
    def setUp(self): self.source=json.loads(WORLD_PATH.read_text(encoding="utf-8")); self.runtime=PolityRuntime(self.source)
    def test_lookup_lifecycle_and_snapshot(self):
        self.assertEqual(("england","france"),self.runtime.ids()); self.assertTrue(self.runtime.set_active("france",False)); self.assertEqual(("england",),self.runtime.ids(active_only=True))
        snapshot=self.runtime.snapshot(); self.runtime.set_active("france",True); self.runtime.restore(snapshot); self.assertFalse(self.runtime.require("france").active)
    def test_invalid_restore_is_atomic(self):
        baseline=self.runtime.snapshot(); bad=copy.deepcopy(baseline); bad["polities"].pop()
        with self.assertRaisesRegex(PolityError,"missing polity"): self.runtime.restore(bad)
        self.assertEqual(baseline,self.runtime.snapshot())
if __name__=="__main__": unittest.main()
