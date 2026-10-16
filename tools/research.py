"""File-based research lifecycle CLI; archives and completed runs are never overwritten."""
import argparse
import hashlib
import json
import os
import re
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def slug(text):
    result = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    if not result or result.upper() in {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1'}:
        raise ValueError('Invalid entity identifier')
    return result


def within(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path escapes intended workspace')
    return path


def init_run(entity_id, legal_name, ticker, *, as_of, mode='full', predecessor=None, root=ROOT):
    root = Path(root)
    date.fromisoformat(as_of)
    company = within(root, root / 'companies' / slug(entity_id))
    company.mkdir(parents=True, exist_ok=True)
    index_path = company / 'index.json'
    index = read_json(index_path) if index_path.exists() else dict(entity_id=slug(entity_id), legal_name=legal_name, latest=None, runs=[])
    if index['legal_name'] != legal_name:
        raise ValueError('Entity id already belongs to another legal entity')
    if predecessor and predecessor not in [r['id'] for r in index['runs']]:
        raise ValueError('Unknown predecessor')
    for seq in range(1, 10000):
        run_id = f'{as_of}-r{seq:03d}'
        run = company / 'runs' / run_id
        if not run.exists():
            break
    run.mkdir(parents=True)
    for folder in ('sources', 'outputs', 'work'):
        (run / folder).mkdir()
    version = read_json(root / 'methodology' / 'current.json')
    method = within(root, root / version['file'])
    record = dict(id=run_id, legal_name=legal_name, ticker=ticker, as_of=as_of, mode=mode, predecessor=predecessor, methodology_version=version['version'], methodology_file=version['file'], methodology_sha256=sha256(method), status='researching', request={}, security={}, evidence_gaps=[], assumptions=[], review_findings=[], checks={}, continuation='Establish security identity and evidence boundary.', model_identity='unknown', stronger_review='pending')
    save_json(run / 'run.json', record)
    save_json(run / 'sources.json', [])
    save_json(run / 'observations.json', [])
    index['runs'].append(dict(id=run_id, mode=mode, status='researching'))
    index['latest_active'] = run_id
    save_json(index_path, index)
    return run


def check_run(run):
    run = Path(run)
    r = read_json(run / 'run.json')
    errors = []
    sources = read_json(run / 'sources.json')
    ids = [s['id'] for s in sources]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate source ids')
    for s in sources:
        if s.get('publication_date') and s['publication_date'] > r['as_of']:
            errors.append(f"Future publication: {s['id']}")
        if s.get('archived_file'):
            archived = within(run, run / s['archived_file'])
            if not archived.exists() or sha256(archived) != s.get('sha256'):
                errors.append(f"Source archive/hash mismatch: {s['id']}")
    for o in read_json(run / 'observations.json'):
        if o.get('status') == 'verified-reported':
            source = next((s for s in sources if s['id'] == o.get('source_id')), None)
            if o.get('value') is None or not source or not source.get('read') or not o.get('location'):
                errors.append(f"Unverified observation: {o.get('metric')}")
        if o.get('status') in {'not-found', 'inaccessible', 'not-applicable'} and o.get('value') is not None:
            errors.append(f"Missing value replaced with number: {o.get('metric')}")
    return errors


def archive(run, url, filename, source_id, title, publisher, publication_date, source_type):
    run = Path(run)
    if (run / 'publication.json').exists():
        raise ValueError('Published run is immutable; create an update')
    if not url.startswith('https://'):
        raise ValueError('Source URL must use HTTPS')
    filename = Path(filename).name
    dest = within(run, run / 'sources' / filename)
    if dest.exists():
        raise ValueError('Source archive already exists')
    record = read_json(run / 'run.json')
    if publication_date and publication_date > record['as_of']:
        raise ValueError('Publication exceeds research as-of date')
    register = read_json(run / 'sources.json')
    if source_id in {s['id'] for s in register}:
        raise ValueError('Source id already exists')
    req = Request(url, headers={'User-Agent': os.environ.get('CR2_USER_AGENT','CompanyResearch2 local public-filings research')})
    with urlopen(req, timeout=45) as response:
        data = response.read(30_000_001)
        if len(data) > 30_000_000:
            raise ValueError('Source exceeds 30 MB archive limit; preserve precise link instead')
    dest.write_bytes(data)
    register.append(dict(id=source_id, title=title, publisher=publisher, type=source_type, publication_date=publication_date, url=url, retrieved=datetime.now(timezone.utc).isoformat(), archived_file=str(dest.relative_to(run)), sha256=sha256(dest), read=False, locations=[]))
    save_json(run / 'sources.json', register)
    return dest


def publish(run, *, root=ROOT):
    run = Path(run)
    if (run / 'publication.json').exists():
        raise ValueError('Run already published')
    r = read_json(run / 'run.json')
    errors = check_run(run)
    required = ('full-report.pdf', 'thesis.pdf', 'valuation.xlsx') if r['mode'] == 'full' else ('pilot.pdf','valuation.xlsx') if r['mode'] == 'pilot' else ('update.pdf',) if r['mode'] == 'update' else ('answer.md',)
    errors += [f'Missing output: {name}' for name in required if not (run / 'outputs' / name).exists()]
    if r['status'] != 'complete' or r.get('continuation'):
        errors.append('Completion status/continuation unresolved')
    if r.get('stronger_review_required') and r.get('stronger_review') != 'passed':
        errors.append('Required stronger review has not passed')
    if any(f.get('material') and not (f.get('resolved') or f.get('limits_conclusion')) for f in r.get('review_findings',[])):
        errors.append('Unresolved material review finding')
    needed = ['arithmetic', 'source_traceability', 'visual_review', 'workbook_recalculation', 'export_roundtrip'] if r['mode'] == 'full' else ['source_traceability', 'visual_review']
    errors += [f'Unchecked: {key}' for key in needed if r.get('checks', {}).get(key) is not True]
    if errors:
        raise ValueError('; '.join(errors))
    files = {str(p.relative_to(run)): sha256(p) for p in run.rglob('*') if p.is_file() and 'work' not in p.relative_to(run).parts and p.name != 'publication.json'}
    save_json(run / 'publication.json', dict(published=datetime.now(timezone.utc).isoformat(), files=files))
    company = run.parents[1]
    index = read_json(company / 'index.json')
    index['latest'] = r['id']
    if index.get('latest_active') == r['id']:
        index['latest_active'] = None
    for row in index['runs']:
        if row['id'] == r['id']:
            row['status'] = 'complete'
    save_json(company / 'index.json', index)


def verify_publication(run):
    run = Path(run)
    return [name for name, expected in read_json(run / 'publication.json')['files'].items() if not (run / name).exists() or sha256(within(run, run / name)) != expected]


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'engine':
        from research_engine import main as engine_main
        sys.exit(engine_main(sys.argv[2:]))
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for key in ('entity-id', 'legal-name', 'ticker', 'as-of'):
        init.add_argument('--' + key, required=True)
    init.add_argument('--mode', choices=['full', 'update', 'focused', 'comparison', 'pilot'], default='full')
    init.add_argument('--predecessor')
    for cmd in ('validate', 'publish', 'verify'):
        sub.add_parser(cmd).add_argument('run')
    sub.add_parser('test')
    sub.add_parser('list')
    checkpoint = sub.add_parser('checkpoint', help='Record an explicit project turn boundary')
    phase = checkpoint.add_mutually_exclusive_group(required=True)
    phase.add_argument('--start', action='store_true')
    phase.add_argument('--complete', action='store_true')
    checkpoint.add_argument('--record', required=True, help='Allowlisted project-relative JSON record')
    sub.add_parser('engine-status', help='Rebuild the research engine checkpoint projection')
    sub.add_parser('engine', help='Explicit case preparation, record translation and read-only case status')
    args = parser.parse_args()
    if args.command in {'checkpoint', 'engine-status'}:
        from research_checkpoint import load_checkpoint_input, record_checkpoint, rebuild_projection
        try:
            if args.command == 'engine-status':
                result = rebuild_projection(ROOT)
            else:
                event = load_checkpoint_input(ROOT, args.record)
                if event.get('phase') != ('start' if args.start else 'complete'):
                    raise ValueError('Record phase differs from explicit command flag')
                result = record_checkpoint(ROOT, event)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except (ValueError, OSError, RuntimeError) as exc:
            parser.error(str(exc))
    elif args.command == 'init':
        print(init_run(args.entity_id, args.legal_name, args.ticker, as_of=args.as_of, mode=args.mode, predecessor=args.predecessor))
    elif args.command == 'test':
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'validation' / 'tests'))
        sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    elif args.command == 'list':
        for p in sorted((ROOT / 'companies').glob('*/index.json')):
            print(json.dumps(read_json(p), ensure_ascii=False))
    elif args.command == 'publish':
        publish(args.run)
        print('Published with immutable hashes')
    else:
        problems = verify_publication(args.run) if args.command == 'verify' else check_run(args.run)
        print(json.dumps({'errors': problems}))
        sys.exit(bool(problems))


if __name__ == '__main__':
    main()
