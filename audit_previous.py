"""Offline audit of immutable v1 predictions; no LLM calls."""
import json
from pathlib import Path
from evaluate import ROOT, synthetic_correct

def audit():
    out = []
    for name in ['20261105-100527-synthetic','20261105-102247-synthetic','20261105-103305-synthetic','20261105-101232-longmemeval']:
        rows = [json.loads(x) for x in (ROOT/'results'/name/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
        changes = [dict(case=r['case_id'], method=r['method'], gold=r['gold'], prediction=r['prediction'], old=r['correct'], new=synthetic_correct(r['gold'],r['prediction']))
                   for r in rows if 'synthetic' in name and r['correct'] != synthetic_correct(r['gold'],r['prediction'])]
        keys = [(r['case_id'], r['question_type'], r['method']) for r in rows]
        out.append(dict(run=name, rows=len(rows), duplicate_keys=len(keys)-len(set(keys)), errors=sum('error' in r for r in rows), scoring_changes=changes,
                        judge_raw_available=all('judge_raw' in r for r in rows) if 'longmemeval' in name else None))
    (ROOT/'artifacts/reliability-offline-audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print([(x['run'],x['rows'],len(x['scoring_changes'])) for x in out])

if __name__ == '__main__':
    audit()
