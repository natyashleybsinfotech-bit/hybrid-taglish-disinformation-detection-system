"""Validate actual long-format survey responses and write a safe export; never invent data."""
import argparse
import csv
from pathlib import Path

FIELDS=['session_code','group','instrument_version','item_id','rating','response_status','tasks_observed','comment']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; choose a new filename')
    with args.input.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=FIELDS:parser.error('Columns must exactly match docs/research/QUESTIONNAIRES.md')
        rows=list(reader)
    seen=set()
    for number,row in enumerate(rows,2):
        group=row['group'];item=row['item_id'];status=row['response_status']
        valid_ids={f'B{i:02}' for i in range(1,15)} if group=='BSIT' else {f'A{i:02}' for i in range(1,19)} if group=='AFP' else set()
        key=(row['session_code'],group,item)
        if not row['session_code'] or item not in valid_ids or key in seen or status not in {'answered','not_observed','skipped'}:
            parser.error(f'Invalid or duplicate response at row {number}')
        if (status=='answered' and row['rating'] not in {'1','2','3','4','5'}) or (status!='answered' and row['rating']):
            parser.error(f'Invalid rating/missingness at row {number}')
        seen.add(key)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader()
        for row in rows:writer.writerow({k: "'"+v if v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items()})
    print(f'Validated {len(rows)} actual response rows. No scores were generated. Keep the export private.')

if __name__=='__main__':main()
