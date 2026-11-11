"""Run full-history, Graphiti, and no-temporal-metadata comparisons."""

import argparse
import asyncio
import csv
import hashlib
import inspect
import uuid
import json
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from runtime import MODEL, ROOT, answer_client, make_graph, prepare_graph
from synthetic import cases as synthetic_cases

SOURCE_SHA = "fb60e59d4a208c99e7d0186ee6335d2a257f17f2"


def parse_date(value):
    if " (" in value:
        return datetime.strptime(value, "%Y/%m/%d (%a) %H:%M").replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value[:10]).replace(tzinfo=timezone.utc)


def longmemeval_cases(limit, seed, max_chars):
    path = ROOT / "longmemeval_oracle.json"
    if not path.exists():
        raise FileNotFoundError(f"Download the public LongMemEval Oracle dataset to {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    rng = random.Random(seed)
    chosen = []
    for kind in ("knowledge-update", "temporal-reasoning", "multi-session"):
        eligible = [
            x for x in raw
            if x["question_type"] == kind
            and sum(len(m["content"]) for s in x["haystack_sessions"] for m in s) <= max_chars
        ]
        eligible.sort(key=lambda x: x["question_id"])
        chosen.extend(rng.sample(eligible, min(limit, len(eligible))))
    result = []
    for item in chosen:
        sessions = sorted(
            zip(item["haystack_dates"], item["haystack_session_ids"], item["haystack_sessions"]),
            key=lambda x: x[0],
        )
        episodes = []
        message_episodes = []
        for date, session_id, messages in sessions:
            body = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
            episodes.append({"date": date, "body": body, "session_id": session_id})
            for index, message in enumerate(messages):
                message_episodes.append({"date": date, "session_id": session_id,
                    "message_index": index, "role": message['role'],
                    "body": f"{message['role'].upper()}: {message['content']}"})
        result.append(
            {
                "id": item["question_id"],
                "type": item["question_type"],
                "episodes": episodes,
                "message_episodes": message_episodes,
                "question_date": item["question_date"],
                "questions": [{"type": item["question_type"], "question": item["question"], "answer": item["answer"]}],
            }
        )
    return result


def episode_context(episodes):
    return "\n\n".join(f"[{e['date']}] {e['body']}" for e in episodes)


def graph_context(edges, include_time):
    if not edges:
        return "No facts found."
    lines = []
    for edge in edges:
        line = f"- {edge.fact}"
        if include_time:
            line += f" [valid_at={edge.valid_at.isoformat() if edge.valid_at else 'unknown'}; invalid_at={edge.invalid_at.isoformat() if edge.invalid_at else 'not recorded'}]"
        lines.append(line)
    return "\n".join(lines)


async def ask(client, question, context, question_date=None):
    system = (
        "Answer the question using only the supplied memory. Treat valid_at as the start of a fact and "
        "invalid_at as the end. An unrecorded end is not proof of current validity; use the dated evidence. "
        "For a historical question, use the date or sequence specified in the question. "
        "If the memory is insufficient, answer UNKNOWN. Give only a short answer, no explanation."
    )
    user = f"Memory:\n{context}\n\nQuestion date: {question_date or 'unspecified'}\nQuestion: {question}"
    start = time.perf_counter()
    response = await client.chat.completions.create(
        model=MODEL,
        temperature=0,
        top_p=1,
        max_tokens=128,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    usage = response.usage
    return {
        "answer": response.choices[0].message.content or "",
        "latency_s": round(time.perf_counter() - start, 3),
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
    }


def synthetic_correct(gold, prediction):
    # Accept only a complete short answer, never a substring inside a denial.
    value = str(prediction).strip().strip('"').strip().rstrip('.').strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(gold)):
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat() == gold
            except ValueError:
                pass
        return False
    normalize = lambda x: re.sub(r"\s+", " ", str(x).strip()).casefold()
    # Closed aliases derived from the benchmark schema, not arbitrary substrings.
    aliases = {normalize(gold)}
    from synthetic import VALUES
    for category, pairs in enumerate(VALUES):
        if any(gold in pair for pair in pairs):
            if category == 2:
                aliases.add(normalize('Project ' + gold))
            elif category == 3:
                aliases.add(normalize(gold + ' laptop'))
            elif category == 4:
                aliases.add(normalize(gold + ' gym'))
    return normalize(value) in aliases


def parse_judgment(raw):
    value = json.loads(raw)
    if not isinstance(value, dict) or type(value.get("correct")) is not bool:
        raise ValueError("Judge must return a JSON boolean named correct")
    return value["correct"]


async def llm_judge(client, question, gold, prediction):
    prompt = (
        "Judge whether the candidate answer is factually equivalent to the reference answer for this question. "
        "Be strict about dates, entities, and negations. Return JSON with a boolean field named correct.\n"
        f"Question: {question}\nReference: {gold}\nCandidate: {prediction}"
    )
    response = await client.chat.completions.create(
        model=MODEL,
        temperature=0,
        top_p=1,
        max_tokens=50,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content
    record = {"judge_raw": raw, "judge_usage": response.usage.model_dump() if response.usage else None}
    try:
        record["correct"] = parse_judgment(raw)
    except (ValueError, TypeError) as exc:
        record.update(error=str(exc), error_stage="judge")
    return record


METHODS = ("full_history", "graphiti", "no_temporal_metadata")


def base_row(case, item, suite, method):
    return dict(suite=suite, case_id=case["id"], question_type=item["type"], method=method,
                question=item["question"], gold=item["answer"], abstention=case["id"].endswith("_abs"))


async def evaluate_answer(row, client, context, date):
    row["context"] = context
    try:
        prediction = await ask(client, row["question"], context, date)
        row.update(prediction, prediction=prediction["answer"])
    except Exception as exc:
        row.update(error=repr(exc), error_stage="answer")
        return row
    try:
        if row["suite"] == "synthetic":
            row["correct"] = synthetic_correct(row["gold"], row["prediction"])
        else:
            row.update(await llm_judge(client, row["question"], row["gold"], row["prediction"]))
    except Exception as exc:
        row.update(error=repr(exc), error_stage="judge")
    return row


def ingestion_episodes(case, granularity):
    if granularity == "session":
        return case["episodes"]
    if granularity == "message" and "message_episodes" in case:
        return case["message_episodes"]
    raise ValueError("Message granularity requires structured LongMemEval messages")


async def run_case(case, run_dir, client, suite, top_k, granularity="session"):
    episodes = ingestion_episodes(case, granularity)
    provenance = dict(episode_granularity=granularity, session_count=len(case['episodes']),
                      message_count=len(case.get('message_episodes', [])), episode_count=len(episodes))
    rows = []
    # Baseline is independent of graph creation, ingestion and retrieval.
    for item in case["questions"]:
        row = base_row(case, item, suite, "full_history")
        row.update(provenance, search_s=0, ingest_s=0, ingest_llm_calls=0)
        rows.append(await evaluate_answer(row, client, episode_context(case["episodes"]), case.get("question_date")))
    graph = None
    metrics = dict(provenance)
    graph_error = None
    try:
        graph, llm = make_graph(run_dir / "graphs" / f"{case['id']}.kuzu")
        await prepare_graph(graph)
        start = time.perf_counter()
        for i, episode in enumerate(episodes):
            await graph.add_episode(name=f"{case['id']}-episode-{i}", episode_body=episode["body"],
                                    source_description="Public LongMemEval conversation" if suite == "longmemeval" else "Synthetic conversation",
                                    reference_time=parse_date(episode["date"]))
            with (run_dir / 'ingestion.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps(dict(case_id=case['id'], episode_index=i, name=f"{case['id']}-episode-{i}",
                    date=episode['date'], session_id=episode.get('session_id'),
                    message_index=episode.get('message_index'), role=episode.get('role'),
                    body_sha256=hashlib.sha256(episode['body'].encode()).hexdigest()))+'\n')
        metrics.update(ingest_s=round(time.perf_counter()-start, 3), ingest_llm_calls=llm.calls,
                       ingest_llm_input_chars=llm.estimated_input_chars, ingest_llm_output_chars=llm.estimated_output_chars)
    except Exception as exc:
        graph_error = repr(exc)
    try:
        for item in case["questions"]:
            error, stage = graph_error, "ingestion"
            edges, search_s = [], 0
            if error is None:
                try:
                    start = time.perf_counter()
                    edges = await graph.search(item["question"], num_results=top_k)
                    search_s = round(time.perf_counter()-start, 3)
                except Exception as exc:
                    error, stage = repr(exc), "retrieval"
            for method in METHODS[1:]:
                row = base_row(case, item, suite, method)
                row.update(metrics, search_s=search_s)
                if error:
                    row.update(error=error, error_stage=stage)
                else:
                    row.update(retrieved_facts=len(edges), retrieved_edge_ids=[e.uuid for e in edges])
                    await evaluate_answer(row, client, graph_context(edges, method == "graphiti"), case.get("question_date"))
                rows.append(row)
    finally:
        if graph is not None:
            try:
                await graph.close()
            except Exception as exc:
                for row in rows:
                    if row["method"] != "full_history":
                        row["cleanup_error"] = repr(exc)
    return rows


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["suite"], row.get("method", "unassigned"), row.get("question_type", "unknown"))].append(row)
    output = []
    for (suite, method, kind), group in sorted(groups.items()):
        scored = [r for r in group if type(r.get("correct")) is bool]
        completed = [r for r in group if "prediction" in r]
        correct = sum(r["correct"] for r in scored)
        def mean(key):
            values = [r[key] for r in group if isinstance(r.get(key), (int, float))]
            return round(sum(values)/len(values), 4) if values else None
        query = [r["latency_s"]+r.get("search_s",0) for r in completed]
        output.append(dict(suite=suite, method=method, question_type=kind, n=len(group),
            n_completed=len(completed), n_scored=len(scored), n_correct=correct,
            n_errors=sum("error" in r for r in group), completion_rate=len(completed)/len(group),
            scoring_coverage=len(scored)/len(group), accuracy=correct/len(group),
            scored_accuracy=correct/len(scored) if scored else None,
            mean_answer_latency_s=mean("latency_s"), mean_retrieval_latency_s=mean("search_s"),
            mean_query_latency_s=sum(query)/len(query) if query else None,
            mean_answer_input_tokens=mean("input_tokens"), mean_graph_build_s_per_case=mean("ingest_s"),
            mean_graph_build_llm_calls_per_case=mean("ingest_llm_calls")))
    return output


