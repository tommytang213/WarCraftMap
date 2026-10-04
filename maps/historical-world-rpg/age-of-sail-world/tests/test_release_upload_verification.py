"""Final payload checks are independent of pre-packaging validation results."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tooling'))
import package_release_candidate as release
import verify_ci_release_artifact as upload


class ReleaseUploadTests(unittest.TestCase):
    def fixture(self, root):
        config = release.load_release_config()
        campaign = b'checksum-consistent but structurally invalid campaign'
        manifest = {
            'format': release.MANIFEST_FORMAT,
            'releaseCandidateId': config['releaseCandidateId'],
            'sourceRevision': 'a' * 40,
            'schemaCompatibility': {'supportedSaveSchemas': [1, 2, 3, 4, 5]},
            'artifacts': [{'kind': 'campaign',
                           'archivePath': config['archive']['campaignPath'],
                           'bytes': len(campaign),
                           'sha256': hashlib.sha256(campaign).hexdigest()}],
        }
        provenance = {'format': release.PROVENANCE_FORMAT, 'sourceRevision': 'a' * 40}
        path = root / 'candidate.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(config['archive']['campaignPath'], campaign)
            archive.writestr(config['archive']['manifestPath'], json.dumps(manifest))
            archive.writestr(config['archive']['provenancePath'], json.dumps(provenance))
        return path, config, campaign

    def test_final_archive_rechecks_extracted_runtime_despite_matching_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            path, config, campaign = self.fixture(Path(directory))
            def reject(extracted, campaign_config):
                self.assertEqual(campaign, extracted.read_bytes())
                raise release.PackagingError('invalid nested map structure')
            with patch.object(release, 'load_campaign_config', return_value=SimpleNamespace(maps=[])), \
                 patch.object(release, 'inspect_campaign'), \
                 patch.object(release, 'verify_campaign_runtime', side_effect=reject) as verify:
                with self.assertRaisesRegex(release.PackagingError, 'invalid nested map structure'):
                    release.verify_release_archive(path, config)
                verify.assert_called_once()

    def test_upload_evidence_binds_exact_bytes_and_revision_and_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, _, _ = self.fixture(root)
            evidence = root / 'evidence.json'
            arguments = ['verify', str(path), '--source-revision', 'a' * 40,
                         '--evidence', str(evidence)]
            # Structural inspection is covered separately; exercise the real CLI
            # digest and revision boundary with a deliberately small ZIP fixture.
            with patch.object(upload, 'verify_release_archive') as verify, patch.object(sys, 'argv', arguments):
                self.assertEqual(0, upload.main())
                verify.assert_called_once()
            result = json.loads(evidence.read_text())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), result['sha256'])
            self.assertEqual(path.stat().st_size, result['bytes'])
            self.assertEqual('a' * 40, result['sourceRevision'])
            evidence.unlink()
            arguments[3] = 'b' * 40
            with patch.object(upload, 'verify_release_archive'), patch.object(sys, 'argv', arguments):
                with self.assertRaisesRegex(SystemExit, 'source revision mismatch'):
                    upload.main()
            self.assertFalse(evidence.exists())
