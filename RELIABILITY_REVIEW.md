# Reliability repair and validation

Review date: 2026-11-08. Original remote revision: d7139e26207587a4b210ef5a52a416c471f7d30c.

## Scope and status

Phases 1 and 2 repair the experiment harness and re-establish a baseline. No message-level ingestion, larger top-k, embedding change, or source-context fallback has been introduced. V1 outputs remain unchanged. The report PDF still describes the original experiment; this document and the v2 artifacts are the validation supplement until final reporting is regenerated.

## Repairs

- Explicit first-use model preparation; evaluation remains offline for embedding. Both empty-cache download and subsequent offline load were verified at 384 dimensions.
- Strict JSON boolean judgment. Raw judge response and token usage are retained locally; invalid judgment is an error, not an incorrect answer silently coerced to true.
- Complete-answer synthetic scoring with category aliases derived from the generator: Project X, X laptop, X gym. Negation, concatenated words and multiple candidates are rejected. This is deliberately a short-answer metric, not a general semantic judge.
- Full-history answering is independent of graph setup/ingestion/retrieval. Every planned method/question retains a row on failure. Answer and judge failures are separated; a failed judge does not erase the generated answer.
- Accuracy uses the planned denominator. Completion and scoring coverage are separate; scored-only accuracy is explicitly labelled. Failure is not interpreted as proof that the model gave a wrong semantic answer.
- Unrecorded invalidation dates are no longer described as confirmed current validity. All methods share the revised answer prompt.
- Manifests record code/data hashes, provider/base URL, prompts and decoding settings. Graph top_p is explicitly documented as omitted. The mutable model alias remains a limitation.
- Pilot mug-price evidence is labelled separately in REPORT.md.

## Offline evidence

Eight tests cover original dataset/ablation checks, strict scoring, judge types, graph creation and retrieval failures, denominator handling and preserving an answer when judging fails. All pass.

`artifacts/reliability-offline-audit.json` checks 540 synthetic and 90 public historical predictions: zero execution errors or duplicate keys. The corrected synthetic scorer changes no historical labels. Public judge raw responses were not saved in v1, so their types cannot be retroactively validated.

Manual review of the 30 graph-condition public answers identifies an ambiguous numerical case: a2f3aa27, reference 1300, prediction "Close to 1300.", labelled false by the old judge. The equivalence depends on whether approximation is accepted; do not silently change this label or claim an independently verified public score. The old graph score includes three correct abstentions. A full blinded human adjudication is not claimed.

## Online protocol

Smoke, two-case synthetic pilot, and three-question public pilot precede formal trials. Three independent full runs per suite are required (20 synthetic cases / 60 questions per method; 30 fixed public questions per method). `aggregate_v2.py` only accepts complete trials whose code hashes match the final frozen implementation. Intermediate trials with changed code are excluded, not overwritten. Pilots are never combined with formal results.

Accuracy is reported as mean and sample standard deviation across trials, including answerable/abstention public strata. Construction time and calls, query latency, answer tokens and judge usage are distinct quantities. Ingestion character counts are not billable token estimates. Query latency excludes construction and judging.

## Remaining limits and modification decision

This is a mechanism reproduction with DeepSeek, local Kuzu, BGE-small, edge-only retrieval and LongMemEval Oracle, not the paper's numerical setup. A negative public result does not refute the paper. Strict scoring and prompt repairs establish a new baseline; differences from v1 cannot be attributed to one research modification.

Before a new modification, inspect whether missing answer facts exist in the stored graph. If absent, test message-level ingestion; if present but not retrieved, test top-k 10 versus 20. Select one intervention, freeze all other settings and compare against the repaired baseline. Neither intervention is implemented in this phase.

### Scorer interpretation

The v2 scorer measures constrained short-answer correctness. In the first accepted synthetic trial, `Kai now leads project Willow.` is semantically correct but rejected because it is a full sentence rather than an allowed complete short answer. This is a format mismatch, not a memory failure. The frozen metric is not changed mid-experiment; such cases must be disclosed alongside strict scores and may motivate a separately evaluated scorer improvement. No post-hoc semantic override is folded into the official strict metric.

### Read-only graph diagnosis (first accepted public trial)

Inspected all relation facts in `20261108-081818-v2-7a3f6b88-longmemeval`, not just retrieved top-k results:

- 031748ae: 6 facts; contains a team outing with 4 engineers plus manager Rachel, but no complete old-4/current-5 engineers update. Event attendance must not be equated with a management headcount update.
- 45dc21b6: 26 facts, dominated by travel/vegan restaurant information; no answer-bearing Emma recipe-count fact.
- e66b632c: 20 facts; current 26:30 5K result exists, but prior 27:45 best time is absent.

These three cases support an ingestion/extraction coverage bottleneck in this trial. Increasing top-k cannot retrieve an absent fact. They motivate message-level ingestion as the next controlled modification, but do not establish the cause of every failure or guarantee that finer ingestion will fix it.
