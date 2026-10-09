"""Read-only operational evidence summary; never certifies trial or trading acceptance."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Operational timestamps need an explicit timezone')
    return parsed.astimezone(timezone.utc)


def summarize(conn, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Report cutoff needs an explicit timezone')
    state = dict(conn.execute('SELECT key,value FROM monitor_state'))
    started = instant(state['trial_started_at']) if state.get('trial_started_at') else None
    if started and started > now:
        raise ValueError('Trial start is after report cutoff')
    sources = {}
    checks = conn.execute('SELECT source,checked_at,outcome,changes_detected FROM monitor_checks').fetchall()
    for source, checked, outcome, changed in sorted(checks, key=lambda row: instant(row[1])):
        when = instant(checked)
        if when > now:
            raise ValueError('Recorded source check is after report cutoff')
        item = sources.setdefault(source, {'checks': 0, 'successful_checks': 0, 'failed_checks': 0,
            'changes_detected': 0, 'first_check': checked, 'last_check': checked,
            'last_success': None, 'largest_gap_between_checks_seconds': None})
        if item['checks']:
            gap = (when - instant(item['last_check'])).total_seconds()
            if gap < 0:
                raise ValueError('Inconsistent timestamp ordering')
            item['largest_gap_between_checks_seconds'] = max(gap, item['largest_gap_between_checks_seconds'] or 0)
        item['checks'] += 1
        item['last_check'] = checked
        if outcome in ('baseline', 'changed', 'unchanged'):
            item['successful_checks'] += 1
            item['last_success'] = checked
        elif outcome == 'failed':
            item['failed_checks'] += 1
        else:
            raise ValueError('Unrecognized source-check outcome')
        item['changes_detected'] += changed
    return {'created_at': now.isoformat(), 'trial_started_at': started.isoformat() if started else None,
        'elapsed_wall_days': (now-started).total_seconds()/86400 if started else None,
        'last_recorded_tick': state.get('last_service_tick'), 'sources': sources,
        'uptime_fraction': None, 'uptime_limitation': 'The last tick and sparse source checks do not measure continuous uptime. Gaps are observed intervals, not proven outages or complete scheduled-slot coverage.',
        'phone_delivery_verified': None, 'phone_scope': 'Not evaluated by this source-history report',
        'acceptance': 'pending-independent-operational-evaluation',
        'analytical_approval': False, 'actionable': False,
        'scope': 'Observed source-check records only. Counts do not establish full-document reading, comprehensive news coverage, fourteen days of successful operation, failure-test acceptance or investment quality.'}


def read_report(database, now=None):
    path = Path(database).resolve(strict=True)
    conn = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        return summarize(conn, now)
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=str(Path(__file__).resolve().parents[1]/'state/observation/operations.sqlite3'))
    args = parser.parse_args()
    print(json.dumps(read_report(args.database), indent=2))
