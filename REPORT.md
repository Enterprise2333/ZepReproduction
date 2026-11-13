# Zep temporal memory: a partial reproduction and controlled modification

FTEC5660 individual reproducibility project, paper 12. The target paper is Rasmussen et al., [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956). The authors' open-source implementation is [Graphiti](https://github.com/getzep/graphiti). This project uses a pinned Graphiti source snapshot and graphiti-core version 0.31.2. Our code and outputs are in [Enterprise2333/ZepReproduction](https://github.com/Enterprise2333/ZepReproduction).

## Target and conclusion

I reproduced one claimed capability: dated conversation episodes can yield old and new knowledge-graph facts with validity intervals, which help answer temporal questions. I then tested one modification: writing each LongMemEval message as a separate episode instead of writing each entire session as one episode. On a fixed 30-question LongMemEval Oracle subset, the three-trial mean accuracy of the dated graph rose from **26.67% to 66.67%**. Graph construction calls rose from about **308 to 4,522 per trial**. The full-history answer scored around 72-73%, so the modified graph still did not surpass it in this setting.

The paper's published LongMemEval-S accuracy gain is not numerically reproduced here. The data, models and retrieval pipeline are materially different. The result supports a narrower claim: ingestion granularity strongly affects what the temporal graph remembers in this local setup.

## System and setup

The pipeline runs the pinned Graphiti source, not a reimplementation. It extracts and resolves entities and relation facts from dated episodes, stores the temporal graph in local Kuzu 0.11.3, retrieves the top 10 relation facts by Graphiti's default search, then asks DeepSeek to answer. Graph operations, answers and automatic judging use `deepseek-chat` through the OpenAI-compatible endpoint `https://api.deepseek.com/v1`; the embedding model is the locally cached `BAAI/bge-small-en-v1.5` with 384 dimensions. Python 3.12 was used. The answer and judge use temperature 0, top_p 1 and output limits of 128 and 50 tokens respectively. Graph construction uses temperature 0 and a 4096-token output limit; top_p is omitted and follows the provider default. The same answer and judge prompts are used in both conditions. The model name is a provider alias, not an immutable model revision.

The original paper used the Zep service, Neo4j, BGE-m3, and GPT-4o family models, with fuller entity and community retrieval. Its reported LongMemEval-S GPT-4o-mini example was 55.4% for full context and 63.8% for Zep, with roughly 115k versus 1.6k answer-context tokens. Those figures are reference points only. Our public data is the Oracle variant, which supplies relevant sessions. We selected 10 questions from each of knowledge-update, temporal-reasoning and multi-session, for 30 questions in total. Selection used seed 5660 and a 30,000-character source ceiling. The selected IDs and data hash are in the manifests. Gold answers and `has_answer` labels do not enter graph construction or answer prompts.

The full-history baseline receives the original dated sessions in both conditions. Session ingestion writes 57 episodes across the 30 cases; message ingestion writes 650 episodes, keeping both user and assistant roles. Every message inherits its session timestamp, keeps its original order and gets no artificial time offset. Both graph conditions use a fresh database per case. Graphiti's default recent-episode context remains unchanged; changing episode size also changes how many original messages that window covers. This is a limitation of isolating the intervention, although no parameter was tuned between conditions.

## Metrics and experimental controls

Each of three trials evaluated the same 30 public questions under three answer contexts: full history; top-10 graph facts with `valid_at` and `invalid_at`; and the same graph facts with only those date fields hidden at answer time. The latter is a context-metadata ablation, not a graph-without-time implementation. Accuracy uses all planned questions. We separately report 27 answerable and 3 abstention questions, mean accuracy and sample standard deviation across trials, plus paired wrong-to-right and right-to-wrong changes. Public answers use a DeepSeek factual-equivalence judge with strict JSON boolean parsing; raw judgments are retained locally. A fully blinded human adjudication was not performed. Repeating the same 30 questions three times measures run variation, not population uncertainty from 90 independent questions.

## Results

