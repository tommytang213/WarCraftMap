import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'tooling'))
import print_release_blockers as diagnostic


class BlockerExcerptTests(unittest.TestCase):
    def row(self, ident='REQ-1', **extra):
        return dict(id=ident, **{'class': 'unreachable'}, message='A concrete blocked action.', **extra)

    def write(self, root, kind, rows):
        if kind == 'traceability':
            name = 'requirement-traceability.json'
            report = {'format': 'warcraftmap_requirement_traceability_v1', 'blockers': rows}
        else:
            name = 'release-blocker-audit.json'
            report = {'format': 'age_of_sail_release_blocker_report_v2', 'findings': rows,
                      'taxonomy': [{'id': 'campaign_blocker', 'releaseBlocking': True},
                                   {'id': 'minor', 'releaseBlocking': False}]}
        (root / name).write_text(json.dumps(report))

    def test_lists_actual_ids_classes_and_messages_with_exact_omissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, 'traceability', [self.row(f'REQ-{i}') for i in range(20)])
            self.write(root, 'release', [self.row('BLOCK', severity='campaign_blocker', disposition='unresolved'),
                                       self.row('RESOLVED', severity='campaign_blocker', disposition='resolved'),
                                       self.row('MINOR', severity='minor', disposition='unresolved')])
            text = diagnostic.render(root)
            self.assertIn('REQ-0 [unreachable] A concrete blocked action.', text)
            self.assertIn('8 additional blocking entries omitted', text)
            self.assertNotIn('REQ-12 ', text)
            self.assertIn('BLOCK [unreachable]', text)
            self.assertNotIn('RESOLVED', text)
            self.assertNotIn('MINOR', text)

    def test_missing_and_malformed_reports_never_imply_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for payload in [None, 'not JSON SECRET', '[]', '{"format":"future"}',
                            json.dumps({'format': 'warcraftmap_requirement_traceability_v1', 'blockers': [None]})]:
                with self.subTest(payload=payload):
                    if payload is not None:
                        (root / 'requirement-traceability.json').write_text(payload)
                    text = diagnostic.render(root)
                    self.assertEqual(text.count('blocker details cannot be listed'), 2)
                    self.assertIn('candidate remains blocked', text)
                    self.assertNotIn('SECRET', text)

    def test_bounded_safe_stdout_and_html_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hostile = '\n::error::injected\x1b[31m<script>bad</script>```' + 'x' * 2000
            rows = [dict(id=hostile, **{'class': hostile}, message=hostile) for _ in range(30)]
            self.write(root, 'traceability', rows)
            self.write(root, 'release', [])
            summary = root / 'summary'
            result = subprocess.run([sys.executable, str(PROJECT / 'tooling/print_release_blockers.py'),
                                     '--diagnostics', str(root), '--summary', str(summary)],
                                    capture_output=True, text=True, check=True)
            self.assertLess(len(result.stdout), 6500)
            self.assertFalse(any(line.startswith('::') for line in result.stdout.splitlines()))
            self.assertNotIn('\x1b', result.stdout)
            self.assertNotIn('<script>', summary.read_text())
            self.assertIn('&lt;script&gt;', summary.read_text())
            self.assertIn('18 additional blocking entries omitted', result.stdout)

    def test_oversized_report_and_malformed_taxonomy_are_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'requirement-traceability.json'
            with path.open('wb') as stream:
                stream.truncate(diagnostic.MAX_REPORT_BYTES + 1)
            (root / 'release-blocker-audit.json').write_text(json.dumps({
                'format': 'age_of_sail_release_blocker_report_v2', 'findings': [], 'taxonomy': None}))
            self.assertEqual(diagnostic.render(root).count('blocker details cannot be listed'), 2)

    def test_release_totals_include_synthetic_blockers_without_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, 'release', [self.row('BLOCK', severity='campaign_blocker', disposition='unresolved')])
            path = root / 'release-blocker-audit.json'
            report = json.loads(path.read_text())
            report['unresolvedCampaignBlockers'] = 20
            path.write_text(json.dumps(report))
            text = diagnostic.render(root)
            self.assertIn('release: 20 blocking entries; showing 1.', text)
            self.assertIn('19 blocking entries have no finding details', text)
            self.assertIn('19 additional blocking entries omitted', text)
            report['findings'] = []
            path.write_text(json.dumps(report))
            self.assertIn('20 blocking entries; showing 0.', diagnostic.render(root))
            self.assertIn('20 additional blocking entries omitted', diagnostic.render(root))

    def test_invalid_totals_and_unknown_severity_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, 'release', [self.row('BLOCK', severity='campaign_blocker', disposition='unresolved')])
            path = root / 'release-blocker-audit.json'
            report = json.loads(path.read_text())
            for total in (True, -1, 0, '20', 1.5):
                invalid = dict(report, unresolvedCampaignBlockers=total)
                path.write_text(json.dumps(invalid))
                self.assertIn('release: report unavailable', diagnostic.render(root))
            report['findings'][0]['severity'] = 'unknown'
            path.write_text(json.dumps(report))
            self.assertIn('release: report unavailable', diagnostic.render(root))

    def test_checked_in_reports_use_supported_formats(self):
        rows, total = diagnostic.load_rows(PROJECT / 'reports/traceability/requirements.json', 'traceability')
        self.assertTrue(rows)
        rows, total = diagnostic.load_rows(PROJECT / 'reports/release-blocker-audit.json', 'release')
        self.assertTrue(rows)


if __name__ == '__main__':
    unittest.main()
