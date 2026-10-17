"""Immutable early-stage research records; never a trading acceptance registry.

The adapter owns the analysis schema and decision_readiness owns acceptance.
This translator binds their existing vocabulary without minting accepted-scoped
artifacts or guessing future portfolio/instruction fingerprints.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

try:
    from .research_checkpoint import (artifact_path, canonical, identifier,
        make_reference, sha256, timestamp, verify_reference, _atomic, _safe_directory, _lock)
    from .scoped_research_adapter import validate_package, validate_output, needs_continuation, MODELS, _no_credentials
    from .decision_readiness import SCOPED_COVERAGE
    from .alert_contract import GATES
except ImportError:
    from research_checkpoint import (artifact_path, canonical, identifier,
        make_reference, sha256, timestamp, verify_reference, _atomic, _safe_directory, _lock)
    from scoped_research_adapter import validate_package, validate_output, needs_continuation, MODELS, _no_credentials
    from decision_readiness import SCOPED_COVERAGE
    from alert_contract import GATES

TYPES = {'request', 'evidence-packet', 'research-result', 'review', 'opportunity-dossier', 'disposition'}
COMMON = {'schema_version', 'id', 'version', 'record_type', 'case_id', 'created_at',
          'observed_at', 'origin', 'provenance_refs', 'unknowns', 'supersedes', 'content'}
REQUEST_FIELDS = {'entity', 'security', 'question', 'holding_window', 'mode',
                  'evidence_cutoff', 'required_coverage', 'stopping_conditions'}
DOSSIER_FIELDS = {'request', 'research', 'expectations', 'price_response', 'holding_window',
    'costs', 'adverse_cases', 'entry_conditions', 'exits', 'reassessment_triggers', 'cash_comparison'}
ADVERSE_CASES = {'no-repricing', 'adverse-surprise', 'delayed-catalyst', 'overnight-gap', 'too-late'}


def _exact(value, keys, message):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(message)


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 40000:
        raise ValueError('Nonempty bounded text required')


def _texts(value, *, nonempty=False):
    if not isinstance(value, list) or len(value) > 1000 or (nonempty and not value):
        raise ValueError('Explicit bounded text list required')
    for item in value:
        _text(item)


def _json(root, ref):
    path = verify_reference(root, ref)
    if path.stat().st_size > 2_000_000:
        raise ValueError('Research artifact too large')
    return json.loads(path.read_text(encoding='utf-8'))


def _record(root, ref, kind, case_id, *, now, stack):
    record = _json(root, ref)
    validate_record(root, record, now=now, _stack=stack)
    if record['record_type'] != kind or record['case_id'] != case_id:
        raise ValueError('Wrong case or record type')
    return record


def envelope(case_id, kind, content, *, record_id, created_at, origin,
             provenance_refs, unknowns, version=1, observed_at=None, supersedes=None):
    return dict(schema_version=1, id=record_id, version=version, record_type=kind,
        case_id=case_id, created_at=created_at, observed_at=observed_at or created_at,
        origin=origin, provenance_refs=provenance_refs, unknowns=unknowns,
        supersedes=supersedes or [], content=content)


def _request(content, now):
    _exact(content, REQUEST_FIELDS, 'Request contract differs')
    _text(content['entity'])
    security = content['security']
    _exact(security, {'legal_entity', 'identifier', 'exchange', 'share_class',
                       'trading_currency', 'price_unit', 'reporting_currency'}, 'Exact security identity required')
    for value in security.values():
        _text(value)
    if security['legal_entity'] != content['entity']:
        raise ValueError('Entity/security mismatch')
    for key in ('question', 'holding_window', 'mode'):
        _text(content[key])
    if timestamp(content['evidence_cutoff']) > now:
        raise ValueError('Future evidence cutoff')
    _texts(content['required_coverage'], nonempty=True)
    if set(content['required_coverage']) != SCOPED_COVERAGE or len(content['required_coverage']) != len(SCOPED_COVERAGE):
        raise ValueError('All nine scoped coverage categories required')
    _texts(content['stopping_conditions'], nonempty=True)


def _context(request, job):
    expected = request['content']
    security = expected['security']
    context = job.get('packet', {}).get('context', {})
    if (job['as_of'] != expected['evidence_cutoff'] or
        context.get('entity') != expected['entity'] or
        context.get('security') != security['identifier'] or
        context.get('currency') != security['reporting_currency'] or
        set(job['scope']['required_categories']) != set(expected['required_coverage'])):
        raise ValueError('Job does not bind the request identity/cutoff/coverage')


def scoped_artifact(job, result, meta):
    """Reuse existing readiness vocabulary without manufacturing acceptance.

    Absent scenarios remain null. Raw claims and numerical assumptions stay in
    the referenced adapter output; this is deterministic indexing, not another
    model summary or an accepted analytical review.
    """
    facts=[dict(id=s['source_id'],path=s['path'],sha256=s['sha256'],
                publication_at=s['published_at'],read_at=s['accessed_at'],locations=s['read_locations']) for s in job['sources']]
    assumptions=[dict(conclusion_id=c['id'],**number) for c in result['conclusions']
                 for number in c['numerical_inputs'] if number['basis']=='assumption']
    contrary=next((c['evidence'] for c in result['coverage'] if c['category']=='contrary_evidence'),[])
    return dict(kind='scoped-company-review' if job['role']=='analysis' else 'scoped-analytical-review',
        label='Unaccepted scoped research; separate from full thesis, portfolio allocation and execution',
        status='unaccepted-scoped',analytical_execution_status=result['status'],
        methodology_sha256=job['methodology']['base']['sha256'],
        scoped_methodology_reference=job['methodology']['scoped'],
        coverage={c['category']:c['status'] for c in result['coverage']},
        claims=result['conclusions'],contrary_evidence=contrary,assumptions=assumptions,scenarios=None,
        scenario_status='not independently structured by the adapter; affected opportunity claims remain unaccepted',
        findings=[dict(id=f['id'],assessment=f['claim'],material=f['severity']=='material',
            status='resolved' if f['outcome']=='resolved' else 'withheld',
            affected_conclusions=f['affected_conclusions']) for f in result['findings']],
        limitations=result['gaps'],source_facts=facts,evidence_refs=[{k:s[k] for k in ('id','path','sha256')} for s in facts],
        check_records=[],window=dict(reviewed_at=meta['completed_at'] if job['role']=='review' else None,expires_at=None),
        disposition='active',disposition_authority='separate version-bound disposition record required',
        gate_activation=False)


def _execution(root, content, role, *, case_id, now, stack):
    _exact(content, {'request', 'job', 'result', 'execution', 'target_record', 'artifact'}, 'Research translation contract differs')
    request = _record(root, content['request'], 'request', case_id, now=now, stack=stack)
    job, result, meta = (_json(root, content[key]) for key in ('job', 'result', 'execution'))
    validate_package(root, job)
    if job['role'] != role or job.get('schema_version') != 2:
        raise ValueError('Compact job role mismatch')
    _context(request, job)
    validate_output(result, job, root)
    if 'processing' in meta:
        try:
            from .research_processing import processing_context
        except ImportError:
            from research_processing import processing_context
        processing_context(root, meta['processing'], verify_reference(root, content['result']).read_bytes(), execution=meta, now=now)
    elif 'processing_receipt' in meta:
        raise ValueError('Processed execution lacks explicit public lineage')
    if content['artifact']!=scoped_artifact(job,result,meta):
        raise ValueError('Translated readiness artifact differs from the validated scoped output')
    if (meta.get('job_id') != job['job_id'] or meta.get('role') != role or
        meta.get('model_requested') != MODELS[role] or meta.get('reasoning_effort') != 'high' or
        meta.get('speed') != 'standard' or meta.get('selected_route_completed') is not True or
        meta.get('execution_outcome') != 'completed' or
        meta.get('output_sha256') != content['result']['sha256'] or
        meta.get('target_sha256') != job['target']['sha256'] or
        meta.get('actual_model') not in {None, MODELS[role]} or
        not meta.get('dispatch_id') or meta.get('authentication') != 'chatgpt-subscription'):
        raise ValueError('Execution evidence does not bind the validated output/route')
    if meta.get('case_id',case_id)!=case_id:
        raise ValueError('Execution belongs to another authorized case')
    if timestamp(meta['started_at']) > timestamp(meta['completed_at']) or timestamp(meta['completed_at']) > now:
        raise ValueError('Execution chronology invalid')
    # Fixture results are useful for engineering tests but remain explicitly
    # simulated. Real dispositions cannot be promoted from them below.
    if meta.get('engineering_test') is not True and meta.get('runtime_verified_live') is not True:
        raise ValueError('Live execution lacks verified restrictions')
    if meta.get('engineering_test') is not True:
        try:
            from .scoped_research_queue import package_sha256
            from .scoped_research_adapter import _packet
        except ImportError:
            from scoped_research_queue import package_sha256
            from scoped_research_adapter import _packet
        packet=_packet(root,job)
        if meta.get('archived_package_sha256')!=package_sha256(job) or meta.get('packet_sha256')!=packet['sha256']:
            raise ValueError('Live execution package or packet binding differs')
    if role == 'review':
        target = _record(root, content['target_record'], 'research-result', case_id, now=now, stack=stack)
        if target['content']['request'] != content['request'] or target['content']['result']['sha256'] != job['target']['sha256']:
            raise ValueError('Review target differs from the exact analysis result')
        analysis_meta = _json(root, target['content']['execution'])
        if analysis_meta.get('processing'):
            supplied = job['target'].get('processing')
            expected = analysis_meta['processing']
            if not isinstance(supplied, dict) or {k: v.get('sha256') for k, v in supplied.items()} != {k: v['sha256'] for k, v in expected.items()}:
                raise ValueError('Review target omits or changes analysis processing context')
        elif 'processing' in job['target']:
            raise ValueError('Review target invents processing context')
        if meta['dispatch_id'] == analysis_meta['dispatch_id']:
            raise ValueError('Independent review must use a fresh dispatch')
    elif content['target_record'] is not None:
        review = _record(root,content['target_record'],'review',case_id,now=now,stack=stack)
        if review['content']['request']!=content['request'] or review['content']['result']['sha256']!=job['target']['sha256']:
            raise ValueError('Correction must target its exact preceding review')
        findings=_json(root,review['content']['result'])['findings']
        if not any(f['severity']=='material' and f['outcome']!='resolved' for f in findings):
            raise ValueError('Correction requires material findings')
    return request, job, result, meta


def validate_record(root, record, *, now=None, _stack=None):
    now = now or datetime.now(timezone.utc)
    _exact(record, COMMON, 'Versioned research record envelope differs')
    if type(record['schema_version']) is not int or record['schema_version'] != 1 or type(record['version']) is not int or record['version'] < 1:
        raise ValueError('Unsupported record schema/version')
    for key in ('id', 'case_id'):
        identifier(record[key])
    if record['record_type'] not in TYPES:
        raise ValueError('Unknown record family')
    created, observed = timestamp(record['created_at']), timestamp(record['observed_at'])
    if observed > created or created > now:
        raise ValueError('Record chronology invalid')
    # Dependencies and executions must already exist at this record's dated
    # creation, rather than merely existing by the time a projection is rebuilt.
    now = created
    _text(record['origin']); _texts(record['unknowns'])
    _no_credentials(record)
    if len(canonical(record)) > 2_000_000:
        raise ValueError('Record exceeds size bound')
    stack = set(_stack or ())
    identity = (record['case_id'], record['id'], record['version'])
    if identity in stack or len(stack) > 20:
        raise ValueError('Cyclic or excessive record references')
    stack.add(identity)
    for field in ('provenance_refs', 'supersedes'):
        if not isinstance(record[field], list) or len(record[field]) > 1000:
            raise ValueError('Explicit bounded reference list required')
        for ref in record[field]:
            verify_reference(root, ref)
    if not record['provenance_refs']:
        raise ValueError('Source or originating artifact reference required')
    if (record['version'] == 1 and record['supersedes']) or (record['version'] > 1 and len(record['supersedes']) != 1):
        raise ValueError('Successor requires exactly one predecessor; first version cannot supersede')
    for ref in record['supersedes']:
        older = _json(root, ref)
        validate_record(root,older,now=now,_stack=stack)
        if (older.get('id'), older.get('case_id'), older.get('record_type')) != (record['id'], record['case_id'], record['record_type']) or older.get('version', 0) != record['version']-1 or timestamp(older['created_at'])>created:
            raise ValueError('Supersession must bind an older version of this record')
    c, kind, cid = record['content'], record['record_type'], record['case_id']
    if kind == 'request':
        _request(c, now)
    elif kind == 'evidence-packet':
        _exact(c, {'request', 'job', 'packet', 'packet_utf8_bytes', 'original_bytes'}, 'Evidence packet record differs')
        req = _record(root, c['request'], 'request', cid, now=now, stack=stack)
        job = _json(root, c['job']); validate_package(root, job); _context(req, job)
        try:
            from .scoped_research_adapter import _packet
        except ImportError:
            from scoped_research_adapter import _packet
        packet = _packet(root, job)
        verify_reference(root, c['packet'])
        if c['packet']['sha256'] != packet['sha256'] or c['packet_utf8_bytes'] != packet['utf8_bytes'] or c['original_bytes'] != packet['original_bytes']:
            raise ValueError('Evidence packet cannot be reproduced')
    elif kind in {'research-result', 'review'}:
        _execution(root, c, 'review' if kind == 'review' else 'analysis', case_id=cid, now=now, stack=stack)
    elif kind == 'opportunity-dossier':
        _exact(c, DOSSIER_FIELDS, 'Opportunity dossier contract differs')
        req = _record(root, c['request'], 'request', cid, now=now, stack=stack)
        research = _record(root, c['research'], 'research-result', cid, now=now, stack=stack)
        if research['content']['request'] != c['request'] or c['holding_window'] != req['content']['holding_window']:
            raise ValueError('Dossier scope differs from company research')
        for field in ('expectations', 'price_response', 'entry_conditions', 'exits', 'reassessment_triggers', 'cash_comparison'):
            _text(c[field])
        if not isinstance(c['adverse_cases'], dict) or set(c['adverse_cases']) != ADVERSE_CASES:
            raise ValueError('All adverse mechanisms must be considered')
        for text in c['adverse_cases'].values(): _text(text)
        costs = c['costs']
        _exact(costs, {'schedule', 'currency', 'round_trip', 'limitations'}, 'Exact cost contract required')
        _text(costs['currency']); _texts(costs['limitations'])
        if costs['schedule'] is None:
            if costs['round_trip'] is not None or not costs['limitations']:
                raise ValueError('Unverified cost schedule cannot supply a numerical cost')
        else:
            verify_reference(root, costs['schedule'])
            if costs['round_trip'] is not None:
                try:
                    amount = Decimal(costs['round_trip']) if isinstance(costs['round_trip'], str) else None
                except InvalidOperation as exc:
                    raise ValueError('Exact decimal cost required') from exc
                if amount is None or not amount.is_finite() or amount < 0:
                    raise ValueError('Exact nonnegative decimal cost required')
    else:
        _exact(c, {'research', 'review', 'dossier', 'status', 'rationale', 'reopening_conditions', 'expires_at'}, 'Disposition contract differs')
        if c['status'] not in {'supported', 'rejected', 'parked'}: raise ValueError('Explicit research disposition required')
        _text(c['rationale']); _texts(c['reopening_conditions'], nonempty=c['status'] == 'parked')
        research = _record(root, c['research'], 'research-result', cid, now=now, stack=stack)
        review = _record(root, c['review'], 'review', cid, now=now, stack=stack)
        dossier = _record(root, c['dossier'], 'opportunity-dossier', cid, now=now, stack=stack)
        if review['content']['target_record'] != c['research'] or dossier['content']['research'] != c['research']:
            raise ValueError('Disposition does not bind matching research/review/dossier')
        review_output = _json(root, review['content']['result'])
        if review_output['status'] != 'review-complete': raise ValueError('Independent review incomplete')
        if c['expires_at'] is not None and timestamp(c['expires_at']) <= created:
            raise ValueError('Disposition expiry precedes creation')
        if c['status'] == 'supported':
            analysis = _json(root, research['content']['result'])
            if analysis['status'] != 'scoped-analysis-complete' or record['unknowns'] or research['unknowns'] or dossier['unknowns']:
                raise ValueError('Incomplete research cannot support opportunity disposition')
            if needs_continuation(review_output):
                raise ValueError('Incomplete independent review cannot support opportunity disposition')
            if any(f['severity'] == 'material' and f['outcome'] != 'resolved' for f in review_output['findings']):
                raise ValueError('Material unresolved review findings')
            if dossier['content']['costs']['schedule'] is None or c['expires_at'] is None:
                raise ValueError('Supported opportunity needs verified costs and bounded expiry')
    return record


def save_record(root, record, *, now=None):
    root = Path(root).resolve()
    validate_record(root, record, now=now)
    relative = 'monitoring/research-engine/cases/' + record['case_id'] + '/' + record['id'] + '-r' + str(record['version']).zfill(3) + '.json'
    with _lock(root):
        folder = _safe_directory(root, str(Path(relative).parent))
        target = folder / Path(relative).name
        data = canonical(record) + b'\n'
        if target.exists():
            if target.is_symlink() or target.read_bytes() != data:
                raise ValueError('Record version is immutable')
        else:
            _atomic(target, data)
    return make_reference(root, relative)


def translate_scoped(root, *, request, job, result, execution, case_id, record_id,
                     created_at, unknowns, target_record=None, origin='scoped adapter translation',
                     version=1,supersedes=None):
    """Deterministic translation retains raw schema output and exact identities."""
    role = _json(root, job)['role']
    raw_job,raw_result,raw_meta=(_json(root,ref) for ref in (job,result,execution))
    content = dict(request=request, job=job, result=result, execution=execution, target_record=target_record,
                   artifact=scoped_artifact(raw_job,raw_result,raw_meta))
    return save_record(root, envelope(case_id, 'review' if role == 'review' else 'research-result',
        content, record_id=record_id, created_at=created_at, origin=origin,
        provenance_refs=[request, job, result, execution] + ([target_record] if target_record else []),
        unknowns=unknowns,version=version,supersedes=supersedes))


def project_case(root, disposition_ref, *, now=None):
    """Read-only current revalidation. No files or acceptance entries are written."""
    now = now or datetime.now(timezone.utc)
    result = dict(schema_version=1, id='research-case-projection', observed_at=now.isoformat(),
        authoritative=False, research_disposition='active', review_status='unverified',
        operational_readiness='evidence incomplete', trade_readiness='evidence incomplete',
        edge_evidence='not assessed', activation='disabled', live_recommendations_enabled=False,
        evidence=[], limitations=[], gates=[dict(gate=g, status='evidence incomplete', evidence=[],
            reason='No current version-bound acceptance evaluated') for g in sorted(GATES)])
    try:
        record = _json(root, disposition_ref)
        validate_record(root, record, now=now)
        if record['record_type'] != 'disposition': raise ValueError('Disposition reference required')
        c = record['content']
        research = _json(root, c['research']); review = _json(root, c['review'])
        analysis_meta = _json(root, research['content']['execution'])
        review_meta = _json(root, review['content']['execution'])
        simulated = analysis_meta.get('engineering_test') is True or review_meta.get('engineering_test') is True
        expired = c['expires_at'] is not None and timestamp(c['expires_at']) <= now
        result.update(case_id=record['case_id'], research_disposition=c['status'],
            review_status='fixture-only' if simulated else 'independently-reviewed',
            evidence=[disposition_ref, c['research'], c['review'], c['dossier']],
            limitations=record['unknowns'] + ['Research disposition is not trade gate acceptance.'])
        for gate in result['gates']:
            if gate['gate'] in {'research', 'dossier'}:
                gate.update(status='invalidated' if expired else 'evidence incomplete',
                    evidence=[c['research'] if gate['gate'] == 'research' else c['dossier']],
                    reason='Expired research window' if expired else 'Scoped evidence retained outside trading acceptance registry')
        if simulated: result['limitations'].append('Simulated workers cannot demonstrate actual analytical review or live readiness.')
    except (ValueError, KeyError, TypeError, OSError):
        result.update(research_disposition='active', review_status='invalidated',
                      limitations=['Missing, changed or inconsistent version-bound research evidence; disposition unverified.'])
        for gate in result['gates']:
            if gate['gate'] in {'research', 'dossier'}: gate['status'] = 'invalidated'
    return result


def project_cases(root, *, now=None):
    """Discover only explicit case-record locations; no whole-project ingestion.

    Multiple disposition lineages are ambiguous. A broken newer record cannot
    cause silent fallback to a favorable old version.
    """
    root=Path(root).resolve();now=now or datetime.now(timezone.utc)
    folder=root/'monitoring/research-engine/cases'
    if not folder.exists():return []
    if folder.is_symlink():raise ValueError('Case directory cannot be a symlink')
    projected=[]
    for case in sorted(folder.iterdir()):
        if not case.is_dir() or case.is_symlink():raise ValueError('Invalid case directory')
        identifier(case.name)
        dispositions=[];requests=[];invalid=False
        for path in sorted(case.glob('*-r*.json')):
            try:
                ref=make_reference(root,path.relative_to(root).as_posix())
                record=_json(root,ref);validate_record(root,record,now=now)
                if record['case_id']!=case.name:raise ValueError('Case location differs')
                if record['record_type']=='disposition':dispositions.append((record,ref))
                elif record['record_type']=='request':requests.append(ref)
            except (OSError,ValueError,KeyError,TypeError):invalid=True
        lineages={r['id'] for r,_ in dispositions}
        if dispositions and len(lineages)==1 and not invalid:
            record,ref=max(dispositions,key=lambda item:item[0]['version'])
            projected.append(project_case(root,ref,now=now))
        else:
            # An impossible reference deliberately yields the same sanitized
            # invalidated projection as a changed disposition.
            p=project_case(root,{'path':'monitoring/research-engine/cases/'+case.name+'/missing.json','sha256':'0'*64},now=now)
            p['case_id']=case.name
            if not dispositions and not invalid:
                p.update(review_status='awaiting review',evidence=requests,
                    limitations=['Case prepared; no completed analysis/review/disposition chain.'])
                for gate in p['gates']:gate['status']='evidence incomplete'
            elif len(lineages)>1:p['limitations']=['Multiple disposition lineages; explicit supersession/reconciliation required.']
            projected.append(p)
    return projected
