#!/usr/bin/env python3
"""Stage one bounded PR536 evidence pack in scratch; never edit the repository.

Run only after terminal validations and script review. This command reads
existing evidence, compresses/copies selected bytes, and creates a manifest.
It does not run tests, Lua, Java, builds, network requests or deployment.
Its source-only link check reads the required local d669 Git tree with ls-tree;
Git network access, fetching, replacement objects and optional locks are disabled.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import importlib.util
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
script_path = Path(__file__).absolute()
verifier_path = script_path.parent / "verify-evidence.py"
for path in [script_path, verifier_path, *script_path.parents]:
    if path.is_symlink():
        raise SystemExit("Evidence helpers must not be reached through symlinks: " + str(path))
HERE = script_path.parent.resolve()
spec = importlib.util.spec_from_file_location("pr536_evidence_verifier", verifier_path)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
require, sha = verify.require, verify.sha
MAX_PACKAGED_BYTES = 32 * 1024 * 1024
TARGET = "maps/historical-world-rpg/age-of-sail-world/reports/issue-438/startup-main-continuation"


def encoded_json(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def read(path):
    return json.loads(verify.file_bytes(path))


def deterministic_gzip(data):
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=stream, compresslevel=9, mtime=0) as output:
        output.write(data)
    return stream.getvalue()


class Pack:
    def __init__(self, root, output):
        self.root, self.output = root, output
        self.files = {}
        self.logical = {}
        self.original = {}
        self.dedup = {}
        self.source_reads = {}
        self.total = 0

    def add(self, logical, source=None, *, data=None, keep=False):
        verify.Evidence.safe(logical)
        require(Path(logical).suffix.lower() not in {".w3x", ".w3n", ".jar", ".so", ".exe", ".zip", ".tar"},
                "Do not package archives/toolchain binaries: " + logical)
        if source is not None:
            source = verify.checked_path(source)
            require(source.is_file(), "Missing original: " + str(source))
            source = source.resolve()
            original_data = verify.file_bytes(source)
            require(data is None or data == original_data, "Supplied bytes differ from original")
            data = original_data
            self.source_reads[str(source)] = sha(data)
        require(isinstance(data, bytes), "Package input must be original bytes")
        digest = sha(data)
        if logical in self.logical:
            retained = self.logical[logical]
            require(self.files[retained]["originalSha256"] == digest, "Conflicting logical input")
        else:
            # Original gzip payloads are never recompressed. Python helpers stay
            # readable/executable; large JSON, logs, Wurst, Lua and map members
            # use deterministic gzip. Identical generated/source bytes occur once.
            compress = not logical.endswith((".gz", ".py", ".md")) and len(data) > 65536
            encoding = "gzip_mtime_0" if compress else "identity"
            key = (digest, encoding)
            retained = None if keep else self.dedup.get(key)
            if retained is None:
                retained = logical + (".gz" if compress else "")
                require(retained not in self.files, "Retained filename collision")
                payload = deterministic_gzip(data) if compress else data
                require(self.total + len(payload) <= MAX_PACKAGED_BYTES, "Bounded pack exceeds 32 MiB; review rather than drop evidence")
                path = self.output / retained
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                self.total += len(payload)
                self.files[retained] = {"file": retained, "encoding": encoding,
                    "packagedBytes": len(payload), "packagedSha256": sha(payload),
                    "originalBytes": len(data), "originalSha256": digest}
                if not keep:
                    self.dedup[key] = retained
            self.logical[logical] = retained
        if source is not None:
            self.alias_original(str(source), retained, digest)
        return retained

    def alias_original(self, original, retained, digest):
        require(Path(original).is_absolute() and retained in self.files, "Invalid original alias")
        require(self.files[retained]["originalSha256"] == digest, "Alias byte mismatch")
        require(original not in self.original or self.original[original] == retained, "Conflicting original alias")
        self.original[original] = retained

    def local(self, relative, *, keep=False):
        return self.add(relative, self.root / relative, keep=keep)


def require_terminal(root, project, source_review):
    # Check terminal receipts before creating any output directory. The separate
    # verifier re-parses raw evidence; terminal labels alone are not acceptance.
    expected = {
        "source-reports/receipt.json": "source_freshness_only_native_and_release_remain_blocked",
        "python-checks/receipt.json": "completed",
        "full-attempt1/receipt.json": "pass",
        "focused-attempt1/receipt.json": "fail",
        "negative-guard-attempt1/receipt.json": "fail",
        "evidence-review/negative-control-review.json": "intended_assertions_confirmed_original_harness_fail_preserved",
        "evidence-review/static-review.json": "pass_static_review",
        verify.PACKING_ATTEMPT + "receipt.json": "fail",
        "compiled-checks/static-review.json": "pass_static_review",
        "compiled-checks/europe-seed/seed-receipt.json": "pass",
        "compiled-checks/baseline/build-result.json": "pass",
        "compiled-checks/revised/build-result.json": "pass",
        "compiled-checks/trade-integer-differential/receipt.json": "pass_under_explicit_models",
        "compiled-checks/startup-comparison/comparison.json": "fail",
        verify.CURRENT_COMPARISON: "pass_under_explicit_models",
        "compiled-checks/catalogue-cardinality.json": "pass_static_source_derivation",
        verify.ADAPTATION + "preparation-receipt.json": "prepared_for_review_not_executed",
        verify.ADAPTATION + "static-review.json": "pass_static_review",
        verify.CURRENT_FULL_SCALE + "receipt.json": "pass_full_scale_roundtrip_under_explicit_stubs",
        verify.CURRENT_FULL_SCALE + "result.json": "pass_full_scale_roundtrip_under_explicit_stubs",
        "compiled-checks/model-review.json": "pass_scoped_model_review",
        "compiled-checks/workflow-state.json": "completed",
        verify.DRIVER + "run-metadata.json": "completed",
    }
    for relative, status in expected.items():
        require(read(root / relative)["status"] == status, "Nonterminal/unexpected receipt: " + relative)
    require(sha(verify.file_bytes(root / verify.PACKING_ATTEMPT / "receipt.json")) == verify.PACKING_RECEIPT,
            "Original packing attempt must remain preserved")
    script_review = read(root / "evidence-review/static-review.json")
    require(script_review["blockingFindings"] == [] and script_review["nativeStatus"] == "not_run"
            and set(script_review["reviewedScripts"]) == {"pack-evidence.py", "verify-evidence.py"}, "Evidence-script review scope")
    for name, row in script_review["reviewedScripts"].items():
        data = verify.file_bytes(HERE / name)
        require(sha(data) == row["sha256"] and len(data) == row["bytes"], "Evidence script changed after review: " + name)
    require(all(script_review["validationPerformed"][flag] is False for flag in
                ["testExecution", "modelExecution", "buildExecution", "packingExecution"]), "Static review must remain static")
    prefix = read(root / "python-checks/receipt.json")
    require(prefix["exitCode"] == 0 and prefix["beforeAfterIdentical"] is True and prefix["wurstSkippedWarningPresent"] is True,
            "Source/Python prefix failed or changed source")
    require(prefix["before"]["sourceIdentity"] == verify.IDENTITY and prefix["after"] == prefix["before"], "Prefix source identity")
    full = read(root / "full-attempt1/receipt.json")
    require(full["sourceIdentity"] == verify.IDENTITY and full["discovered"] == full["succeeded"] == 698, "Full gate source/count")
    require(not verify.checked_path(root / "compiled-checks/full-scale-revised").exists(), "Original full-scale stage was never run")
    checkpoint = read(root / "compiled-checks/workflow-state.json")
    require(checkpoint["remainingStages"] == [] and checkpoint["activeToolSessionId"] is None and
            checkpoint["validationStatus"] == "pass_under_explicit_models_after_reviewed_catalogue_adaptation", "Compiled workflow still active/incomplete")
    review = read(source_review)
    require(review["status"] == "pass_source_review_only" and not review["blockingFindings"], "Source review incomplete")
    gate, integration = verify.load_gate(project)
    require(integration.source_identity(project, verify.REVISION) == verify.IDENTITY, "Current source differs")
    return integration


def collect(pack, project, source_review, integration):
    root, repo = pack.root, project.parents[2]
    for relative in ["run-wurst.py", "prepare.log", "refresh-reports.py", "refresh-reports.log",
                     "seed/receipt.json", "seed/discovery.json", "toolchain/relocation-receipt.json", "toolchain/grill",
                     "focused-attempt1.log", "negative-guard-attempt1.log", "full-attempt1.log",
                     "python-checks/run_prefix.py", "python-checks/before.json", "python-checks/after.json",
                     "python-checks/receipt.json", "python-checks/execution.log",
                     "evidence-review/negative-control-review.json", "evidence-review/review-negative-control.py",
                     "evidence-review/retention-plan.md", "evidence-review/static-review.json", "evidence-review/packing-attempt1.log"]:
        pack.local(relative)
    failed_pack = read(root / verify.PACKING_ATTEMPT / "receipt.json")
    pack.local(verify.PACKING_ATTEMPT + "receipt.json")
    for name, row in failed_pack["preservedFiles"].items():
        retained = pack.local(verify.PACKING_ATTEMPT + verify.Evidence.safe(name))
        require(pack.files[retained]["originalSha256"] == row["sha256"] and
                pack.files[retained]["originalBytes"] == row["bytes"], "Preserved packing failure bytes changed")
    for name in ["verify-evidence.py", "pack-evidence.py"]:
        retained = pack.add(name, HERE / name)
        pack.logical["evidence-review/" + name] = retained
    pack.add("source-review.json", source_review)
    for prefix in ["focused-attempt1", "negative-guard-attempt1", "full-attempt1"]:
        for name in ["receipt.json", "results.json", "discovery.json", "compiler-inputs-before.json",
                     "compiler-inputs-after.json", "dependency-before.json", "execution.log"]:
            pack.local(prefix + "/" + name)
    for name in ["receipt.json", "runtime.stdout", "runtime.stderr", "release.stdout", "release.stderr",
                 "traceability.stdout", "traceability.stderr"]:
        pack.local("source-reports/" + name)
    tooling = project.parent / "_shared/tooling"
    for name in ["wurst_execution.py", "integration_evidence.py"]:
        pack.add("common/" + name, tooling / name)
    pack.add("common/runtime-execution.json", project / "scenario/runtime-execution.json")
    pack.add("common/package.json", project / "package.json")
    inventory = verify.source_inventory(project)
    require(sha(verify.canonical(inventory)) == verify.SOURCE, "Source inventory changed")
    pack.add("source-inputs.json", data=encoded_json(inventory))
    for row in read(source_review)["reviewedFiles"]:
        path = repo / verify.Evidence.safe(row["path"])
        canonical_path, data = verify.read_source_file(project, path)
        require(sha(data) == row["sha256"], "Reviewed source changed")
        retained = pack.add("source/" + row["path"], canonical_path, data=data)
        pack.alias_original(str(path), retained, sha(data))
    authored = integration.execution_sources(project)
    full_inputs = read(root / "full-attempt1/compiler-inputs-before.json")
    extra_names = {"_build/common.j", "_build/blizzard.j", "wurst.build", "wurst_run.args",
                   "wurst/ScenarioData.wurst", "wurst/ScenarioSettings.wurst", "wurst/ConformanceData.wurst"}
    require(set(full_inputs) - set(authored) == extra_names, "Review changed unauthored full-gate inputs")
    for name in sorted(extra_names):
        path = root / "full-attempt1/compile" / name
        require(sha(verify.file_bytes(path)) == full_inputs[name], "Completed full input differs")
        pack.add("full-attempt1/inputs/" + name, path)
    base = "compiled-checks/"
    for name in ["README.md", "preparation-manifest.json", "static-review.json", "continuation_common.py",
                 "compile_europe.py", "trade_integer_differential.py", "compare_startup.py", "run_full_scale.py",
                 "europe-seed/seed-receipt.json", "model-review.json", "catalogue-cardinality.py", "catalogue-cardinality.json",
                 "workflow-state.json"]:
        pack.local(base + name)
    for name in ["run-metadata.json", "01-prepare.log", "02-baseline.log", "03-revised.log", "04-integer-differential.log",
                 "05-startup-comparison.log", "06-startup-current-catalogue.log", "07-full-scale-current-catalogue.log"]:
        pack.local(verify.DRIVER + name)
    adaptation = read(root / verify.ADAPTATION / "preparation-receipt.json")
    for name in ["preparation-receipt.json", "static-review.json", *adaptation["adaptedFiles"], *adaptation["patches"]]:
        pack.local(verify.ADAPTATION + verify.Evidence.safe(name))
    preparation, static = read(root / base / "preparation-manifest.json"), read(root / base / "static-review.json")
    references = []
    for name, row in preparation["frozenInputs"].items():
        if "copy" not in row:
            continue
        retained = pack.local(base + "frozen/" + name)
        require(row["original"]["sha256"] == row["copy"]["sha256"] == pack.files[retained]["originalSha256"], "Frozen input changed")
        pack.alias_original(row["original"]["path"], retained, row["original"]["sha256"])
        marker = "/WarCraftMap/"
        require(marker in row["original"]["path"], "Frozen original must be an existing repository reference")
        relative = row["original"]["path"].split(marker, 1)[1]
        require(sha(verify.file_bytes(repo / relative)) == row["original"]["sha256"], "Existing frozen reference differs")
        references.append({"role": "frozen_original_" + name, "repoPath": relative,
                           "bytes": row["original"]["bytes"], "sha256": row["original"]["sha256"]})
    for name, row in static["reviewedRepositoryApiSources"].items():
        retained = pack.add("common/" + name, tooling / name)
        require(pack.files[retained]["originalSha256"] == row["sha256"], "Reviewed repository helper changed")
    pack.add("common/AGENTS.md", repo / "AGENTS.md")
    seed = read(root / base / "europe-seed/seed-receipt.json")
    for name in sorted(set(seed["compilerInputs"]) - set(authored)):
        require(name in extra_names, "Unexpected generated Europe input")
        path = root / base / "europe-seed/compile" / name
        require(sha(verify.file_bytes(path)) == seed["compilerInputs"][name], "Europe generated input changed")
        pack.add(base + "europe-seed/inputs/" + name, path)
    for mode in ["baseline", "revised"]:
        prefix = base + mode + "/"
        for name in ["build-result.json", "inputs-before.json", "inputs-after.json", "dependency-before.json", "typecheck.log", "build.log"]:
            pack.local(prefix + name)
        if mode == "baseline":
            pack.local(prefix + "baseline-reversion.patch")
        build = read(root / prefix / "build-result.json")
        if mode == "baseline":
            reader = build["independentReader"]
            retained = pack.add("common/mpyq-reviewed.py", Path(reader["path"]))
            require(pack.files[retained]["originalSha256"] == reader["sha256"], "Independent reader bytes changed")
        for name, row in build["extracted"].items():
            verify.Evidence.safe(name)
            retained = pack.local(prefix + name)
            require(pack.files[retained]["originalSha256"] == row["sha256"], "Extracted member differs")
        comparison = base + "startup-comparison/" + mode + "/"
        for name in ["frozen/result.json", "frozen/probe-lua54-initialization.py", "frozen/late-startup-stubs.lua",
                     f"frozen/europe_central_east-{mode}-trade-snapshot.txt",
                     "observer/startup-and-first-callbacks.json", "observer/observe-startup.lua", "observer/observe-startup.py"]:
            pack.local(comparison + name)
        for index in range(1, 5):
            pack.local(comparison + f"observer/cache-write-{index}.txt.gz", keep=True)
    pack.local(base + "startup-comparison/comparison.json")
    pack.local(verify.CURRENT_COMPARISON)
    frozen_pathing = preparation["frozenInputs"]["frozenPathing"]
    pack.alias_original(frozen_pathing["path"], pack.logical[base + "baseline/war3map.wpm"], frozen_pathing["sha256"])
    differential = base + "trade-integer-differential/"
    for name in ["receipt.json", "cases.json", "native-slice-models.json"]:
        pack.local(differential + name)
    for model in read(root / differential / "native-slice-models.json"):
        require(re_safe_model(model), "Unsafe model filename")
        for mode in ["baseline", "revised"]:
            pack.local(differential + model + "-" + mode + ".json")
    for name in ["receipt.json", "result.json", "execution.log"]:
        pack.local(verify.CURRENT_FULL_SCALE + name)
    native = "maps/historical-world-rpg/age-of-sail-world/reports/issue-438/startup-work-reduction/previous-native-observation.json"
    native_data = verify.file_bytes(repo / native)
    references.append({"role": "latest_actual_native_observation", "repoPath": native,
                       "bytes": len(native_data), "sha256": sha(native_data)})
    return references


def re_safe_model(name):
    return isinstance(name, str) and name and all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Completed validation-536-continuation directory")
    parser.add_argument("--project", required=True, type=Path, help="Exact authored age-of-sail-world source checkout")
    parser.add_argument("--output", required=True, type=Path, help="New scratch staging directory; never a repository path")
    parser.add_argument("--source-review", type=Path, help="Defaults to workspace integration/source-review.json")
    args = parser.parse_args()
    root, project, output = [verify.checked_path(path).resolve() for path in [args.root, args.project, args.output]]
    repo = project.parents[2]
    require(root.is_dir() and project.is_dir(), "Missing evidence/source root")
    require(not output.exists(), "Preserve prior staging; choose a new output path")
    require(output.is_relative_to(root.parent) and not output.is_relative_to(root) and not output.is_relative_to(repo),
            "Staging must be a new sibling scratch directory outside validation and repository trees")
    source_review = verify.checked_path(args.source_review or root.parent / "integration/source-review.json").resolve()
    integration = require_terminal(root, project, source_review)
    output.mkdir(parents=True)
    pack = Pack(root, output)
    references = collect(pack, project, source_review, integration)
    prefix = read(root / "python-checks/receipt.json")
    comparison = read(root / verify.CURRENT_COMPARISON)
    readme = f"""# PR #536 startup continuation evidence

