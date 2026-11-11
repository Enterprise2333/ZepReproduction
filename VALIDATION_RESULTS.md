# Repaired baseline: validation results

Experiments: 2026-11-08; final audit: 2026-11-10. Reliability v2; this is a new baseline, not a causal test of a single research modification.

Three independent trials per suite. Accuracy uses all planned questions. SD is the sample standard deviation across trials, expressed in percentage points.

| Suite | Method | Stratum | n per trial | Accuracy mean ± SD | Minimum scoring coverage |
|---|---|---|---:|---:|---:|
| longmemeval | full_history | abstention | 3 | 100.00% ± 0.00 pp | 100.0% |
| longmemeval | full_history | all | 30 | 70.00% ± 3.33 pp | 100.0% |
| longmemeval | full_history | answerable | 27 | 66.67% ± 3.70 pp | 100.0% |
| longmemeval | graphiti | abstention | 3 | 100.00% ± 0.00 pp | 100.0% |
| longmemeval | graphiti | all | 30 | 26.67% ± 0.00 pp | 100.0% |
| longmemeval | graphiti | answerable | 27 | 18.52% ± 0.00 pp | 100.0% |
| longmemeval | no_temporal_metadata | abstention | 3 | 100.00% ± 0.00 pp | 100.0% |
| longmemeval | no_temporal_metadata | all | 30 | 23.33% ± 0.00 pp | 100.0% |
| longmemeval | no_temporal_metadata | answerable | 27 | 14.81% ± 0.00 pp | 100.0% |
| synthetic | full_history | all | 60 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | full_history | change-date | 20 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | full_history | current | 20 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | full_history | historical | 20 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | graphiti | all | 60 | 99.44% ± 0.96 pp | 100.0% |
| synthetic | graphiti | change-date | 20 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | graphiti | current | 20 | 98.33% ± 2.89 pp | 100.0% |
| synthetic | graphiti | historical | 20 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | no_temporal_metadata | all | 60 | 66.67% ± 0.00 pp | 100.0% |
| synthetic | no_temporal_metadata | change-date | 20 | 0.00% ± 0.00 pp | 100.0% |
| synthetic | no_temporal_metadata | current | 20 | 100.00% ± 0.00 pp | 100.0% |
| synthetic | no_temporal_metadata | historical | 20 | 100.00% ± 0.00 pp | 100.0% |

## Interpretation

- Synthetic scores use complete short-answer matching and closed category aliases. A semantically correct full sentence can fail this strict metric; see RELIABILITY_REVIEW.md for the confirmed Willow example. Do not call that a memory failure.
- Public scores use DeepSeek as judge, not a blinded human panel. Raw judgments and usage remain in the local per-run JSONL. Old v1 judgments cannot be retrospectively type-checked.
- Full history, dated graph and the no-date context share the answer model/prompt. The ablation hides fields at answer time; temporal graph construction and retrieved edges remain intact.
- The paper uses materially different models/data/retrieval. These results concern a simplified mechanism reproduction, not reproduction of the published LongMemEval-S numbers.
- Read-only inspection of three failing graphs found missing answer-bearing facts. Message-level ingestion is the recommended next isolated modification; it has not yet been implemented.

## Accepted runs

- 20261108-081508-v2-673fb819-synthetic: 0 errors
- 20261108-081818-v2-7a3f6b88-longmemeval: 0 errors
- 20261108-082746-v2-356b7a99-synthetic: 0 errors
- 20261108-083305-v2-ef25e6f5-longmemeval: 0 errors
- 20261108-084242-v2-2813f162-synthetic: 0 errors
- 20261108-084808-v2-759cd0aa-longmemeval: 0 errors

## Exclusions

- 20261108-081249-v2-2cdf6b03-synthetic: implementation changed during validation; excluded

## Costs and limitations

Per-run answer tokens, judge tokens, construction calls/time and query latency are in artifacts/reliability-v2-summary.json. Construction is shared between the two graph conditions: do not sum it twice. Construction character counts are not exact billable tokens; no monetary saving is claimed. Query timing excludes construction and judging.

Eight offline tests pass. Empty-cache model download, subsequent offline readiness and clear failure on an unprepared offline cache were exercised. A complete installation on a second clean machine was not performed.

This document records the repaired baseline before the message-level modification. The final `REPORT.md`, `PRESENTATION.md`, and PDF now include the completed modification experiment.
