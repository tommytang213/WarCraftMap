"""Fresh planner audits verify evidence without replacing committed reports."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
import planning_audit


class PlanningAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        (self.project / "physical-maps.json").write_text(json.dumps({
            "outputDirectory": "_build/release", "campaign": {"fileName": "Campaign"}}))
        for name, path in planning_audit.REPORTS.items():
            target = self.project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"status": "pass", "old": name}))
        self.revision = "a" * 40

    def regenerate(self, *, identity_changed=False, crash=False):
        identity = {"sourceRevision": self.revision, "sourceTreeSha256": "b" * 64}
        with mock.patch.object(planning_audit, "PROJECT", self.project), \
             mock.patch.object(planning_audit, "source_identity", side_effect=[identity, {} if identity_changed else identity]), \
             mock.patch.object(planning_audit.release_blocker_audit, "build_report", return_value={"status": "fail"},
                               side_effect=ValueError("broken manifest") if crash else None) as release, \
             mock.patch.object(planning_audit.runtime_acceptance, "audit_acceptance", return_value={"status": "fail"}) as runtime, \
             mock.patch.object(planning_audit.requirement_traceability_audit, "build_report", return_value={"status": "fail"}) as trace:
            result = planning_audit.regenerate(self.revision)
        return result, release, runtime, trace

    def test_all_audits_regenerate_without_rewriting_recorded_passes(self):
        before = {p: p.read_bytes() for p in self.project.rglob("*.json")}
        result, release, runtime, trace = self.regenerate()
        self.assertTrue(result["regenerated"])
        for name in planning_audit.REPORTS:
            self.assertEqual(result["reports"][name]["report"]["status"], "fail")
            self.assertEqual(result["reports"][name]["recorded"]["status"], "pass")
        self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*.json")})
        for audit in (release, runtime):
            self.assertIsNone(audit.call_args.kwargs["execution"])
            self.assertIsNone(audit.call_args.kwargs["campaign"])
            self.assertEqual(audit.call_args.kwargs["revision"], self.revision)
        self.assertEqual(trace.call_args.args, (None, None, None, self.revision))

    def test_available_evidence_is_passed_to_each_verifier_with_new_revision(self):
        execution = self.project / "_build/wurst-tests"
        execution.mkdir(parents=True)
        (execution / "results.json").write_text('{"sourceRevision":"old"}')
        (execution / "execution.log").write_bytes(b"transcript")
        campaign = self.project / "_build/release/Campaign.w3n"
        campaign.parent.mkdir()
        campaign.write_bytes(b"artifact")
        _, release, runtime, trace = self.regenerate()
        for audit in (release, runtime):
            self.assertEqual(audit.call_args.kwargs["execution"], {"sourceRevision": "old"})
            self.assertEqual(audit.call_args.kwargs["revision"], self.revision)
            self.assertEqual(audit.call_args.kwargs["campaign"], campaign)
        self.assertEqual(trace.call_args.args, (campaign, {"sourceRevision": "old"}, b"transcript", self.revision))

    def test_one_audit_crash_preserves_other_findings(self):
        result, _, runtime, trace = self.regenerate(crash=True)
        self.assertIn("broken manifest", result["reports"]["release"]["error"])
        runtime.assert_called_once()
        trace.assert_called_once()

    def test_sources_changing_during_regeneration_cannot_close_gate(self):
        result, _, _, _ = self.regenerate(identity_changed=True)
        self.assertFalse(result["regenerated"])


if __name__ == "__main__":
    unittest.main()
