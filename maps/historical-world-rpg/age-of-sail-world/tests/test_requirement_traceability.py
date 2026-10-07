"""Small real nested MPQs exercise the gate, not Warcraft gameplay.

Interpreter transcripts below are synthetic protocol fixtures, never release
evidence. The RC pipeline separately verifies the pinned compiler and full suite.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import requirement_traceability as trace
import requirement_traceability_audit as scenario
import package_release_candidate as release
import wurst_execution as execution
from warcraft_campaign import write_mpq


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "campaign"
        (self.project / "docs").mkdir(parents=True)
        (self.project / "wurst").mkdir()
        (self.project / "docs/lock.md").write_text("# Lock\n\n- <!-- req:REQ-0001 --> Registered action persists. Replays reject.\n")
        (self.project / "wurst/Adapter.wurst").write_text(
            'package Adapter\npublic function install()\n\tTriggerAddAction(listener, function route)\n'
            'public function route()\n\tstate.commit()\npublic function persist()\n\tstore.write(state)\n'
            'public function restore()\n\tstate.read(store)\n')
        (self.project / "wurst/Fixture.wurst").write_text(
            'package Fixture\n@test function fixture()\n\tinstall()\n\tdriveRegisteredAdapter()\n\tstate.value.assertEquals(1)\n')
        self.catalogue = self.project / "catalogue.json"
        self.catalogue.write_text('[{"id":"port"}]')
        self.ledger = {"documents": ["docs/lock.md"], "requiredCatalogues": ["settlements"], "dependencies": [],
                       "requirements": [{"id": "REQ-0001", "path": "docs/lock.md", "section": "Lock",
                                         "text": "Registered action persists. Replays reject.", "classification": "mechanism",
                                         "kind": "runtime", "requiredCases": ["success", "failure", "stale", "replay"],
                                         "obligations": [{"id": "REQ-0001.01", "text": "Registered action persists."},
                                                         {"id": "REQ-0001.02", "text": "Replays reject."}]}]}
        def ref(symbol, token):
            return {"path": "wurst/Adapter.wurst", "symbol": symbol, "contains": [token]}
        mapping = {"mechanism": [ref("route", "state.commit()")],
                   "entry": {"id": "wc3-event", "kind": "event", "registration": ref("install", "TriggerAddAction(listener, function route)"),
                             "path": [ref("route", "state.commit()")], "testInvocation": "driveRegisteredAdapter()"},
                   "state": {"owner": "CampaignState", "mutation": "route -> commit", "rejection": "stale revision and replay ID reject without mutation",
                             "outcome": "port ownership changes", "references": [ref("route", "state.commit()") ]},
                   "persistence": {"mode": "persisted", "reason": "Versioned state round trip", "references": [ref("persist", "store.write(state)")],
                                   "save": ref("persist", "store.write(state)"), "load": ref("restore", "state.read(store)")},
                   "transition": {"mode": "reconstructed", "reason": "Restore stable port ID on next map", "references": [ref("restore", "state.read(store)")]},
                   "artifact": {"mapIds": ["@regional"], "callPatterns": [r"\bTriggerAddAction\(", r'\bregisterSettlement\("port"\)']}}
        self.mappings = {"requirements": {}, "dependencies": {}}
        self.receipts = []
        for clause in self.ledger["requirements"][0]["obligations"]:
            row = copy.deepcopy(mapping)
            row["tests"] = {}
            for case in self.ledger["requirements"][0]["requiredCases"]:
                receipt = {"requirement": clause["id"], "case": case, "entryPoint": "wc3-event",
                           "observed": ["registration", "adapter", "validation", "mutation", "persistence", "transition", "outcome"]}
                self.receipts.append(receipt)
                row["tests"][case] = {"id": "wurst/Fixture.wurst:fixture", "level": "production_adapter", "entryPoint": "wc3-event",
                                       "assertions": ["state.value.assertEquals(1)"], "receipt": receipt}
            self.mappings["requirements"][clause["id"]] = row
        self.specs = [{"id": "settlements", "sources": [{"path": "catalogue.json", "selector": "*"}],
                       "runtime": {"selector": "settlements"}, "compare": "records", "compiledIdPattern": r'\bregisterSettlement\({id}\)'}]
        self.maps = [{"id": "region", "packagePath": "Maps/Region.w3x", "bootstrap": False}]
        self.runtime = {"physicalMap": {"id": "region", "bootstrap": False}, "settlements": [{"id": "port"}]}
        self.script = b'function main()\n TriggerAddAction(listener, route)\n registerSettlement("port")\nend\n'
        self.artifact = self.project / "final.w3n"
        self.write_artifact()
        self.evidence, self.transcript = self.make_evidence()

    def make_evidence(self):
        log = ('Running tests\nRunning /compile/wurst/Fixture.wurst:2 - fixture..\n' +
               ''.join('TRACEABILITY ' + json.dumps(row) + '\n' for row in self.receipts) +
               '\tOK!\nTests succeeded: 1/1\nFinished running tests\n').encode()
        expected = [{"id": "wurst/Fixture.wurst:fixture", "line": 2}]
        tests, errors = execution.parse_results(log.decode(), expected)
        inputs = {f"wurst/{name}": execution.sha((self.project / "wurst" / name).read_bytes()) for name in ("Adapter.wurst", "Fixture.wurst")}
        report = {"format": execution.FORMAT, "status": "pass", "sourceRevision": "a"*40, "returnCode": 0,
                  "expected": expected, "tests": tests, "errors": errors, "inputs": inputs,
                  "inputSetSha256": execution.sha(execution.canonical(inputs)), "logSha256": execution.sha(log),
                  "compiler": {"sha256": execution.PINNED_COMPILER_SHA256}, "discovered": 1, "succeeded": 1}
        return report, log

    def write_artifact(self, extra=None):
        files = {"war3map.lua": self.script, "runtime/scenario-runtime.json": json.dumps(self.runtime).encode(),
                 "war3map.w3e": b"terrain", "war3map.wpm": b"pathing", "war3mapUnits.doo": b"objects",
                 "war3mapImported/icon.blp": b"asset"}
        if extra:
            files.update(extra)
        files["(listfile)"] = ("\n".join(files) + "\n").encode()
        nested = self.project / "built.w3x"
        write_mpq(nested, files)
        campaign = {"Maps/Region.w3x": nested.read_bytes(), "war3campaign.w3f": b"metadata"}
        campaign["(listfile)"] = ("\n".join(campaign) + "\n").encode()
        write_mpq(self.artifact, campaign)

    def report(self):
        return trace.audit(self.project, self.ledger, self.mappings, self.specs, self.maps, artifact=self.artifact,
                           evidence=self.evidence, transcript=self.transcript, revision="a"*40)

    def assertBlocked(self, category):
        report = self.report()
        self.assertIn(category, report["blockerClasses"])
        self.assertFalse(report["candidateReady"])
        with self.assertRaisesRegex(ValueError, "blocks candidate publication"):
            trace.require_ready(report)
        return report

    def test_complete_explicit_mapping_and_exact_final_artifact_pass(self):
        report = self.report()
        self.assertEqual([], report["blockers"])
        trace.require_ready(report)
        self.assertEqual(trace.sha(self.artifact.read_bytes()), report["artifact"]["sha256"])
        self.assertEqual(1, report["catalogues"][0]["sourceCount"])
        self.assertEqual(1, report["catalogues"][0]["packagedUniqueCount"])

    def test_removed_production_registration_blocks_even_when_handler_exists(self):
        path = self.project / "wurst/Adapter.wurst"
        path.write_text(path.read_text().replace('TriggerAddAction(listener, function route)', 'skip'))
        self.assertBlocked("unreachable")

    def test_removed_persistence_path_blocks_even_when_save_class_exists(self):
        path = self.project / "wurst/Adapter.wurst"
        path.write_text(path.read_text().replace('store.write(state)', 'skip'))
        self.assertBlocked("unpersisted")

    def test_save_only_mapping_cannot_claim_load_coverage(self):
        del self.mappings["requirements"]["REQ-0001.01"]["persistence"]["load"]
        self.assertBlocked("unpersisted")

    def test_build_entry_cannot_claim_player_reachability(self):
        self.mappings["requirements"]["REQ-0001.01"]["entry"]["kind"] = "build"
        self.assertBlocked("unreachable")

    def test_removed_integration_mapping_blocks_despite_passing_suite(self):
        del self.mappings["requirements"]["REQ-0001.01"]["tests"]["failure"]
        self.assertBlocked("integration-missing")

    def test_removed_artifact_registration_blocks_despite_source_marker(self):
        self.script = self.script.replace(b'registerSettlement("port")', b'')
        self.write_artifact()
        self.assertBlocked("artifact-missing")

    def test_comment_or_diagnostic_string_cannot_replace_packaged_call(self):
        self.script = b'function main()\n print([[registerSettlement("port")]])\n -- registerSettlement("port")\nend'
        self.write_artifact()
        self.assertBlocked("artifact-missing")

    def test_parent_mapping_never_satisfies_children(self):
        row = self.mappings["requirements"].pop("REQ-0001.01")
        self.mappings["requirements"].pop("REQ-0001.02")
        self.mappings["requirements"]["REQ-0001"] = row
        report = self.assertBlocked("invalid-mapping")
        self.assertEqual(2, report["blockerClasses"]["unmapped"])

    def test_each_clause_requires_its_own_receipt(self):
        self.mappings["requirements"]["REQ-0001.02"] = copy.deepcopy(self.mappings["requirements"]["REQ-0001.01"])
        self.assertBlocked("integration-missing")

    def test_internal_method_tests_do_not_establish_reachability(self):
        for test in self.mappings["requirements"]["REQ-0001.01"]["tests"].values():
            test["level"] = "internal"
        self.assertBlocked("test-only")

    def test_receipt_cannot_replace_executing_production_registration(self):
        path = self.project / "wurst/Fixture.wurst"
        path.write_text(path.read_text().replace('\tinstall()\n', ''))
        self.evidence, self.transcript = self.make_evidence()
        self.assertBlocked("integration-missing")

    def test_static_test_tokens_without_executed_receipts_block(self):
        self.receipts = []
        self.evidence, self.transcript = self.make_evidence()
        self.assertBlocked("static-only")

    def test_stale_test_source_and_failed_execution_cannot_be_reused(self):
        path = self.project / "wurst/Fixture.wurst"
        path.write_text(path.read_text() + '// changed after execution\n')
        self.assertBlocked("integration-missing")
        self.evidence["status"] = "fail"
        self.assertBlocked("integration-missing")

    def test_added_or_deleted_production_source_invalidates_execution(self):
        path = self.project / "wurst/Extra.wurst"
        path.write_text("package Extra\n")
        self.assertBlocked("integration-missing")
        self.evidence["inputs"]["wurst/Extra.wurst"] = trace.sha(path.read_bytes())
        self.evidence["inputSetSha256"] = execution.sha(execution.canonical(self.evidence["inputs"]))
        self.assertEqual("pass", self.report()["status"])
        path.unlink()
        self.assertBlocked("integration-missing")

    def test_shared_source_hashes_are_checked_in_the_flattened_compiler_namespace(self):
        shared = self.project.parent / "_shared/wurst"
        shared.mkdir(parents=True)
        path = shared / "Mechanism.wurst"
        path.write_text("package Mechanism\n")
        self.evidence["inputs"]["wurst/Mechanism.wurst"] = trace.sha(path.read_bytes())
        self.evidence["inputSetSha256"] = execution.sha(execution.canonical(self.evidence["inputs"]))
        self.assertEqual("pass", self.report()["status"])
        path.write_text("package Mechanism\n// modified after execution\n")
        self.assertBlocked("integration-missing")

    def test_grill_normalized_build_file_is_not_mistaken_for_stale_source(self):
        build = self.project / "wurst.build"
        build.write_text('projectName: Fixture\nscriptMode: LUA\nwc3Patch: v3.0\n')
        self.evidence["inputs"]["wurst.build"] = trace.sha(b'---\nprojectName: Fixture\nwc3Patch: v3.0\nscriptMode: LUA\n')
        self.evidence["inputSetSha256"] = execution.sha(execution.canonical(self.evidence["inputs"]))
        self.assertEqual("pass", self.report()["status"])
        build.unlink()
        self.assertBlocked("integration-missing")

    def test_self_consistent_transcript_cannot_omit_a_current_test(self):
        path = self.project / "wurst/Fixture.wurst"
        path.write_text(path.read_text() + "@test function anotherTest()\n\tskip\n")
        self.evidence, self.transcript = self.make_evidence()
        # The protocol hashes are current, but only fixture() was executed.
        self.assertBlocked("integration-missing")

    def test_receipts_after_terminal_test_result_are_not_execution_evidence(self):
        receipts, self.receipts = self.receipts, []
        self.evidence, self.transcript = self.make_evidence()
        self.transcript += ''.join('TRACEABILITY ' + json.dumps(row) + '\n' for row in receipts).encode()
        self.evidence["logSha256"] = execution.sha(self.transcript)
        self.assertBlocked("integration-missing")

    def test_authority_sub_bullet_new_prose_and_removed_clause_cannot_be_dropped(self):
        path = self.project / "docs/lock.md"
        path.write_text(path.read_text() + '  - Reject interrupted transfer.\n\nRecovery must retain the old save.\n')
        self.assertBlocked("authority-drift")
        self.ledger["requirements"][0]["obligations"].pop()
        self.assertBlocked("authority-drift")

    def test_whole_authority_document_cannot_be_excluded(self):
        (self.project / "docs/roadmap.md").write_text("- <!-- req:ROAD-0001 --> Another locked behavior.\n")
        errors = trace.authority_errors(self.project, self.ledger, ["docs/lock.md", "docs/roadmap.md"])
        self.assertIn("authoritative document set omitted or changed", errors)
        self.assertTrue(any("ROAD-0001" in message for message in errors))

    def test_scenario_content_cannot_substitute_for_framework(self):
        row = self.mappings["requirements"]["REQ-0001.01"]
        row["content"] = row.pop("mechanism")
        self.assertBlocked("data-only")

    def test_catalogue_count_mismatch_fails_candidate_readiness(self):
        self.catalogue.write_text('[{"id":"port"},{"id":"missing-city"}]')
        report = self.assertBlocked("census-mismatch")
        self.assertEqual(2, report["catalogues"][0]["sourceCount"])
        self.assertEqual(1, report["catalogues"][0]["packagedUniqueCount"])

    def test_same_count_wrong_ids_and_changed_records_also_block(self):
        self.runtime["settlements"] = [{"id": "wrong-city"}]
        self.write_artifact()
        self.assertBlocked("census-mismatch")
        self.runtime["settlements"] = [{"id": "port", "controller": "wrong-polity"}]
        self.write_artifact()
        self.assertBlocked("census-mismatch")

    def test_extra_compiled_registration_cannot_hide_behind_matching_json_counts(self):
        self.script += b'\nregisterSettlement("ghost")\n'
        self.write_artifact()
        report = self.assertBlocked("census-mismatch")
        self.assertEqual(["ghost"], report["catalogues"][0]["maps"][0]["compiledUnexpectedIds"])

    def test_shared_constructor_allows_only_explicit_authoritative_companion_ids(self):
        companion = self.project / "other-catalogue.json"
        companion.write_text('[{"id":"harbor"}]')
        self.specs[0]["compiledCompanions"] = [{"path": "other-catalogue.json", "selector": "*", "idPrefix": "defense:", "idSuffix": ":primary"}]
        self.script += b'\nregisterSettlement("defense:harbor:primary")\n'
        self.write_artifact()
        self.assertEqual("pass", self.report()["status"])
        companion.write_text('[]')
        self.assertBlocked("census-mismatch")

    def test_inlined_catalogue_identities_are_counted_from_real_lua_assignments(self):
        self.specs[0].pop("compiledIdPattern")
        self.specs[0].update(compare="ids", runtime={"representation": "compiled-identities"},
                             compiledIdPatterns=[r'\bSettlement_id_storage\[[^\]]+\]\s*=\s*{id}\s*$'])
        self.runtime.pop("settlements")  # No duplicated JSON manifest is needed.
        self.script += b'\nSettlement_id_storage[1] = "port"\nSettlement_id_storage[2] = ""\n'
        self.write_artifact()
        report = self.report()
        self.assertEqual("pass", report["status"])
        self.assertEqual(1, report["catalogues"][0]["packagedUniqueCount"])
        self.script = self.script.replace(b'Settlement_id_storage[1] = "port"', b'print([[Settlement_id_storage[1] = "port"]])\n-- Settlement_id_storage[1] = "port"')
        self.write_artifact()
        self.assertBlocked("census-mismatch")

    def test_duplicate_packaged_catalogue_ids_block(self):
        self.runtime["settlements"] *= 2
        self.write_artifact()
        self.assertBlocked("census-mismatch")

    def test_union_distribution_does_not_bypass_geographic_partition(self):
        self.catalogue.write_text('[{"id":"port","map":"somewhere-else"}]')
        self.runtime["settlements"] = [{"id": "port", "map": "somewhere-else"}]
        self.specs[0].update(distribution="union", partition={"sourceField": "map", "mapField": "assignments"})
        self.maps[0]["assignments"] = ["here"]
        self.write_artifact()
        self.assertBlocked("census-mismatch")

    def test_only_final_embedded_payload_counts_not_build_directory(self):
        # Mutating an intermediate after final packaging cannot change a census.
        (self.project / "built.w3x").write_bytes(b"an unrelated intermediate")
        self.assertEqual("pass", self.report()["status"])
        self.runtime["settlements"] = []
        self.write_artifact()
        self.assertBlocked("census-mismatch")

    def test_omitted_census_or_unlisted_archive_payload_blocks(self):
        self.specs = []
        self.assertBlocked("census-mismatch")
        outer = trace._members(self.artifact)
        outer["hidden.lua"] = b"hidden"
        write_mpq(self.artifact, outer)
        self.assertBlocked("artifact-missing")

    def test_byte_composition_accounts_all_members_without_double_counting(self):
        report = self.report()["artifact"]
        outer = report["composition"]
        self.assertEqual(sum(outer["categories"].values()), outer["decodedBytes"])
        self.assertEqual(self.artifact.stat().st_size, outer["archiveBytes"])
        self.assertEqual(outer["archiveBytes"], sum(outer["storedCategories"].values()) + outer["containerOverheadBytes"])
        nested = report["nestedDecodedCategories"]
        for category in ("compiled_lua", "runtime_data", "terrain", "pathing", "object_data", "imported_assets"):
            self.assertGreater(nested[category], 0)
        self.assertGreater(outer["categories"]["embedded_maps"], 0)
        self.assertGreater(outer["categories"]["campaign_metadata"], 0)

    def test_broken_runtime_retains_embedded_map_byte_composition(self):
        self.write_artifact({"runtime/scenario-runtime.json": b"{broken"})
        report = self.assertBlocked("artifact-missing")
        self.assertGreater(report["artifact"]["nestedDecodedCategories"]["runtime_data"], 0)
        self.assertGreater(report["artifact"]["nestedDecodedCategories"]["terrain"], 0)

    def test_unexpected_map_blocks_but_remains_in_byte_composition(self):
        outer = trace._members(self.artifact)
        outer["maps/unexpected.w3x"] = (self.project / "built.w3x").read_bytes()
        outer["(listfile)"] = ("\n".join(outer) + "\n").encode()
        write_mpq(self.artifact, outer)
        report = self.assertBlocked("artifact-missing")
        self.assertEqual(2, len(report["artifact"]["maps"]))
        self.assertEqual(2 * len(b"terrain"), report["artifact"]["nestedDecodedCategories"]["terrain"])

    def test_compressed_member_storage_is_distinct_from_decoded_size(self):
        members = trace._members(self.project / "built.w3x")
        members["war3mapimported/icon.blp"] = b"asset" * 10000
        nested = self.project / "compressed.w3x"
        with zipfile.ZipFile(nested, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
        outer = trace._members(self.artifact)
        outer["maps/region.w3x"] = nested.read_bytes()
        write_mpq(self.artifact, outer)
        report = self.report()["artifact"]
        self.assertLess(report["nestedStoredCategories"]["imported_assets"], report["nestedDecodedCategories"]["imported_assets"])
        row = report["maps"][0]
        self.assertEqual(row["archiveBytes"], sum(row["storedCategories"].values()) + row["containerOverheadBytes"])

    def test_cross_system_endpoints_need_explicit_executed_interaction(self):
        endpoints = ["REQ-0001.01", "REQ-0001.02"]
        self.ledger["dependencies"] = [{"id": "DEP-capture", "interaction": "combat changes ownership", "requirements": endpoints}]
        for clause in self.ledger["requirements"][0]["obligations"]:
            clause["dependencyIds"] = ["DEP-capture"]
        self.assertBlocked("dependency-uncovered")
        joint = copy.deepcopy(self.mappings["requirements"][endpoints[0]])
        joint["requirements"] = endpoints
        for case, test in joint["tests"].items():
            test["receipt"]["requirement"] = "DEP-capture"
            self.receipts.append(test["receipt"])
        self.mappings["dependencies"]["DEP-capture"] = joint
        self.evidence, self.transcript = self.make_evidence()
        self.assertEqual("pass", self.report()["status"])
        del joint["tests"]["failure"]
        self.assertBlocked("dependency-uncovered")

    def test_dependency_edge_cannot_be_removed_while_obligations_still_require_it(self):
        for clause in self.ledger["requirements"][0]["obligations"]:
            clause["dependencyIds"] = ["DEP-capture"]
        self.assertBlocked("authority-drift")

    def test_required_failure_stale_and_replay_cases_cannot_be_exempted(self):
        self.ledger["requirements"][0]["requiredCases"] = ["success"]
        self.assertBlocked("authority-drift")

    def test_upload_recomputes_census_from_exact_extracted_w3n(self):
        config = release.load_release_config()
        trace_report = self.report()
        payloads = {config["archive"]["campaignPath"]: self.artifact.read_bytes(),
                    "Metadata/wurst-execution.json": release.canonical(self.evidence),
                    "Metadata/wurst-execution.log": self.transcript,
                    "Metadata/requirement-traceability.json": release.canonical(trace_report)}
        manifest = {"format": release.MANIFEST_FORMAT, "releaseCandidateId": config["releaseCandidateId"],
                    "sourceRevision": "a"*40, "schemaCompatibility": {"supportedSaveSchemas": [1, 2, 3, 4, 5, 6, 7]},
                    "artifacts": [{"kind": "campaign" if name.endswith(".w3n") else "evidence", "archivePath": name,
                                   "bytes": len(value), "sha256": trace.sha(value)} for name, value in payloads.items()]}
        payloads[config["archive"]["manifestPath"]] = release.canonical(manifest)
        payloads[config["archive"]["provenancePath"]] = release.canonical({
            "format": release.PROVENANCE_FORMAT, "sourceRevision": "a"*40,
            "gates": {"wurstExecution": "pass", "requirementTraceability": "pass"}})
        uploaded = self.project / "candidate.zip"
        release._write_zip(uploaded, payloads)

        def validate(extracted, evidence, log, revision):
            self.assertEqual(self.artifact.read_bytes(), extracted.read_bytes())
            report = trace.audit(self.project, self.ledger, self.mappings, self.specs, self.maps,
                                 artifact=extracted, evidence=evidence, transcript=log, revision=revision)
            trace.require_ready(report)
            return report

        # Binary structure is covered by the real MPQ integration tests; this
        # fixture isolates the actual final-payload traceability/upload boundary.
        with patch.object(release, "load_campaign_config", return_value=SimpleNamespace(maps=[])), \
             patch.object(release, "inspect_campaign"), patch.object(release, "verify_campaign_runtime"), \
             patch.object(release, "_campaign_rows", return_value=[]), \
             patch.object(scenario, "validate_final", side_effect=validate) as gate:
            release.verify_release_archive(uploaded, config)
            gate.assert_called_once()
            # Even a checksum-consistent archived PASS becomes invalid when the
            # authoritative expected catalogue differs from the final payload.
            self.catalogue.write_text('[{"id":"port"},{"id":"new-port"}]')
            with self.assertRaisesRegex(release.PackagingError, "traceability blocks candidate publication"):
                release.verify_release_archive(uploaded, config)

    def test_candidate_builder_blocks_before_writing_zip_and_removes_stale_candidate(self):
        config = release.load_release_config()
        evidence_dir = self.project / "_build/wurst-tests"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "results.json").write_bytes(release.canonical(self.evidence))
        (evidence_dir / "execution.log").write_bytes(self.transcript)
        output = self.project / "_build/release" / config["archive"]["fileName"]
        output.parent.mkdir()
        output.write_bytes(b"stale candidate")
        self.catalogue.write_text('[{"id":"port"},{"id":"missing-city"}]')

        def current_report(artifact=None, evidence=None, transcript=None, revision=""):
            if artifact is not None:
                self.assertEqual(self.artifact.read_bytes(), artifact.read_bytes())
            return self.report()

        with patch.object(release, "PROJECT", self.project), \
             patch.object(scenario, "PROJECT", self.project), \
             patch.object(scenario, "build_report", side_effect=current_report), \
             patch.object(release, "load_release_config", return_value=config), \
             patch.object(release, "validate_gates", return_value=({}, {}, {}, [])), \
             patch.object(release, "load_campaign_config", return_value=SimpleNamespace(maps=[])), \
             patch.object(release, "authoritative_hashes", return_value={}), \
             patch.object(release, "build_campaign", return_value=self.artifact), \
             patch.object(release, "normalized_campaign", return_value={}), \
             patch.object(release, "verify_campaign_runtime", return_value={}) as legacy, \
             patch.object(release, "_write_zip") as publish:
            with self.assertRaisesRegex(release.PackagingError, "traceability blocks candidate publication"):
                release.build_release_candidate(revision="a"*40)
            publish.assert_not_called()
            legacy.assert_not_called()
        self.assertFalse(output.exists())
        self.assertTrue((output.parent / "requirement-traceability.json").is_file())

    def test_compiler_cleanup_failure_preserves_current_source_diagnostics_only(self):
        config = release.load_release_config()
        build_dir = self.project / "_build"
        final_report = build_dir / "release/requirement-traceability.json"
        final_report.parent.mkdir(parents=True)
        final_report.write_text('{"candidateReady":true}')
        source_report = self.report()

        def compilation_failure(*args):
            self.assertFalse(final_report.exists())
            shutil.rmtree(build_dir)
            raise release.PackagingError("compiler failed")

        with patch.object(release, "PROJECT", self.project), \
             patch.object(release, "load_release_config", return_value=config), \
             patch.object(scenario, "build_report", return_value=source_report), \
             patch.object(release, "_build_release_candidate", side_effect=compilation_failure):
            with self.assertRaisesRegex(release.PackagingError, "compiler failed"):
                release.build_release_candidate(revision="a"*40)
        self.assertEqual(source_report, trace.load(build_dir / "requirement-traceability-source.json"))
        self.assertFalse(final_report.exists())

    def test_upload_verification_failure_never_exposes_candidate_path(self):
        output = self.project / "release/candidate.zip"
        with patch.object(release, "verify_release_archive", side_effect=release.PackagingError("census mismatch")):
            with self.assertRaisesRegex(release.PackagingError, "census mismatch"):
                release.publish_verified_archive(output, {"evidence": b"unverified"}, {})
        self.assertFalse(output.exists())
        self.assertEqual([], list(output.parent.iterdir()))


class AuthoritativeInventoryTests(unittest.TestCase):
    def test_complete_ledger_and_report_are_current_and_honest(self):
        ledger = trace.load(scenario.DIRECTORY / "requirements.json")
        self.assertEqual([], trace.authority_errors(PROJECT, ledger))
        self.assertGreater(len(ledger["requirements"]), 470)
        self.assertGreater(sum(len(row["obligations"]) for row in ledger["requirements"]), 640)
        self.assertGreaterEqual(len(ledger["dependencies"]), 22)
        report = scenario.build_report()
        self.assertFalse(report["candidateReady"])
        self.assertEqual(trace.canonical(report), scenario.REPORT.with_suffix(".json").read_bytes())
        self.assertEqual(trace.render_markdown(report), scenario.REPORT.with_suffix(".md").read_text())

    def test_failed_final_gate_writes_diagnostics_before_refusing_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(scenario, "PROJECT", Path(directory)), patch.object(scenario, "build_report", return_value={
                    "status": "fail", "candidateReady": False, "blockerCount": 1, "blockers": [{"id": "x", "class": "unmapped", "message": "gap"}],
                    "requirements": [], "dependencies": [], "catalogues": [], "artifact": None}):
                with self.assertRaisesRegex(ValueError, "blocks candidate publication"):
                    scenario.validate_final(Path("final.w3n"), {}, b"", "a"*40)
                self.assertTrue((Path(directory)/"_build/release/requirement-traceability.json").is_file())


if __name__ == "__main__":
    unittest.main()
