"""Run full-history, Graphiti, and no-temporal-metadata comparisons."""

import argparse
import asyncio
import csv
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
        for date, session_id, messages in sessions:
            body = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
            episodes.append({"date": date, "body": body, "session_id": session_id})
        result.append(
            {
                "id": item["question_id"],
                "type": item["question_type"],
                "episodes": episodes,
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
            line += f" [valid_at={edge.valid_at.isoformat() if edge.valid_at else 'unknown'}; invalid_at={edge.invalid_at.isoformat() if edge.invalid_at else 'still valid'}]"
        lines.append(line)
    return "\n".join(lines)


async def ask(client, question, context, question_date=None):
    system = (
        "Answer the question using only the supplied memory. Treat valid_at as the start of a fact and "
        "invalid_at as the end. For a current-state question, prefer a fact with no invalid_at. "
        "For a historical question, use the date or sequence specified in the question. "
        "If the memory is insufficient, answer UNKNOWN. Give only a short answer, no explanation."
    )
    user = f"Memory:\n{context}\n\nQuestion date: {question_date or 'unspecified'}\nQuestion: {question}"
    start = time.perf_counter()
    response = await client.chat.completions.create(
        model=MODEL,
        temperature=0,
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
    a = re.sub(r"[^a-z0-9]", "", str(gold).lower())
    b = re.sub(r"[^a-z0-9]", "", str(prediction).lower())
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(gold)):
        if a in b:
            return True
        for pattern in (r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}", r"\d{1,2}\s+[A-Za-z]+\s+\d{4}"):
            match = re.search(pattern, prediction)
            if match:
                for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
                    try:
                        return datetime.strptime(match.group(), fmt).date().isoformat() == gold
                    except ValueError:
                        pass
        return False
    return a in b


async def llm_judge(client, question, gold, prediction):
    prompt = (
        "Judge whether the candidate answer is factually equivalent to the reference answer for this question. "
        "Be strict about dates, entities, and negations. Return JSON with a boolean field named correct.\n"
        f"Question: {question}\nReference: {gold}\nCandidate: {prediction}"
    )
    response = await client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=50,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return bool(json.loads(response.choices[0].message.content)["correct"])


async def run_case(case, run_dir, client, suite, top_k):
    db_path = run_dir / "graphs" / f"{case['id']}.kuzu"
    graph, llm = make_graph(db_path)
    rows = []
    try:
        await prepare_graph(graph)
        start = time.perf_counter()
        node_count = edge_count = 0
        for i, episode in enumerate(case["episodes"]):
            result = await graph.add_episode(
                name=f"{case['id']}-episode-{i}",
                episode_body=episode["body"],
                source_description="Public LongMemEval conversation" if suite == "longmemeval" else "Synthetic conversation",
                reference_time=parse_date(episode["date"]),
            )
            node_count += len(result.nodes)
            edge_count += len(result.edges)
        ingest_s = round(time.perf_counter() - start, 3)
        ingest_calls = llm.calls
        history = episode_context(case["episodes"])
        for item in case["questions"]:
            query = item["question"]
            search_start = time.perf_counter()
            edges = await graph.search(query, num_results=top_k)
            search_s = round(time.perf_counter() - search_start, 3)
            contexts = {
                "full_history": history,
                "graphiti": graph_context(edges, True),
                "no_temporal_metadata": graph_context(edges, False),
            }
            for method, context in contexts.items():
                try:
                    prediction = await ask(client, query, context, case.get("question_date"))
                    correct = (
                        synthetic_correct(item["answer"], prediction["answer"])
                        if suite == "synthetic"
                        else await llm_judge(client, query, item["answer"], prediction["answer"])
                    )
                    row = {
                        "suite": suite,
                        "case_id": case["id"],
                        "question_type": item["type"],
                        "method": method,
                        "question": query,
                        "gold": item["answer"],
                        "prediction": prediction["answer"],
                        "correct": correct,
                        "retrieved_facts": len(edges),
                        "retrieved_edge_ids": [e.uuid for e in edges],
                        "context": context,
                        "ingest_s": ingest_s,
                        "ingest_llm_calls": ingest_calls,
                        "ingest_llm_input_chars": llm.estimated_input_chars,
                        "ingest_llm_output_chars": llm.estimated_output_chars,
                        "nodes": node_count,
                        "edges": edge_count,
                        "search_s": search_s if method != "full_history" else 0,
                        **prediction,
                    }
                    rows.append(row)
                except Exception as exc:
                    rows.append({"suite": suite, "case_id": case["id"], "question_type": item["type"], "method": method, "error": repr(exc)})
    finally:
        await graph.close()
    return rows


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if "correct" in row:
            groups[(row["suite"], row["method"], row["question_type"])].append(row)
    output = []
    for (suite, method, kind), group in sorted(groups.items()):
        output.append(
            {
                "suite": suite,
                "method": method,
                "question_type": kind,
                "n": len(group),
                "accuracy": round(sum(r["correct"] for r in group) / len(group), 4),
                "mean_answer_latency_s": round(sum(r["latency_s"] for r in group) / len(group), 3),
                "mean_retrieval_latency_s": round(sum(r["search_s"] for r in group) / len(group), 3),
                "mean_query_latency_s": round(sum(r["latency_s"] + r["search_s"] for r in group) / len(group), 3),
                "mean_answer_input_tokens": round(sum(r["input_tokens"] or 0 for r in group) / len(group), 1),
                "mean_graph_build_s_per_case": round(sum(r["ingest_s"] for r in group) / len(group), 3),
                "mean_graph_build_llm_calls_per_case": round(sum(r["ingest_llm_calls"] for r in group) / len(group), 1),
            }
        )
    return output


async def main(args):
    if args.suite == "synthetic":
        chosen = synthetic_cases()[: args.limit]
    else:
        chosen = longmemeval_cases(args.limit, args.seed, args.max_chars)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{args.suite}"
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
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
                current = await run_case(case, run_dir, client, args.suite, args.top_k)
            except Exception as exc:
                current = [{"suite": args.suite, "case_id": case["id"], "error": repr(exc)}]
                print(f"  ERROR: {exc}", flush=True)
            rows.extend(current)
            with (run_dir / "predictions.jsonl").open("a", encoding="utf-8") as f:
                for row in current:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            summary = summarize(rows)
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
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
    asyncio.run(main(parser.parse_args()))

