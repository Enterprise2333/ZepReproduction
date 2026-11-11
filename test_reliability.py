import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from evaluate import parse_judgment, synthetic_correct, summarize, run_case
from synthetic import cases


class Reliability(unittest.IsolatedAsyncioTestCase):
    def test_judge_types(self):
        self.assertIs(parse_judgment('{"correct":false}'), False)
        self.assertIs(parse_judgment('{"correct":true}'), True)
        for raw in ('{"correct":"false"}', '{"correct":1}', '{}', 'null', 'broken'):
            with self.assertRaises((ValueError, TypeError)):
                parse_judgment(raw)

    def test_strict_answers(self):
        for text in ('Not Harbor Studio', 'Harbor Studio or Atlas Labs', 'HarborStudio'):
            self.assertFalse(synthetic_correct('Harbor Studio', text))
        self.assertTrue(synthetic_correct('Harbor Studio', ' harbor  studio. '))
        self.assertTrue(synthetic_correct('Beacon', 'Project Beacon.'))
        self.assertTrue(synthetic_correct('Hilltop', 'Hilltop gym'))
        self.assertFalse(synthetic_correct('Hilltop', 'Not Hilltop gym'))
        self.assertTrue(synthetic_correct('2024-04-03', 'April 3, 2024.'))
        for text in ('Not April 3, 2024', '2024-04-03 or 2024-04-04', '2024-02-30'):
            self.assertFalse(synthetic_correct('2024-04-03', text))

    async def test_graph_failure_keeps_baseline_and_denominator(self):
        answer = dict(answer='Harbor Studio', latency_s=0.1, input_tokens=10, output_tokens=2)
        with tempfile.TemporaryDirectory() as tmp, patch('evaluate.make_graph', side_effect=RuntimeError('injected')), patch('evaluate.ask', new=AsyncMock(return_value=answer)):
            rows = await run_case(cases()[0], Path(tmp), None, 'synthetic', 10)
        self.assertEqual(len(rows), 9)
        self.assertEqual(sum('prediction' in r for r in rows), 3)
        self.assertEqual(sum('error' in r for r in rows), 6)
        summary = summarize(rows)
        for row in summary:
            self.assertEqual(row['n'], 1)
            if row['method'] != 'full_history':
                self.assertEqual(row['accuracy'], 0)
                self.assertEqual(row['scoring_coverage'], 0)

    async def test_invalid_judge_preserves_answer(self):
        from evaluate import evaluate_answer
        row = dict(suite='longmemeval', question='q', gold='g')
        with patch('evaluate.ask', new=AsyncMock(return_value=dict(answer='a', latency_s=1))), patch('evaluate.llm_judge', new=AsyncMock(return_value=dict(judge_raw='bad', error='invalid', error_stage='judge'))):
            await evaluate_answer(row, None, 'context', None)
        self.assertEqual(row['prediction'], 'a')
        self.assertEqual(row['judge_raw'], 'bad')
        self.assertNotIn('correct', row)

    async def test_retrieval_failure_is_per_question(self):
        from types import SimpleNamespace
        graph = SimpleNamespace(add_episode=AsyncMock(), search=AsyncMock(side_effect=RuntimeError('search failed')), close=AsyncMock())
        llm = SimpleNamespace(calls=2, estimated_input_chars=10, estimated_output_chars=10)
        with tempfile.TemporaryDirectory() as tmp, patch('evaluate.make_graph', return_value=(graph,llm)), patch('evaluate.prepare_graph', new=AsyncMock()), patch('evaluate.ask', new=AsyncMock(return_value=dict(answer='Harbor Studio',latency_s=0.1))):
            rows = await run_case(cases()[0], Path(tmp), None, 'synthetic', 10)
        self.assertEqual(len(rows),9)
        self.assertEqual(sum(r.get('error_stage')=='retrieval' for r in rows),6)
        self.assertEqual(sum('prediction' in r for r in rows),3)
        graph.close.assert_awaited_once()
