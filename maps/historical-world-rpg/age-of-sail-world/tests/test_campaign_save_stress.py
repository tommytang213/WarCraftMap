import copy, json, sys, unittest
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT.parent/"_shared"/"engine"))
import campaign_save as saves
import campaign_save_stress as stress
import cross_map_persistence as transfers
import large_world_stress as worlds


class CampaignSaveStressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.world_profiles=worlds.load_profiles(PROJECT/"scenario/benchmarks/large-world.json")
        cls.profiles=stress.load_profiles(PROJECT/"scenario/benchmarks/campaign-save-stress.json",cls.world_profiles)

    def test_representative_long_campaign_meets_finalized_budgets(self):
        config=self.profiles["representative"]
        first=stress.run("representative",config,self.world_profiles[config["worldProfile"]])
        second=stress.run("representative",config,self.world_profiles[config["worldProfile"]])
        self.assertTrue(first["passed"],first["failures"])
        self.assertEqual(first["normalizedHash"],second["normalizedHash"])
        self.assertEqual(1,len(set(first["pathHashes"].values())))
        self.assertGreater(first["distinctCycleHashes"],1)
        self.assertGreaterEqual(first["cycles"],30) # wraps all fifteen autosave slots
        self.assertGreaterEqual(first["mapRevisits"],6)
        self.assertEqual(15,len(first["autosaveSlots"]))
        self.assertEqual(stress.AUTHORITATIVE_DOMAINS,frozenset(first["authoritativeDomains"]))

    def test_rejections_and_interrupted_writes_preserve_active_and_stored_state(self):
        profile=self.world_profiles["small_correctness"]
        h=stress.Harness(worlds.generate_fixture(profile)); slot=saves.SaveSlot("manual",1)
        h.manager.save(slot,"valid"); original=h.storage.read(slot.stable_id)
        baseline=copy.deepcopy((h.world,h.players,h.runtime))
        rejected=[original[:-17], bytes(original).replace(b'"checksum":"',b'"checksum":"0',1)]
        for bad in rejected:
            h.storage._slots[slot.stable_id]=bad
            with self.assertRaises(saves.SaveError): h.manager.load(slot)
            self.assertEqual(baseline,(h.world,h.players,h.runtime))
        h.storage._slots[slot.stable_id]=original
        h.world["time"]=1; h.storage.fail_next_write=True
        with self.assertRaises(saves.StorageError): h.manager.save(slot,"interrupted")
        self.assertEqual(original,h.storage.read(slot.stable_id))

    def test_compatible_integrity_valid_metadata_rejections_are_non_mutating(self):
        profile=self.world_profiles["small_correctness"]
        h=stress.Harness(stress.complete_fixture(profile)); slot=saves.SaveSlot("manual",1)
        h.manager.save(slot,"valid"); original=h.storage.read(slot.stable_id)
        baseline=copy.deepcopy((h.world,h.players,h.runtime))
        for field,value in (("buildVersion","stale.0"),("scenario",{"id":"other_scenario","version":"1"})):
            document=json.loads(original); document[field]=value
            document["integrity"]["checksum"]=saves._checksum(document)
            candidate=stress.canonical(document); h.storage._slots[slot.stable_id]=candidate
            with self.assertRaises(saves.IncompatibleSaveError): h.manager.load(slot)
            self.assertEqual(candidate,h.storage.read(slot.stable_id))
            self.assertEqual(baseline,(h.world,h.players,h.runtime))
        document=json.loads(original); document["schemaVersion"]=saves.CURRENT_SCHEMA_VERSION+1
        document["integrity"]["checksum"]=saves._checksum(document)
        candidate=stress.canonical(document); h.storage._slots[slot.stable_id]=candidate
        with self.assertRaises(saves.IncompatibleSaveError): h.manager.load(slot)
        self.assertEqual(candidate,h.storage.read(slot.stable_id))
        self.assertEqual(baseline,(h.world,h.players,h.runtime))

    def test_unsafe_deferral_captures_only_finalized_authority(self):
        h=stress.Harness(worlds.generate_fixture(self.world_profiles["small_correctness"])); slot=saves.SaveSlot("autosave",1)
        h.safe=False; h.world["time"]=99
        self.assertEqual("deferred",h.manager.save(slot,"boundary").status)
        self.assertIsNone(h.storage.read(slot.stable_id))
        h.world["time"]=100; h.safe=True; h.manager.retry_deferred()
        self.assertEqual(100,saves.load_save(h.storage.read(slot.stable_id))["state"]["world"]["time"])

    def test_scripted_boundaries_cover_battles_captures_quests_and_transitions(self):
        fixture=stress.complete_fixture(self.world_profiles["small_correctness"])
        before=copy.deepcopy(fixture); stress.apply_scripted_transition(fixture,3)
        self.assertNotEqual(before["entities"]["wars"],fixture["entities"]["wars"])
        self.assertNotEqual(before["entities"]["armies"],fixture["entities"]["armies"])
        self.assertNotEqual(before["entities"]["provinces"],fixture["entities"]["provinces"])
        self.assertNotEqual(before["entities"]["quests"],fixture["entities"]["quests"])
        self.assertNotEqual(before["activeRegionId"],fixture["activeRegionId"])
        ids=[item["id"] for values in fixture["entities"].values() for item in values]
        self.assertEqual(len(ids),len(set(ids)))

    def test_transient_and_reconstructible_runtime_state_is_excluded(self):
        h=stress.Harness(stress.complete_fixture(self.world_profiles["small_correctness"]))
        h.runtime={"unitHandle":1234,"camera":{"x":10}}
        slot=saves.SaveSlot("manual",1); h.manager.save(slot,"runtime-exclusion")
        document=saves.load_save(h.storage.read(slot.stable_id))
        self.assertNotIn("runtime",document["state"])
        h.world["unitHandle"]=1234
        with self.assertRaisesRegex(saves.SaveError,"transient Warcraft handles"):
            h.manager.save(saves.SaveSlot("manual",2),"reject-handle")

    def test_migration_failure_preserves_source_and_active_state(self):
        h=stress.Harness(worlds.generate_fixture(self.world_profiles["small_correctness"])); slot=saves.SaveSlot("manual",1)
        h.manager.save(slot,"valid"); old=stress._old_payload(h.storage.read(slot.stable_id),1); h.storage._slots[slot.stable_id]=old
        baseline=copy.deepcopy((h.world,h.players,h.runtime)); registry=saves.MigrationRegistry(); registry._migrations[1]=lambda d: d
        with self.assertRaises(saves.IncompatibleSaveError): h.manager.__class__(build_version="phase7.1",scenario_id="persistence_stress",scenario_version="1",
            storage=h.storage,capture_state=lambda:(h.world,h.players),validate_state=lambda w,p:worlds.validate_fixture(w),
            reconstruct_runtime=h._reconstruct,activate_state=h._activate,is_save_safe=lambda:True,registry=registry).load(slot)
        self.assertEqual(old,h.storage.read(slot.stable_id)); self.assertEqual(baseline,(h.world,h.players,h.runtime))

    def test_cross_map_adapter_commit_and_envelope_failures_are_atomic(self):
        profile=self.world_profiles["small_correctness"]
        h=stress.Harness(stress.complete_fixture(profile)); storage=transfers.MemoryTransferStorage(); active={"id":"map_a"}
        def activate(map_id,state,_runtime): active.update(id=map_id); setattr(h,"world",copy.deepcopy(state))
        def manager(adapter):
            return transfers.CrossMapTransferManager(scenario_id="persistence_stress",scenario_version="1",build_version="phase7.1",
                campaign_schema=saves.CURRENT_SCHEMA_VERSION,manifest=transfers.PhysicalMapManifest(stress._manifest()),storage=storage,
                capture_state=lambda:h.world,load_destination_content=stress._content,activate=activate,adapters=[adapter])
        good=manager(transfers.ReconstructionAdapter("authority",lambda state,content,assignment:len(state["entities"])))
        good.transfer("map_a","map_b",{},"valid"); committed=storage.read_committed(); baseline=copy.deepcopy((h.world,active))
        storage.fail_next_commit=True
        with self.assertRaises(transfers.TransferStorageError): good.transfer("map_b","map_c",{},"interrupted")
        self.assertEqual(committed,storage.read_committed()); self.assertEqual(baseline,(h.world,active))
        broken=manager(transfers.ReconstructionAdapter("broken",lambda *_:(_ for _ in ()).throw(RuntimeError("boom"))))
        with self.assertRaises(transfers.ReconstructionError): broken.transfer("map_b","map_c",{},"adapter-failure")
        self.assertEqual(committed,storage.read_committed()); self.assertEqual(baseline,(h.world,active))
        for candidate in (committed[:-13],bytes(committed).replace(b'"checksum":"',b'"checksum":"0',1)):
            storage._committed=candidate
            with self.assertRaises(transfers.TransferError): good.resume()
            self.assertEqual(candidate,storage.read_committed()); self.assertEqual(baseline,(h.world,active))

    def test_cross_map_incompatibility_and_migration_failure_are_non_mutating(self):
        h=stress.Harness(stress.complete_fixture(self.world_profiles["small_correctness"]))
        storage=transfers.MemoryTransferStorage(); active={"id":"map_a"}
        def activate(map_id,state,_runtime): active.update(id=map_id); setattr(h,"world",copy.deepcopy(state))
        def manager(**kwargs):
            return transfers.CrossMapTransferManager(scenario_id="persistence_stress",scenario_version="1",build_version="phase7.1",
                campaign_schema=saves.CURRENT_SCHEMA_VERSION,manifest=transfers.PhysicalMapManifest(stress._manifest()),storage=storage,
                capture_state=lambda:h.world,load_destination_content=stress._content,activate=activate,
                adapters=[transfers.ReconstructionAdapter("authority",lambda *_:None)],**kwargs)
        current=manager(); current.transfer("map_a","map_b",{},"valid")
        committed=storage.read_committed(); baseline=copy.deepcopy((h.world,active))
        for field,value in (("buildVersion","stale.0"),("scenario",{"id":"other_scenario","version":"1"})):
            document=json.loads(committed); document[field]=value
            document["integrity"]["checksum"]=transfers._checksum(document)
            candidate=stress.canonical(document); storage._committed=candidate
            with self.assertRaises(transfers.IncompatibleTransferError): current.resume()
            self.assertEqual(candidate,storage.read_committed()); self.assertEqual(baseline,(h.world,active))
        document=json.loads(committed); document["schemaVersion"]=0
        document["integrity"]["checksum"]=transfers._checksum(document)
        candidate=stress.canonical(document); storage._committed=candidate
        registry=transfers.TransferMigrationRegistry(); registry._migrations[0]=lambda _document: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(transfers.IncompatibleTransferError): manager(migration_registry=registry).resume()
        self.assertEqual(candidate,storage.read_committed()); self.assertEqual(baseline,(h.world,active))

if __name__=="__main__": unittest.main()
