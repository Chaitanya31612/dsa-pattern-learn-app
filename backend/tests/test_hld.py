import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hld_api import DIMENSIONS, REPAIR_DIMENSIONS, build_hld_router, catalog
from build_hld_course import DEFAULT_SOURCE, build


class StubProvider:
    def __init__(self):
        self.calls = []
        self.content = json.dumps({'dimensions': [{'id': k, 'score': 3 if i < 2 else 2, 'evidence': 'A stated decision', 'feedback': 'Specific reasoning'} for i, k in enumerate(DIMENSIONS)],
                                  'summary': 'Provisional', 'strengths': [], 'gaps': [], 'next_exercise': 'Change freshness', 'critical_issue': False})
        self.success = True

    def analyze(self, content, prompt):
        self.calls.append((json.loads(content), prompt))
        return SimpleNamespace(content=self.content, success=self.success, provider=SimpleNamespace(value='stub'), model='test')


class HLDTests(unittest.TestCase):
    def setUp(self):
        self.provider = StubProvider()
        app = FastAPI()
        app.include_router(build_hld_router(lambda: self.provider))
        self.client = TestClient(app)
        self.payload = {'module_id': '03-url-shortener', 'exercise_id': 'p1', 'attempt': {'phases': {'contract': 'Only owners update mappings.'}, 'diagram': '', 'assisted': False}}

    def test_import_preserves_all_content_and_visual_pairs(self):
        built = build(DEFAULT_SOURCE)
        self.assertEqual(len(built['modules']), 31)
        self.assertEqual(sum(len(m['questions']) for m in built['modules']), 124)
        self.assertEqual(sum(m['hours'] for m in built['modules']), 136)
        for m in built['modules']:
            self.assertEqual(len(m['visuals']), 2)
            self.assertTrue(all(s.get('quick') for s in m['sections']))
            self.assertTrue(all(e['prompt'] and e['solution'] for e in m['exercises']))
        self.assertEqual({m['chapter'] for m in built['modules'] if m.get('track') == 'volume-2' and m.get('chapter')}, set(range(1, 14)))
        self.assertEqual(sum(len(m['exercises']) for m in built['modules']), 95)
        self.assertTrue(all(m['examples'] for m in built['modules'] if m['track'] == 'volume-2'))
        self.assertEqual(built, catalog())

    def test_practice_chat_does_not_send_reference_solution(self):
        self.provider.content = 'What freshness do you need?'
        res = self.client.post('/api/ai/hld-chat', json={**self.payload, 'mode': 'practice', 'messages': [{'role': 'user', 'content': 'Clarify this'}]})
        self.assertEqual(res.status_code, 200)
        content, prompt = self.provider.calls[0]
        self.assertNotIn('Reference argument:', content['reference'])
        self.assertIn('do NOT provide a full solution', prompt)
        self.assertIn('short sentences', prompt)

    def test_derived_score_and_assisted_gate(self):
        res = self.client.post('/api/hld/evaluate', json=self.payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['total'], 18)
        self.assertTrue(res.json()['passed'])
        self.payload['attempt']['assisted'] = True
        self.assertFalse(self.client.post('/api/hld/evaluate', json=self.payload).json()['passed'])

    def test_volume2_feedback_uses_the_selected_reference_and_practice_does_not(self):
        self.payload['module_id'] = '27-payments'
        response = self.client.post('/api/hld/evaluate', json=self.payload)
        self.assertEqual(response.status_code, 200)
        content, _ = self.provider.calls[-1]
        self.assertIn('provider', content['reference_argument'])
        self.assertIn('2,000', content['exercise'])
        self.provider.content = 'What can you know after the reply is lost?'
        response = self.client.post('/api/ai/hld-chat', json={**self.payload, 'mode': 'practice', 'messages': [{'role': 'user', 'content': 'One hint'}]})
        self.assertEqual(response.status_code, 200)
        content, _ = self.provider.calls[-1]
        self.assertNotIn('reference_argument', content)
        self.assertNotIn('Reference argument:', content['reference'])

    def test_repair_has_its_own_rubric_and_cannot_award_a_design_pass(self):
        self.payload['exercise_id'] = 'p3'
        # An eight-area report is invalid for a focused repair.
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 502)
        report = json.loads(self.provider.content)
        report['dimensions'] = [{**d, 'score': 3} for d in report['dimensions'] if d['id'] in REPAIR_DIMENSIONS]
        self.provider.content = json.dumps(report)
        response = self.client.post('/api/hld/evaluate', json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['scope'], 'repair')
        self.assertEqual(response.json()['total'], 12)
        self.assertFalse(response.json()['passed'])
        self.assertIn('focused repair', self.provider.calls[-1][1])

    def test_invalid_scores_and_duplicate_dimensions_never_get_saved(self):
        data = json.loads(self.provider.content)
        data['dimensions'][0]['score'] = 100
        self.provider.content = json.dumps(data)
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 502)
        data['dimensions'][0]['score'] = 2
        data['dimensions'][0]['evidence'] = '   '
        self.provider.content = json.dumps(data)
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 502)
        data['dimensions'][0]['evidence'] = 'Stated evidence'
        data['dimensions'][0]['id'] = data['dimensions'][1]['id']
        self.provider.content = json.dumps(data)
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 502)

    def test_provider_failure_and_empty_design_do_not_fabricate_scores(self):
        self.provider.success = False
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 503)
        self.payload['attempt']['phases'] = {}
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 422)
        self.payload['module_id'] = 'missing'
        self.assertEqual(self.client.post('/api/hld/evaluate', json=self.payload).status_code, 404)


if __name__ == '__main__':
    unittest.main()
