"""Export only complete formal trials matching the frozen implementation."""
import hashlib
import json
import csv
import statistics
from collections import defaultdict
from evaluate import ROOT, METHODS

def aggregate():
    expected_hashes = {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('evaluate.py','runtime.py','synthetic.py')}
    groups = defaultdict(list)
    accepted=[]
    excluded=[]
    costs=[]
    for folder in sorted((ROOT/'results').glob('*-v2-*')):
        m=json.loads((folder/'manifest.json').read_text())
        expected_cases=20 if m['suite']=='synthetic' else 30
        if len(m['selected_ids']) != expected_cases: continue
        if m['source_hashes'] != expected_hashes:
            excluded.append(dict(run=folder.name, reason='implementation changed during validation; excluded'))
            continue
        rows=[json.loads(x) for x in (folder/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
        expected_rows=180 if m['suite']=='synthetic' else 90
        if len(rows)!=expected_rows:
            excluded.append(dict(run=folder.name, reason='incomplete'))
            continue
        if len({(r['case_id'],r['method'],r['question_type']) for r in rows})!=expected_rows:
            raise ValueError('duplicate rows: '+folder.name)
        accepted.append(dict(run=folder.name,suite=m['suite'],errors=sum('error' in r for r in rows)))
        for method in METHODS:
            subset=[r for r in rows if r['method']==method]
            case_metrics={r['case_id']:r for r in subset}
            costs.append(dict(run=folder.name,method=method,
                answer_input_tokens=sum(r.get('input_tokens') or 0 for r in subset),
                answer_output_tokens=sum(r.get('output_tokens') or 0 for r in subset),
                judge_total_tokens=sum((r.get('judge_usage') or {}).get('total_tokens',0) for r in subset),
                graph_build_seconds=sum(r.get('ingest_s',0) for r in case_metrics.values()),
                graph_build_calls=sum(r.get('ingest_llm_calls',0) for r in case_metrics.values()),
                mean_query_seconds=statistics.mean(r.get('latency_s',0)+r.get('search_s',0) for r in subset)))
        for method in METHODS:
            for stratum in ('all','answerable','abstention') if m['suite']=='longmemeval' else ('all','current','historical','change-date'):
                subset=[r for r in rows if r['method']==method and (stratum=='all' or (stratum=='answerable' and not r['abstention']) or (stratum=='abstention' and r['abstention']) or r['question_type']==stratum)]
                if subset:
                    groups[(m['suite'],method,stratum)].append(dict(accuracy=sum(r.get('correct') is True for r in subset)/len(subset),n=len(subset),coverage=sum(type(r.get('correct')) is bool for r in subset)/len(subset)))
        # Compact, shareable records; omit source conversation/context and judge text.
        compact=[{k:v for k,v in r.items() if k not in ('context','judge_raw')} for r in rows]
        (ROOT/'artifacts'/(folder.name+'-predictions.json')).write_text(json.dumps(compact,indent=2),encoding='utf-8')
        (ROOT/'artifacts'/(folder.name+'-manifest.json')).write_text(json.dumps(m,indent=2),encoding='utf-8')
    result=[dict(suite=k[0],method=k[1],stratum=k[2],trials=len(v),n_per_trial=v[0]['n'],mean_accuracy=statistics.mean(x['accuracy'] for x in v),sample_sd=statistics.stdev(x['accuracy'] for x in v) if len(v)>1 else None,min_scoring_coverage=min(x['coverage'] for x in v)) for k,v in sorted(groups.items())]
    # Graph build costs are shared by the two graph conditions, never add them twice.
    (ROOT/'artifacts/reliability-v2-summary.json').write_text(json.dumps(dict(accepted=accepted,excluded=excluded,results=result,costs=costs),indent=2),encoding='utf-8')
    print(json.dumps(dict(accepted=accepted,excluded=excluded,results=result),indent=2))
if __name__=='__main__': aggregate()