This report retains validation of clean source `{verify.REVISION}`, after integration of main `58d1b88d0fb4b852b639d2d82a5a24dee92ed92c`, starting from published `{verify.PUBLISHED}`. The source identity is `{verify.SOURCE}`. The source checkout is required to verify authored tests and production probe bindings.

## Source changes and required checks

The continuation rejects an empty public `session_start` or `major_milestone` encoding before writing a checkpoint or acknowledging the pending startup request. The failed attempt rolls back in-memory state and preserves the pending request for a valid retry. The integer digit fast path returns ASCII digits directly and retains the existing fallback semantics for other input. Integration retains main's schema 17 migrations and all eight date-bound checks.

The unchanged full Wurst gate completed 698/698 tests with observed passing tests in all 28 required systems and all 84 production probes observed. The separate source/Python prefix completed with unittest counts {[row['tests'] for row in prefix['unittestSummaries']]}; Wurst was explicitly skipped in that prefix and synthetic fixture Wurst lines are not counted as actual Wurst execution. The focused-attempt1 original receipt remains failed because the strict transcript gate rejected the read-only setup.log diagnostic even though its 66 selected assertions passed. The negative-guard-attempt1 original receipt also remains failed. Its separate review confirms exactly the two intended guard assertions failed (0/2), while preserving the temporary harness's rejection of the compiler's normal failed-test wrapper.

