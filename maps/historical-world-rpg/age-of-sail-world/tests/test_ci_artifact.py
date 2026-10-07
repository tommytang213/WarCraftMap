import re
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[4]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "map-build.yml"
TYPECHECK_WORKFLOW = REPOSITORY / ".github" / "workflows" / "wurst-typecheck.yml"


class MapArtifactWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.typecheck_workflow = TYPECHECK_WORKFLOW.read_text(encoding="utf-8")

    def test_validation_and_typecheck_precede_upload(self):
        source_validation = self.workflow.index("validate_map_source.py")
        package = self.workflow.index("./tooling/package_release_candidate.sh")
        verify = self.workflow.index("verify_ci_release_artifact.py")
        upload = self.workflow.index("actions/upload-artifact@")
        self.assertLess(source_validation, package)
        self.assertLess(package, verify)
        self.assertLess(verify, upload)
        packager = REPOSITORY / "maps/historical-world-rpg/_shared/tooling/package_wurst_campaign.py"
        self.assertIn('[executable, "typecheck"]', packager.read_text())

    def test_expected_artifact_path_name_and_retention_are_fixed(self):
        self.assertIn("_build/release/AgeOfSailWorld-phase9-rc1.zip", self.workflow)
        self.assertIn("name: age-of-sail-world-release-candidate", self.workflow)
        self.assertIn("--source-revision \"$SOURCE_REVISION\"", self.workflow)
        self.assertIn("artifact-evidence.json", self.workflow)
        self.assertRegex(self.workflow, r"retention-days:\s+14\b")
        self.assertIn("if-no-files-found: error", self.workflow)

    def test_upload_uses_the_copied_verified_payload_and_checkout_revision(self):
        # Together with the executable upload-verifier integration test, bind
        # the workflow's copy, digest input and upload directory to one payload.
        self.assertIn('-e SOURCE_REVISION="$GITHUB_SHA"', self.workflow)
        self.assertIn('artifact_dir="$RUNNER_TEMP/age-of-sail-release"', self.workflow)
        self.assertIn('-v "$artifact_dir:/out"', self.workflow)
        self.assertIn('cp "/tmp/workspace/$RELEASE_ARTIFACT" /out/AgeOfSailWorld-phase9-rc1.zip', self.workflow)
        self.assertRegex(self.workflow, r'verify_ci_release_artifact\.py\s+\\\s+"/out/AgeOfSailWorld-phase9-rc1\.zip"')
        self.assertIn('--evidence "/out/artifact-evidence.json"', self.workflow)
        self.assertIn('path: ${{ runner.temp }}/age-of-sail-release', self.workflow)
        self.assertIn('set -eu', self.workflow)
        self.assertNotIn('continue-on-error:', self.workflow)
        player_upload = self.workflow.split('- name: Upload Age of Sail campaign', 1)[1]
        self.assertNotIn('always()', player_upload)
        for step in ('Create versioned player files', 'Confirm verified release payload and evidence',
                     'Upload Age of Sail campaign'):
            body = self.workflow.split('- name: ' + step, 1)[1].split('- name:', 1)[0]
            self.assertIn("if: steps.candidate.outputs.ready == 'true'", body)

    def test_failed_requirement_gate_retains_only_diagnostics_and_stops_publication(self):
        diagnostics = self.workflow.split('- name: Retain requirement diagnostics', 1)[1].split('- name:', 1)[0]
        self.assertIn('if: always()', diagnostics)
        self.assertIn('path: ${{ runner.temp }}/age-of-sail-release/diagnostics', diagnostics)
        self.assertNotIn('.w3n', diagnostics)
        self.assertNotIn('.zip', diagnostics)
        stop = self.workflow.index('if [ "$candidate_status" -ne 0 ]; then exit "$candidate_status"; fi')
        copy = self.workflow.index('cp "/tmp/workspace/$RELEASE_ARTIFACT"')
        self.assertLess(stop, copy)
        self.assertIn('requirement-traceability.*', self.workflow)
        self.assertIn('requirement_traceability_audit.py --check', self.workflow)

    def test_candidate_shell_only_exposes_a_verified_ready_archive(self):
        # Execute the workflow's actual publication branch. Only the expensive
        # build and separate upload verifier are stubbed; report copying, exit
        # handling, status output and candidate copying use real temporary files.
        container = textwrap.dedent(self.workflow.split('              candidate_status=0', 1)[1]
                                   .split("\n            '\n", 1)[0])
        container = 'candidate_status=0\n' + container
        host = textwrap.dedent(self.workflow.split('          case "$(cat ', 1)[1]
                              .split('\n      - name:', 1)[0])
        host = 'case "$(cat ' + host
        cases = [(0, 0, True, True, 'ready'), (3, 0, True, False, 'blocked'),
                 (1, 0, True, False, None), (2, 0, True, False, None),
                 (99, 0, True, False, None), (0, 1, True, True, None),
                 (3, 0, False, False, None), (3, 0, True, True, None)]
        for build_exit, verify_exit, reports, candidate, expected in cases:
            with self.subTest(build=build_exit, verifier=verify_exit, reports=reports, candidate=candidate), \
                 tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / 'workspace/campaign'
                release_dir = project / '_build/release'
                release_dir.mkdir(parents=True)
                out = root / 'out'
                out.mkdir()
                if reports:
                    for suffix in ('.json', '.md'):
                        (release_dir / ('requirement-traceability' + suffix)).write_text('current diagnostics')
                if candidate:
                    (release_dir / 'candidate.zip').write_bytes(b'verifier input')
                script = container.replace('/tmp/workspace', str(root / 'workspace')).replace('/out', str(out))
                environment = {**os.environ, 'MAP_PROJECT': 'campaign',
                               'RELEASE_ARTIFACT': 'campaign/_build/release/candidate.zip',
                               'SOURCE_REVISION': 'a'*40, 'BUILD_EXIT': str(build_exit),
                               'VERIFY_EXIT': str(verify_exit), 'VERIFIED': str(out / 'verified')}
                result = subprocess.run(['sh', '-ec',
                                         'su() { return "$BUILD_EXIT"; }\n'
                                         'python3() { echo invoked > "$VERIFIED"; return "$VERIFY_EXIT"; }\n' + script],
                                        env=environment, text=True, capture_output=True)
                status = out / 'candidate-status'
                self.assertEqual(expected is not None, result.returncode == 0, result.stderr)
                self.assertEqual(expected is not None, status.exists())
                self.assertEqual(build_exit == 0, (out / 'verified').exists())
                self.assertEqual(build_exit == 0, (out / 'AgeOfSailWorld-phase9-rc1.zip').exists())
                if reports:
                    self.assertTrue((out / 'diagnostics/requirement-traceability.json').exists())
                if expected:
                    self.assertEqual(expected, status.read_text().strip())
                    output = out / 'github-output'
                    summary = out / 'github-summary'
                    host_result = subprocess.run(['bash', '-ec', host], text=True, capture_output=True,
                                                 env={**environment, 'artifact_dir': str(out), 'GITHUB_OUTPUT': str(output),
                                                      'GITHUB_STEP_SUMMARY': str(summary)})
                    self.assertEqual(0, host_result.returncode, host_result.stderr)
                    self.assertEqual('ready=' + ('true' if expected == 'ready' else 'false') + '\n', output.read_text())
                    if expected == 'blocked':
                        self.assertIn('Candidate publication: blocked', summary.read_text())
                        self.assertIn('No player candidate was published', summary.read_text())

    def test_missing_or_unknown_publication_status_fails_ci(self):
        host = 'case "$(cat ' + textwrap.dedent(self.workflow.split('          case "$(cat ', 1)[1]
                                              .split('\n      - name:', 1)[0])
        for status in (None, '', 'unknown', 'ready\nblocked'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if status is not None:
                    (root / 'candidate-status').write_text(status)
                output = root / 'github-output'
                result = subprocess.run(['bash', '-ec', host], text=True, capture_output=True,
                                        env={**os.environ, 'artifact_dir': str(root), 'GITHUB_OUTPUT': str(output)})
                self.assertNotEqual(0, result.returncode)
                self.assertFalse(output.exists())

    def test_container_builds_do_not_mutate_repository_bind_mounts(self):
        for workflow in (self.workflow, self.typecheck_workflow):
            self.assertIn('-v "$PWD:/source:ro"', workflow)
            self.assertNotIn('-v "$PWD:/workspace"', workflow)
            self.assertNotIn("chown -R wurstuser:wurstuser /source", workflow)
            self.assertNotIn("chown -R wurstuser:wurstuser /workspace", workflow)
            self.assertIn("cp -a /source /tmp/workspace", workflow)

    def test_actions_and_wurst_image_are_immutable(self):
        actions = re.findall(r"uses:\s+[^\s@]+@([^\s#]+)", self.workflow)
        self.assertGreaterEqual(len(actions), 2)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in actions))
        self.assertRegex(self.workflow, r"frotty/wurstscript@sha256:[0-9a-f]{64}")
        config = REPOSITORY / "maps/historical-world-rpg/age-of-sail-world/wurst.build"
        self.assertIn("wc3Patch: v3.0", config.read_text())
        self.assertIn("scriptMode: LUA", config.read_text())

    def test_required_validation_and_both_release_paths_execute_tests(self):
        shared = REPOSITORY / "maps/historical-world-rpg/_shared/tooling"
        map_build = (shared / "package_wurst_map.py").read_text().split("def build(", 1)[1]
        campaign = (shared / "package_wurst_campaign.py").read_text().split("def build_campaign(", 1)[1]
        self.assertLess(map_build.index("execute_tests("), map_build.index('[executable, "build"'))
        self.assertLess(campaign.index("run_execution_tests("), campaign.index("for physical in config.maps:"))
        self.assertIn("./tooling/package_release.sh", self.typecheck_workflow)
        checks = (REPOSITORY / "automation/run_checks.sh").read_text()
        self.assertIn('WARCRAFTMAP_WURST_CHECK:-required', checks)
        self.assertIn("./tooling/package_release.sh", checks)
        self.assertIn('-v "$repo_root:/source:ro"', checks)
        self.assertIn('chown -R wurstuser:wurstuser /tmp/historical-world-rpg', checks)
        self.assertIn('su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg/age-of-sail-world && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh"', checks)
        self.assertNotIn('chown -R wurstuser:wurstuser /source', checks)
        self.assertNotIn("frotty/wurstscript:latest", checks)
        self.assertNotIn("grill install wurstscript", checks)
        image = re.search(r"frotty/wurstscript@sha256:[0-9a-f]{64}", self.workflow)[0]
        for source in (checks, self.typecheck_workflow, (shared / "wurst_execution.py").read_text()):
            self.assertIn(image, source)
        for workflow in (self.workflow, self.typecheck_workflow):
            self.assertIn('-e SOURCE_REVISION="$GITHUB_SHA"', workflow)
            self.assertNotIn("continue-on-error:", workflow)
        release = (REPOSITORY / "maps/historical-world-rpg/age-of-sail-world/tooling/package_release_candidate.py").read_text()
        self.assertIn('archive.read("Metadata/wurst-execution.json")', release)
        self.assertIn('archive.read("Metadata/wurst-execution.log")', release)


if __name__ == "__main__":
    unittest.main()
