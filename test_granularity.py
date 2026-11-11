import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from evaluate import longmemeval_cases, ingestion_episodes, episode_context, run_case

class GranularityTests(unittest.IsolatedAsyncioTestCase):
    def test_preserves_sessions_roles_order_and_labels(self):
        for c in longmemeval_cases(10,5660,30000):
            before=episode_context(c['episodes'])
            messages=ingestion_episodes(c,'message')
            for session in c['episodes']:
                group=[m for m in messages if m['session_id']==session['session_id']]
                self.assertEqual('\n'.join(m['body'] for m in group),session['body'])
                self.assertEqual([m['message_index'] for m in group],list(range(len(group))))
                self.assertTrue(all(m['date']==session['date'] for m in group))
                self.assertTrue(all(set(m)=={'date','session_id','message_index','role','body'} for m in group))
            self.assertEqual(episode_context(c['episodes']),before)
            self.assertIs(ingestion_episodes(c,'session'),c['episodes'])

    async def test_actual_writes_preserve_order_and_baseline(self):
        c=longmemeval_cases(1,5660,30000)[0]
        g=SimpleNamespace(add_episode=AsyncMock(), search=AsyncMock(return_value=[]),close=AsyncMock())
        llm=SimpleNamespace(calls=0,estimated_input_chars=0,estimated_output_chars=0)
        ask=AsyncMock(return_value=dict(answer='UNKNOWN',latency_s=0))
        with tempfile.TemporaryDirectory() as t, patch('evaluate.make_graph',return_value=(g,llm)),patch('evaluate.prepare_graph',new=AsyncMock()),patch('evaluate.ask',new=ask),patch('evaluate.llm_judge',new=AsyncMock(return_value={'correct':False})):
            rows=await run_case(c,Path(t),None,'longmemeval',10,'message')
            self.assertEqual(len(Path(t,'ingestion.jsonl').read_text().splitlines()),len(c['message_episodes']))
        self.assertEqual([x.kwargs['episode_body'] for x in g.add_episode.await_args_list],[m['body'] for m in c['message_episodes']])
        self.assertEqual(ask.await_args_list[0].args[2],episode_context(c['episodes']))
        self.assertTrue(all(r['episode_count']==len(c['message_episodes']) for r in rows))

    def test_message_mode_rejects_unstructured_input(self):
        with self.assertRaises(ValueError): ingestion_episodes({'episodes':[]},'message')
