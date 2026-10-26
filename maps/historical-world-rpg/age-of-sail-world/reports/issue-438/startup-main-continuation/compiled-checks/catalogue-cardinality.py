#!/usr/bin/env python3
"""Derive current trade cardinality from pinned generated/authored inputs.

Read-only source analysis. Does not execute Lua, Java, tests, or generation
commands, and never changes production inputs or the earlier failed evidence.
The industry catalog builder reads source JSON and returns an in-memory value.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
PROJECT = WORKSPACE / "WarCraftMap/maps/historical-world-rpg/age-of-sail-world"
REVISION = "d6697380d979f96b2f3543593c6383402ba26e5b"
SOURCE = "d08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37"
IDENTITY = {"sourceRevision": REVISION, "sourceTreeSha256": SOURCE}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha(data)}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    integration = module("catalogue_source_identity", PROJECT.parent / "_shared/tooling/integration_evidence.py")
    assert integration.source_identity(PROJECT, REVISION) == IDENTITY
    generated = ROOT / "europe-seed/compile/wurst/ScenarioData.wurst"
    source = generated.read_text()
    builds = {name: json.loads((ROOT / name / "build-result.json").read_text()) for name in ("baseline", "revised")}
    for build in builds.values():
        assert build["status"] == "pass" and build["sourceIdentityAtAssembly"] == IDENTITY
        assert build["compilerInputs"]["wurst/ScenarioData.wurst"] == sha(generated.read_bytes())
    functions = {}
    for part in re.split(r"(?m)^(?:public )?function ", source)[1:]:
        name = part.split("(", 1)[0]
        assert name not in functions
        functions[name] = part
    pairs = lambda text: re.findall(r'runtime\.registerMarketProfile\("([^"]+)",\s*"([^"]+)"', text)
    inventory = {name: pairs(text) for name, text in functions.items() if pairs(text)}
    trade_names = sorted((name for name in inventory if re.fullmatch(r"configureGeneratedTrade[0-9]+", name)),
                         key=lambda name: int(name.removeprefix("configureGeneratedTrade")))
    assert trade_names == ["configureGeneratedTrade" + str(i) for i in range(62)]
    assert set(inventory) == set(trade_names) | {"configureGeneratedIndustryMarkets"}
    calls = re.findall(r"\b(configureGeneratedTrade[0-9]+)\(runtime\)", functions["configureGeneratedTrade"])
    assert calls == trade_names
    base = [pair for name in trade_names for pair in inventory[name]]
    assert len(base) == len(set(base)) == 8422
    industry_path = PROJECT / "tooling/industry_catalog.py"
    industry = module("current_industry_catalogue", industry_path).build(PROJECT)
    assert industry["wurst"].strip() in source
    industry_pairs = inventory["configureGeneratedIndustryMarkets"]
    assert industry_pairs == [tuple(pair) for pair in industry["catalog"]["markets"]]
    assert len(industry_pairs) == len(set(industry_pairs)) == 20
    conditional = re.findall(r'if runtime\.findMarket\("([^"]+)",\s*"([^"]+)"\) == null\n\s+runtime\.registerMarketProfile\("([^"]+)",\s*"([^"]+)"',
                             functions["configureGeneratedIndustryMarkets"])
    assert [(a, b) for a, b, c, d in conditional if (a, b) == (c, d)] == industry_pairs
    added = sorted(set(industry_pairs) - set(base))
    assert added == [(city, "iron_goods") for city in ("milan", "nuremberg", "stockholm", "vienna")]
    union = sorted(set(base) | set(industry_pairs))
    assert len(union) == 8426
    registration = PROJECT.parent / "_shared/wurst/CampaignRegistration.wurst"
    registration_source = registration.read_text()
    assert registration_source.count("configureGeneratedTrade(trade)") == 1
    assert registration_source.count("configureGeneratedIndustryMarkets(trade)") == 1
    assert registration_source.index("configureGeneratedTrade(trade)") < registration_source.index("configureGeneratedIndustryMarkets(trade)")
    stores = sum(functions[name].count("runtime.registerStore(") for name in trade_names)
    personal_calls = sum(functions[name].count("runtime.registerPersonalStore()") for name in trade_names)
    assert stores == 828 and personal_calls == 1
    authority_files = {relative: identity(PROJECT / relative) for relative in industry["sources"]}
    authority_files["../_shared/wurst/CampaignRegistration.wurst"] = identity(registration)
    authority_files["../_shared/wurst/PlayableTrade.wurst"] = identity(PROJECT.parent / "_shared/wurst/PlayableTrade.wurst")
    assert integration.source_identity(PROJECT, REVISION) == IDENTITY
    report = {
        "format": "pr536_current_catalogue_cardinality_v1", "status": "pass_static_source_derivation",
        "createdAtUtc": datetime.now(timezone.utc).isoformat(), "sourceIdentity": IDENTITY,
        "nativeStatus": "not_run", "nativeHangResolution": "not_established", "schema": 17,
        "historicalMarketCount": 8422, "baseMarketCount": len(base), "industryMarketDefinitions": len(industry_pairs),
        "industryAddedMarketCount": len(added), "industryAddedMarkets": [list(pair) for pair in added],
        "marketCount": len(union), "lastMarketIndex": len(union) - 1,
        "storeCount": stores + personal_calls, "lastStoreIndex": stores + personal_calls - 1,
        "baseMarketIdentitySha256": sha(json.dumps(base, separators=(",", ":")).encode()),
        "combinedMarketIdentitySha256": sha(json.dumps(union, separators=(",", ":")).encode()),
        "tradeConfigurationFunctions": trade_names, "industryMarketPairs": [list(pair) for pair in industry_pairs],
        "sourceInputs": authority_files,
        "inputs": {"generatedScenario": identity(generated), "runner": identity(Path(__file__).resolve()),
                   **{name + "Build": identity(ROOT / name / "build-result.json") for name in builds}},
        "registrationOrder": ["configureGeneratedTrade", "configureGeneratedIndustryMarkets"],
        "assertionUpdateScope": "Exact market count 8422 to 8426 and last market index 8421 to 8425 only; no reduction of data coverage, native stub change, budget change, source change, or original-evidence rewrite.",
        "validationPerformed": {"staticSourceDerivation": True, "testExecution": False, "modelExecution": False,
                                "buildExecution": False, "sourceEdits": False},
        "limitations": ["Static source/catalogue derivation is not Warcraft execution.",
                        "Current compiled runtime observations are separate evidence, not the source of this expected count."]
    }
    output = ROOT / "catalogue-cardinality.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "marketCount": len(union), "storeCount": report["storeCount"],
                      "industryAddedMarkets": report["industryAddedMarkets"], "receipt": identity(output)}, indent=2))


if __name__ == "__main__":
    main()