The first evidence-pack attempt also **failed**, before creating an output directory: the strict path reader rejected the project's tracked `Agriculture.wurst` shared-source link. Its original reviewed helpers, review, raw rejection log, checkpoint, tracked link inventory and validation-input identities remain preserved under `evidence-review/packing-attempt1-preserved/`. The corrected source-only reader accepts only the exact 51 shared Wurst links recorded in the local `{verify.REVISION}` Git tree, including the bootstrap link, and verifies their same-name canonical regular target blobs. Parent directories, evidence inputs, historical references and package traversal keep their no-link checks. No source, gate, test, model or build was changed or rerun for this packaging correction.

## Compiled and modeled evidence

Both compiled arms use integrated schema 17 source. The counterfactual baseline reverses only the two public empty-encode guards and the trade integer digit fast path; it is not published 99524f6 or historical schema 15 save data. Their typecheck/build logs, actual archived Lua and known extracted member bytes are retained. W3X archives remain workspace-only: two-reader known-member archive checks were performed during the original build and are not rerun by this integrity verifier.

The integer differential covers 703 cases under eight explicit slice models. The same integrated-source startup arms produce these measured values under the retained explicit native models:

| Measurement | Counterfactual baseline | Revised source |
| --- | ---: | ---: |
| Startup `SubString` calls | {comparison['nativeCalls']['SubString']['before']:,} | {comparison['nativeCalls']['SubString']['after']:,} |
| Startup `StringLength` calls | {comparison['nativeCalls']['StringLength']['before']:,} | {comparison['nativeCalls']['StringLength']['after']:,} |
| Sampled startup instructions | {comparison['instructionSamples']['before']:,} | {comparison['instructionSamples']['after']:,} |
| Modeled callbacks through 1.001 synthetic seconds | 37 | 37 |
| Sampled callback instructions | 14,710,000 | 14,710,000 |

