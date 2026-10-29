import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from animalcross import App

class ContinuousTests(unittest.TestCase):
    def app(self):
        return SimpleNamespace(continuous_enabled=True, busy=False, stopping_services=False,
            continuous_count=0, cfg={'comfy':'local'}, task_api=Mock(return_value={}),
            events=Mock(), unload_impl=Mock(), village=Mock(), run_job=Mock(), after=Mock(), continuous_tick=Mock())

    def test_no_overlap_and_disabled_means_no_new_tasks(self):
        app=self.app(); app.busy=True
        App.continuous_tick(app)
        app.run_job.assert_not_called()
        app.busy=False; app.continuous_enabled=False
        App.continuous_tick(app)
        app.run_job.assert_not_called()

    def test_new_job_runs_real_team_and_does_not_request_render(self):
        app=self.app()
        with tempfile.TemporaryDirectory() as root, patch('animalcross.DATA',Path(root)), patch('animalcross.Team') as team:
            (Path(root)/'project.md').write_text('Zasady')
            team.return_value.run.return_value='Nowy scenariusz'
            App.continuous_tick(app)
            app.run_job.call_args.args[1]()
            history,memory=team.return_value.run.call_args.args
            self.assertEqual(len(history),1)
            self.assertIn('Nie uruchamiaj generowania',history[0]['content'])
            self.assertEqual(memory,'Zasady')
            self.assertEqual(app.continuous_count,1)

    def test_busy_comfy_blocks_model_call(self):
        app=self.app(); app.task_api.return_value={'queue_running':[1]}
        with tempfile.TemporaryDirectory() as root, patch('animalcross.DATA',Path(root)), patch('animalcross.Team') as team:
            (Path(root)/'project.md').write_text('Zasady')
            App.continuous_tick(app)
            with self.assertRaises(RuntimeError): app.run_job.call_args.args[1]()
            team.assert_not_called()
