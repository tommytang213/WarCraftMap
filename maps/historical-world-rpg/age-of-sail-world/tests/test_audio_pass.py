import copy
import importlib.util
import json
import tempfile
import sys
import wave
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SHARED=ROOT.parent/"_shared"
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); result=importlib.util.module_from_spec(spec); sys.modules[name]=result; spec.loader.exec_module(result); return result
pipeline=module(ROOT/"tooling/audio_pipeline.py","audio_pipeline")
playback=module(SHARED/"engine/audio_playback.py","audio_playback")

class AudioPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/"scenario/audio/manifest.json").read_text())
        cls.profiles=json.loads((ROOT/"scenario/audio/profiles.json").read_text())

    def test_manifest_profiles_reports_and_stock_first_budget(self):
        result=pipeline.validate(self.manifest,self.profiles)
        self.assertEqual(0,result["importedBytes"]); self.assertEqual(0,result["decodedBytes"])
        self.assertTrue(all(x["source"]=="stock" for x in self.manifest["assets"]))
        coverage,waveform=pipeline.reports(self.manifest,self.profiles)
        self.assertEqual(coverage,json.loads((ROOT/"scenario/audio/reports/coverage.json").read_text()))
        self.assertEqual(waveform,json.loads((ROOT/"scenario/audio/reports/waveform-loudness.json").read_text()))
        self.assertEqual({"europe","africa","middle_east_india","southeast_asia","east_asia","americas_caribbean","pacific"},{x["value"] for x in coverage["contexts"]["region"]})
        for context in ("settlement","travel","combat","modal","event"): self.assertTrue(coverage["contexts"][context])

    def test_deterministic_context_precedence_and_no_discovery_leak(self):
        director=playback.AudioDirector(self.manifest,self.profiles)
        base=playback.AudioContext("pacific_north",region_id="pacific")
        self.assertEqual(director.plan(base,4),director.plan(base,4))
        self.assertEqual("region_pacific",director.plan(base)[0]["profileId"])
        combat=playback.AudioContext("pacific_north",region_id="pacific",combat="naval")
        self.assertTrue(all(x["profileId"]=="combat_naval" for x in director.plan(combat)))
        hidden=playback.AudioContext("africa",event="discovery")
        self.assertNotIn("event_discovery",{x["profileId"] for x in director.plan(hidden)})
        revealed=playback.AudioContext("africa",event="discovery",discovered_ids=("current_target",))
        self.assertEqual({"event_discovery"},{x["profileId"] for x in director.plan(revealed)})

    def test_crossfade_loop_ownership_reconstruction_and_switching(self):
        director=playback.AudioDirector(self.manifest,self.profiles)
        land=playback.AudioContext("europe_west",region_id="europe",travel="land")
        first=director.transition(land,0,1); self.assertTrue(first); self.assertEqual(len(director.active),len(set(director.active)))
        kinds={x["id"]:x["kind"] for x in self.manifest["categories"]}
        self.assertTrue(all(kinds[category] in {"music","ambience","loop"} for category in director.active))
        sea=playback.AudioContext("americas_caribbean",region_id="americas_caribbean",travel="sea")
        changed=director.transition(sea,5000,2)
        self.assertTrue(any(x["op"]=="fade_out" and x["durationMs"]>0 for x in changed))
        self.assertTrue(any(x["op"]=="fade_in" and x["durationMs"]>0 for x in changed))
        expected=copy.deepcopy(director.active); director.reconstruct(sea,9000,2); self.assertEqual(expected,director.active)
        self.assertNotIn("stock_event_hint",director.last_played_ms)
        self.assertNotIn("campaign",director.presentation_snapshot())

    def test_cooldown_concurrency_missing_fallback_and_bounded_channels(self):
        director=playback.AudioDirector(self.manifest,self.profiles)
        self.assertEqual("fallback",director.one_shot("missing",0)["op"])
        self.assertEqual("play",director.one_shot("stock_event_hint",0)["op"])
        self.assertEqual("suppressed",director.one_shot("stock_event_hint",100)["op"])
        self.assertEqual("play",director.one_shot("stock_discovery",100)["op"])
        self.assertEqual("suppressed",director.one_shot("stock_treasure",100)["op"])
        self.assertLessEqual(len(director.active)+len(director.transient),self.manifest["budgets"]["maximumActiveChannels"])

    def test_rejects_malformed_loud_clipped_bad_loop_oversize_orphan_and_duplicate(self):
        cases=[]
        def bad(edit): data=copy.deepcopy(self.manifest); edit(data); return data
        cases.append(bad(lambda d:d["assets"][0]["technical"].update(format="ogg")))
        cases.append(bad(lambda d:d["assets"][0]["technical"].update(integratedLufs=-2)))
        cases.append(bad(lambda d:d["assets"][0]["technical"].update(peakDbfs=1)))
        cases.append(bad(lambda d:d["assets"][4]["technical"].update(loopEndMs=999999)))
        cases.append(bad(lambda d:d["assets"].append(copy.deepcopy(d["assets"][0]))))
        cases.append(bad(lambda d:d["assets"].append({**copy.deepcopy(d["assets"][0]),"id":"unused_asset","locator":"unused"})))
        for data in cases:
            with self.subTest(case=len(data["assets"])),self.assertRaises(pipeline.AudioValidationError): pipeline.validate(data,self.profiles)

    def test_import_validation_rejects_silent_and_oversized(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/"audio").mkdir(); source=root/"audio/test.wav"
            with wave.open(str(source),"wb") as sound:
                sound.setnchannels(1); sound.setsampwidth(2); sound.setframerate(22050); sound.writeframes(b"\0\0"*2205)
            data=copy.deepcopy(self.manifest); asset=data["assets"][0]; asset.update(id="import_test",source="import",locator="audio/test.wav")
            asset["technical"].update(format="wav",durationMs=100,sampleRateHz=22050,channels=1,encodedBytes=source.stat().st_size,decodedBytes=4410,sha256=__import__("hashlib").sha256(source.read_bytes()).hexdigest())
            profiles=copy.deepcopy(self.profiles)
            for row in [profiles["fallbackProfile"],*profiles["profiles"]]:
                for values in row["layers"].values():
                    for i,value in enumerate(values):
                        if value=="stock_music_human": values[i]="import_test"
            data["fallbacks"]["music"]="import_test"
            with self.assertRaisesRegex(pipeline.AudioValidationError,"silent"): pipeline.validate(data,profiles,root)
            with wave.open(str(source),"wb") as sound:
                sound.setnchannels(1); sound.setsampwidth(2); sound.setframerate(22050); sound.writeframes(b"\1\0"*2205)
            asset["technical"].update(encodedBytes=source.stat().st_size,sha256=__import__("hashlib").sha256(source.read_bytes()).hexdigest())
            data["budgets"]["maximumImportedBytes"]=1
            with self.assertRaisesRegex(pipeline.AudioValidationError,"budget"): pipeline.validate(data,profiles,root)

if __name__=="__main__": unittest.main()