All other startup native-call counts match, and each callback's native-call map and sampled instruction count match. The scoped review resolves one shifted compiled callback line to the identical bridge function. This is model-only work evidence; it is not a native elapsed-time measurement or a claim of Warcraft timing or behavioral parity.

All four ordered saved payloads are byte-identical between these schema 17 arms ({comparison['cachePayloadBytesTotal']:,} uncompressed bytes per arm). The original gzip bytes for all eight payload files are retained separately. This comparison does not claim equality with historical schema 15 save bytes.

The original startup comparison **failed** its historical exact expectation of 8,422 markets. Its failed receipt, runner, outer log and all completed raw outputs remain unchanged. The separate source-derived `catalogue-cardinality.json` proves 8,422 base market pairs plus four absent industry pairs (`iron_goods` in Milan, Nuremberg, Stockholm and Vienna), giving 8,426 markets and last index 8,425. The store count stays 829. An independently reviewed, read-only derivation applies that exact current-source expectation to the already completed startup outputs; no startup model was rerun.

The original full-scale stage was never run. Its first execution used a separate, reviewed case and runner with only the exact market count/index literals and source/path bindings adapted. Native stubs, all other assertions and both 2-billion-instruction phase budgets remain unchanged. The passing full-scale revised model covers all 8,426 markets, 829 stores and 829 populated provenance lots, including mutation, reconstruction, selection and catalogue-order restoration, and exact saved/restored capture equality. All model results are supplemental developer evidence.

