import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from queue import Queue
from unittest.mock import patch
import animalcross as ac

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"models": []}')
    def do_POST(self):
        value = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(value).encode())

class Core(unittest.TestCase):
    def test_http_get_post(self):
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}'
            self.assertEqual(ac.api(url, '/api/ps'), {'models': []})
            self.assertEqual(ac.api(url, '/echo', {'model': 'ą'}), {'model': 'ą'})
        finally: server.shutdown(); server.server_close(); thread.join()

    def test_workflow_format(self):
        graph = {'1': {'class_type': 'KSampler', 'inputs': {}}}
        self.assertEqual(ac.workflow_from(graph), graph)
        self.assertEqual(ac.workflow_from({'prompt': graph}), graph)
        for bad in ({'nodes': []}, {}, {'1': {'inputs': {}}}):
            with self.assertRaises(ValueError): ac.workflow_from(bad)

    def test_atomic_settings(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'settings.json'
            ac.atomic_json(path, {'model': 'pierwszy'})
            ac.atomic_json(path, {'model': 'drugi'})
            self.assertEqual(json.loads(path.read_text()), {'model': 'drugi'})

    def test_unload_refuses_remaining_model(self):
        fake = type('Fake', (), {'cfg': {'ollama': 'http://localhost:11434', 'model': 'qwen'}, 'events': Queue()})()
        with patch.object(ac, 'api', side_effect=[{'models': [{'name': 'qwen'}]}, {}, {'models': [{'name': 'other'}]}]):
            with self.assertRaises(RuntimeError): ac.App.unload_impl(fake)

    def test_busy_blocks_generation_before_submission(self):
        jobs = []
        graph = {'1': {'class_type': 'KSampler', 'inputs': {}}}
        fake = type('Fake', (), {'workflow': graph, 'cfg': {'comfy': 'http://localhost:8188'},
                               'run_job': lambda self, desc, fn: jobs.append(fn)})()
        ac.App.generate(fake)
        with patch.object(ac, 'api', return_value={'queue_running': [['task']]} ) as api:
            with self.assertRaises(RuntimeError): jobs[0]()
            self.assertEqual(api.call_count, 1)

if __name__ == '__main__': unittest.main()

class Launchers(unittest.TestCase):
    def test_folder_resolves_expected_executable_not_uninstaller(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / 'Uninstall.exe').touch()
            with self.assertRaises(ValueError): ac.resolve_launcher(root, ['ComfyUI.exe'])
            executable = directory / 'ComfyUI.exe'; executable.touch()
            self.assertEqual(ac.resolve_launcher(root, ['ComfyUI.exe']), str(executable))
            self.assertEqual(ac.resolve_launcher(str(executable), ['ComfyUI.exe']), str(executable))

