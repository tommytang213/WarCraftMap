#!/usr/bin/env python3
"""Validate release recovery guidance against executable contracts."""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
METADATA = PROJECT / "scenario/recovery-support.json"
PLAYER_DOC = PROJECT / "docs/PLAYER_RECOVERY.md"
RUNBOOK = PROJECT / "docs/RECOVERY_RUNBOOK.md"


class RecoveryDocumentationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RecoveryDocumentationError(message)


def validate():
    support = json.loads(METADATA.read_text(encoding="utf-8"))
    player = PLAYER_DOC.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")
    require(support.get("format") == "warcraftmap_recovery_support_v1", "unsupported recovery metadata")
    require(support.get("language") == "en", "recovery help must be English")

    commands = {item["name"]: item for item in support.get("commands", [])}
    require(set(commands) == {"unstuck", "god"}, "recovery command inventory drift")
    for name, source_name in (("unstuck", "UnstuckRecovery.wurst"), ("god", "PlayerGodMode.wurst")):
        command = commands[name]
        source = (PROJECT / "wurst" / source_name).read_text(encoding="utf-8")
        registration = re.escape(
            f'registry.register("{name}", "", "{command["registrationUsage"]}", '
            f'"{command["summary"]}", "{command["help"]}"')
        require(re.search(registration, source), f"{name} in-game help differs from recovery metadata")
        require(command["syntax"] in player, f"player guide omits {command['syntax']}")
        for option in command["options"]:
            require(re.search(rf"(?<![A-Za-z]){re.escape(option)}(?![A-Za-z])", player), f"undocumented {name} option {option}")

    unstuck = (PROJECT / "wurst/UnstuckRecovery.wurst").read_text(encoding="utf-8")
    order = ["if not point.anchor", "if e.hasLastSafe", "if point.anchor", "\n\t\treturn false\n\tfunction recoverOne"]
    offsets = [unstuck.index(token, unstuck.index("function recoverEntity")) for token in order]
    require(offsets == sorted(offsets), "unstuck fallback implementation order drift")
    cursor = -1
    for phrase in commands["unstuck"]["fallbackOrder"]:
        cursor = player.find(phrase, cursor + 1)
        require(cursor >= 0, f"player guide omits or reorders unstuck fallback: {phrase}")

    save_source = (PROJECT.parent / "_shared/engine/campaign_save.py").read_text(encoding="utf-8")
    compatibility = json.loads((PROJECT / "scenario/compatibility/release-save-v1.json").read_text(encoding="utf-8"))
    slots = support.get("saveSlots", [])
    require([x["stableId"] for x in slots] == compatibility["matrix"]["slots"], "save slot metadata differs from compatibility matrix")
    require("AUTOSAVE_SLOT_COUNT = 15" in save_source, "autosave count drift")
    for slot in slots:
        require(slot["kind"] in save_source and slot["stableId"] in player, f"save slot {slot['kind']} is stale or undocumented")

    runtime = (PROJECT / "wurst/PlayableCampaignRuntime.wurst").read_text(encoding="utf-8")
    save_commands = support.get("saveCommands", [])
    require({row["name"] for row in save_commands} == {"save", "load", "saves"}, "save command inventory drift")
    for row in save_commands:
        registration = (f'commands.register("{row["name"]}", "", "{row["registrationUsage"]}", '
                        f'"{row["summary"]}", "{row["help"]}"')
        require(registration in runtime, f"{row['name']} help differs from recovery metadata")
    for command in ("/save N", "/load N", "/load manual N", "/load autosave N",
                    "/load session_start", "/load major_milestone", "/load retry", "/saves manual 11"):
        require(command in player, f"undocumented save action: {command}")
    require(compatibility.get("recoveryLoadRequest", {}).get("current") == 1,
            "recovery request compatibility contract drift")

    compatibility_source = (PROJECT.parent / "_shared/engine/release_save_compatibility.py").read_text(encoding="utf-8")
    integrity_source = (PROJECT.parent / "_shared/engine/world_integrity.py").read_text(encoding="utf-8")
    diagnostics = support["diagnostics"]
    require(diagnostics["compatibility"] in compatibility_source, "compatibility diagnostic name drift")
    require(diagnostics["integrity"] in integrity_source, "integrity diagnostic name drift")
    require(diagnostics["provenance"] == "provenance.json", "package provenance name drift")
    for reference in support["maintainerReferences"]:
        require((PROJECT / reference).is_file(), f"broken recovery reference: {reference}")
        require(reference in runbook, f"runbook omits recovery reference: {reference}")

    combined = (player + "\n" + runbook).lower()
    for stale in ("todo", "tbd", "placeholder", "single-map", "world editor"):
        require(stale not in combined, f"forbidden recovery documentation text: {stale}")
    required = ("active campaign state", "original stored save", "ownership", "control", "native warcraft save/load", "session-only")
    for phrase in required:
        require(phrase in combined, f"recovery guarantee is undocumented: {phrase}")
    return support


if __name__ == "__main__":
    validate()
    print("Recovery documentation and support metadata are consistent.")
