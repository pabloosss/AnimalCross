import unittest
from unittest.mock import patch
from types import SimpleNamespace
from services import stop_service

class ServiceTests(unittest.TestCase):
    def test_remote_endpoint_never_stopped(self):
        with patch('services.os.name','nt'),patch('services.subprocess.run') as run:
            with self.assertRaises(ValueError): stop_service('http://example.com:8188','comfy')
            run.assert_not_called()

    def test_stop_verifies_process_and_uses_listener_port(self):
        with patch('services.os.name','nt'),patch('services.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"stopped":[123]}',stderr='')) as run:
            self.assertEqual(stop_service('http://127.0.0.1:8188','comfy'),{'stopped':[123]})
            script=run.call_args.args[0][-1]
            self.assertIn('-LocalPort 8188',script)
            self.assertIn('ComfyUI',script)
            self.assertIn('Stop-Process -Id $processId',script)
            self.assertNotIn('Stop-Process -Name',script)

    def test_permission_failure_not_reported_as_success(self):
        with patch('services.os.name','nt'),patch('services.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='Access denied')):
            with self.assertRaisesRegex(RuntimeError,'Access denied'): stop_service('http://localhost:11434','ollama')
