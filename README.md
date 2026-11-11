# Zep / Graphiti temporal memory reproduction

This project is a **local, simplified reproduction** of the main temporal-memory mechanism in [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956). It writes dated conversational episodes to the open-source [Graphiti](https://github.com/getzep/graphiti) engine, retrieves dated facts, and asks the same LLM to answer with (1) the full conversation, (2) Graphiti facts and their validity dates, and (3) the same facts without validity dates.

It is **not** the proprietary Zep service or an exact reproduction of the paper's published scores. Differences include DeepSeek instead of GPT-4o, an English BGE small embedding model instead of BGE-m3, local Kuzu instead of Neo4j, edge-only RRF retrieval instead of the paper's full edge/entity/community context, and a smaller LongMemEval Oracle subset rather than LongMemEval-S. The results therefore test the mechanism, not numeric agreement with the paper.

## Files

- `runtime.py`: DeepSeek client, local embeddings, Kuzu driver, and the workaround for the current Kuzu full-text index setup.
- `smoke.py`: two-event write/search demonstration.
- `synthetic.py`: 20 deterministic two-event cases, each with current, historical, and update-date questions.
- `evaluate.py`: benchmarks and per-question output, including a public LongMemEval Oracle subset.
- `REPORT.md`: setup, results, and limitations.
- `environment-lock.txt`: package versions from the tested virtual environment.
- `PRESENTATION.md`: a 10-12 minute presentation outline using the completed formal comparison.
- `artifacts/`: compact manifests, summaries, and predictions from the completed runs; public conversation text is excluded.
- `results/`: generated per-run manifests, predictions, summaries, and Kuzu databases (local only).
- `graphiti/`: pinned upstream source snapshot at commit `fb60e59d4a208c99e7d0186ee6335d2a257f17f2` (local only).

## Setup on Windows PowerShell

Use Python 3.12. The current local virtual environment is `.venv`. For a fresh setup:

```powershell
cd D:\Project\ZepReproduction
git clone https://github.com/getzep/graphiti.git graphiti
git -C graphiti checkout fb60e59d4a208c99e7d0186ee6335d2a257f17f2
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "graphiti[kuzu]"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe prepare_model.py
```

Put your `DEEPSEEK_API_KEY` in `.env`. This file is ignored by Git. Run `prepare_model.py` explicitly to download the embedding model into `model_cache/` before evaluation. Evaluation uses only the cache; `prepare_model.py --offline` checks readiness. Use `--cache-dir` to validate a separate empty cache. If the default Hugging Face endpoint is unavailable, set `HF_ENDPOINT=https://hf-mirror.com` for the first download. Later runs use the cached model offline. The source snapshot can be obtained from `https://api.github.com/repos/getzep/graphiti/zipball/fb60e59d4a208c99e7d0186ee6335d2a257f17f2` and extracted to `graphiti/`.

## Run

```powershell
.\.venv\Scripts\python.exe smoke.py
.\.venv\Scripts\python.exe evaluate.py --suite synthetic --limit 20
.\.venv\Scripts\python.exe evaluate.py --suite longmemeval --limit 10 --seed 5660 --max-chars 30000
```

For LongMemEval, download [the public Oracle JSON](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json) to `longmemeval_oracle.json`. The Oracle dataset provides the relevant sessions for each question; it is materially easier than the original full-history LongMemEval-S task. The script samples at most `--limit` examples from each of `knowledge-update`, `temporal-reasoning`, and `multi-session`, with fixed seed and a context-length ceiling. Selected IDs are written to `manifest.json`.

Every run creates a dated folder in `results/` with:

- `manifest.json`: input IDs, versions, seed, and settings.
- `predictions.jsonl`: question, gold answer, prediction, full context used, correctness, retrieval IDs, latency, token usage, ingestion metrics, or an explicit error.
- `summary.json` and `summary.csv`: accuracy, mean answer latency, and mean answer input tokens by method and question type.
- The summaries also show retrieval plus answer latency and Graphiti construction cost per case.
- `graphs/`: a separate Kuzu database per case, so no cross-case memory leaks.

The synthetic scorer uses deterministic answer/date matching. The LongMemEval scorer uses a DeepSeek factual-equivalence judge; this is an extra source of variance and potential bias. All raw answers remain in `predictions.jsonl` for manual auditing. The script writes after each case, so partial runs preserve completed results.

Three complete synthetic trials and one 30-question public Oracle run are exported in `artifacts/`. Use `summarize_run.py` to rebuild summaries from a local JSONL run, and `export_results.py` to refresh the compact tables for the recorded runs.

## Experimental controls

The three answer methods use the same DeepSeek model, temperature, and answer prompt. The ablation reuses the *same retrieved edges* and removes only `valid_at`/`invalid_at` from the constructed context. The full-history baseline includes original episode timestamps. Graph ingestion uses only episode text and timestamps; reference answers and `has_answer` labels are never added to the graph or supplied to the answer model. Public data is sorted by session timestamp before ingestion.

Known upstream compatibility issues in Graphiti 0.31.2: its Kuzu driver's public `build_indices_and_constraints` is a no-op despite search requiring full-text indexes, and the current episode code expects `_database` when `group_id` is supplied. This project calls the driver's maintenance indexing operation directly and uses one database per case without `group_id`. The upstream source snapshot is otherwise unchanged.

## Reliability revision (v2)

Run `python -m unittest discover -p "test_*.py"` and `python audit_previous.py` before experiments. `python validate_baseline.py` runs smoke/pilots followed by three trials per suite and stops on any recorded error. Old runs are preserved. V2 run timestamps are UTC and include unique IDs.

V2 rejects non-boolean judge results and saves raw judgments and usage. Synthetic scoring accepts complete answers and a closed set of category aliases (Project X, X laptop, X gym); negations and alternative answers are rejected. Full-history answers execute independently of the graph. Every planned question/method has a record, including failures. `accuracy` is correct/planned; `scored_accuracy` is correct/scored. Completion rate and scoring coverage must be reported alongside them. Unknown invalidation dates are labelled "not recorded", not confirmed current validity.

Manifests store source/data hashes, answer/judge prompts, provider and decoding settings. Graph top_p remains omitted (provider default), and the model name is a mutable provider alias, not a pinned model revision. Ingestion character counts are proxies, not billable tokens. Judge token usage is separate from answer usage; query timing excludes graph construction and judging.

## Episode granularity modification

The default remains `--episode-granularity session`. Use `--episode-granularity message` only for LongMemEval. Both roles are preserved; each message retains the original session timestamp, role and message index. Writes are sequential; no artificial timestamp offsets are introduced. The full-history answer context is unchanged. Graphiti's default recent-episode context is retained, so the number of messages it covers changes with granularity.

Diagnostic pilot (not a representative accuracy estimate):

```powershell
.\.venv\Scripts\python.exe evaluate.py --suite longmemeval --limit 10 --case-ids 031748ae,45dc21b6,e66b632c --episode-granularity session
.\.venv\Scripts\python.exe evaluate.py --suite longmemeval --limit 10 --case-ids 031748ae,45dc21b6,e66b632c --episode-granularity message
```

Runs use the separate `granularity-v1` name and manifest version. Each successful write is recorded in `ingestion.jsonl` with source identifiers and a body hash. Prediction rows include session/message/episode counts. Do not feed these runs into `aggregate_v2.py`; the archived reliability-v2 summaries are frozen historical artifacts tied to their original source hashes. The 30-question subset contains 57 sessions / 650 messages. Formal paired three-trial execution awaits review of pilot costs.

## Completed formal comparison

The 30-question Oracle subset was run in three paired trials for session and message ingestion. See `REPORT.md`, `FORMAL_GRANULARITY_RESULTS.md`, the matching simple PDF in `output/pdf/`, and `artifacts/formal-granularity-summary.json`. Each of six conditions has 90 complete prediction records. The public `artifacts/formal-granularity-summary.json` contains aggregate numbers and case IDs. Detailed per-trial predictions, full contexts and local databases remain available locally. The formal dated-graph mean was 26.67% for session ingestion and 66.67% for message ingestion, with substantially more graph-building calls for the latter. These are Oracle subset results under the documented DeepSeek/Kuzu/BGE-small setup, not paper-matched LongMemEval-S scores.
