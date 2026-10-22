#!/usr/bin/env python3
"""Verify retained PR536 evidence without executing tests, Lua, Java or builds.

Requires the authored source checkout: --project must name age-of-sail-world
with the exact d669 source identity. A later report-only commit is acceptable;
changed source inputs are not. Original absolute receipt paths are provenance,
never paths to read. Large retained text may be stored as <original-name>.gz.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True
REVISION = "d6697380d979f96b2f3543593c6383402ba26e5b"
SOURCE = "d08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37"
PUBLISHED = "99524f6e4c356e02acc6ea7fa2f3b9a73fb62d13"
COMPILER = "1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145"
DEPENDENCY = "cce79096e71dcb066cf94785bc5cb48ef66c26db"
GATE = "49fe8dd2c491ef16ebfcfb481aa782d27c1356779ad229b10e0ba1b108513101"
INTEGRATION = "eb4ca67743156f917654715f1041d2ff9d32445cf6fe5fa664b15b6cfc6426a2"
CONTRACT = "c3ac7c2d1d8f34d55e05e2c46ba22acf740e86ea74b2898132dfecf8e44e3e85"
LIBRARY = "fdaa987d06dd329be3232a65ea71cae427f3bfd26f5b757d8853628d33d9492a"
WPM = "7cf3b29475751ebe1d962e17651b0c42ace030b9fa2e4523cf935adf27aee0bd"
IDENTITY = {"sourceRevision": REVISION, "sourceTreeSha256": SOURCE}
CHANGED = {"wurst/PlayableCampaignRuntime.wurst", "wurst/PlayableTrade.wurst"}
ADAPTATION = "compiled-checks/catalogue-adaptation/"
CURRENT_COMPARISON = "compiled-checks/startup-comparison/comparison-current-catalogue.json"
CURRENT_FULL_SCALE = "compiled-checks/full-scale-revised-current-catalogue/"
DRIVER = "compiled-checks/driver-20261021T141701Z/"


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def checked_path(path):
    """Reject lexical symlinks before resolve/read, including all ancestors."""
    lexical = Path(path).absolute()
    for component in [lexical, *lexical.parents]:
        require(not component.is_symlink(), "Symlink is not an evidence/source input: " + str(component))
    return lexical


def file_bytes(path):
    return checked_path(path).read_bytes()


def source_inventory(project):
    roots = [project / name for name in ("map", "scenario", "wurst", "wurst-bootstrap", "tooling", "tests")]
    roots += [project.parent / "_shared"]
    files = [p for root in roots for p in root.rglob("*") if p.is_file()
             and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}]
    files += [p for p in project.iterdir() if p.is_file() and p.suffix in {".json", ".build", ".args"}]
    return {Path(os.path.relpath(p, project)).as_posix(): sha(file_bytes(p)) for p in sorted(set(files))}


class Evidence:
    def __init__(self, root):
        self.root = checked_path(root).resolve()
        self.manifest = None
        self.entries = {}
        manifest = self.root / "manifest.json"
        if manifest.is_file():
            self.manifest = json.loads(file_bytes(manifest))
            require(self.manifest["format"] == "warcraftmap_pr536_continuation_evidence_v1" and
                    self.manifest["status"] == "complete_source_and_model_evidence_native_not_run", "Evidence pack incomplete")
            require(self.manifest["sourceIdentity"] == IDENTITY and self.manifest["publishedRevision"] == PUBLISHED, "Manifest source")
            require(self.manifest["nativeStatus"] == "not_run" and self.manifest["nativeHangResolution"] == "not_established"
                    and self.manifest["playerArtifactProduced"] is False and self.manifest["sourceCheckoutRequired"] is True, "Manifest scope")
            for entry in self.manifest["files"]:
                name = self.safe(entry["file"])
                require(name != "manifest.json" and name not in self.entries, "Duplicate/self manifest entry")
                path = checked_path(self.root / name)
                require(path.resolve().is_relative_to(self.root) and not path.is_symlink(), "Evidence escaped root")
                raw = file_bytes(path)
                require(len(raw) == entry["packagedBytes"] and sha(raw) == entry["packagedSha256"], name + ": packaged bytes")
                if entry["encoding"] == "gzip_mtime_0":
                    require(raw[:4] == b"\x1f\x8b\x08\x00" and raw[4:8] == b"\0\0\0\0", name + ": nondeterministic gzip")
                    data = gzip.decompress(raw)
                else:
                    require(entry["encoding"] == "identity", name + ": unsupported encoding")
                    data = raw
                require(len(data) == entry["originalBytes"] and sha(data) == entry["originalSha256"], name + ": original bytes")
                self.entries[name] = entry
            actual = set()
            for path in self.root.rglob("*"):
                require(not path.is_symlink(), "Evidence pack contains a symlink")
                if path.is_file() and path != manifest:
                    actual.add(path.relative_to(self.root).as_posix())
            require(actual == set(self.entries), "Manifest must bind the exact retained file set")
            for logical, retained in self.manifest["logicalAliases"].items():
                self.safe(logical)
                require(retained in self.entries, "Dangling logical alias")
            for original, retained in self.manifest["originalPathAliases"].items():
                require(Path(original).is_absolute() and retained in self.entries, "Invalid original-path alias")

    @staticmethod
    def safe(name):
        require(isinstance(name, str) and name and "\\" not in name, "Invalid evidence path")
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.as_posix() == name and ".." not in path.parts, "Unsafe evidence path: " + name)
        return name

    def has(self, name):
        if self.manifest is not None:
            return name in self.manifest["logicalAliases"]
        return checked_path(self.root / name).is_file() or checked_path(Path(str(self.root / name) + ".gz")).is_file()

    def data(self, name):
        self.safe(name)
        if self.manifest is not None:
            retained = self.manifest["logicalAliases"][name]
            entry = self.entries[retained]
            raw = file_bytes(self.root / retained)
            require(sha(raw) == entry["packagedSha256"], "Retained file changed during verification")
            return gzip.decompress(raw) if entry["encoding"] == "gzip_mtime_0" else raw
        path = checked_path(self.root / name)
        require(not Path(name).is_absolute() and ".." not in Path(name).parts,
                "Unsafe evidence path: " + name)
        compressed = not path.is_file()
        if compressed:
            path = checked_path(Path(str(path) + ".gz"))
        require(path.resolve().is_relative_to(self.root) and not path.is_symlink(), "Evidence escaped root")
        data = file_bytes(path)
        return gzip.decompress(data) if compressed else data

    def read(self, name):
        return json.loads(self.data(name))

    def bind(self, identity, name):
        data = self.data(name)
        require(identity["sha256"] == sha(data), name + ": identity mismatch")
        require("bytes" not in identity or identity["bytes"] == len(data), name + ": length mismatch")
        if self.manifest is not None and "path" in identity:
            require(self.manifest["originalPathAliases"].get(identity["path"]) == self.manifest["logicalAliases"][name],
                    name + ": original path is not bound to this retained file")


def load_gate(project):
    tooling = project.parent / "_shared/tooling"
    modules = {}
    for name, digest in [("wurst_execution", GATE), ("integration_evidence", INTEGRATION)]:
        path = tooling / (name + ".py")
        require(sha(file_bytes(path)) == digest, name + ": required original verifier changed")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    integration = modules["integration_evidence"]
    require(sha(canonical(source_inventory(project))) == SOURCE, "Source inventory differs or contains links")
    require(integration.source_identity(project, REVISION) == IDENTITY,
            "Source checkout must have the exact d669/d084 inputs; do not weaken this check for future main")
    require(sha(file_bytes(project / "scenario/runtime-execution.json")) == CONTRACT, "Changed coverage contract")
    return modules["wurst_execution"], integration


def verify_source_context(pack, project):
    repo = project.parents[2]
    inventory = source_inventory(project)
    require(sha(canonical(inventory)) == SOURCE, "Source inventory identity mismatch")
    script_review = pack.read("evidence-review/static-review.json")
    require(script_review["status"] == "pass_static_review" and script_review["blockingFindings"] == []
            and script_review["nativeStatus"] == "not_run", "Evidence-script static review incomplete")
    require(set(script_review["reviewedScripts"]) == {"pack-evidence.py", "verify-evidence.py"}, "Evidence-script review coverage")
    for name, row in script_review["reviewedScripts"].items():
        pack.bind(row, name if pack.has(name) else "evidence-review/" + name)
    require(all(script_review["validationPerformed"][flag] is False for flag in
                ["testExecution", "modelExecution", "buildExecution", "packingExecution"]), "Static review execution scope")
    if pack.manifest is not None:
        require(pack.read("source-inputs.json") == inventory, "Retained source inventory mismatch")
        for name, digest in [("wurst_execution.py", GATE), ("integration_evidence.py", INTEGRATION), ("runtime-execution.json", CONTRACT)]:
            require(sha(pack.data("common/" + name)) == digest, "Required retained verifier/contract: " + name)
        require(pack.data("common/package.json") == file_bytes(project / "package.json"), "Retained package configuration")
        require(pack.manifest["integratedMainRevision"] == "58d1b88d0fb4b852b639d2d82a5a24dee92ed92c", "Integrated main changed")
        require(pack.manifest["sourceCheckoutUrl"] == "https://github.com/tommytang213/WarCraftMap/tree/" + REVISION, "Pinned checkout URL")
        native = None
        for row in pack.manifest["historicalReferences"]:
            relative = Evidence.safe(row["repoPath"])
            path = checked_path(repo / relative)
            require(path.resolve().is_relative_to(repo), "Historical reference escaped repository")
            data = file_bytes(path)
            require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Historical reference changed: " + relative)
            if row["role"] == "latest_actual_native_observation":
                require(native is None, "Duplicated latest native observation")
                native = json.loads(data)
        require(native and native["sourceRevision"] == "a1b43969eb57de4127b005956823d6b876a86068"
                and native["reportedAtUtc"] == "2026-10-20T16:52:49Z" and native["destinationGameplay"] == "failed"
                and native["destinationLuaInitialized"] == "unknown" and native["diagnosis"] == "unconfirmed"
                and native["releaseCandidate"] is False, "Native history was omitted or relabeled")
        review = pack.read("source-review.json")
        require(review["status"] == "pass_source_review_only" and not review["blockingFindings"], "Source review not passing")
        for row in review["reviewedFiles"]:
            data = file_bytes(repo / Evidence.safe(row["path"]))
            require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Reviewed source changed")
            require(pack.data("source/" + row["path"]) == data, "Retained reviewed source changed")
    receipt = pack.read("source-reports/receipt.json")
    require(receipt["status"] == "source_freshness_only_native_and_release_remain_blocked"
            and receipt["sourceIdentity"]["sourceTreeSha256"] == SOURCE and receipt["nativeStatus"] == "not_run"
            and receipt["sourcesUnchanged"] is True, "Source reports altered acceptance scope")
    require([(r["name"], r["expectedExitCode"]) for r in receipt["commands"]] ==
            [("runtime", 1), ("release", 1), ("traceability", 0)], "Source report commands")
    for row in receipt["commands"]:
        require(row["exitCode"] == row["expectedExitCode"], "Source report command failed unexpectedly")
        for stream in ["stdout", "stderr"]:
            require(sha(pack.data("source-reports/" + row["name"] + "." + stream)) == row[stream + "Sha256"], "Source report raw stream")
    runtime, release = pack.read("source-reports/runtime.stdout"), pack.read("source-reports/release.stdout")
    require(runtime["status"] == release["status"] == "fail" and runtime["failures"] == receipt["runtimeFailures"] == 30,
            "Source acceptance failures were hidden")
    require(receipt["traceabilityBlockers"] == 7004 and b"7004 publication blockers" in pack.data("source-reports/traceability.stdout"), "Publication blockers changed")
    return inventory


def full_inputs(pack, integration, project):
    authored = {name: file_bytes(path) for name, path in integration.execution_sources(project).items()}
    before = pack.read("full-attempt1/compiler-inputs-before.json")
    require(before == pack.read("full-attempt1/compiler-inputs-after.json"), "Full-gate inputs changed")
    data = dict(authored)
    for name in sorted(before.keys() - authored.keys()):
        # The retained pack stores only these seven unauthored inputs. The
        # workspace fallback reads the completed assembly, never materializes it.
        retained = "full-attempt1/inputs/" + name
        if pack.has(retained):
            data[name] = pack.data(retained)
        else:
            data[name] = pack.data("full-attempt1/compile/" + name)
    require({name: sha(value) for name, value in data.items()} == before, "Authored/generated/config inputs differ")
    return data


def verify_full(pack, gate, integration, project):
    receipt = pack.read("full-attempt1/receipt.json")
    result = pack.read("full-attempt1/results.json")
    log = pack.data("full-attempt1/execution.log")
    require(receipt["status"] == "pass" and receipt["mode"] == "full", "Full gate did not pass")
    require(receipt["sourceIdentity"] == result["sourceIdentity"] == IDENTITY, "Full-gate source mismatch")
    require(receipt["sourceRevision"] == REVISION and receipt["sourceState"] == "clean_committed_tree", "Full-gate revision/state")
    for flag in ["sourceInputsUnchanged", "compilerInputsUnchanged", "dependencyInputsUnchanged"]:
        require(receipt[flag] is True, "Full gate: " + flag)
    for flag in ["playerArtifactProduced", "repositoryGateModified", "repositoryTestDeadlineModified"]:
        require(receipt[flag] is False, "Full gate changed scope: " + flag)
    require(receipt["nativeStatus"] == "not_run", "Full gate is not native execution")
    gate.verify_evidence(result, log, REVISION)
    coverage = integration.verify_execution_coverage(result, log, project, REVISION)
    require(coverage == receipt["productionCoverage"], "Receipt coverage differs from original verifier")
    contract = integration.load_contract(project)
    observed = integration.observed_probes(log.decode(), result["tests"], contract)
    observed_ids = {probe for hits in observed.values() for probe in hits}
    require(len(coverage) == len(contract["systems"]) == 28 and all(coverage.values()), "Every required system needs an observed passing test")
    require(len(contract["probes"]) == 84 and observed_ids == set(contract["probes"]), "Every contract probe needs a raw observed passing-test hit")
    require(result["expected"] == pack.read("full-attempt1/discovery.json"), "Full discovery mismatch")
    require(receipt["testCount"] == receipt["discovered"] == receipt["succeeded"] ==
            result["discovered"] == result["succeeded"] == 698, "Incomplete full discovery")
    data = full_inputs(pack, integration, project)
    contract = integration.load_contract(project)
    instrumented = {}
    for name, value in data.items():
        probes = {key: row for key, row in contract["probes"].items() if row["path"] == name}
        instrumented[name] = sha(integration.instrument(value.decode(), probes).encode() if probes else value)
    require(instrumented == result["inputs"], "Instrumented inputs do not reconstruct from original sources")
    dependency = pack.read("full-attempt1/dependency-before.json")
    require(dependency["revision"] == DEPENDENCY and dependency["dirty"] is False and dependency["files"], "Dependency identity")
    seed = pack.read("seed/receipt.json")
    require(seed["dependency"] == dependency, "Full gate/seed dependency mismatch")
    require(seed["sourceIdentity"]["sourceTreeSha256"] == SOURCE, "Seed source mismatch")
    require(seed["authoredInputs"] == {n: sha(file_bytes(p)) for n, p in integration.execution_sources(project).items()}, "Seed authored inputs")
    return data, dependency, coverage


def verify_failed_attempts(pack, gate, original):
    names = {"emptySessionEncodingPreservesPendingStartupAndCanRetry", "emptyMilestoneEncodingPreservesPendingStartupAndCanRetry"}
    for prefix, count, succeeded, revision in [("focused-attempt1", 66, 66, PUBLISHED),
                                              ("negative-guard-attempt1", 2, 0, REVISION)]:
        receipt, result = pack.read(prefix + "/receipt.json"), pack.read(prefix + "/results.json")
        log = pack.data(prefix + "/execution.log")
        require(receipt["status"] == result["status"] == "fail", prefix + ": failure relabeled")
        require(receipt["nativeStatus"] == "not_run" and receipt["sourceIdentity"]["sourceTreeSha256"] == SOURCE, prefix + ": scope/source")
        require(result["sourceRevision"] == revision and result["logSha256"] == sha(log), prefix + ": raw binding")
        require(result["discovered"] == count and result["succeeded"] == succeeded and result["executionStatus"] == "completed", prefix + ": terminal counts")
        require(result["expected"] == pack.read(prefix + "/discovery.json"), prefix + ": discovery")
        rows, issues = gate.parse_results(log.decode(), result["expected"])
        require(rows == result["tests"] and issues, prefix + ": original failure diagnostic absent")
        require(result["errors"] == issues + (["grill test exited 1"] if prefix.startswith("negative") else []), prefix + ": diagnostics differ")
        require(all(row["status"] == ("assertion_failed" if prefix.startswith("negative") else "pass") for row in rows), prefix + ": unexpected result")
        selected = {}
        for name, value in original.items():
            text = value.decode()
            if prefix.startswith("negative") and name == "wurst/PlayableCampaignRuntime.wurst":
                for slot, variable in [("session_start", "session"), ("major_milestone", "milestone")]:
                    before = f'if {variable} == "" or not saves.storage.writeTransactional("{slot}", {variable})'
                    require(text.count(before) == 1, "Missing guard")
                    text = text.replace(before, f'if not saves.storage.writeTransactional("{slot}", {variable})')
            if name.endswith(".wurst"):
                chosen = {row["id"].rsplit(":", 1)[1] for row in result["expected"] if row["id"].rsplit(":", 1)[0] == name}
                text = gate.select_tests(text, chosen)
            selected[name] = sha(text.encode())
        require(selected == result["inputs"] == pack.read(prefix + "/compiler-inputs-before.json") ==
                pack.read(prefix + "/compiler-inputs-after.json"), prefix + ": unauthorized input difference")
        require(result["inputSetSha256"] == sha(canonical(selected)), prefix + ": input digest")
        try:
            gate.verify_evidence(result, log, revision)
        except gate.WurstExecutionError:
            pass
        else:
            raise ValueError(prefix + ": strict positive gate must reject this attempt")
        if prefix.startswith("negative"):
            require({row["id"].rsplit(":", 1)[1] for row in rows} == names, "Wrong negative-control tests")
            require(log.count(b"\tFAILED assertion:") == 2 and b"Tests succeeded: 0/2\n" in log, "Wrong negative assertions")
            require(log.count(b"Test failed: Expected <false>, Actual <true>") == 4, "Wrong assertion/wrapper text")
            require(b"No builtin function" not in log and b"FileNotFoundException" not in log, "Incidental negative error")
    review = pack.read("evidence-review/negative-control-review.json")
    require(review["status"] == "intended_assertions_confirmed_original_harness_fail_preserved", "Negative review scope")
    require(review["nativeStatus"] == "not_run" and review["originalAttemptStatus"] == "fail", "Negative review relabeled result")
    for path, digest in review["evidenceSha256"].items():
        require(sha(pack.data(path)) == digest, "Negative review binding: " + path)
    require(review["reviewScriptSha256"] == sha(pack.data("evidence-review/review-negative-control.py")), "Negative review script binding")


def verify_prefix(pack):
    receipt = pack.read("python-checks/receipt.json")
    before, after = pack.read("python-checks/before.json"), pack.read("python-checks/after.json")
    raw = pack.data("python-checks/execution.log")
    log = raw.decode()
    require(receipt["status"] == "completed" and receipt["exitCode"] == 0, "Source/Python prefix incomplete or failed")
    require(before == after == receipt["before"] == receipt["after"] and receipt["beforeAfterIdentical"] is True, "Prefix changed source")
    require(before["sourceIdentity"] == IDENTITY and before["head"] == REVISION and before["statusPorcelain"] == "", "Prefix source/head")
    require(receipt["logSha256"] == sha(raw) and receipt["logBytes"] == len(raw), "Prefix raw transcript binding")
    require(receipt["environmentOverride"]["WARCRAFTMAP_WURST_CHECK"] == "skip" and receipt["fullWurstGateSatisfiedByThisRun"] is False, "Prefix scope")
    require(receipt["wurstSkippedWarningPresent"] is True and
            "WARNING: Wurst typecheck and execution skipped by explicit WARCRAFTMAP_WURST_CHECK=skip" in log, "Missing explicit skipped-Wurst label")
    summaries = [{"tests": int(n), "durationSeconds": float(t)} for n, t in re.findall(r"^Ran (\d+) tests? in ([0-9.]+)s", log, re.M)]
    require(summaries and summaries == receipt["unittestSummaries"], "Prefix test summaries mismatch")
    require(len(re.findall(r"^OK(?: \([^\n]+\))?\s*$", log, re.M)) == len(summaries), "Prefix terminal unittest status")
    return summaries


def revert_production(name, data):
    text = data.decode()
    if name == "wurst/PlayableCampaignRuntime.wurst":
        for slot, variable in [("session_start", "session"), ("major_milestone", "milestone")]:
            before = f'if {variable} == "" or not saves.storage.writeTransactional("{slot}", {variable})'
            require(text.count(before) == 1, "Counterfactual guard absent")
            text = text.replace(before, f'if not saves.storage.writeTransactional("{slot}", {variable})')
    elif name == "wurst/PlayableTrade.wurst":
        start = text.index("// Decimal digits are the common case in every market/store record. Avoid a\n")
        end = text.index("function tradeInteger(string value) returns boolean\n", start)
        helper = text[start:end]
        require(helper.count("function tradeDecimalDigit(string character) returns int") == 1 and helper.count("\nfunction ") == 1,
                "Counterfactual helper scope")
        text = text[:start] + text[end:]
        before = "let digit=tradeDecimalDigit(SubString(value,i,i+1))"
        require(text.count(before) == 1, "Counterfactual digit call absent")
        text = text.replace(before, 'let digit="0123456789".indexOf(SubString(value,i,i+1))')
        require("tradeDecimalDigit" not in text, "Counterfactual helper still referenced")
    return text.encode()


def verify_builds(pack, dependency, original):
    prefix = "compiled-checks/"
    preparation = pack.read(prefix + "preparation-manifest.json")
    require(preparation["sourceIdentity"] == IDENTITY and preparation["schema"] == 17 and preparation["nativeStatus"] == "not_run", "Preparation source/scope")
    for name, row in preparation["scripts"].items():
        pack.bind(row, prefix + name)
    static = pack.read(prefix + "static-review.json")
    require(static["status"] == "pass_static_review" and static["sourceIdentity"] == IDENTITY and not static["blockingFindings"], "Compiled scripts static review")
    pack.bind(static["preparationManifest"], prefix + "preparation-manifest.json")
    pack.bind(static["readme"], prefix + "README.md")
    for name, row in static["reviewedScripts"].items():
        pack.bind(row, prefix + name)
    for name, row in preparation["frozenInputs"].items():
        if "copy" in row:
            pack.bind(row["copy"], prefix + "frozen/" + name)
            require(row["original"]["sha256"] == row["copy"]["sha256"], "Frozen input was changed")
    seed = pack.read(prefix + "europe-seed/seed-receipt.json")
    require(seed["status"] == "pass" and seed["sourceIdentityAtAssembly"] == IDENTITY and seed["schema"] == 17, "Europe seed")
    require(seed["dependencyInputs"] == dependency["files"], "Build/full-gate dependency mismatch")
    source_inputs = {}
    for name, digest in seed["compilerInputs"].items():
        if name in original and sha(original[name]) == digest:
            source_inputs[name] = original[name]
        else:
            path = prefix + "europe-seed/inputs/" + name
            source_inputs[name] = pack.data(path if pack.has(path) else prefix + "europe-seed/compile/" + name)
        require(sha(source_inputs[name]) == digest, "Generated Europe input mismatch: " + name)
    builds = {}
    for mode in ["baseline", "revised"]:
        base = prefix + mode + "/"
        build = pack.read(base + "build-result.json")
        require(build["format"] == "pr536_continuation_europe_compile_v1" and build["status"] == "pass" and build["mode"] == mode, "Build status")
        require(build["sourceIdentityAtAssembly"] == IDENTITY and build["sourceRevision"] == REVISION and build["schema"] == 17, "Build source/schema")
        require(build["nativeStatus"] == "not_run" and build["playerArtifactProduced"] is False, "Build scope")
        require(build["compilerSha256"] == COMPILER and build["dependencyRevision"] == DEPENDENCY and build["dependencyInstallInvoked"] is False, "Build pins")
        for flag in ["compilerInputsUnchangedDuringBuild", "independentKnownMembersEqual", "compilerOutputEqualsArchiveLua", "authoredSourcesUnchanged", "dependencyInputsUnchanged"]:
            require(build[flag] is True, "Build boundary: " + flag)
        require(build["typecheckExitCode"] == build["buildExitCode"] == 0 and not build.get("error"), "Build failed")
        pack.bind(build["seedReceipt"], prefix + "europe-seed/seed-receipt.json")
        inputs = pack.read(base + "inputs-before.json")
        require(inputs == pack.read(base + "inputs-after.json") == build["compilerInputs"], "Build inputs changed")
        require(build["wurstInputs"] == {n: v for n, v in inputs.items() if n.startswith("wurst/")}, "Build Wurst inventory")
        require(pack.read(base + "dependency-before.json") == seed["dependencyInputs"], "Build dependency inventory")
        require(build["generatedInputs"] == seed["generatedInputs"] and build["mapInputs"] == seed["mapInputs"], "Build map/scenario changed")
        changed = {name for name, value in inputs.items() if seed["compilerInputs"].get(name) != value}
        require(inputs.keys() == seed["compilerInputs"].keys() and changed == (CHANGED if mode == "baseline" else set()), "Build changed extra inputs")
        require({row["file"] for row in build["changedProductionInputs"]} == changed, "Counterfactual disclosure mismatch")
        expected_changes = []
        for name in sorted(CHANGED if mode == "baseline" else []):
            revised, baseline = source_inputs[name], revert_production(name, source_inputs[name])
            require(sha(baseline) == inputs[name], "Counterfactual bytes differ from reviewed reversal")
            expected_changes.append({"file": name, "before": sha(revised), "after": sha(baseline)})
        require(build["changedProductionInputs"] == expected_changes, "Counterfactual before/after declaration")
        for name, row in preparation["sourceVariants"].items():
            require(inputs[name] == row[mode + "Sha256"], "Prepared source variant mismatch")
        require([row["stage"] for row in build["stages"]] == ["typecheck", "build"], "Build stages")
        for stage in build["stages"]:
            pack.bind(stage["log"], base + stage["stage"] + ".log")
            text = pack.data(base + stage["stage"] + ".log").decode()
            require(stage["exitCode"] == 0 and stage["compiler"]["sha256"] == COMPILER, "Build compiler/exit")
            require(("Typecheck succeeded." if stage["stage"] == "typecheck" else "Map built.") in text, "Missing build completion")
            require(not re.search(r"(?m)(?:Exception in thread|\b[\w.$]*(?:Exception|Error):|^Error in File|No builtin function|Typecheck failed|Build failed)", text), "Compiler diagnostic")
        script = pack.data(base + "war3map.lua")
        require(sha(script) == build["compiledScriptSha256"] and len(script) == build["compiledScriptBytes"], "Actual archived Lua mismatch")
        pack.bind(build["extracted"]["war3map.lua"], base + "war3map.lua")
        for name, row in build["extracted"].items():
            pack.bind(row, base + name)
        require(preparation["frozenInputs"]["frozenPathing"] == static["frozenInputs"]["frozenPathing"], "Static/preparation pathing identity differs")
        require(preparation["frozenInputs"]["frozenPathing"]["sha256"] == WPM, "Frozen pathing pin differs")
        pack.bind(preparation["frozenInputs"]["frozenPathing"], base + "war3map.wpm")
        require(b"function MilitarySettlementRuntime_MilitarySettlementRuntime_validateSnapshot(" not in script, "Both arms must use current parse-once path")
        builds[mode] = build
    return builds


def verify_differential(pack, builds):
    base = "compiled-checks/trade-integer-differential/"
    receipt = pack.read(base + "receipt.json")
    require(receipt["status"] == "pass_under_explicit_models" and receipt["sourceRevision"] == REVISION and receipt["nativeStatus"] == "not_run", "Differential scope")
    require(receipt["productionFunctionOverrides"] is False and receipt["configOrMainExecuted"] is False and receipt["instructionBudgetPerState"] == 500_000_000, "Differential execution changed")
    cases, models = pack.read(base + "cases.json"), pack.read(base + "native-slice-models.json")
    require(len(cases) == 703 and len(models) == len(receipt["models"]) == 8, "Differential coverage")
    for name, target in [("cases", base + "cases.json"), ("sliceModels", base + "native-slice-models.json"), ("runner", "compiled-checks/trade_integer_differential.py")]:
        pack.bind(receipt["inputs"][name], target)
    for mode in builds:
        pack.bind(receipt["inputs"][mode + "Build"], "compiled-checks/" + mode + "/build-result.json")
    require({row["sliceModel"] for row in receipt["models"]} == set(models), "Missing differential model")
    for row in receipt["models"]:
        model, pair = row["sliceModel"], {}
        for mode in builds:
            path = base + model + "-" + mode + ".json"
            pack.bind(row["results"][mode], path)
            result = pack.read(path)
            function_count = len(re.findall(rb"^function ([A-Za-z_][A-Za-z0-9_]*)\(", pack.data("compiled-checks/" + mode + "/war3map.lua"), re.M))
            require(result["compiledFunctionsCheckedUnchanged"] == function_count > 0 and result["instructions"] <= 500_000_000, "Differential function/budget")
            require(row["substringCalls"][mode] == result["substringCalls"] and row["instructions"][mode] == result["instructions"], "Differential measured values")
            pair[mode] = result["results"]
        require(pair["baseline"] == pair["revised"] and row["exactBooleanResultsEqual"] is True and row["status"] == "pass" and row["cases"] == 703, "Differential boolean mismatch")
        require([v["id"] for v in pair["revised"]] == [v["id"] for v in cases], "Differential case order")
        require(sha(canonical(pair["revised"])) == row["outputsSha256"], "Differential output hash")
        if model in {"raw_byte_slices", "invalid_slice_to_replacement_marker"}:
            expected = []
            for case in cases:
                value = bytes.fromhex(case["valueHex"])
                accepted = bool(re.fullmatch(rb"(?:0|[1-9][0-9]*|-[1-9][0-9]*)", value)) and -2147483648 <= int(value) <= 2147483647
                require(case["canonicalAsciiExpected"] == accepted, "ASCII oracle corpus mismatch")
                expected.append(accepted)
            require([v["accepted"] for v in pair["revised"]] == expected and row["canonicalAsciiOracleChecked"] is True, "ASCII oracle result mismatch")


def verify_catalogue_adaptation(pack, builds, project):
    """Bind the source-derived count and reviewed copies without running them."""
    base = "compiled-checks/"
    proof = pack.read(base + "catalogue-cardinality.json")
    require(proof["format"] == "pr536_current_catalogue_cardinality_v1" and
            proof["status"] == "pass_static_source_derivation" and proof["sourceIdentity"] == IDENTITY,
            "Current catalogue proof source/status")
    require(proof["schema"] == 17 and proof["nativeStatus"] == "not_run" and
            proof["nativeHangResolution"] == "not_established", "Catalogue proof scope")
    require(proof["validationPerformed"]["staticSourceDerivation"] is True and
            all(proof["validationPerformed"][key] is False for key in
                ["testExecution", "modelExecution", "buildExecution", "sourceEdits"]), "Catalogue proof execution scope")
    generated_name = base + "europe-seed/inputs/wurst/ScenarioData.wurst"
    if not pack.has(generated_name):
        generated_name = base + "europe-seed/compile/wurst/ScenarioData.wurst"
    for key, name in [("generatedScenario", generated_name), ("runner", base + "catalogue-cardinality.py"),
                      ("baselineBuild", base + "baseline/build-result.json"), ("revisedBuild", base + "revised/build-result.json")]:
        pack.bind(proof["inputs"][key], name)
    source_names = {"../_shared/wurst/CampaignRegistration.wurst", "../_shared/wurst/PlayableTrade.wurst",
                    "scenario/economy/global-goods.json", "scenario/economy/playable-trade.json",
                    "scenario/progression/gameplay-effect-design.json", "scenario/progression/industry.json",
                    "scenario/world/world.json", "tooling/industry_catalog.py"}
    source_names |= {"scenario/settlements/" + name + "-1450.json" for name in
                     ["africa", "americas-caribbean", "east-asia", "europe", "middle-east-india", "pacific", "southeast-asia"]}
    require(set(proof["sourceInputs"]) == source_names, "Catalogue authority inputs changed")
    source_data = {}
    for relative, row in proof["sourceInputs"].items():
        # These two explicit shared-source paths are the only permitted '..'.
        # Recorded old absolute paths remain provenance and are never followed.
        path = checked_path(project / relative)
        require(path.resolve().is_relative_to(project.parents[2]), "Catalogue authority escaped source checkout")
        source_data[relative] = file_bytes(path)
        require(sha(source_data[relative]) == row["sha256"] and len(source_data[relative]) == row["bytes"],
                "Catalogue source input mismatch: " + relative)
    generated = pack.data(generated_name)
    require(all(build["compilerInputs"]["wurst/ScenarioData.wurst"] == sha(generated) for build in builds.values()),
            "Catalogue derivation is not bound to both compiled inputs")
    functions = {}
    for part in re.split(r"(?m)^(?:public )?function ", generated.decode())[1:]:
        name = part.split("(", 1)[0]
        require(name not in functions, "Duplicate generated function")
        functions[name] = part
    pairs = lambda text: re.findall(r'runtime\.registerMarketProfile\("([^"]+)",\s*"([^"]+)"', text)
    inventory = {name: pairs(text) for name, text in functions.items() if pairs(text)}
    trade_names = ["configureGeneratedTrade" + str(i) for i in range(62)]
    require(set(inventory) == set(trade_names) | {"configureGeneratedIndustryMarkets"}, "Unexpected market registration path")
    require(proof["tradeConfigurationFunctions"] == trade_names and
            re.findall(r"\b(configureGeneratedTrade[0-9]+)\(runtime\)", functions["configureGeneratedTrade"]) == trade_names,
            "Generated base market registration order")
    original_pairs = [pair for name in trade_names for pair in inventory[name]]
    industry_pairs = inventory["configureGeneratedIndustryMarkets"]
    conditional = re.findall(r'if runtime\.findMarket\("([^"]+)",\s*"([^"]+)"\) == null\n\s+runtime\.registerMarketProfile\("([^"]+)",\s*"([^"]+)"',
                             functions["configureGeneratedIndustryMarkets"])
    require([(a, b) for a, b, c, d in conditional if (a, b) == (c, d)] == industry_pairs,
            "Industry registrations must only add absent market pairs")
    added, combined = sorted(set(industry_pairs) - set(original_pairs)), sorted(set(original_pairs) | set(industry_pairs))
    require(len(original_pairs) == len(set(original_pairs)) == proof["baseMarketCount"] == proof["historicalMarketCount"] == 8422,
            "Historical base catalogue changed")
    require(len(industry_pairs) == len(set(industry_pairs)) == proof["industryMarketDefinitions"] == 20 and
            [list(pair) for pair in industry_pairs] == proof["industryMarketPairs"], "Industry catalogue proof mismatch")
    require(added == [(city, "iron_goods") for city in ["milan", "nuremberg", "stockholm", "vienna"]] and
            [list(pair) for pair in added] == proof["industryAddedMarkets"] and len(added) == proof["industryAddedMarketCount"] == 4,
            "Current market additions differ")
    require(len(combined) == proof["marketCount"] == 8426 and proof["lastMarketIndex"] == 8425,
            "Current source market count/index mismatch")
    require(sha(canonical(original_pairs)) == proof["baseMarketIdentitySha256"] and
            sha(canonical(combined)) == proof["combinedMarketIdentitySha256"], "Catalogue pair identity mismatch")
    registration = source_data["../_shared/wurst/CampaignRegistration.wurst"].decode()
    registration_calls = ["configureGeneratedTrade(trade)", "configureGeneratedIndustryMarkets(trade)"]
    require(all(registration.count(call) == 1 for call in registration_calls) and
            registration.index(registration_calls[0]) < registration.index(registration_calls[1]) and
            proof["registrationOrder"] == ["configureGeneratedTrade", "configureGeneratedIndustryMarkets"], "Authored registration order")
    stores = sum(functions[name].count("runtime.registerStore(") for name in trade_names)
    personal = sum(functions[name].count("runtime.registerPersonalStore()") for name in trade_names)
    require(stores == 828 and personal == 1 and proof["storeCount"] == stores + personal == 829 and
            proof["lastStoreIndex"] == 828, "Unchanged current store count/index")

    prepared, review = pack.read(ADAPTATION + "preparation-receipt.json"), pack.read(ADAPTATION + "static-review.json")
    require(prepared["format"] == "pr536_current_catalogue_adaptation_preparation_v1" and
            prepared["status"] == "prepared_for_review_not_executed" and prepared["sourceIdentity"] == IDENTITY and
            prepared["schema"] == 17 and prepared["nativeStatus"] == "not_run", "Adaptation preparation scope")
    require(set(prepared["adaptedFiles"]) == {"README.md", "compare_completed_startup.py", "preparation-transformations.json",
            "full-scale-roundtrip-current-catalogue.lua", "verify-trade-full-scale-current-catalogue.py", "run_full_scale_current_catalogue.py"},
            "Adaptation file scope changed")
    require(set(prepared["patches"]) == {"full-scale-case.patch", "full-scale-runner.patch", "full-scale-wrapper.patch", "startup-comparison.patch"},
            "Adaptation literal patch scope changed")
    for group, prefix in [("retainedInputs", base), ("adaptedFiles", ADAPTATION), ("patches", ADAPTATION)]:
        for name, row in prepared[group].items():
            pack.bind(row, prefix + Evidence.safe(name))
    pack.bind(prepared["catalogueCardinality"], base + "catalogue-cardinality.json")
    pack.bind(prepared["originalFailedComparison"], base + "startup-comparison/comparison.json")
    require(prepared["frozenInputs"] == pack.read(base + "preparation-manifest.json")["frozenInputs"], "Adaptation changed frozen inputs")
    require(all(prepared["validationPerformed"][key] is False for key in
                ["compilerExecution", "derivedComparisonExecution", "fullScaleExecution", "modelExecution", "startupReexecution"]),
            "Preparation execution scope")
    require(review["status"] == "pass_static_review" and review["blockingFindings"] == [] and review["sourceIdentity"] == IDENTITY and
            review["nativeStatus"] == "not_run" and review["nativeHangResolution"] == "not_established", "Adaptation review incomplete")
    for key, name in [("preparationReceipt", ADAPTATION + "preparation-receipt.json"), ("catalogueCardinality", base + "catalogue-cardinality.json"),
                      ("cardinalityDerivationScript", base + "catalogue-cardinality.py"), ("reviewedReadme", ADAPTATION + "README.md"),
                      ("reviewedCase", ADAPTATION + "full-scale-roundtrip-current-catalogue.lua"),
                      ("transformations", ADAPTATION + "preparation-transformations.json")]:
        pack.bind(review[key], name)
    require(set(review["reviewedScripts"]) == {"compare_completed_startup.py", "run_full_scale_current_catalogue.py",
            "verify-trade-full-scale-current-catalogue.py"} and review["reviewedPatches"] == prepared["patches"], "Adaptation review scope")
    for name, row in review["reviewedScripts"].items():
        pack.bind(row, ADAPTATION + name)
    require(all(review["validationPerformed"][key] is False for key in
                ["testExecution", "modelExecution", "buildExecution", "derivedComparisonExecution", "fullScaleExecution",
                 "nativeExecution", "packingExecution", "projectEdits", "startupReexecution"]), "Adaptation review must remain static")
    changes = pack.read(ADAPTATION + "preparation-transformations.json")
    require(changes["execution"] is False and changes["nativeStatus"] == "not_run", "Literal transformation scope")
    pairs_to_change = [("8422", "8426"), ("8421", "8425")]
    expected_counts = {"case": {"8422_to_8426": 7, "8421_to_8425": 9}, "runner": {"8422_to_8426": 1, "8421_to_8425": 0}}
    expected_bindings = [
        {"before": "ROOT = Path(__file__).resolve().parent", "after": "ROOT = Path(" + repr(str(Path(changes["runner"]["original"]["path"]).parent)) + ")"},
        {"before": "SOURCE_SHA = '0730e299ae8fa093e317bb586f7b0992dd30e8ca86082be84637653c3865ecda'",
         "after": "SOURCE_SHA = " + repr(builds["revised"]["wurstInputs"]["wurst/PlayableTrade.wurst"])},
        {"before": "case = ROOT / 'full-scale-roundtrip.lua'", "after": "case = Path(" + repr(changes["case"]["adapted"]["path"]) + ")"},
    ]
    require(prepared["bindingChanges"] == changes["runner"]["bindings"] == expected_bindings, "Adapted runner bindings changed")
    for kind, old, new in [("case", base + "frozen/full-scale-roundtrip.lua", ADAPTATION + "full-scale-roundtrip-current-catalogue.lua"),
                           ("runner", base + "frozen/verify-trade-full-scale-original.py", ADAPTATION + "verify-trade-full-scale-current-catalogue.py")]:
        pack.bind(changes[kind]["original"], old)
        pack.bind(changes[kind]["adapted"], new)
        text, counts = pack.data(old).decode(), {}
        if kind == "runner":
            for change in expected_bindings:
                require(text.count(change["before"]) == 1, "Missing original full-scale binding")
                text = text.replace(change["before"], change["after"])
        for before, after in pairs_to_change:
            text, count = re.subn(r"\b" + before + r"\b", after, text)
            counts[before + "_to_" + after] = count
        require(counts == changes[kind]["wholeTokenReplacements"] == expected_counts[kind] ==
                prepared[kind + "WholeTokenReplacements"], "Full-scale count replacement scope")
        require(text.encode() == pack.data(new), "Full-scale copy changed beyond reviewed bindings/counts")
    require(prepared["assertionChange"] == {"marketCount": {"before": 8422, "after": 8426}, "lastMarketIndex": {"before": 8421, "after": 8425},
            "storeCount": 829, "lastStoreIndex": 828}, "Adaptation changed additional count assertions")
    require(not pack.has("compiled-checks/full-scale-revised/receipt.json") and not pack.has("compiled-checks/full-scale-revised/result.json"),
            "Original full-scale stage was never run; preserve that absence")
    return proof, prepared, changes


def verify_startup(pack, builds, catalogue):
    base = "compiled-checks/startup-comparison/"
    failed = pack.read(base + "comparison.json")
    require(failed["status"] == "fail" and failed["error"] == "AssertionError: " and
            failed["sourceRevision"] == REVISION and failed["schema"] == 17, "Original stale-count failure was not preserved")
    pack.bind(failed["runner"], "compiled-checks/compare_startup.py")
    failure_log = pack.data(DRIVER + "05-startup-comparison.log").decode()
    require('assert new["runtimeCounts"]["markets"] == 8422 and new["runtimeCounts"]["stores"] == 829' in failure_log
            and failure_log.rstrip().endswith("AssertionError"), "Original failure transcript is not the stale exact-count assertion")
    comparison = pack.read(CURRENT_COMPARISON)
    require(comparison["format"] == "pr536_current_catalogue_retained_startup_comparison_v1" and
            comparison["modelExecutedByThisDerivation"] is False and comparison["allOtherOriginalComparisonConditionsRetained"] is True,
            "Current comparison must derive only from retained completed models")
    for key, name in [("runner", ADAPTATION + "compare_completed_startup.py"), ("originalFailedComparison", base + "comparison.json"),
                      ("adaptationPreparation", ADAPTATION + "preparation-receipt.json"), ("adaptationReview", ADAPTATION + "static-review.json"),
                      ("catalogueCardinality", "compiled-checks/catalogue-cardinality.json")]:
        pack.bind(comparison[key], name)
    require(comparison["assertionChanges"] == [{"field": "runtimeCounts.markets", "historical": 8422,
            "currentSourceExpectation": catalogue["marketCount"]}], "Startup count assertion adaptation changed")
    require(comparison["runtimeCounts"]["markets"] == catalogue["marketCount"] == 8426 and
            comparison["runtimeCounts"]["stores"] == catalogue["storeCount"] == 829, "Startup count differs from current source derivation")
    require(comparison["status"] == "pass_under_explicit_models" and comparison["sourceRevision"] == REVISION and comparison["schema"] == 17, "Startup comparison scope/source")
    require(comparison["nativeStatus"] == "not_run" and comparison["nativeHangResolution"] == "not_established", "Unsupported native conclusion")
    require(comparison["frozenInputs"] == failed["frozenInputs"] == pack.read("compiled-checks/preparation-manifest.json")["frozenInputs"],
            "Startup derivation changed frozen inputs")
    for key in ["baselineMeaning", "historicalCounts", "limitations", "observerVariant", "nativeStatus", "nativeHangResolution"]:
        require(comparison[key] == failed[key], "Startup derivation changed original scope: " + key)
    require(len(comparison["cachePayloads"]) == 4, "Payload comparison incomplete")
    frozen, observed, payloads = {}, {}, {}
    for mode, build in builds.items():
        prefix = base + mode + "/"
        run, report = pack.read(prefix + "frozen/result.json"), pack.read(prefix + "observer/startup-and-first-callbacks.json")
        frozen[mode], observed[mode], payloads[mode] = run, report, []
        build_path = "compiled-checks/" + mode + "/build-result.json"
        pack.bind(comparison[mode + "Build"], build_path)
        pack.bind(comparison["retainedResults"][mode]["frozen"], prefix + "frozen/result.json")
        pack.bind(comparison["retainedResults"][mode]["observer"], prefix + "observer/startup-and-first-callbacks.json")
        pack.bind(run["boundBuildReceipt"], build_path)
        pack.bind(run["runner"], "compiled-checks/compare_startup.py")
        require(run["status"] == "completed_under_stubs" and run["completed"] is True and run["campaignStarted"] and run["campaignRegistered"], "Frozen startup incomplete")
        require(run["nativeStatus"] == "not_run" and run["runtimeVersion"] == "Lua 5.3" and run["instructions"] <= run["instructionBudget"] == 2_000_000_000, "Frozen runtime/scope/budget")
        require(run["compiledLuaSha256"] == build["compiledScriptSha256"], "Frozen compiled script mismatch")
        pack.bind(run["tradeSnapshotIdentity"], prefix + f"frozen/europe_central_east-{mode}-trade-snapshot.txt")
        require(run["harnessSha256"] == sha(pack.data("compiled-checks/frozen/probe-lua54-initialization.py")) and
                run["lateNativeStubsSha256"] == sha(pack.data("compiled-checks/frozen/late-startup-stubs.lua")), "Frozen model input mismatch")
        require(report["status"] == "completed_under_explicit_stubs" and report["nativeStatus"] == "not_run", "Observer scope")
        for key, path in [("buildReceipt", build_path), ("compiledLua", "compiled-checks/" + mode + "/war3map.lua"),
                          ("harness", prefix + "frozen/probe-lua54-initialization.py"), ("nativeStubs", prefix + "frozen/late-startup-stubs.lua"),
                          ("observer", prefix + "observer/observe-startup.lua"), ("runner", prefix + "observer/observe-startup.py")]:
            pack.bind(report["inputs"][key], path)
        for local, common in [("frozen/probe-lua54-initialization.py", "probe-lua54-initialization.py"),
                              ("frozen/late-startup-stubs.lua", "late-startup-stubs.lua"), ("observer/observe-startup.lua", "observe-startup.lua")]:
            require(pack.data(prefix + local) == pack.data("compiled-checks/frozen/" + common), "Startup model differs between arms or from frozen input")
        runner = pack.data("compiled-checks/frozen/observe-startup-template.py").decode()
        substitutions = {
            "OUT=ROOT/'validation-536/native-boundary-audit/europe-repair/observer'": "OUT=Path(" + repr(str(Path(report["inputs"]["runner"]["path"]).parent)) + ")",
            "EVIDENCE=ROOT/'WarCraftMap/maps/historical-world-rpg/age-of-sail-world/reports/issue-438/trade-startup'": "EVIDENCE=Path(" + repr(str(Path(report["inputs"]["harness"]["path"]).parent)) + ")",
            "SCRIPT=ROOT/'validation-536/native-boundary-audit/europe-repair/war3map.lua'": "SCRIPT=Path(" + repr(report["inputs"]["compiledLua"]["path"]) + ")",
            "RECEIPT=ROOT/'validation-536/native-boundary-audit/europe-repair/build-result.json'": "RECEIPT=Path(" + repr(report["inputs"]["buildReceipt"]["path"]) + ")",
        }
        for before, after in substitutions.items():
            require(runner.count(before) == 1, "Observer path binding absent")
            runner = runner.replace(before, after)
        require(runner.encode() == pack.data(prefix + "observer/observe-startup.py"), "Observer runner changed beyond four paths")
        require(report["inputs"]["library"]["sha256"] == LIBRARY, "Observer Lua library")
        execution = report["execution"]
        require(execution["startupCompleted"] is True and execution["startup"]["started"] and execution["startup"]["registered"], "Observer startup incomplete")
        require(execution["startup"]["nativeCalls"] == run["nativeCalls"], "Frozen/observer startup counters differ")
        phase = execution["callbackPhase"]
        require(phase["completed"] and phase["callbackCount"] == len(execution["callbacks"]) == 37 and phase["throughSeconds"] == 1.001, "Callback scope")
        require(phase["instructions"] <= phase["budget"] == 200_000_000 and not execution["callbackErrors"] and
                all(row["completed"] is True for row in execution["callbacks"]), "Callback error/budget")
        require(len(report["cachePayloads"]) == 4, "Missing observer payload")
        for index, row in enumerate(report["cachePayloads"], 1):
            path = prefix + f"observer/cache-write-{index}.txt.gz"
            pack.bind(row["compressed"], path)
            payload = gzip.decompress(pack.data(path))
            require(len(payload) == row["bytes"] and sha(payload) == row["sha256"], "Decompressed payload mismatch")
            payloads[mode].append(payload)
        require(comparison["callbackPhases"]["before" if mode == "baseline" else "after"] == phase, "Callback receipt differs")
        arm = "before" if mode == "baseline" else "after"
        phase_names = {"PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState",
                       "PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState",
                       "MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot", "runtimeChecksum"}
        selected_phases = [{key: row[key] for key in ["name", "nativeCalls", "instructions", "completed"]}
                           for row in execution["phases"] if row["name"] in phase_names]
        require(comparison["phases"][arm] == selected_phases and
                comparison["nativeArgumentVolumes"][arm] == execution["nativeArgumentVolumes"], "Derived phase/native argument evidence differs")
    require(payloads["baseline"] == payloads["revised"], "Saved payload bytes changed")
    for index, row in enumerate(comparison["cachePayloads"], 1):
        left, right = [observed[mode]["cachePayloads"][index - 1] for mode in ["baseline", "revised"]]
        data = payloads["revised"][index - 1]
        require(row["index"] == index and row["exactBaselineBytesEqual"] is True, "Payload equality receipt")
        require((left["mission"], left["key"]) == (right["mission"], right["key"]) == (row["mission"], row["key"]), "Payload order/key")
        require(row["bytes"] == len(data) and row["sha256"] == sha(data), "Payload comparison digest")
        for mode in builds:
            pack.bind(row[mode + "Compressed"], base + mode + f"/observer/cache-write-{index}.txt.gz")
    require(comparison["cachePayloadBytesTotal"] == sum(map(len, payloads["revised"])), "Payload byte total")
    old, new = frozen["baseline"], frozen["revised"]
    for field in ["runtimeCounts", "tradeSnapshotIdentity", "finalCacheRequest"]:
        require(old[field] == new[field] == comparison[field], "Startup authority changed: " + field)
    calls = {n: {"before": old["nativeCalls"].get(n, 0), "after": new["nativeCalls"].get(n, 0),
                 "difference": new["nativeCalls"].get(n, 0) - old["nativeCalls"].get(n, 0)}
             for n in sorted(set(old["nativeCalls"]) | set(new["nativeCalls"]))}
    require(calls == comparison["nativeCalls"] and calls["SubString"]["difference"] < 0, "Startup work comparison")
    require(comparison["instructionSamples"] == {"before": old["instructions"], "after": new["instructions"]} ==
            {"before": 875150000, "after": 834300000}, "Startup sampled instruction values")
    require(calls["SubString"] == {"before": 10060261, "after": 9298589, "difference": -761672} and
            calls["StringLength"] == {"before": 2042487, "after": 1527363, "difference": -515124}, "Startup measured native-call values")
    sequence = lambda report: [{k: row[k] for k in ["atSeconds", "kind", "completed"]} for row in report["execution"]["callbacks"]]
    result = {"callbackSequenceEqual": sequence(observed["baseline"]) == sequence(observed["revised"]),
              "nonTargetStartupNativeCallDeltas": {n: row["difference"] for n, row in calls.items() if n != "SubString" and row["difference"]},
              "savedPayloadsCompared": 4, "cachePayloadBytesTotal": comparison["cachePayloadBytesTotal"]}
    review = pack.read("compiled-checks/model-review.json")
    require(review["status"] == "pass_scoped_model_review" and review["sourceIdentity"] == IDENTITY, "Model review missing/source mismatch")
    require(review["nativeStatus"] == "not_run" and review["nativeHangResolution"] == "not_established"
            and review["nativeParityClaimed"] is False and review["timingSpeedupClaimed"] is False, "Model review overclaims native or timing parity")
    require(review["callbackSequenceFields"] == ["atSeconds", "kind", "completed"] and
            review["callbackSequenceEqual"] == result["callbackSequenceEqual"] is True, "Callback sequence was not equal and explicitly reviewed")
    require(review["nonTargetStartupNativeCallDeltas"] == result["nonTargetStartupNativeCallDeltas"], "Unreviewed non-target native-call delta")
    require(result["nonTargetStartupNativeCallDeltas"] == {"StringLength": -515124} and
            review["startupNativeCallDeltas"] == {name: row["difference"] for name, row in calls.items() if row["difference"]} and
            review["otherStartupNativeCallCountsEqual"] is True, "Unexpected additional startup native delta")
    for key, path in [("comparison", CURRENT_COMPARISON), ("baselineObserver", base + "baseline/observer/startup-and-first-callbacks.json"),
                      ("revisedObserver", base + "revised/observer/startup-and-first-callbacks.json"), ("baselineFrozen", base + "baseline/frozen/result.json"),
                      ("revisedFrozen", base + "revised/frozen/result.json")]:
        pack.bind(review["inputs"][key], path)
    pack.bind(review["catalogueCardinality"], "compiled-checks/catalogue-cardinality.json")
    pack.bind(review["originalFailedComparison"], base + "comparison.json")
    require(review["cachePayloadBytesTotal"] == comparison["cachePayloadBytesTotal"] == 3203778 and
            review["runtimeCounts"] == comparison["runtimeCounts"], "Scoped model review count/payload claim")
    for mode in builds:
        pack.bind(review["compiledLuaInputs"][mode], "compiled-checks/" + mode + "/war3map.lua")
    require(review["sameFrozenObservationFields"] == ["camera", "messages", "syntheticUnitCount", "syntheticQuestCount",
            "syntheticRegionCount", "timerRegistrations", "campaignRegistered", "campaignStarted", "finalCacheRequest",
            "runtimeCounts", "tradeSnapshotIdentity"], "Reviewed frozen observation scope changed")
    require(all(old[key] == new[key] for key in review["sameFrozenObservationFields"]), "Reviewed frozen observation differs")
    callback_rows = [observed[mode]["execution"]["callbacks"] for mode in ["baseline", "revised"]]
    native_equal = all(left["nativeCalls"] == right["nativeCalls"] for left, right in zip(*callback_rows))
    instruction_equal = all(left["instructions"] == right["instructions"] for left, right in zip(*callback_rows))
    require(review["allCallbackNativeCallMapsEqual"] == native_equal is True and
            review["allCallbackInstructionSamplesEqual"] == instruction_equal is True and
            review["callbackCount"] == 37 and review["throughSyntheticSeconds"] == 1.001,
            "Reviewed callback native/instruction trace differs")
    require(all(report["execution"]["callbackPhase"]["instructions"] == review["callbackInstructionSamplesPerArm"] == 14710000
                for report in observed.values()), "Reviewed callback phase samples differ")
    shifts = []
    scripts = {mode: pack.data("compiled-checks/" + mode + "/war3map.lua").decode().splitlines() for mode in builds}
    for index, (left, right) in enumerate(zip(*callback_rows), 1):
        left_stable = {key: value for key, value in left.items() if key not in {"cpuSeconds", "callbackDefinedLine"}}
        right_stable = {key: value for key, value in right.items() if key not in {"cpuSeconds", "callbackDefinedLine"}}
        require(left_stable == right_stable, "Callback changed beyond CPU sample/compiler line")
        if left.get("callbackDefinedLine") != right.get("callbackDefinedLine"):
            before, after = left["callbackDefinedLine"], right["callbackDefinedLine"]
            # Root's explicit review hashes the same three LF-joined source
            # lines without a terminal newline. No function execution occurs.
            bodies = ["\n".join(scripts[mode][line - 1:line + 2]) for mode, line in [("baseline", before), ("revised", after)]]
            require(bodies[0] == bodies[1] and bodies[0].startswith("function __wurst_callback_bridge_onGodModeEntityEvent(") and
                    bodies[0].rstrip().endswith("end"), "Shifted callback is not the identical compiled bridge")
            shifts.append({"callbackIndex": index, "before": before, "after": after,
                           "sameCompiledFunction": "__wurst_callback_bridge_onGodModeEntityEvent", "functionBodySha256": sha(bodies[0].encode())})
    require(review["compilerLineShifts"] == shifts and review["ignoredComparisonFields"] == ["cpuSeconds"], "Unreviewed callback line shift")
    for index, row in enumerate(review["savedPayloads"], 1):
        comparison_row = comparison["cachePayloads"][index - 1]
        require(row == {key: comparison_row[key] for key in ["bytes", "index", "key", "mission", "sha256"]} | {"exactBytesEqual": True},
                "Reviewed saved payload claim differs")
    require(len(review["savedPayloads"]) == 4 and all(review["validationPerformed"][key] is False for key in
                ["testExecution", "modelExecution", "buildExecution", "sourceEdits"]), "Model review execution scope")
    return result


def verify_full_scale(pack, builds, catalogue, changes):
    base = CURRENT_FULL_SCALE
    receipt, result = pack.read(base + "receipt.json"), pack.read(base + "result.json")
    require(receipt["format"] == "pr536_continuation_current_catalogue_full_scale_binding_v1", "Current full-scale wrapper format")
    require(receipt["status"] == result["status"] == "pass_full_scale_roundtrip_under_explicit_stubs", "Full-scale result failed")
    require(receipt["nativeStatus"] == result["nativeStatus"] == "not_run" and receipt["sourceRevision"] == REVISION, "Full-scale scope/source")
    for flag in ["nativeStubsChanged", "budgetsChanged", "productionFunctionOverrides", "playerArtifactProduced"]:
        require(receipt[flag] is False, "Full-scale changed scope: " + flag)
    require(receipt["fullScaleLuaCaseChanged"] is True and receipt["allOtherFullScaleAssertionsUnchanged"] is True and
            receipt["fullScaleCaseChangeScope"] == "Only whole-token 8422 to 8426 and 8421 to 8425", "Full-scale adaptation scope")
    require(receipt["exitCode"] == 0 and result["productionFunctionOverrides"] is False and result["compiledFunctionsCheckedUnchanged"] > 0, "Full-scale execution/function identity")
    pack.bind(receipt["log"], base + "execution.log")
    pack.bind(receipt["result"], base + "result.json")
    for key, name in [("runner", ADAPTATION + "run_full_scale_current_catalogue.py"),
                      ("boundRunner", ADAPTATION + "verify-trade-full-scale-current-catalogue.py"),
                      ("retainedRunner", "compiled-checks/frozen/verify-trade-full-scale-original.py"),
                      ("retainedCase", "compiled-checks/frozen/full-scale-roundtrip.lua"),
                      ("adaptedCase", ADAPTATION + "full-scale-roundtrip-current-catalogue.lua"),
                      ("catalogueCardinality", "compiled-checks/catalogue-cardinality.json"),
                      ("adaptationPreparation", ADAPTATION + "preparation-receipt.json"),
                      ("adaptationReview", ADAPTATION + "static-review.json"), ("startupComparison", CURRENT_COMPARISON),
                      ("compiledScript", "compiled-checks/revised/war3map.lua"), ("buildReceipt", "compiled-checks/revised/build-result.json")]:
        pack.bind(receipt[key], name)
    require(receipt["bindingChanges"] == changes["runner"]["bindings"] and
            receipt["caseWholeTokenReplacements"] == changes["case"]["wholeTokenReplacements"] and
            receipt["runnerWholeTokenReplacements"] == changes["runner"]["wholeTokenReplacements"], "Full-scale declared literal changes")
    require(receipt["frozenInputs"] == pack.read("compiled-checks/preparation-manifest.json")["frozenInputs"], "Full-scale frozen inputs changed")
    pack.bind(result["inputs"]["compiledLua"], "compiled-checks/revised/war3map.lua")
    pack.bind(result["inputs"]["buildReceipt"], "compiled-checks/revised/build-result.json")
    for mode in ["baseline", "revised"]:
        pack.bind(result["inputs"]["pathing"], "compiled-checks/" + mode + "/war3map.wpm")
    for key, path in [("frozenHarness", "compiled-checks/frozen/probe-lua54-initialization.py"),
                      ("frozenNativeStubs", "compiled-checks/frozen/late-startup-stubs.lua"),
                      ("roundtripHarness", ADAPTATION + "verify-trade-full-scale-current-catalogue.py"),
                      ("roundtripCase", ADAPTATION + "full-scale-roundtrip-current-catalogue.lua")]:
        pack.bind(result["inputs"][key], path)
    function_count = len(re.findall(rb"^function ([A-Za-z_][A-Za-z0-9_]*)\(", pack.data("compiled-checks/revised/war3map.lua"), re.M))
    require(result["compiledFunctionsCheckedUnchanged"] == function_count > 0, "Full-scale function identity count")
    require(result["inputs"]["productionSourceSha256"] == builds["revised"]["wurstInputs"]["wurst/PlayableTrade.wurst"], "Full-scale production source")
    require(result["runtimeLibrary"]["sha256"] == LIBRARY and result["runtimeVersion"] == "Lua 5.3", "Full-scale library")
    require(result["instructionBudgetPerPhase"] == receipt["instructionBudgetPerPhase"] == 2_000_000_000, "Full-scale budget")
    phases = result["execution"]["phases"]
    require(set(phases) == {"startup", "roundtrip"} and all(p["completed"] is True and p["instructions"] <= 2_000_000_000 and not p.get("budgetExhausted") for p in phases.values()), "Full-scale phases")
    row = result["execution"]["roundtrip"]
    require(row["marketCount"] == row["mutatedMarkets"] == catalogue["marketCount"] == 8426 and
            row["storeCount"] == row["populatedStores"] == row["mutatedStores"] == catalogue["storeCount"] == 829, "Full-scale cardinality")
    require(row["populatedLots"] == row["clearedLots"] == row["restoredLots"] == 829, "Full-scale provenance")
    require(all(row[n] is True for n in ["reconstructReturned", "exactCaptureEquality", "selectionRestored", "catalogueOrderRestored"]), "Full-scale restoration")
    require(len(phases["roundtrip"]["stages"]) == 5 and all(p["completed"] is True for p in phases["roundtrip"]["stages"]), "Full-scale stage completion")
    require(result["captures"]["saved"] == result["captures"]["restored"] != result["captures"]["mutated"], "Full-scale captured identities")


def verify_compiled_driver(pack):
    driver, checkpoint = pack.read(DRIVER + "run-metadata.json"), pack.read("compiled-checks/workflow-state.json")
    require(driver["format"] == "pr536_compiled_sequence_driver_v1" and
            checkpoint["format"] == "pr536_compiled_workflow_checkpoint_v1", "Compiled workflow provenance format")
    for receipt in [driver, checkpoint]:
        require(receipt["status"] == "completed" and
                receipt["validationStatus"] == "pass_under_explicit_models_after_reviewed_catalogue_adaptation" and
                receipt["nativeStatus"] == "not_run" and receipt["nativeHangResolution"] == "not_established" and
                receipt["noActiveJvms"] is True and receipt["noActiveModels"] is True, "Compiled workflow incomplete/scope changed")
        pack.bind(receipt["fullGateReceipt"], "full-attempt1/receipt.json")
    require(driver["sourceIdentity"] == driver["sourceIdentityAtStop"] == driver["sourceIdentityAtCompletion"] == IDENTITY and
            checkpoint["sourceRevision"] == REVISION, "Compiled workflow source identity")
    require(driver["reviewedScriptsUnchanged"] is True and driver["frozenInputsUnchanged"] is True, "Compiled workflow inputs changed")
    require(checkpoint["currentStage"] == "complete" and checkpoint["currentStageStatus"] == "pass_under_explicit_models" and
            checkpoint["remainingStages"] == [] and all(checkpoint[key] is None for key in
                ["activeInternalReceipt", "activeOuterLog", "activeToolSessionId"]), "Compiled workflow still active")
    for key, name in [("fullGateResults", "full-attempt1/results.json"), ("preparationManifest", "compiled-checks/preparation-manifest.json"),
                      ("staticReview", "compiled-checks/static-review.json"), ("resumptionPreparation", ADAPTATION + "preparation-receipt.json"),
                      ("resumptionReview", ADAPTATION + "static-review.json")]:
        pack.bind(driver[key], name)
    stages = [("prepare", "compiled-checks/europe-seed/seed-receipt.json"),
              ("baseline", "compiled-checks/baseline/build-result.json"), ("revised", "compiled-checks/revised/build-result.json"),
              ("integer-differential", "compiled-checks/trade-integer-differential/receipt.json"),
              ("startup-comparison", "compiled-checks/startup-comparison/comparison.json"),
              ("startup-current-catalogue", CURRENT_COMPARISON), ("full-scale-current-catalogue", CURRENT_FULL_SCALE + "receipt.json")]
    require(driver["stages"] == checkpoint["completedStages"] and len(driver["stages"]) == len(stages), "Compiled stage history changed")
    for number, ((name, receipt_name), row) in enumerate(zip(stages, driver["stages"]), 1):
        require(row["number"] == number and row["name"] == name and
                row["status"] == ("fail" if number == 5 else "pass") and row["exitCode"] == (1 if number == 5 else 0),
                "Original failed stage or terminal sequence was rewritten")
        if number > 1:
            require(row["sourceIdentity"] == IDENTITY, "Compiled stage source identity")
        # Stage 1 has no separate source field; its bound seed receipt's exact
        # sourceIdentityAtAssembly is already checked by verify_builds.
        pack.bind(row["outerLogIdentity"], DRIVER + f"{number:02d}-{name}.log")
        pack.bind(row["receipt"], receipt_name)
    require(driver["stages"][5]["modelReexecution"] is False, "Current catalogue comparison reran startup")
    require(len(driver["preservedFailures"]) == 1 and driver["preservedFailures"][0]["stageNumber"] == 5 and
            driver["preservedFailures"][0]["stage"] == "startup-comparison", "Original failure history missing")
    pack.bind(driver["preservedFailures"][0]["receipt"], "compiled-checks/startup-comparison/comparison.json")
    pack.bind(checkpoint["historicalFailurePreserved"], "compiled-checks/startup-comparison/comparison.json")
    require(driver["terminalEvidence"] == checkpoint["terminalEvidence"], "Terminal evidence maps differ")
    terminal = {"adaptationPreparation": ADAPTATION + "preparation-receipt.json", "adaptationReview": ADAPTATION + "static-review.json",
                "baseline": "compiled-checks/baseline/build-result.json", "revised": "compiled-checks/revised/build-result.json",
                "cardinalityProof": "compiled-checks/catalogue-cardinality.json", "currentCatalogueComparison": CURRENT_COMPARISON,
                "fullScale": CURRENT_FULL_SCALE + "receipt.json", "fullScaleResult": CURRENT_FULL_SCALE + "result.json",
                "independentModelReview": "compiled-checks/model-review.json",
                "integerDifferential": "compiled-checks/trade-integer-differential/receipt.json",
                "originalStartupFailure": "compiled-checks/startup-comparison/comparison.json", "seed": "compiled-checks/europe-seed/seed-receipt.json"}
    require(set(driver["terminalEvidence"]) == set(terminal), "Terminal evidence scope changed")
    for key, name in terminal.items():
        pack.bind(driver["terminalEvidence"][key], name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Completed validation/evidence directory with the original relative layout")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--project", type=Path, help="Authored age-of-sail-world source checkout; exact d669/d084 inputs required")
    source.add_argument("--repo", type=Path, help="WarCraftMap checkout containing the exact d669/d084 project inputs")
    parser.add_argument("--require-manifest", action="store_true", help="Require the final exact-file-set manifest and explicit original-path aliases")
    args = parser.parse_args()
    project = checked_path(args.project or args.repo / "maps/historical-world-rpg/age-of-sail-world").resolve()
    pack = Evidence(args.root)
    require(not args.require_manifest or pack.manifest is not None, "Final manifest is required")
    gate, integration = load_gate(project)
    verify_source_context(pack, project)
    inputs, dependency, coverage = verify_full(pack, gate, integration, project)
    verify_failed_attempts(pack, gate, inputs)
    summaries = verify_prefix(pack)
    builds = verify_builds(pack, dependency, inputs)
    verify_differential(pack, builds)
    catalogue, prepared, changes = verify_catalogue_adaptation(pack, builds, project)
    startup = verify_startup(pack, builds, catalogue)
    verify_full_scale(pack, builds, catalogue, changes)
    verify_compiled_driver(pack)
    require(integration.source_identity(project, REVISION) == IDENTITY, "Source changed during verification")
    print(json.dumps({"status": "pass_completed_source_and_model_evidence_native_not_run", "sourceIdentity": IDENTITY,
                      "fullWurstTests": 698, "requiredGate": "unchanged execute_tests plus verify_execution_coverage",
                      "coverageSystems": len(coverage), "pythonPrefixSummaries": summaries,
                      "pythonPrefixWurstExplicitlySkipped": True, "earlierAttemptStatuses": {"focused-attempt1": "fail", "negative-guard-attempt1": "fail", "originalStartupComparison": "fail", "originalFullScaleStage": "not_run"},
                      "currentCatalogue": {"markets": catalogue["marketCount"], "stores": catalogue["storeCount"], "sourceDerivedIndustryAdditions": catalogue["industryAddedMarkets"]},
                      "integerDifferential": {"models": 8, "casesPerModel": 703}, "startup": startup,
                      "nativeStatus": "not_run", "nativeContinueVerifiedFixed": False,
                      "nativeHangResolution": "not_established", "playerArtifactProduced": False,
                      "archiveScope": "Archived Lua bytes and original known-member equality receipts verified; original W3X archives are not re-extracted",
                      "manifestChecked": pack.manifest is not None,
                      "retainedFiles": len(pack.entries) if pack.manifest is not None else None,
                      "verificationScope": "Original raw/source/probe/model bindings and explicit review; manifest and existing historical references additionally checked when retained"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, EOFError) as error:
        raise SystemExit("Evidence verification failed: " + str(error)) from error
