#!/usr/bin/env python3
"""Offset-recording comparison against pinned War3Net binary reader layouts.

This investigation cursor is deliberately separate from the production W3F/W3I
parsers. It supports the observed empty-table fixtures only, not arbitrary maps.
No script/model code from an archive is executed. See README.md for provenance.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_shared/tooling"))
from independent_mpq import load_reader, open_archive, read_member, sha256


class Cursor:
    def __init__(self, data):
        self.data, self.offset, self.fields = data, 0, {}

    def field(self, name, fmt=None):
        start = self.offset
        if fmt is None:
            end = self.data.index(0, start)
            value = self.data[start:end].decode("utf-8")
            self.offset = end + 1
        else:
            values = struct.unpack_from("<" + fmt, self.data, start)
            value = values[0] if len(values) == 1 else list(values)
            self.offset += struct.calcsize("<" + fmt)
        self.fields[name] = {"offset": start, "size": self.offset - start, "value": value}
        return value

    def end(self):
        if self.offset != len(self.data):
            raise ValueError(f"unparsed bytes at {self.offset}/{len(self.data)}")
        return {"sha256": sha256(self.data), "bytesConsumed": self.offset, "fields": self.fields}


def w3f(data):
    c = Cursor(data)
    version = c.field("format", "i")
    if version not in (1, 2, 3): raise ValueError("unsupported investigation W3F version")
    for n in ("campaignVersion", "editorVersion"): c.field(n, "i")
    for n in ("title", "difficulty", "author", "description"): c.field(n)
    for n in ("flags", "background"): c.field(n, "i")
    for n in ("backgroundPath", "minimapPath"): c.field(n)
    c.field("ambientSound", "i"); c.field("ambientPath")
    c.field("fogStyle", "i"); c.field("fog", "3f")
    c.field("fogColor", "4B"); c.field("race", "i")
    if version >= 3: c.field("extendedFog", "5fi")
    if version >= 2: c.field("backgroundVersion", "i")
    for i in range(c.field("buttons", "i")):
        c.field(f"button.{i}.visible", "i")
        for n in ("chapter", "title", "path"): c.field(f"button.{i}.{n}")
    for i in range(c.field("maps", "i")):
        c.field(f"map.{i}.unknown"); c.field(f"map.{i}.path")
    return c.end()


def w3i(data):
    c = Cursor(data)
    version = c.field("format", "i")
    if version not in (31, 39): raise ValueError("unsupported investigation W3I version")
    c.field("saves", "i"); c.field("editor", "i"); c.field("producer", "4i")
    for n in ("title", "author", "description", "playersText"): c.field(n)
    c.field("camera", "8f"); c.field("margins", "4i")
    c.field("dimensions", "2i"); c.field("flags", "I"); c.field("tileset", "c")
    # Convert raw code bytes for JSON without changing the observation.
    c.fields["tileset"]["value"] = c.fields["tileset"]["value"].decode("ascii")
    c.field("loadingBackground", "i")
    if version >= 39: c.field("raceHud", "i")
    for n in ("loadingPath", "loadingText", "loadingTitle", "loadingSubtitle"): c.field(n)
    c.field("gameDataSet", "i")
    for n in ("prologuePath", "prologueText", "prologueTitle", "prologueSubtitle"): c.field(n)
    c.field("fogStyle", "i"); c.field("fog", "3f"); c.field("fogColor", "4B")
    if version >= 39: c.field("extendedFog", "5fi")
    c.field("weather", "I"); c.field("soundEnvironment")
    c.field("lightEnvironment", "B"); c.field("waterColor", "4B")
    for n in ("scriptLanguage", "supportedModes", "gameDataVersion"): c.field(n, "i")
    if version >= 39:
        c.field("cameraZoom", "3i"); c.field("waterOverrides", "10I")
    for i in range(c.field("players", "i")):
        for n in ("id", "controller", "race"): c.field(f"player.{i}.{n}", "i")
        if version >= 39: c.field(f"player.{i}.raceHud", "i")
        c.field(f"player.{i}.flags", "i"); c.field(f"player.{i}.name")
        c.field(f"player.{i}.position", "2f"); c.field(f"player.{i}.priorities", "4I")
    for i in range(c.field("forces", "i")):
        c.field(f"force.{i}.flags", "I"); c.field(f"force.{i}.mask", "I"); c.field(f"force.{i}.name")
    for n in ("upgrades", "tech", "randomUnits", "randomItems"):
        if c.field(n, "i") != 0: raise ValueError("nonempty tables not supported by investigation cursor")
    return c.end()


def compare(reader_path, campaign, reference_campaign, reference_map):
    reader = load_reader(reader_path)
    payload = campaign.read_bytes()
    if sha256(payload) != "4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad":
        raise ValueError("not the SHA-verified smoke #3 baseline")
    outer = open_archive(reader, payload)
    manifest = json.loads(read_member(outer, "campaign-manifest.json"))
    maps = []
    for entry in manifest["maps"]:
        data = read_member(outer, entry["packagePath"])
        if sha256(data) != entry["sha256"]: raise ValueError("map manifest mismatch")
        maps.append({"path": entry["packagePath"], "sha256": sha256(data)})
    selector = open_archive(reader, read_member(outer, "Maps/AgeOfSailWorld.w3x"))
    reference = reference_campaign.read_bytes()
    stock = reference_map.read_bytes()
    if sha256(reference) != "aac17d7739cf181e59846808960d0ccdbf0ccadbd68e6b18df0cbdf5079f1530":
        raise ValueError("reference campaign pin mismatch")
    if sha256(stock) != "18af23464674350adf20270e070766ce4894f5e878ccae3c1034b88c02281893":
        raise ValueError("reference map pin mismatch")
    return {
        "campaignSha256": sha256(payload), "maps": maps,
        "sourceIdentity": json.loads(read_member(selector, "runtime/build-identity.json")),
        "selectorW3f": w3f(read_member(outer, "war3campaign.w3f")),
        "referenceW3f": w3f(read_member(open_archive(reader, reference), "war3campaign.w3f")),
        "selectorW3i": w3i(read_member(selector, "war3map.w3i")),
        "referenceW3i": w3i(read_member(open_archive(reader, stock), "war3map.w3i")),
        "referenceNativeLaunch": "not_run", "referenceScriptLanguage": "JASS",
        "diagnosis": "diagnosis_unconfirmed", "real_client_launch": "failed",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("reader", "campaign", "reference-campaign", "reference-map", "output"):
        p.add_argument("--" + n, type=Path, required=True)
    a = p.parse_args()
    a.output.write_text(json.dumps(compare(a.reader, a.campaign, a.reference_campaign, a.reference_map), indent=2) + "\n")
