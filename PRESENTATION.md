# Presentation outline (about 8-10 minutes)

1. **Research question (1 min).** The Zep paper claims a temporal knowledge graph can preserve evolving agent memory and retrieve compact context. I tested one part: old/new fact validity and its effect on answers.
2. **Pipeline (1 min).** Dated conversation -> Graphiti entity/fact extraction -> Kuzu graph -> hybrid fact search -> DeepSeek answer. Show the two-event smoke output: Atlas Labs became invalid on 15 April 2024; Harbor Studio became valid.
3. **What differs from the paper (1 min).** DeepSeek, BGE small embeddings, Kuzu, edge-only search, LongMemEval Oracle subset, one session per episode. Explain why published percentages are reference points rather than a direct target.
4. **Controlled experiment (1 min).** Compare full history, Graphiti with `valid_at`/`invalid_at`, and identical retrieved facts with those two dates removed. Temperature and answer prompt are fixed.
5. **Synthetic results (1 min).** 20 cases x 3 questions. All three methods answer current and historical state correctly; change date is 20/20 with full history or dated graph and 0/20 when temporal metadata is removed. Full history is cheaper on these short cases.
6. **Public subset results (1.5 min).** 30 LongMemEval Oracle questions: full history 24/30, simplified Graphiti 7/30, no-date graph 7/30. For the 27 answerable questions, scores are 21/27 vs 4/27. Graph prompts are much shorter, but relevant facts are frequently missing.
7. **Failure example and debugging (1 min).** Show the engineers question: source history says four then five, but graph search only returns the new job title, so the answer becomes `UNKNOWN`. Explain Kuzu index workaround and the session-level ingestion shortcut.
8. **Conclusion and next steps (1 min).** Temporal metadata works when the needed fact is extracted. This simplified public-data run does not match the paper's accuracy gain. Next: message-level ingestion, paper-matched split/models, broader retrieval, human spot checks, repeated public trials.

Record the screen showing `REPORT.md`, `README.md`, and one `predictions.jsonl` example. Keep the recording under 15 minutes. A Zoom recording URL must be supplied by the student after recording; no link is invented here.

