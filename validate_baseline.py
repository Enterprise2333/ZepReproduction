"""Run validation first, then three independent trials; never overwrite old runs."""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
if __name__ == '__main__':
    folder = ROOT/'results'/('validation-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    folder.mkdir()
    stages = [('smoke', ['smoke.py']), ('pilot-synthetic', ['evaluate.py','--suite','synthetic','--limit','2']),
              ('pilot-public', ['evaluate.py','--suite','longmemeval','--limit','1'])]
    stages += [(f'{suite}-trial{trial}', ['evaluate.py','--suite',suite,'--limit',limit]) for trial in range(1,4) for suite,limit in [('synthetic','20'),('longmemeval','10')]]
    records=[]
    for name, args in stages:
        print('START', name, flush=True)
        before=set((ROOT/'results').glob('*-v2-*'))
        with (folder/(name+'.log')).open('w', encoding='utf-8') as f:
            result=subprocess.run([sys.executable,'-u',*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        new=set((ROOT/'results').glob('*-v2-*'))-before
        record=dict(stage=name,exit_code=result.returncode,runs=[str(x) for x in new])
        records.append(record)
        (folder/'stages.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        if result.returncode: raise SystemExit('Failed: '+name)
        for run in new:
            rows=[json.loads(x) for x in (run/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
            if any('error' in r for r in rows): raise SystemExit('Recorded errors: '+str(run))
        print('DONE', name, flush=True)
    print('VALIDATION COMPLETE', folder, flush=True)
