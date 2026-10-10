#!/usr/bin/env python3
"""Check allocation definitions and registered actions in same-source diagnostic Lua."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT.parent / "_shared/tooling"), str(PROJECT / "tooling")]
from hero_progression_catalog import load_catalog
from hero_starting_profiles import starting_definitions
from hero_allocations import allocation_definitions
from integration_evidence import source_identity
from warcraft_campaign import MpqReader


def inspect(archive):
    mpq = MpqReader(archive)
    lua_bytes = mpq.read("war3map.lua")
    lua = lua_bytes.decode()
    runtime = json.loads(mpq.read("runtime/scenario-runtime.json"))
    identity = json.loads(mpq.read("runtime/build-identity.json"))
    assert identity == source_identity(PROJECT, identity["sourceRevision"]), "source mismatch"
    catalog, _ = load_catalog()
    world = json.loads((PROJECT / "scenario/world/world.json").read_text())
    starts = starting_definitions(world, catalog)
    definitions = allocation_definitions(catalog, starts)
    assert runtime["heroAllocationDefinitions"] == definitions
    assert runtime["heroStartingDefinitions"] == starts
    assert runtime["heroGrowthCadence"] == catalog["growth"]
    assert runtime["heroRecoveryDays"] == catalog["defeatRecovery"]["recoveryDays"]
    assert runtime["questDefinitions"] == world["quests"]
    # Match real invocation argument tuples, not stack trace strings or names.
    def call(method, arguments):
        literal = r"\s*,\s*".join(re.escape(json.dumps(v)) for v in arguments)
        stack = r'(?:,\s*"when calling ' + method + r' in ScenarioData, line \d+")?'
        pattern = r"(?m)^\s*HeroAllocationDefinitions_HeroAllocationDefinitions_" + method + r"\([^,\n]+,\s*" + literal + stack + r"\s*\)"
        assert re.search(pattern, lua), (method, arguments)
    for key, kind in (("skills", "skill"), ("masteries", "mastery")):
        for row in definitions[key]:
            call("addRank", [kind, row["id"], row["name"]])
    for row in definitions["abilities"]:
        call("addAbility", [row["id"], row["name"]])
    for row in definitions["perks"]:
        call("addPerk", [row["id"], row["abilityId"], row["minimumLevel"], "".join(f"~{p}~" for p in row["prerequisitePerkIds"])])
    for row in definitions["personalTrees"]:
        call("addTree", [row["id"], "".join(f"~{p}~" for p in row["perkIds"])])
    commands = ["progression", "improveskill", "improvemastery", "chooseperk"]
    for name in commands:
        assert re.search(r'\bCommandRegistry_CommandRegistry_register\([^,\n]+,\s*"' + name + '",', lua), name
    assert re.search(r'(?<!function )\bWarcraftRpgRuntime_WarcraftRpgRuntime_allocate\(', lua)
    assert "ability effects are pending" in lua
    assert "Respecialization is unavailable" in lua
    return {"status": "pass", "sourceIdentity": identity,
            "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "luaSha256": hashlib.sha256(lua_bytes).hexdigest(),
            "definitionCounts": {key: len(value) for key, value in definitions.items() if isinstance(value, list)},
            "registeredCommands": commands, "heroCount": len(starts["profiles"]),
            "scope": "Allocation and selected entitlements only; static diagnostic artifact inspection.",
            "abilityEffects": "blocked_pending_consumers", "nativeClient": "not_run", "releaseReady": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive), indent=2, sort_keys=True) + "\n")
