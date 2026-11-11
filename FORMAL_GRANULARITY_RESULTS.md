# Formal episode-granularity experiment

Three paired trials of the same 30 LongMemEval Oracle questions. Session versus message ingestion is the intervention. These are simplified Zep reproduction results, not paper-matched LongMemEval-S scores. The same questions recur across trials: do not treat the 90 repeated question observations as 90 independent examples or infer population significance from the reported standard deviation.

| Mode | Method | Stratum | Mean accuracy | Sample SD (pp) |
|---|---|---|---:|---:|
| message | full_history | abstention | 100.00% | 0.00 |
| message | full_history | all | 73.33% | 0.00 |
| message | full_history | answerable | 70.37% | 0.00 |
| message | graphiti | abstention | 100.00% | 0.00 |
| message | graphiti | all | 66.67% | 5.77 |
| message | graphiti | answerable | 62.96% | 6.42 |
| message | no_temporal_metadata | abstention | 100.00% | 0.00 |
| message | no_temporal_metadata | all | 51.11% | 1.92 |
| message | no_temporal_metadata | answerable | 45.68% | 2.14 |
| session | full_history | abstention | 100.00% | 0.00 |
| session | full_history | all | 72.22% | 1.92 |
| session | full_history | answerable | 69.14% | 2.14 |
| session | graphiti | abstention | 100.00% | 0.00 |
| session | graphiti | all | 26.67% | 3.33 |
| session | graphiti | answerable | 18.52% | 3.70 |
| session | no_temporal_metadata | abstention | 100.00% | 0.00 |
| session | no_temporal_metadata | all | 23.33% | 0.00 |
| session | no_temporal_metadata | answerable | 14.81% | 0.00 |

## Paired changes

| Trial | Method | Wrong → right | Right → wrong |
|---:|---|---:|---:|
| 1 | full_history | 0 | 0 |
| 1 | graphiti | 14 | 1 |
| 1 | no_temporal_metadata | 9 | 1 |
| 2 | full_history | 0 | 0 |
| 2 | graphiti | 13 | 1 |
| 2 | no_temporal_metadata | 10 | 1 |
| 3 | full_history | 1 | 0 |
| 3 | graphiti | 11 | 0 |
| 3 | no_temporal_metadata | 8 | 0 |

## Cost and interpretation

Independent trial work ran concurrently on a shared host/API; execution order was not fully counterbalanced. Query and construction timing can reflect contention. Do not interpret them as isolated speed benchmarks. Graph construction is shared by the dated/no-date contexts and must not be counted twice. Character telemetry is not billable token usage; monetary cost is not inferred.

Execution/judge errors in the final accepted records: 0. Full trial counts, coverage, case IDs, regressions, tokens and calls are in artifacts/formal-granularity-summary.json.

The pilot deliberately selected three prior failures; its 3/3 result is not mixed into these formal results. Message order and session timestamps are preserved; both user and assistant content is included. The default recent-episode window is unchanged, so its effective message coverage differs by mode. Public judgments are LLM-based, not a blinded human adjudication.

Results combine complete per-case records from multiple execution windows under the same ingestion, prompting and scoring configuration. Source provenance is retained for audit. Costs refer to accepted-case processing, not total account spending. Model aliases are not pinned revisions.
