import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("remote_region_management", ROOT / "_shared/engine/remote_region_management.py")
remote = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = remote; SPEC.loader.exec_module(remote)


class Token:
    def __init__(self, pause): self.pause, self.open = pause, True
    def close(self):
        if self.open: self.open = False; self.pause.owners -= 1; self.pause.paused = self.pause.before if self.pause.owners == 0 else True


class Pause:
    def __init__(self, paused=False): self.paused, self.before, self.owners = paused, paused, 0
    def open_modal_management_screen(self):
        if self.owners == 0: self.before = self.paused
        self.owners += 1; self.paused = True
        return Token(self)


class Runtime:
    def __init__(self): self.region, self.entities, self.calls, self.fail = "europe", (), [], False
    def snapshot(self): return copy.deepcopy((self.region, self.entities, self.calls))
    def restore(self, value): self.region, self.entities, self.calls = copy.deepcopy(value)
    def retire_region(self, region): self.calls.append(("retire", region)); self.entities = ()
    def reconstruct_region(self, region, entities):
        if self.fail: raise RuntimeError("adapter failed")
        self.calls.append(("reconstruct", region, tuple(entities))); self.region, self.entities = region, tuple(entities)
    def focus_region(self, region): self.calls.append(("focus", region)); self.region = region


class RemoteRegionManagementTests(unittest.TestCase):
    def make(self, *, paused=False, budget=8):
        state = {"physicalRegionId": "europe", "campaignTime": 12, "entities": {
            "hero": {"regionId": "europe", "kind": "character", "playerControllable": True, "locallyRelevant": True, "position": [1, 2]},
            "army": {"regionId": "africa", "kind": "troops", "playerControllable": True, "locallyRelevant": True, "activeObjectCount": 2},
            "fort": {"regionId": "africa", "kind": "holding", "playerControllable": True, "locallyRelevant": True, "construction": 4},
            "hidden": {"regionId": "pacific", "kind": "fleet", "playerControllable": True, "locallyRelevant": True},
        }}
        runtime, pause = Runtime(), Pause(paused)
        manager = remote.RegionManagement({"europe", "africa", "pacific"}, state, runtime, pause,
            knows_region=lambda r: r != "pacific", may_command_region=lambda r: r == "africa", active_object_budget=budget)
        return manager, runtime, pause

    def test_authorized_selection_separates_physical_and_command_regions(self):
        manager, runtime, pause = self.make()
        before = copy.deepcopy(manager.state["entities"]["hero"])
        result = manager.select("africa")
        self.assertEqual(("europe", "africa", True), (result.physical_region_id, result.command_region_id, result.remote))
        self.assertEqual(("army", "fort"), result.represented_entity_ids)
        self.assertEqual(before, manager.state["entities"]["hero"])
        self.assertNotIn("hero", runtime.entities)
        self.assertTrue(pause.paused)

    def test_unknown_knowledge_and_authorization_fail_without_leaking_or_mutating(self):
        manager, runtime, _ = self.make()
        before = manager.export_authoritative_state(), runtime.snapshot()
        with self.assertRaises(remote.UnknownRegion): manager.select("moon")
        with self.assertRaises(remote.RegionNotKnown): manager.select("pacific")
        self.assertEqual(before, (manager.export_authoritative_state(), runtime.snapshot()))
        manager.knows_region = lambda _r: True
        with self.assertRaises(remote.RegionNotAuthorized): manager.select("pacific")

    def test_return_retires_remote_objects_without_teleport_and_restores_prior_pause(self):
        manager, runtime, pause = self.make(paused=True)
        hero = copy.deepcopy(manager.state["entities"]["hero"])
        manager.select("africa"); result = manager.return_to_physical_region()
        self.assertFalse(result.remote); self.assertEqual("europe", runtime.region)
        self.assertEqual(hero, manager.state["entities"]["hero"])
        self.assertTrue(pause.paused); self.assertEqual(0, pause.owners)

    def test_existing_nested_modal_owner_remains_after_remote_view_closes(self):
        manager, _, pause = self.make()
        outer = pause.open_modal_management_screen()
        manager.select("africa"); self.assertEqual(2, pause.owners)
        manager.close(); self.assertEqual(1, pause.owners); self.assertTrue(pause.paused)
        outer.close(); self.assertFalse(pause.paused)

    def test_orders_building_state_inactive_simulation_and_reconstruction_survive_switches(self):
        manager, _, _ = self.make()
        manager.select("africa")
        manager.issue_order("army", {"type": "move", "destination": "coast"})
        manager.operate_holding("fort", {"type": "construct", "building": "dock"})
        manager.return_to_physical_region()
        manager.simulate_inactive(3, lambda state, region, days: state["entities"]["fort"].update(construction=state["entities"]["fort"].get("construction", 0) + days) if region == "africa" else None)
        manager.select("africa")
        self.assertEqual("move", manager.state["entities"]["army"]["order"]["type"])
        self.assertEqual(("construct", 7), (manager.state["entities"]["fort"]["order"]["type"], manager.state["entities"]["fort"]["construction"]))

    def test_adapter_failure_atomically_restores_context_and_pause(self):
        manager, runtime, pause = self.make(); before = runtime.snapshot()
        runtime.fail = True
        with self.assertRaises(RuntimeError): manager.select("africa")
        self.assertEqual(("europe", before), (manager.command_region_id, runtime.snapshot()))
        self.assertFalse(pause.paused); self.assertEqual(0, pause.owners)

    def test_budget_is_checked_before_retirement(self):
        manager, runtime, _ = self.make(budget=2); before = runtime.snapshot()
        with self.assertRaises(remote.ActiveObjectBudgetExceeded): manager.select("africa")
        self.assertEqual(before, runtime.snapshot())

    def test_save_load_persists_orders_but_reconstructs_physical_view(self):
        manager, _, _ = self.make(); manager.select("africa"); manager.issue_order("army", {"type": "hold"})
        saved = manager.export_authoritative_state()
        self.assertNotIn("commandRegionId", saved)
        resumed = remote.RegionManagement({"europe", "africa", "pacific"}, saved, Runtime(), Pause(),
            knows_region=lambda _r: True, may_command_region=lambda _r: True)
        self.assertEqual(("europe", "hold"), (resumed.command_region_id, resumed.state["entities"]["army"]["order"]["type"]))

    def test_command_parser_and_feedback(self):
        manager, _, _ = self.make()
        self.assertEqual(("error", "Usage: /region <region-id|return>"), remote.parse_region_command("  "))
        self.assertEqual(("select", "africa"), remote.parse_region_command(" AFRICA "))
        self.assertIn("remains in europe", remote.execute_region_command(manager, "africa"))
        self.assertIn("No strategic entity was moved", remote.execute_region_command(manager, "return"))


if __name__ == "__main__": unittest.main()
