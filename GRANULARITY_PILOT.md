# Message-level ingestion: implementation and diagnostic pilot

2026-11-10. Development plan steps 1–6 complete. This document records the diagnostic pilot before the completed formal comparison; see the final report for complete results.

## Implementation

`evaluate.py --episode-granularity session|message` defaults to session. Both user and assistant messages are retained. Messages inherit session timestamps and original order without invented offsets. Source session ID, role and message index are retained in memory and successful-write provenance logs. The full-history context, answer/judge prompts, models, embedding, top-k and scoring remain unchanged. Graphiti's default recent-episode context is unchanged; its effective message coverage changes with granularity and is part of the intervention's limitation.

Tests: 11 pass, including all 30 selected cases' content reconstruction, role/order/timestamp preservation, absence of extra label fields, actual mocked write order, unchanged baseline context and rejection of unsupported synthetic message mode. Both online modes completed without errors. Manifest comparison verifies identical selected IDs, source/data hashes, prompts, model settings and top-k.

## Diagnostic results

These are three deliberately chosen previous failures, not a random sample and not an accuracy estimate for the full benchmark.

| Measure | Session | Message |
|---|---:|---:|
| Episodes | 6 | 72 |
| Graph correct | 0/3 | 3/3 |
| No-time graph correct | 0/3 | 2/3 |
| Full-history correct | 2/3 | 2/3 |
| Graph build calls | 49 | 484 |
| Build time | 66.58 s | 466.67 s |
| Estimated input characters | 664,051 | 4,953,655 |

Graph facts and retrieved contexts confirm the intended mechanism:

- 031748ae: message graph contains past four-engineer and current five-engineer facts with temporal metadata; the dated condition answers correctly while the no-time condition fails.
- 45dc21b6: message graph contains the updated count of three Emma recipes; both graph contexts answer correctly.
- e66b632c: message graph contains the old 27:45 best time; both graph contexts answer correctly. Full history returns the current 26:30 time and is incorrect in both runs.

See artifacts/granularity-pilot-summary.json and artifacts/granularity-pilot-diagnosis.json. Raw judge responses, full contexts and databases remain in local results folders; no historical baseline output was overwritten.

## Approval checkpoint for the formal experiment

The fixed 30 questions contain 57 sessions and 650 messages. Three trials of BOTH modes mean 171 session episodes and 1,950 message episodes, with 540 answer predictions and 540 judge calls across the two modes. Graph ingestion estimates, extrapolated linearly per episode from this pilot:

| Mode | Estimated graph calls | Estimated graph build hours |
|---|---:|---:|
| Session, three trials | 1,396 | 0.53 |
| Message, three trials | 13,108 | 3.51 |

Total roughly 14,504 graph calls and 4.04 construction hours, plus answering/judging and overhead. This is a planning estimate, not a limit or guarantee: graph growth and content affect calls and latency. Graph telemetry records characters, not actual billed input/output/cache tokens, so a reliable currency estimate cannot be derived from these records. Do not equate the 9.88x call ratio with the billing ratio. Exact monetary cost requires provider usage/billing records or additional token instrumentation.

The formal experiment is complete. Prompts, top-k and scoring were held fixed. The final report includes regressions as well as improvements.
