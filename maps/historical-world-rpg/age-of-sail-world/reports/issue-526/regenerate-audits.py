"""Fresh source-only audits, explicitly insufficient for release closure."""
from pathlib import Path
import gzip
import json
import sys

project = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(project / 'tooling'), str(project.parent / '_shared/tooling')]
import release_blocker_audit
import runtime_acceptance
import requirement_traceability_audit
from integration_evidence import source_identity
from wurst_execution import source_revision

root = Path(__file__).resolve().parent
revision = source_revision(project)
reports = {
    'release': release_blocker_audit.build_report(revision=revision),
    'runtime': runtime_acceptance.audit_acceptance(revision=revision),
    'traceability': requirement_traceability_audit.build_report(revision=revision),
}
summary = {'scope': 'Fresh source-only audits; full-suite, packaged campaign evidence and new-main regeneration remain controller validation.',
           'sourceIdentity': source_identity(project, revision), 'reports': {}}
for name, report in reports.items():
    filename = name + '-audit.json.gz'
    with gzip.GzipFile(str(root / filename), 'wb', mtime=0) as stream:
        stream.write((json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    summary['reports'][name] = {'file': filename, 'status': report['status'],
                              'blockerCount': report.get('blockerCount', report.get('unresolvedCampaignBlockers'))}
(root / 'audits.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary['reports'], sort_keys=True))
