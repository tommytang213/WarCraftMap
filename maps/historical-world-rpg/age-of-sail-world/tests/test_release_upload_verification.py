"""Final payload checks are independent of pre-packaging validation results."""
import hashlib
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tooling'))
import package_release_candidate as release
import verify_ci_release_artifact as upload
from warcraft_campaign import write_mpq
import warcraft_campaign as mpq


class ReleaseNormalizationTests(unittest.TestCase):
    def test_encrypted_members_support_compression_sectors_fixed_keys_and_partial_words(self):
        files = {'(listfile)': b'nested/data.bin\r\n',
                 'nested/data.bin': bytes(range(256)) * 33 + b'xyz'}

        def encrypt(value, key):
            aligned = len(value) & ~3
            return mpq._encrypt(value[:aligned], key & 0xffffffff) + value[aligned:]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'encrypted.w3x'
            for single in (False, True):
                for compressed in (False, True):
                    for fixed in (False, True):
                        with self.subTest(single=single, compressed=compressed, fixed=fixed):
                            write_mpq(path, files)
                            template = path.read_bytes()
                            block_at = struct.unpack_from('<I', template, 20)[0]
                            data_at = block_at + len(files) * 16
                            blocks, data = [], bytearray()
                            for name, value in sorted(files.items()):
                                offset = data_at + len(data)
                                key = mpq._hash(name.rsplit('/', 1)[-1], 3)
                                if fixed:
                                    key = ((key + offset) ^ len(value)) & 0xffffffff
                                chunks = ([value] if single else
                                          [value[start:start + 4096] for start in range(0, len(value), 4096)])
                                encoded = []
                                for index, chunk in enumerate(chunks):
                                    candidate = b'\x02' + zlib.compress(chunk)
                                    packed = candidate if compressed and len(candidate) < len(chunk) else chunk
                                    encoded.append(encrypt(packed, key + index))
                                if compressed and not single:
                                    offsets = [(len(encoded) + 1) * 4]
                                    for chunk in encoded:
                                        offsets.append(offsets[-1] + len(chunk))
                                    table = encrypt(struct.pack(f'<{len(offsets)}I', *offsets), key - 1)
                                else:
                                    table = b''
                                packed = table + b''.join(encoded)
                                flags = mpq.FILE_EXISTS | mpq.FILE_ENCRYPTED
                                flags |= mpq.FILE_SINGLE_UNIT if single else 0
                                flags |= mpq.FILE_COMPRESS if compressed else 0
                                flags |= mpq.FILE_FIX_KEY if fixed else 0
                                blocks.append(struct.pack('<IIII', offset, len(packed), len(value), flags))
                                data.extend(packed)
                            header = bytearray(template[:block_at])
                            struct.pack_into('<I', header, 8, data_at + len(data))
                            path.write_bytes(header + mpq._encrypt(b''.join(blocks), mpq._hash('(block table)', 3)) + data)
                            self.assertEqual(files, mpq.MpqReader(path).members())
                            self.assertEqual({'nested/data.bin': release.sha_bytes(files['nested/data.bin'])},
                                             release.normalized_map(path))

    def campaign(self, root, name, *, timestamp=0, reverse=False, changed=None,
                 unlisted=False, attributes_flags=2):
        files = {'war3map.lua': b'function main() end', 'war3map.w3e': b'terrain',
                 'runtime/scenario-runtime.json': b'{"mapId":"africa"}'}
        if changed:
            files[changed] += b'changed gameplay content'
        names = sorted(files, reverse=reverse)
        files['(listfile)'] = ('\r\n'.join(names) + '\r\n').encode()
        if unlisted:
            files['hidden.lua'] = b'unlisted gameplay code'
        files['(attributes)'] = struct.pack('<II', 100, attributes_flags) + struct.pack(
            '<Q', timestamp) * (len(files) + 1)
        nested = root / (name + '.w3x')
        write_mpq(nested, files)
        payload = bytearray(nested.read_bytes())
        # All members are uncompressed single-unit files: either sector size
        # is valid and changes only MPQ container metadata.
        if reverse:
            struct.pack_into('<H', payload, 14, 4)
        outer = root / (name + '.w3n')
        write_mpq(outer, {
            'Maps/Africa.w3x': bytes(payload), 'war3campaign.w3f': b'campaign metadata',
            'campaign-manifest.json': json.dumps({'maps': [
                {'id': 'africa', 'sha256': hashlib.sha256(payload).hexdigest()}
            ]}).encode(),
        })
        return outer, SimpleNamespace(maps=[SimpleNamespace(package_path='Maps/Africa.w3x')])

    def test_real_mpq_contents_ignore_container_order_timestamps_and_sector_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, config = self.campaign(root, 'first')
            second, _ = self.campaign(root, 'second', timestamp=42, reverse=True)
            self.assertNotEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(release.normalized_campaign(first, config),
                             release.normalized_campaign(second, config))

    def test_real_mpq_gameplay_changes_are_never_normalized_away(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, config = self.campaign(root, 'first')
            for member in ('war3map.lua', 'war3map.w3e', 'runtime/scenario-runtime.json'):
                with self.subTest(member=member):
                    second, _ = self.campaign(root, 'second', changed=member)
                    self.assertNotEqual(release.normalized_campaign(first, config),
                                        release.normalized_campaign(second, config))

    def test_incomplete_listfile_cannot_hide_archived_gameplay_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path, config = self.campaign(Path(directory), 'unlisted', unlisted=True)
            with self.assertRaisesRegex(release.PackagingError, 'does not cover every archived member'):
                release.normalized_campaign(path, config)

    def test_unknown_attributes_cannot_be_discarded_as_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path, config = self.campaign(Path(directory), 'patch-flags', attributes_flags=8)
            with self.assertRaisesRegex(release.PackagingError, 'unsupported MPQ attributes layout'):
                release.normalized_campaign(path, config)


class ReleaseUploadTests(unittest.TestCase):
    def test_malformed_candidate_configuration_is_rejected_without_attribute_error(self):
        original = json.loads(release.CONFIG.read_text())
        variants = ["pass", [], None]
        variants += [{**original, key: value}
                     for key in ("requiredGates", "archive", "runtimeTarget", "audit", "releaseDocuments")
                     for value in ("pass", None)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            for config in variants:
                path.write_text(json.dumps(config))
                with self.subTest(config=config), self.assertRaisesRegex(release.PackagingError, "RC configuration stage failed"):
                    release.load_release_config(path)

    def test_copied_archive_requires_exact_acceptance_and_completed_publication_gates(self):
        from wurst_execution_fixture import passing_evidence
        identity = {'sourceRevision': 'a' * 40, 'sourceTreeSha256': 'b' * 64}
        current = release.runtime_acceptance.audit_sources()
        current.update(identity)
        current['executionStatus'] = 'completed'
        for level in ('runtimeIntegration', 'builtArtifact'):
            current['evidenceLevels'][level].update(identity, status='pass', executionStatus='completed', failures=[])
        current['evidenceLevels']['runtimeIntegration'].update(logSha256='c' * 64, inputSetSha256='d' * 64)
        current['evidenceLevels']['builtArtifact']['artifactSha256'] = 'e' * 64
        for row in current['systems']:
            row.update(executionStatus='completed', executedTests=['synthetic protocol fixture'])
            row['stages'].update({stage: True for stage in release.runtime_acceptance.STAGES})
        release.runtime_acceptance.finalize(current)
        blocker = {'status': 'pass', 'candidateReady': True}
        trace_fixture = {'fixture': 'traceability gate tested separately'}
        report, log = passing_evidence()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, config, campaign = self.fixture(root)
            for mode in ('complete', 'missing', 'releaseValidated=false', 'stale-artifact',
                         'not-run-gate', 'missing-gate', 'stale-integration',
                         'missing-traceability', 'stale-traceability', 'missing-traceability-gate'):
                with self.subTest(mode=mode):
                    recorded = copy.deepcopy(current)
                    gates = {name: 'pass' for name in ('wurstExecution', 'runtimeAcceptance',
                                                     'packagedArtifactVerification', 'zeroCampaignBlockers',
                                                     'requirementTraceability')}
                    if mode == 'releaseValidated=false':
                        recorded['systems'][0]['stages']['releaseValidated'] = False
                    if mode == 'stale-integration':
                        recorded['evidenceLevels']['runtimeIntegration']['sourceRevision'] = 'c' * 40
                    if mode == 'not-run-gate':
                        gates['runtimeAcceptance'] = 'not_run'
                    if mode == 'missing-gate':
                        del gates['packagedArtifactVerification']
                    if mode == 'missing-traceability-gate':
                        del gates['requirementTraceability']
                    payloads = {config['archive']['campaignPath']: campaign,
                                'Metadata/wurst-execution.json': release.canonical(report),
                                'Metadata/wurst-execution.log': log,
                                'Metadata/release-blocker-audit.json': release.canonical(blocker)}
                    if mode != 'missing-traceability':
                        payloads['Metadata/requirement-traceability.json'] = release.canonical(
                            {'stale': True} if mode == 'stale-traceability' else trace_fixture)
                    if mode != 'missing':
                        payloads['Metadata/runtime-acceptance.json'] = release.canonical(recorded)
                    artifact = copy.deepcopy(current['evidenceLevels']['builtArtifact'])
                    if mode == 'stale-artifact':
                        artifact['sourceRevision'] = 'c' * 40
                    manifest = {'format': release.MANIFEST_FORMAT,
                                'releaseCandidateId': config['releaseCandidateId'],
                                'sourceRevision': identity['sourceRevision'],
                                'schemaCompatibility': {'supportedSaveSchemas': [1, 2, 3, 4, 5, 6, 7]},
                                'artifactValidation': artifact,
                                'artifacts': [{'kind': 'payload', 'archivePath': name, 'bytes': len(value),
                                               'sha256': release.sha_bytes(value)} for name, value in payloads.items()]}
                    payloads[config['archive']['manifestPath']] = release.canonical(manifest)
                    payloads[config['archive']['provenancePath']] = release.canonical({
                        'format': release.PROVENANCE_FORMAT, 'sourceRevision': identity['sourceRevision'],
                        'sourceIdentity': identity, 'gates': gates})
                    release._write_zip(path, payloads)
                    # Each expensive verifier has separate production tests;
                    # here exercise the final publication comparison boundary.
                    with patch.object(release, 'load_campaign_config'), \
                         patch.object(release, 'inspect_campaign'), \
                         patch.object(release, 'verify_campaign_runtime'), \
                         patch.object(release, '_campaign_rows', return_value=[]), \
                         patch.object(release, 'source_identity', return_value=identity), \
                         patch.object(release.runtime_acceptance, 'audit_acceptance', return_value=copy.deepcopy(current)), \
                         patch.object(release.traceability, 'validate_final', return_value=trace_fixture), \
                         patch('release_blocker_audit.build_report', return_value=blocker):
                        if mode == 'complete':
                            release.verify_release_archive(path, config)
                        else:
                            with self.assertRaises(release.PackagingError):
                                release.verify_release_archive(path, config)

    def test_execution_failures_block_upload_even_with_checksum_valid_packaging(self):
        from wurst_execution_fixture import passing_evidence
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, config, campaign = self.fixture(root)
            evidence = root / 'upload-evidence.json'
            with zipfile.ZipFile(path) as archive:
                initial_manifest = json.loads(archive.read(config['archive']['manifestPath']))
            for mode in ('pass', 'assertion', 'exception', 'absent-tool', 'missing-execution',
                         'incomplete', 'zero', 'not-run', 'missing-status', 'malformed-json'):
                with self.subTest(mode=mode):
                    report, log = passing_evidence()
                    if mode == 'assertion':
                        log = log.replace(b'OK!', b'FAILED assertion: Expected true')
                    elif mode == 'exception':
                        log = log.replace(b'OK!', b'NullPointerException in interpreter')
                    elif mode == 'absent-tool':
                        report['returnCode'] = 127
                    elif mode == 'incomplete':
                        log = log.replace(b'Finished running tests', b'')
                    elif mode == 'zero':
                        report.update(expected=[], tests=[], discovered=0, succeeded=0)
                        log = b'Running tests\nTests succeeded: 0/0\nFinished running tests\n'
                    elif mode == 'not-run':
                        report['executionStatus'] = 'not_run'
                    elif mode == 'missing-status':
                        del report['executionStatus']
                    report['logSha256'] = hashlib.sha256(log).hexdigest()
                    if mode == 'malformed-json':
                        report = 'pass'
                    trace_fixture = {'fixture': 'traceability gate tested separately'}
                    payloads = {config['archive']['campaignPath']: campaign,
                                'Metadata/requirement-traceability.json': release.canonical(trace_fixture)}
                    if mode != 'missing-execution':
                        payloads['Metadata/wurst-execution.json'] = release.canonical(report)
                        payloads['Metadata/wurst-execution.log'] = log
                    manifest = dict(initial_manifest)
                    manifest['artifacts'] = [
                        {'kind': 'campaign' if name.endswith('.w3n') else 'execution-evidence',
                         'archivePath': name, 'bytes': len(value), 'sha256': release.sha_bytes(value)}
                        for name, value in payloads.items()]
                    payloads[config['archive']['manifestPath']] = release.canonical(manifest)
                    payloads[config['archive']['provenancePath']] = release.canonical({
                        'format': release.PROVENANCE_FORMAT, 'sourceRevision': 'a' * 40,
                        'gates': {'wurstExecution': 'pass', 'requirementTraceability': 'pass'}})
                    release._write_zip(path, payloads)
                    arguments = ['verify', str(path), '--source-revision', 'a' * 40, '--evidence', str(evidence)]
                    # Structural gates intentionally succeed; exercise the real
                    # copied-payload verifier and execution gate before upload.
                    with patch.object(release, 'load_campaign_config', return_value=SimpleNamespace(maps=[])), \
                         patch.object(release, 'inspect_campaign'), \
                         patch.object(release, 'verify_campaign_runtime'), \
                         patch.object(release.traceability, 'validate_final', return_value=trace_fixture), \
                         patch.object(release, '_campaign_rows', return_value=[]), \
                         patch.object(sys, 'argv', arguments):
                        if mode == 'pass':
                            # A passing unrelated suite is not production-path
                            # integration, even with consistent ZIP checksums.
                            with self.assertRaisesRegex(release.PackagingError, 'automated candidate acceptance failed'):
                                upload.main()
                            self.assertFalse(evidence.exists())
                        else:
                            with self.assertRaisesRegex(release.PackagingError, 'Wurst execution evidence'):
                                upload.main()
                            self.assertFalse(evidence.exists())

    def test_source_only_gate_cannot_authorize_candidate_publication(self):
        report = release.runtime_acceptance.audit_sources()
        # A caller cannot promote source metadata by changing only PASS flags.
        report.update(status='pass', candidateReady=True)
        with self.assertRaisesRegex(release.PackagingError, 'automated candidate acceptance failed'):
            release.require_candidate_ready(report)

    def test_malformed_publication_metadata_fails_with_a_gate_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            path, config, _ = self.fixture(Path(directory))
            with zipfile.ZipFile(path) as archive:
                original = {name: archive.read(name) for name in archive.namelist()}
            manifest_name = config['archive']['manifestPath']
            provenance_name = config['archive']['provenancePath']
            manifest = json.loads(original[manifest_name])
            variants = [(name, value) for name in (manifest_name, provenance_name)
                        for value in ('pass', [], None)]
            variants += [(manifest_name, {**manifest, field: value})
                         for field, value in (('schemaCompatibility', 'pass'),
                                              ('artifacts', 'pass'), ('artifacts', ['pass']),
                                              ('artifacts', [{}]), ('sourceRevision', None))]
            for name, value in variants:
                with self.subTest(name=name, value=value):
                    release._write_zip(path, {**original, name: release.canonical(value)})
                    with self.assertRaisesRegex(release.PackagingError, 'release inspection stage failed'):
                        release.verify_release_archive(path, config)

    def test_provenance_includes_selector_compiler_options_and_shared_tooling(self):
        inputs = release.authoritative_hashes()
        for relative in ("wurst-bootstrap/Bootstrap.wurst", "wurst_run.args",
                         "../_shared/tooling/warcraft_map_info.py",
                         "../_shared/tooling/package_wurst_map.py"):
            self.assertEqual(release.sha(release.PROJECT / relative), inputs[relative])

    def fixture(self, root):
        config = release.load_release_config()
        campaign = b'checksum-consistent but structurally invalid campaign'
        manifest = {
            'format': release.MANIFEST_FORMAT,
            'releaseCandidateId': config['releaseCandidateId'],
            'sourceRevision': 'a' * 40,
            'schemaCompatibility': {'supportedSaveSchemas': [1, 2, 3, 4, 5, 6, 7]},
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
            def reject(extracted, campaign_config, **identity):
                self.assertEqual(campaign, extracted.read_bytes())
                self.assertEqual('a' * 40, identity['revision'])
                self.assertEqual(64, len(identity['source_tree_sha256']))
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
