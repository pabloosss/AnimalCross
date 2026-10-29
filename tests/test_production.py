import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from production import Production, recover
from team import Team
from agent import Agent


class ProductionTests(unittest.TestCase):
    def test_recovery_does_not_replay_or_change_completed_job(self):
        with tempfile.TemporaryDirectory() as root:
            interrupted = Production(root, 'one', 'Film')
            finished = Production(root, 'two', 'Pomysł')
            finished.finish('done', 'Plan gotowy')
            recover(root)
            self.assertEqual(json.loads(interrupted.path.read_text())['state'], 'interrupted')
            self.assertEqual(json.loads(finished.path.read_text())['state'], 'done')

    def test_writer_and_technician_overlap_before_operator(self):
        started = threading.Event()
        writing = threading.Event()
        inspected = threading.Event()
        def api(base, route, **kw):
            if route == '/system_stats':
                started.set()
                if not writing.wait(2): raise RuntimeError('No parallel writer')
                return {'devices': []}
            inspected.set()
            return {}
        def ask(instruction, content):
            if 'Jesteś scenarzystą' in instruction:
                self.assertTrue(started.wait(2))
                writing.set()
            return 'Tekst'
        class Operator:
            evidence = []
            def __init__(self, *args): pass
            def run(self, history, memory):
                if not inspected.is_set(): raise RuntimeError('Operator started too early')
                return 'Wynik'
        with tempfile.TemporaryDirectory() as root:
            team = Team(api, {'comfy': 'local'}, Path(root), lambda *a: None, lambda: None)
            with patch.object(team, 'ask', side_effect=ask), patch('team.Agent', Operator):
                team.run([{'role': 'user', 'content': 'Film'}], '')
            self.assertTrue(inspected.is_set())

    def test_render_records_actual_outputs(self):
        def api(base, route, payload=None):
            return {'/queue': {}, '/prompt': {'prompt_id': 'remote-id'},
                    '/history/remote-id': {'remote-id': {'status': {'completed': True},
                        'outputs': {'1': {'videos': [{'filename': 'film.mp4', 'type': 'output'}]}}}},
                    '/free': {}}[route]
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            (path/'agent_workflow.json').write_text('{}')
            agent = Agent(api, {'comfy': 'local'}, path, lambda *a: None, lambda: None)
            result = agent.execute('run_workflow', {})
            saved = json.loads(next((path/'renders').glob('*.json')).read_text())
            self.assertEqual(saved, result)
            self.assertEqual(saved['outputs']['1']['videos'][0]['filename'], 'film.mp4')