async def main(args):
    if args.suite == "synthetic":
        chosen = synthetic_cases()[: args.limit]
    else:
        chosen = longmemeval_cases(args.limit, args.seed, args.max_chars)
    if args.case_ids:
        ids = args.case_ids.split(',')
        available = {c['id']: c for c in chosen}
        if len(ids) != len(set(ids)) or any(i not in available for i in ids):
            raise ValueError('case-ids must be unique IDs in the selected benchmark')
        chosen = [available[i] for i in ids]
    for case in chosen:
        ingestion_episodes(case, args.episode_granularity)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-granularity-v1-" + uuid.uuid4().hex[:8] + f"-{args.suite}-{args.episode_granularity}"
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "evaluation_version": "granularity-v1", "scoring_version": "reliability-v2",
                "episode_granularity": args.episode_granularity,
                "episode_counts": {c['id']: len(ingestion_episodes(c,args.episode_granularity)) for c in chosen},
                "message_counts": {c['id']:len(c.get('message_episodes',[])) for c in chosen},
                "timestamp_policy": "inherit session time; preserve message order; no artificial offsets",
                "provider": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
                "answer_config": {"temperature": 0, "top_p": 1, "max_tokens": 128},
                "judge_config": {"temperature": 0, "top_p": 1, "max_tokens": 50},
                "graph_config": {"temperature": 0, "max_tokens": 4096, "top_p": "omitted; provider default"},
                "source_hashes": {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ("evaluate.py", "runtime.py", "synthetic.py")},
                "data_sha256": hashlib.sha256((ROOT/("longmemeval_oracle.json" if args.suite == "longmemeval" else "synthetic.py")).read_bytes()).hexdigest(),
                "answer_function": inspect.getsource(ask), "judge_function": inspect.getsource(llm_judge),
                "suite": args.suite,
                "seed": args.seed,
                "max_chars": args.max_chars if args.suite == "longmemeval" else None,
                "selected_ids": [x["id"] for x in chosen],
                "graphiti_sha": SOURCE_SHA,
                "graphiti_version": "0.31.2",
                "llm_model": MODEL,
                "embedding_model": "BAAI/bge-small-en-v1.5",
                "graph_backend": "Kuzu 0.11.3",
                "top_k": args.top_k,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    client = answer_client()
    rows = []
    async with client:
        for i, case in enumerate(chosen, 1):
            print(f"[{i}/{len(chosen)}] {case['id']}", flush=True)
            try:
                current = await run_case(case, run_dir, client, args.suite, args.top_k, args.episode_granularity)
            except Exception as exc:
                current = [dict(base_row(case, item, args.suite, method), error=repr(exc), error_stage="case") for item in case["questions"] for method in METHODS]
                print(f"  ERROR: {exc}", flush=True)
            rows.extend(current)
            with (run_dir / "predictions.jsonl").open("a", encoding="utf-8") as f:
                for row in current:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            summary = summarize(rows)
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            if any('Insufficient Balance' in r.get('error', '') or 'Error code: 402' in r.get('error', '') for r in current):
                (run_dir / 'STOPPED.json').write_text(json.dumps({
                    'reason': 'provider_balance_exhausted', 'case_id': case['id'],
                    'completed_case_count': i, 'remaining_ids': [c['id'] for c in chosen[i:]],
                    'note': 'Preserve completed records; retry failed/missing cases separately.'
                }, indent=2), encoding='utf-8')
                raise SystemExit('Stopped: DeepSeek balance exhausted; predictions preserved.')
            for x in summary:
                if x["question_type"] == "current" or args.suite == "longmemeval":
                    print(" ", x["method"], x["question_type"], f"{x['accuracy']:.1%}", f"n={x['n']}", flush=True)
    with (run_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]) if summary else ["suite", "method", "question_type", "n", "accuracy"])
        writer.writeheader()
        writer.writerows(summary)
    print("Results:", run_dir, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["synthetic", "longmemeval"], required=True)
    parser.add_argument("--limit", type=int, default=20, help="Synthetic cases or LongMemEval cases per category")
    parser.add_argument("--seed", type=int, default=5660)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--max-chars", type=int, default=30000)
    parser.add_argument("--episode-granularity", choices=['session','message'], default='session')
    parser.add_argument("--case-ids", help="Comma-separated IDs within the fixed selected subset; for diagnostic pilots")
    asyncio.run(main(parser.parse_args()))
