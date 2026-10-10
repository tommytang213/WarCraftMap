#!/usr/bin/env python3
"""Inspect actual diagnostic W3X definitions, bound to the current source tree.

This supplements pinned execution; it supplies no native-launch evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT.parent / "_shared/tooling"), str(PROJECT / "tooling")]
from hero_progression_catalog import load_catalog
from hero_starting_profiles import starting_definitions, growth_cadence
from integration_evidence import source_identity
from warcraft_campaign import MpqReader

STRING = r'"(?:\\.|[^"\\])*"'


def inspect(archive):
    mpq = MpqReader(archive)
    lua_bytes = mpq.read("war3map.lua")
    lua = lua_bytes.decode()
    runtime = json.loads(mpq.read("runtime/scenario-runtime.json"))
    identity = json.loads(mpq.read("runtime/build-identity.json"))
    assert identity == source_identity(PROJECT, identity["sourceRevision"]), "artifact source mismatch"
    world = json.loads((PROJECT / "scenario/world/world.json").read_text())
    catalog, _ = load_catalog()
    cadence = growth_cadence(catalog)
    assert runtime["heroGrowthCadence"] == cadence
    assert runtime["heroStartingDefinitions"] == starting_definitions(world, catalog)
    assert runtime["heroRecoveryDays"] == catalog["defeatRecovery"]["recoveryDays"]
    assert runtime["questDefinitions"] == world["quests"]
    pattern = re.compile(r'\bRpgHero_new_RpgHero\(\s*(?P<call>' + STRING +
                         r')|\bRpgHero_id_storage\[[^\n]+?\]\s*=\s*(?P<inline>' + STRING + ')')
    starts = [(m, json.loads(m["call"] or m["inline"])) for m in pattern.finditer(lua)]
    # The compiler's allocation routine initializes the ID storage to empty.
    starts = [(m, ident) for m, ident in starts if ident]
    assert sorted(ident for _, ident in starts) == sorted(h["id"] for h in world["characters"])
    for index, (match, ident) in enumerate(starts):
        block = lua[match.start():starts[index + 1][0].start() if index + 1 < len(starts) else len(lua)]
        for field, value in cadence.items():
            values = re.findall(r'\bRpgHero_' + field + r'_storage\[[^\n]+?\]\s*=\s*(\d+)', block)
            assert values and set(map(int, values)) == {value}, (ident, field, values)
        assert "HeroRoster_HeroRoster_register(" in block, (ident, "not registered")
    # Require actual calls as well as definitions. Arithmetic is executed by
    # the independently verified threshold vectors in the pinned transcript.
    for name in ("RpgHero_RpgHero_awardExperience", "heroExperienceForLevel",
                 "heroLevelForExperience"):
        assert re.search(r'(?<!function )\b' + name + r'\(', lua), name
    # The pinned build inlines the next-level cost into inspection. Check the
    # actual assignment expression, not its diagnostic stack-trace string.
    summary = lua.split("function RpgHero_RpgHero_progressionSummary(", 1)[1].split("\nfunction ", 1)[0]
    assert re.search(r'=\s*\(\(100\s*\*\s*(\w+)\)\s*\+\s*\(\(25\s*\*\s*\(\1\s*-\s*1\)\)\s*\*\s*\(\1\s*-\s*1\)\)\)', summary)
    assert "Choice points " in lua and "Remaining experience " in lua
    return {"status": "pass", "sourceIdentity": identity,
            "scope": "Static same-source diagnostic W3X definitions; no native launch claim.",
            "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "luaSha256": hashlib.sha256(lua_bytes).hexdigest(),
            "heroCount": len(starts), "heroGrowthCadence": cadence,
            "startingProfiles": "unchanged authored profiles, zero initial unspent points",
            "heroRecoveryDays": runtime["heroRecoveryDays"],
            "questCount": len(runtime["questDefinitions"]),
            "questIntegrationBlockerCount": len(runtime["questIntegrationBlockers"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive), indent=2, sort_keys=True) + "\n")