| Ingestion | Answer context | All 30, mean ± SD in pp | Answerable 27, mean ± SD in pp |
|---|---|---:|---:|
| Session | Full history | 72.22% ± 1.92 | 69.14% ± 2.14 |
| Session | Dated graph | 26.67% ± 3.33 | 18.52% ± 3.70 |
| Session | Graph without displayed dates | 23.33% ± 0.00 | 14.81% ± 0.00 |
| Message | Full history | 73.33% ± 0.00 | 70.37% ± 0.00 |
| Message | Dated graph | 66.67% ± 5.77 | 62.96% ± 6.42 |
| Message | Graph without displayed dates | 51.11% ± 1.92 | 45.68% ± 2.14 |

All three abstention questions were scored correct under every method and trial. For the dated graph, the message modification improved 14, 13 and 11 paired questions across the three trials, while 1, 1 and 0 previously correct questions regressed. Thus the 40.00 percentage-point overall gain does not mean every item improved. The full-history difference between modes, despite identical context, illustrates model/judge variation and the mutable model alias; it should not be attributed to ingestion. The dated-message graph beats its own no-date answer context by 15.56 points on average, but both use the same underlying temporal graph.

| Graph construction per 30-case trial | Session mean | Message mean |
|---|---:|---:|
| Graphiti LLM calls | 308 | 4,522 |
| Build time in minutes | 6.2 | 81.0 |

The message condition used about 14.7 times as many graph-building calls and 13.0 times as much recorded construction time. Parallel trial work shared the same host and API, so elapsed time is descriptive rather than an isolated speed benchmark. Query latency excludes graph construction and judging. Construction is shared by the dated and no-date answer contexts and must not be counted twice. Character telemetry for graph LLM calls is not billable token usage, so no currency cost is inferred. Per-run answer tokens, judge tokens, time and calls are in `artifacts/formal-granularity-summary.json`.

## Case analysis and edge cases

The three-question diagnostic pilot was intentionally selected from prior failures. Its 0/3 to 3/3 graph improvement is not mixed into the formal score. In the formal runs, the Emma recipe-count question and previous 5K best-time question changed from wrong to right in all three trials. The engineers update changed from wrong to right in only one trial. The other two message runs knew the current five-person count but did not answer both old and new counts. This is a remaining extraction and retrieval variability issue. Case identifiers remain available in the result artifacts.

Two regressions deserve attention. In trial 1, a question with gold answer 1300 changed from the session answer "Nearly 1300", which was judged correct, to the message answer "1250", which was judged incorrect. In trial 2, a transport question changed from "Train" to "Bus". The numerical example also illustrates automatic-judge sensitivity to approximation: a prior evaluation judged "Close to 1300" differently. We retained the recorded judgments rather than silently overriding them.

Operational edge cases handled in the code: explicit first-use embedding download and offline readiness check; Kuzu full-text index setup; one database per case to avoid `group_id` incompatibility and cross-case leakage; baseline execution independent of graph failures; strict boolean judge parsing with raw responses retained; complete planned-answer denominators and coverage/error metrics; and a distinction between unknown invalidation time and confirmed current validity. The original source is unchanged. The model/data hashes, prompts, selected question IDs, per-case sources and predictions remain auditable. The historical 20-case synthetic test also confirms that date answers fall from 20/20 to 0/20 when answer-time date fields are hidden, across three trials, but these cases are deliberately simple.

## Limits and recommendations

The measured improvement is specific to this Oracle subset, DeepSeek, local Kuzu, BGE-small and top-10 relation-only retrieval. Message-level writing costs far more graph calls, and the full-history answer remains slightly more accurate on these short relevant histories. A larger reproduction would pin an immutable model revision, use the paper's LongMemEval-S split and prompt protocol, add entity and community context, log exact construction token usage, and review judge disagreements with a human. Future users should verify the embedding cache, Kuzu indexes, data hash and selected IDs before comparing scores. The companion presentation outline uses the complete formal results.
