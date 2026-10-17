"""Explicit research case commands. No automatic jobs, acceptance or activation."""
import argparse
import hashlib
import json
from pathlib import Path

from research import ROOT
from research_checkpoint import artifact_path, make_reference, canonical, _atomic, _safe_directory, identifier
from research_records import validate_record, save_record, translate_scoped, project_case, envelope, _context
from scoped_research_adapter import validate_package, _packet
from scoped_research_queue import ScopedQueue


def load(root, path):
    p = artifact_path(root, path)
    if p.stat().st_size > 2_000_000: raise ValueError('Command input exceeds byte bound')
    return json.loads(p.read_text(encoding='utf-8'))


def prepare(root, *, request_path, job_path, record_id, created_at):
    request = make_reference(root, request_path)
    job_ref = make_reference(root, job_path)
    req, job = load(root, request_path), load(root, job_path)
    validate_record(root, req); validate_package(root, job)
    if req['record_type'] != 'request': raise ValueError('Research request required')
    _context(req,job)
    identifier(record_id)
    packet = _packet(root, job)
    relative = 'monitoring/research-engine/cases/' + req['case_id'] + '/packets/' + packet['sha256'] + '.json'
    folder = _safe_directory(root, str(Path(relative).parent)); target = folder / Path(relative).name
    if target.exists():
        if target.is_symlink() or target.read_bytes() != packet['bytes']: raise ValueError('Frozen packet changed')
    else: _atomic(target, packet['bytes'])
    record = envelope(req['case_id'], 'evidence-packet', dict(request=request, job=job_ref,
        packet=make_reference(root, relative), packet_utf8_bytes=packet['utf8_bytes'], original_bytes=packet['original_bytes']),
        record_id=record_id, created_at=created_at, origin='explicit case preparation',
        provenance_refs=[request, job_ref], unknowns=list(req['unknowns']))
    return save_record(root, record)


