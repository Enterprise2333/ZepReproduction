"""Three paired trials, each pair sequential; up to three independent pairs in parallel.

Concurrent timing is descriptive, not an isolated latency benchmark.
"""
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

ROOT=Path(__file__).resolve().parent
KEYS=('selected_ids','source_hashes','data_sha256','answer_config','judge_config','graph_config','top_k','llm_model','answer_function','judge_function')

def run():
    folder=ROOT/'results'/('formal-granularity-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    folder.mkdir()
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('evaluate.py','runtime.py','synthetic.py')}
    records=[]; lock=Lock()
    expected=json.loads((ROOT/'artifacts/longmemeval-manifest.json').read_text())['selected_ids']
    (folder/'protocol.json').write_text(json.dumps(dict(trials=3,workers=3,source_hashes=hashes,expected_ids=expected,
        note='Three independent pairs share host/API capacity. Within each pair modes are sequential. Latencies may reflect contention.'),indent=2))
    def pair(trial):
        manifests=[]
        for mode in (('session','message') if trial%2 else ('message','session')):
            name=f'trial{trial}-{mode}'
            print('START',name,flush=True)
            cmd=[sys.executable,'-u','evaluate.py','--suite','longmemeval','--limit','10','--seed','5660','--max-chars','30000','--top-k','10','--episode-granularity',mode]
            log=folder/(name+'.log')
            with log.open('w',encoding='utf-8') as stream:
                proc=subprocess.run(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            lines=log.read_text(encoding='utf-8').splitlines()
            paths=[line.removeprefix('Results:').strip() for line in lines if line.startswith('Results:')]
            record=dict(trial=trial,mode=mode,exit_code=proc.returncode,run=paths[-1] if paths else None)
            if proc.returncode or not paths:
                record['failure']='process failed; inspect log'
            else:
                path=Path(paths[-1]); manifest=json.loads((path/'manifest.json').read_text())
                rows=[json.loads(x) for x in (path/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
                record.update(rows=len(rows),errors=sum('error' in r for r in rows))
                valid=(manifest['source_hashes']==hashes and manifest['selected_ids']==expected and
                    len(rows)==90 and len({(r['case_id'],r['method']) for r in rows})==90)
                if not valid: record['failure']='protocol mismatch'
                manifests.append(manifest)
            with lock:
                records.append(record)
                (folder/'stages.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
            if record.get('failure') or record.get('errors'): raise RuntimeError(str(record))
            print('DONE',name,flush=True)
        if any(manifests[0][k]!=manifests[1][k] for k in KEYS):raise RuntimeError('Pair configuration mismatch')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(pair,i) for i in range(1,4)]
        for future in futures:future.result()
    print('FORMAL COMPLETE',folder,flush=True)

if __name__=='__main__':run()
