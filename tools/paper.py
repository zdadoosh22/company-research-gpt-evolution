"""Manual structured interface to isolated prospective paper records.

No automatic observations, quotes, fills, delivery or live-ledger access.
Every submitted record retains the caller's evidence and experimental scope.
"""
import argparse
import json
from pathlib import Path
from paper_study import PaperStudy

ROOT=Path(__file__).resolve().parents[1]
OPERATIONS={'create_cohort','register_opportunity','record_quote','entry_fill',
            'cancel_entry','request_exit','cancel_exit','exit_fill','snapshot'}

def execute(study,payload):
    if not isinstance(payload,dict) or set(payload)!={'operation','arguments'}:
        raise ValueError('Use exactly operation and arguments')
    operation=payload['operation']
    if operation not in OPERATIONS or not isinstance(payload['arguments'],dict):
        raise ValueError('Unknown paper operation or invalid named arguments')
    result=getattr(study,operation)(**payload['arguments'])
    return {'mode':'prospective-paper','actionable':False,'operation':operation,'result':result}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('json_file')
    parser.add_argument('--database',default='study.sqlite3',help='Relative path within state/paper only')
    args=parser.parse_args()
    directory=(ROOT/'state'/'paper').resolve()
    database=(directory/args.database).resolve()
    if not database.is_relative_to(directory) or database==directory:
        raise ValueError('Paper database must stay inside state/paper')
    payload=json.loads(Path(args.json_file).read_text(encoding='utf-8-sig'))
    with PaperStudy(database) as study:
        print(json.dumps(execute(study,payload),indent=2,default=str))

if __name__=='__main__':
    main()