def export_memory(root,disposition_path):
    """Explicit deterministic reuse of structured outputs; no model summary."""
    disposition_ref=make_reference(root,disposition_path)
    disposition=load(root,disposition_path);validate_record(root,disposition)
    if disposition['record_type']!='disposition':raise ValueError('Disposition required')
    c=disposition['content'];research=load(root,c['research']['path']);review=load(root,c['review']['path'])
    request_ref=research['content']['request'];request=load(root,request_ref['path'])
    records=[];files=[]
    def stable(record):
        return 'cr2-'+hashlib.sha256(canonical([record['case_id'],record['id'],record['version']])).hexdigest()[:32]
    for record,ref,kind,pointer in ((request,request_ref,'entity','/content/security'),
            (research,c['research'],'claim','/content/artifact'),(review,c['review'],'claim','/content/artifact'),
            (disposition,disposition_ref,'disposition','/content')):
        sid=stable(record);value=record['content'] if pointer=='/content' else record['content']['security' if kind=='entity' else 'artifact']
        text=json.dumps(value,sort_keys=True)
        predecessors=[stable(load(root,old['path'])) for old in record['supersedes']]
        files.append(dict(source_id=sid,repository_path=ref['path'],sha256=ref['sha256'],bytes=(root/ref['path']).stat().st_size))
        review_status=('unreviewed-request' if record['record_type']=='request' else
            'scoped-output-unaccepted' if record['record_type']=='research-result' else
            project_case(root,disposition_ref)['review_status'])
        records.append(dict(id=sid,record_type=kind,entity_id=request['content']['entity'],security_id=request['content']['security']['identifier'],
            question_scope=request['id'],source_id=sid,source_path=ref['path'],source_sha256=ref['sha256'],location=pointer,text=text,
            text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),review_status=review_status,
            origin_kind='project-analysis',originating_run=record['case_id'],project_record_created_at=record['created_at'],
            captured_at=record['observed_at'],analysis_at=record['created_at'],public_source_date=None,
            reviewed_at=record['created_at'] if record['record_type']=='review' else review['created_at'] if kind=='disposition' else None,
            valid_until=c['expires_at'] if kind=='disposition' else None,polarity='unknown',
            assumptions=[],limitations=record['unknowns'],affected_record_ids=[],contradicts=[],
            supersedes_record_ids=predecessors,superseded_effective_at=record['created_at'] if predecessors else None,
            disposition=c['status'] if kind=='disposition' else None,
            reopen_conditions=c['reopening_conditions'] if kind=='disposition' else [],readiness_effect='none'))
    payload=dict(schema='cr2.research-memory.v1',records=records)
    manifest=dict(schema='cr2.research-memory.sources.v1',files=files)
    digest=hashlib.sha256(canonical([payload,manifest])).hexdigest()
    relative='monitoring/research-engine/cases/'+disposition['case_id']+'/memory/'+digest
    folder=_safe_directory(root,relative)
    refs={}
    for name,value in [('records.json',payload),('sources.json',manifest)]:
        p=folder/name;data=canonical(value)+b'\n'
        if p.exists():
            if p.is_symlink() or p.read_bytes()!=data:raise ValueError('Memory export changed')
        else:_atomic(p,data)
        refs[name]=make_reference(root,relative+'/'+name)
    return refs


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default=str(ROOT))
    sub=p.add_subparsers(dest='command', required=True)
    record=sub.add_parser('record', help='Validate and append a versioned record')
    record.add_argument('--input',required=True)
    packet=sub.add_parser('prepare', help='Freeze exact authorized evidence packet')
    for name in ('request','job','record-id','created-at'):packet.add_argument('--'+name,required=True)
    archive=sub.add_parser('archive-result', help='Export a revalidated queue result without private state')
    archive.add_argument('--job-id',required=True);archive.add_argument('--case-id',required=True)
    revalidate=sub.add_parser('revalidate-failed-output', help='Deterministically revalidate one retained failed response')
    revalidate.add_argument('--job-id',required=True);revalidate.add_argument('--batch-id',required=True)
    translate=sub.add_parser('translate', help='Bind a validated scoped result or independent review')
    for name in ('request','job','result','execution','case-id','record-id','created-at'):
        translate.add_argument('--'+name,required=True)
    translate.add_argument('--target-record');translate.add_argument('--unknown',action='append',default=[])
    translate.add_argument('--version',type=int,default=1);translate.add_argument('--supersedes')
    status=sub.add_parser('case-status',help='Revalidate a case without changing acceptance')
    status.add_argument('--disposition',required=True)
    memory=sub.add_parser('memory-export',help='Export explicit case records for the derived history index')
    memory.add_argument('--disposition',required=True)
    args=p.parse_args(argv);root=Path(args.root).resolve()
    try:
        if args.command=='record': result=save_record(root,load(root,args.input))
        elif args.command=='prepare': result=prepare(root,request_path=args.request,job_path=args.job,record_id=args.record_id,created_at=args.created_at)
        elif args.command=='archive-result': result=ScopedQueue(root).export_result(args.job_id,case_id=args.case_id)
        elif args.command=='revalidate-failed-output': result=ScopedQueue(root).revalidate_failed_output(job_id=args.job_id,batch_id=args.batch_id)
        elif args.command=='translate':
            refs={key:make_reference(root,getattr(args,key)) for key in ('request','job','result','execution')}
            result=translate_scoped(root,**refs,case_id=args.case_id,record_id=args.record_id,created_at=args.created_at,
                unknowns=args.unknown,target_record=make_reference(root,args.target_record) if args.target_record else None,
                version=args.version,supersedes=[make_reference(root,args.supersedes)] if args.supersedes else [])
        elif args.command=='memory-export':result=export_memory(root,args.disposition)
        else:result=project_case(root,make_reference(root,args.disposition))
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        p.error(str(exc))


if __name__=='__main__':raise SystemExit(main())
