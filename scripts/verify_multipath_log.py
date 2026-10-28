"""Check real multipath framing, sample indices, ADC errors and capture accounting."""
from pathlib import Path
import argparse, json
import binary_log

def verify(path):
    captures={};records=0
    with Path(path).open('rb') as f:
        header=binary_log.read_header(f)
        for record in binary_log.records(f):
            records+=1
            if record['kind'] not in (6,7,9): continue
            rows=list(binary_log.rows(record))
            if record['kind']==6:
                b=rows[0];captures[b['shot_seq']]={**b,'samples':0,'gaps':0,'adc_errors':0,'next_index':b['first_index'],'complete':False}
            elif record['kind']==7:
                b=rows[0];c=captures[b['shot_seq']]
                if b['sample_index']<c['next_index']: raise ValueError('Duplicate/reversed sample indices')
                c['gaps']+=b['sample_index']-c['next_index'];c['samples']+=len(rows)
                c['adc_errors']+=sum(row['adc_error'] for row in rows);c['next_index']=rows[-1]['sample_index']+1
            else:
                end=rows[0];c=captures.get(end['shot_seq'])
                if c is None: continue  # No-arrival/unavailable attempt has no BEGIN.
                c.update(end);c['complete']=end['reason']==0
                if c['samples']!=end['written_samples']: raise ValueError('End/write count mismatch')
                c['lossless']=c['complete'] and not any(c[k] for k in ('gaps','adc_errors','lost_samples','edge_drops','request_drops')) and c['samples']==c['target_samples']
    return dict(header=header,records=records,crc='PASS',captures=list(captures.values()))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('path');parser.add_argument('--out');args=parser.parse_args()
    result=verify(args.path);text=json.dumps(result,indent=2)
    if args.out:Path(args.out).write_text(text,encoding='utf-8')
    print(text)
