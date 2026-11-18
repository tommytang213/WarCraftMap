"""Bounded diagnostic excerpts only. Never decides candidate readiness."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_ROWS = 12


def safe_text(value, limit):
    if not isinstance(value, str):
        raise ValueError('invalid diagnostic field')
    # One printable ASCII line, no terminal controls or injected workflow lines.
    value = ''.join(c if ' ' <= c <= '~' else ' ' for c in value)
    value = ' '.join(value.split())
    return value[:limit] + ('...' if len(value) > limit else '')


def load_rows(path, kind):
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise ValueError('oversized report')
    with path.open('rb') as source:
        payload = source.read(MAX_REPORT_BYTES + 1)
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError('oversized report')
    report = json.loads(payload)
    expected = ('warcraftmap_requirement_traceability_v1' if kind == 'traceability'
                else 'age_of_sail_release_blocker_report_v2')
    if not isinstance(report, dict) or report.get('format') != expected:
        raise ValueError('unsupported report format')
    rows = report.get('blockers' if kind == 'traceability' else 'findings')
    if not isinstance(rows, list):
        raise ValueError('missing diagnostic entries')
    if kind == 'release':
        taxonomy = report.get('taxonomy')
        if not isinstance(taxonomy, list) or any(not isinstance(t, dict) or
                not isinstance(t.get('id'), str) or type(t.get('releaseBlocking')) is not bool for t in taxonomy):
            raise ValueError('invalid release taxonomy')
        blocking = {t['id'] for t in taxonomy if t['releaseBlocking']}
        if any(not isinstance(row, dict) or not isinstance(row.get('severity'), str) or
               row['severity'] not in {t['id'] for t in taxonomy} or
               not isinstance(row.get('disposition'), str) for row in rows):
            raise ValueError('invalid finding classification')
        rows = [row for row in rows if row['disposition'] == 'unresolved' and row['severity'] in blocking]
    # Validate every selected row before printing a potentially misleading subset.
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in ('id', 'class', 'message')):
            raise ValueError('invalid diagnostic entry')
    return rows


def render(diagnostics):
    lines = ['Release blocker excerpt (diagnostic only; candidate remains blocked).']
    for filename, kind in [('requirement-traceability.json', 'traceability'),
                           ('release-blocker-audit.json', 'release')]:
        try:
            rows = load_rows(diagnostics / filename, kind)
        except (OSError, ValueError, TypeError, RecursionError):
            # Do not echo malformed payloads, exception contents or filesystem paths.
            lines.append(f'{kind}: report unavailable, malformed or too large; blocker details cannot be listed.')
            continue
        shown = rows[:MAX_ROWS]
        lines.append(f'{kind}: {len(rows)} blocking entries; showing {len(shown)}.')
        for row in shown:
            lines.append('  blocker: ' + safe_text(row['id'], 100) + ' [' +
                         safe_text(row['class'], 80) + '] ' + safe_text(row['message'], 240))
        lines.append(f'{kind}: {len(rows) - len(shown)} additional blocking entries omitted from this excerpt.')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diagnostics', type=Path, required=True)
    parser.add_argument('--summary', type=Path, required=True)
    args = parser.parse_args()
    text = render(args.diagnostics)
    print(text, end='')
    with args.summary.open('a') as summary:
        summary.write('\n<pre>\n' + html.escape(text) + '</pre>\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
