"""The isolated continuation may use free compute, never unverified storage."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BRANCH = 'fix/dot-wc3-continuation-20261118'
GUARD = f"github.head_ref != '{BRANCH}' && github.ref != 'refs/heads/{BRANCH}'"

class DiagnosticArtifactGuardTests(unittest.TestCase):
    def test_every_artifact_upload_excludes_diagnostic_pr_and_manual_ref(self):
        uploads = 0
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            text = path.read_text()
            for step in re.split(r'(?m)^      - ', text)[1:]:
                if 'uses: actions/upload-artifact@' in step:
                    uploads += 1
                    conditions = re.findall(r'(?m)^        if: (.+)$', step)
                    self.assertEqual(len(conditions), 1, path.name)
                    self.assertIn(GUARD, conditions[0], path.name)
        self.assertEqual(uploads, 6)

    def test_release_and_failed_run_conditions_are_preserved(self):
        text = (ROOT / '.github/workflows/map-build.yml').read_text()
        self.assertIn('if: always() && ' + GUARD, text)
        self.assertIn("if: steps.candidate.outputs.ready == 'true' && (github.event_name != 'push' || github.ref == 'refs/heads/main') && " + GUARD, text)

    def test_map_build_explains_absent_artifacts_for_diagnostic_runs(self):
        text = (ROOT / ".github/workflows/map-build.yml").read_text()
        self.assertIn("if: always() && (github.head_ref ==", text)
        self.assertIn("Earlier artifact-download references do not apply to this run.", text)
        self.assertIn("No downloadable workflow artifacts or release candidate are provided", text)

    def test_no_artifact_substitute_or_cache_action_creates_storage(self):
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            text = path.read_text()
            self.assertNotRegex(text, r'uses: actions/cache(?:/save)?@')
            # The unique branch is an upload exclusion, never a push trigger or job gate.
            header = text.split('\njobs:\n', 1)[0]
            self.assertNotIn(BRANCH, header)
            for line in text.splitlines():
                if BRANCH in line:
                    self.assertTrue(line.startswith('        if: '), (path.name, line))

if __name__ == '__main__':
    unittest.main()
