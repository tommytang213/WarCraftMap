"""Regenerate source audits without treating focused tests as a full suite."""
from pathlib import Path
import gzip
import json
import sys

project = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(project / 'tooling'), str(project.parent / '_shared/tooling')]
from integration_evidence import source_identity
from wurst_execution import source_revision
import release_blocker_audit
import runtime_acceptance
import requirement_traceability_audit

folder = Path(__file__).resolve().parent
revision = source_revision(project)
identity = source_identity(project, revision)
reports = {
    'release': release_blocker_audit.build_report(revision=revision),
    'runtime': runtime_acceptance.audit_acceptance(revision=revision),
    'traceability': requirement_traceability_audit.build_report(revision=revision),
}
index = dict(sourceIdentity=identity, scope='Fresh source audits; full-suite execution and packaged campaign evidence deferred to controller. Publication remains blocked.', reports={})
for name, report in reports.items():
    assert all(report[k] == v for k, v in identity.items()), name
    filename = name + '-audit.json.gz'
    (folder / filename).write_bytes(gzip.compress((json.dumps(report, indent=2, sort_keys=True) + '\n').encode(), mtime=0))
    index['reports'][name] = dict(file=filename, status=report['status'], blockerCount=report.get('blockerCount', report.get('unresolvedCampaignBlockers')))
(folder / 'audits.json').write_text(json.dumps(index, indent=2, sort_keys=True) + '\n')
print(json.dumps(index, indent=2))