## Native acceptance remains open

**Native status remains `not_run`; Continue freeze resolution is not established.** The latest actual observation is the retained owner report for a1b4396 at 2026-10-20 16:52:49 UTC: Austria → Victory → Continue unresponsive, with no observed destination terrain or controllable unit. Keep PR #536 draft/unmerged and issue #438 open until the existing real-client acceptance and review requirements are satisfied. These artifacts are not a player release candidate.

Run the read-only verifier with the exact source checkout:

```sh
python3 -B verify-evidence.py --root /path/to/startup-main-continuation --project /path/to/WarCraftMap/maps/historical-world-rpg/age-of-sail-world --require-manifest
```

The pinned source is available at https://github.com/tommytang213/WarCraftMap/tree/{verify.REVISION}. The checkout must contain that local Git tree; a source archive without its Git objects is insufficient. A later report-only commit is accepted only if the source identity remains unchanged. The source-link check uses read-only `git ls-tree` with network access and fetching disabled. The verifier does not weaken source checks for future main, execute tests or native models, rebuild maps, or contact any service.

`manifest.json` binds the exact retained file set, original and compressed hashes, logical aliases, original absolute-path aliases, and existing historical references. Identical generated/source bytes are stored once; original saved-payload gzip files are preserved separately and unchanged. Recorded absolute paths are provenance, never destinations followed by the verifier. Historical inputs already in the repository are referenced rather than duplicated in full.
"""
    pack.add("README.md", data=readme.encode())
    require(sha(verify.canonical(verify.source_inventory(project))) == verify.SOURCE, "Source/link inputs changed during packing")
    require(integration.source_identity(project, verify.REVISION) == verify.IDENTITY, "Source changed during packing")
    for path, digest in pack.source_reads.items():
        require(sha(verify.file_bytes(path)) == digest, "Original evidence changed during packing: " + path)
    manifest = {
        "format": "warcraftmap_pr536_continuation_evidence_v1",
        "status": "complete_source_and_model_evidence_native_not_run",
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "sourceIdentity": verify.IDENTITY, "publishedRevision": verify.PUBLISHED,
        "integratedMainRevision": "58d1b88d0fb4b852b639d2d82a5a24dee92ed92c",
        "sourceCheckoutRequired": True,
        "pinnedSourceGitTreeRequired": verify.REVISION,
        "sourceCheckoutUrl": "https://github.com/tommytang213/WarCraftMap/tree/" + verify.REVISION,
        "intendedRepositoryPath": TARGET, "nativeStatus": "not_run", "nativeHangResolution": "not_established",
        "playerArtifactProduced": False, "sourceOrGateMutatedByPacking": False,
        "schema": 17, "baselineMeaning": "Integrated source counterfactual; only two empty-encode guards and trade digit fast path reverted",
        "earlierAttemptStatuses": {"focused-attempt1": "fail", "negative-guard-attempt1": "fail", "originalStartupComparison": "fail", "originalFullScaleStage": "not_run", "packing-attempt1": "fail"},
        "catalogueAdaptation": "Source-derived 8426 markets, 829 stores; original failure preserved; startup comparison derived without model reexecution",
        "archiveScope": "Known-member archive checks performed at build; no W3X binaries retained or re-extracted by integrity verification",
        "packagedBytesExcludingManifest": pack.total,
        "files": [pack.files[n] for n in sorted(pack.files)],
        "logicalAliases": dict(sorted(pack.logical.items())),
        "originalPathAliases": dict(sorted(pack.original.items())),
        "historicalReferences": references,
    }
    (output / "manifest.json").write_bytes(encoded_json(manifest))
    print(json.dumps({"status": "staged_requires_independent_integrity_verification", "output": str(output),
                      "files": len(pack.files), "logicalInputs": len(pack.logical), "packagedBytesExcludingManifest": pack.total,
                      "manifestSha256": sha((output / "manifest.json").read_bytes()),
                      "nativeStatus": "not_run", "repositoryModified": False}, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, EOFError) as error:
        raise SystemExit("Evidence staging failed; preserve any partial output for review: " + str(error)) from error
