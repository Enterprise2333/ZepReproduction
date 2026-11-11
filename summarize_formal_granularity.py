"""Validate and summarize the preregistered three-pair experiment."""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from evaluate import ROOT, METHODS
from run_formal_granularity import KEYS

def summarize(folder):
    stages=json.loads((folder/'stages.json').read_text())
    protocol=json.loads((folder/'protocol.json').read_text())
    assert {(r['trial'],r['mode']) for r in stages}=={(i,m) for i in (1,2,3) for m in ('session','message')}
    assert len(stages)==6
    runs={}; manifests={}; costs=[]; summary=defaultdict(list); changes=[]
    for stage in stages:
        assert stage['exit_code']==0 and not stage.get('failure')
        path=Path(stage['run']);m=json.loads((path/'manifest.json').read_text())
        assert m['source_hashes']==protocol['source_hashes'] and m['selected_ids']==protocol['expected_ids']
        rows=[json.loads(x) for x in (path/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(rows)==90 and len({(r['case_id'],r['method']) for r in rows})==90
        trial,mode=stage['trial'],stage['mode'];runs[trial,mode]=rows;manifests[trial,mode]=m
        for method in METHODS:
            selected=[r for r in rows if r['method']==method]
            for stratum in ('all','answerable','abstention'):
                subset=[r for r in selected if stratum=='all' or (stratum=='abstention')==r['abstention']]
                summary[mode,method,stratum].append(dict(trial=trial,n=len(subset),accuracy=sum(r.get('correct') is True for r in subset)/len(subset),coverage=sum(type(r.get('correct')) is bool for r in subset)/len(subset)))
            costs.append(dict(trial=trial,mode=mode,method=method,
                build_calls=sum(r.get('ingest_llm_calls',0) for r in selected),
                build_seconds=sum(r.get('ingest_s',0) for r in selected),
                input_tokens=sum(r.get('input_tokens') or 0 for r in selected),
                output_tokens=sum(r.get('output_tokens') or 0 for r in selected),
                judge_tokens=sum((r.get('judge_usage') or {}).get('total_tokens',0) for r in selected),
                mean_query_seconds=statistics.mean(r.get('latency_s',0)+r.get('search_s',0) for r in selected)))
        compact=[{k:v for k,v in r.items() if k not in ('context','judge_raw')} for r in rows]
        target=ROOT/'artifacts'/f'formal-trial{trial}-{mode}'
        public_manifest=dict(m)
        if public_manifest.get('recovery_provenance'):
            public_manifest['recovery_provenance']={k:v for k,v in public_manifest['recovery_provenance'].items() if k not in ('change','note')}
        target.with_suffix('.json').write_text(json.dumps(dict(manifest=public_manifest,predictions=compact),indent=2),encoding='utf-8')
    for trial in (1,2,3):
        assert all(manifests[trial,'session'][k]==manifests[trial,'message'][k] for k in KEYS)
        for method in METHODS:
            a={r['case_id']:r for r in runs[trial,'session'] if r['method']==method}
            b={r['case_id']:r for r in runs[trial,'message'] if r['method']==method}
            improved=[i for i in a if a[i].get('correct') is False and b[i].get('correct') is True]
            regressed=[i for i in a if a[i].get('correct') is True and b[i].get('correct') is False]
            changes.append(dict(trial=trial,method=method,improved=improved,regressed=regressed))
    results=[dict(mode=k[0],method=k[1],stratum=k[2],trials=v,mean=statistics.mean(x['accuracy'] for x in v),sd=statistics.stdev(x['accuracy'] for x in v)) for k,v in sorted(summary.items())]
    public_protocol={k:v for k,v in protocol.items() if k!='recovery'}
    output=dict(protocol=public_protocol,stages=stages,results=results,costs=costs,paired_changes=changes,
        errors=sum('error' in r for rows in runs.values() for r in rows))
    (ROOT/'artifacts/formal-granularity-summary.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    lines=['# Formal episode-granularity experiment','',
        'Three paired trials of the same 30 LongMemEval Oracle questions. Session versus message ingestion is the intervention. These are simplified Zep reproduction results, not paper-matched LongMemEval-S scores. The same questions recur across trials: do not treat the 90 repeated question observations as 90 independent examples or infer population significance from the reported standard deviation.','',
        '| Mode | Method | Stratum | Mean accuracy | Sample SD (pp) |','|---|---|---|---:|---:|']
    for r in results:lines.append(f"| {r['mode']} | {r['method']} | {r['stratum']} | {100*r['mean']:.2f}% | {100*r['sd']:.2f} |")
    lines+=['','## Paired changes','','| Trial | Method | Wrong → right | Right → wrong |','|---:|---|---:|---:|']
    for r in changes:lines.append(f"| {r['trial']} | {r['method']} | {len(r['improved'])} | {len(r['regressed'])} |")
    lines+=['','## Cost and interpretation','',
        'Independent trial work ran concurrently on a shared host/API; execution order was not fully counterbalanced. Query and construction timing can reflect contention. Do not interpret them as isolated speed benchmarks. Graph construction is shared by the dated/no-date contexts and must not be counted twice. Character telemetry is not billable token usage; monetary cost is not inferred.',
        '',f"Execution/judge errors in the final accepted records: {output['errors']}. Full trial counts, coverage, case IDs, regressions, tokens and calls are in artifacts/formal-granularity-summary.json.",
        '', 'The pilot deliberately selected three prior failures; its 3/3 result is not mixed into these formal results. Message order and session timestamps are preserved; both user and assistant content is included. The default recent-episode window is unchanged, so its effective message coverage differs by mode. Public judgments are LLM-based, not a blinded human adjudication.']
    lines+=['', 'Results combine complete per-case records from multiple execution windows under the same ingestion, prompting and scoring configuration. Source provenance is retained for audit. Costs refer to accepted-case processing, not total account spending. Model aliases are not pinned revisions.']
    (ROOT/'FORMAL_GRANULARITY_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(results=results,paired_changes=changes,errors=output['errors']),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();summarize(a.folder)
