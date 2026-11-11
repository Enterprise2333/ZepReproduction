# Presentation outline (10-12 minutes)

Record a Zoom presentation under 15 minutes. Use `REPORT.md` and `FORMAL_GRANULARITY_RESULTS.md` on screen; insert the recording URL before submission.

1. **Target (1 min).** Zep temporal graph keeps old/new facts and their validity dates. Demonstrate the two-event employer update. Define this as a partial behavior reproduction.
2. **Pipeline and scope (1 min).** Pinned authors' Graphiti source -> local Kuzu -> top-10 relation facts -> DeepSeek answer. Fixed 30-question LongMemEval Oracle subset, three trials. Explain differences from the paper's Zep service, LongMemEval-S, GPT-4o models, BGE-m3 and fuller retrieval; paper numbers are reference points, not directly comparable.
3. **What was repaired (1 min).** Embedding cache preparation, Kuzu indexes, per-case graph isolation, independent full-history baseline, strict JSON judge booleans, error-inclusive denominators and explicit unknown invalidation date. Show 12 passing tests and one manifest; no API key on screen.
4. **Controlled modification (1 min).** Change a session episode into one episode per user/assistant message. Keep original order and session timestamp. Fix data, models, top-k, prompts and scoring. Full-history context remains the same. Explain that Graphiti's recent-episode context now spans fewer original messages.
5. **Main result (2 min).** Dated graph: session 26.67% (SD 3.33 pp) -> message 66.67% (SD 5.77 pp), 30 questions in each of three trials. Answerable-only: 18.52% -> 62.96%. Full history around 72-73%. All abstention questions correct. Three trials repeat the same questions, so SD is run variability.
6. **Paired changes and failures (1.5 min).** Wrong-to-right counts 14, 13, 11; right-to-wrong 1, 1, 0. Emma recipe count and previous 5K best time improve in all three runs. Engineers update improves in only one, showing pilot 3/3 was not representative. Show 1300 -> 1250 and Train -> Bus regressions; mention LLM judge sensitivity.
7. **Temporal ablation (1 min).** The same message graph facts without displayed validity dates score 51.11%, versus 66.67% with dates. Explain that the ablation changes answer context, not graph construction.
8. **Cost (1 min).** Mean graph-building calls per 30-case trial: 308 -> 4,522; construction time 6.2 -> 81.0 min. Both graph answer contexts share construction. Parallel work means timing is descriptive. Character counts are not billing tokens.
9. **Conclusion and recommendations (1 min).** Message granularity helps this simplified memory pipeline at substantial cost, yet does not beat full-history accuracy here. Next steps: pin exact model/data, paper-matched split and prompts, broader retrieval, exact token accounting, and human review of judge disagreements.

The report PDF has no page headers or footers. Keep the screen recording simple and focused on the code, manifest, result table, and two concrete cases.
