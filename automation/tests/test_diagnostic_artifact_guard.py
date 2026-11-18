"""The isolated continuation may use free compute, never unverified storage."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BRANCH = 'fix/dot-wc3-continuation-20261118'
GUARD = f"github.head_ref != '{BRANCH}' && github.ref != 'refs/heads/{BRANCH}'"

SUMMARY_GUARD = ('              if [ "${GITHUB_HEAD_REF:-}" = "' + BRANCH + '" ] || '
                 '[ "${GITHUB_REF:-}" = "refs/heads/' + BRANCH + '" ]; then')


def branch_mentions_are_diagnostic_only(filename, text):
    if BRANCH in text.split('\njobs:\n', 1)[0]:
        return False
    permitted = set()
    if filename == 'map-build.yml':
        # Only this already-blocked summary arm can mention the branch in shell.
        prefix = ('            blocked)\n'
                  '              echo "ready=false" >> "$GITHUB_OUTPUT"\n'
                  '              if ! python3 maps/historical-world-rpg/age-of-sail-world/tooling/print_release_blockers.py --diagnostics "$artifact_dir/diagnostics" --summary "$GITHUB_STEP_SUMMARY"; then\n'
                  '                echo "::warning::Blocker excerpt unavailable; candidate remains blocked. See validation logs."\n'
                  '              fi\n')
        fragment = prefix + SUMMARY_GUARD
        if text.count(fragment) == 1:
            permitted.add(text[:text.index(fragment) + len(prefix)].count('\n'))
    # Only conditions on actual upload steps, or the explicit logs-only notice,
    # may exclude this branch. Validation steps must never inherit an exemption.
    for match in re.finditer(r'(?m)^      - (.*?)(?=^      - |\Z)', text, re.DOTALL):
        step = match.group(0)
        upload = bool(re.search(r'(?m)^        uses: actions/upload-artifact@', step) or
                      re.search(r'^      - uses: actions/upload-artifact@', step))
        notice = (filename == 'map-build.yml' and step.startswith('      - name: Explain diagnostic-only artifact policy\n')
                  and all(not line.strip() or line.startswith(('      - name:', '        if:', '        run:', '          echo '))
                          for line in step.splitlines()))
        if (upload and not re.search(r'(?m)^        run:', step)) or notice:
            start = text[:match.start()].count('\n')
            for offset, line in enumerate(step.splitlines()):
                if line.startswith('        if: '):
                    permitted.add(start + offset)
    return all(index in permitted for index, line in enumerate(text.splitlines()) if BRANCH in line)

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
            # Branch mentions remain upload/diagnostic guards, never triggers or job gates.
            header = text.split('\njobs:\n', 1)[0]
            self.assertNotIn(BRANCH, header)
            self.assertTrue(branch_mentions_are_diagnostic_only(path.name, text), path.name)

    def test_validation_steps_cannot_exclude_diagnostic_branch(self):
        text = (ROOT / '.github/workflows/map-build.yml').read_text()
        for label in ('Run mandatory validation', 'Compile sources'):
            changed = text + '\n      - name: ' + label + '\n        if: ' + GUARD + '\n        run: python3 validate.py\n'
            self.assertFalse(branch_mentions_are_diagnostic_only('map-build.yml', changed))
        changed = text.replace('      - name: Explain diagnostic-only artifact policy',
                               '      - name: Skip validation on continuation')
        self.assertFalse(branch_mentions_are_diagnostic_only('map-build.yml', changed))

    def test_summary_exception_cannot_allow_other_branch_shell_or_triggers(self):
        text = (ROOT / '.github/workflows/map-build.yml').read_text()
        self.assertTrue(branch_mentions_are_diagnostic_only('map-build.yml', text))
        self.assertFalse(branch_mentions_are_diagnostic_only('other.yml', text))
        for changed in (text.replace('echo "ready=false"', 'echo "ready=true"'),
                        text + '\n' + SUMMARY_GUARD,
                        text.replace('            blocked)', '            ready)'),
                        'on: ["' + BRANCH + '"]\n' + text):
            self.assertFalse(branch_mentions_are_diagnostic_only('map-build.yml', changed))

if __name__ == '__main__':
    unittest.main()
