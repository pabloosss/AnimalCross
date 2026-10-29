"""Durable production records, independent of the UI and model responses."""
import json
import threading
import time
from pathlib import Path


class Production:
    def __init__(self, directory, ident, request):
        self.path = Path(directory) / 'productions' / (ident + '.json')
        self.lock = threading.Lock()
        self.data = {'id': ident, 'request': request, 'created': time.time(),
                     'state': 'running', 'roles': {}, 'messages': [], 'result': ''}
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)

    def update(self, role, state, detail):
        with self.lock:
            self.data['roles'][role] = {'state': state, 'detail': detail}
            self.save()

    def message(self, envelope):
        with self.lock:
            self.data['messages'].append(envelope)
            self.save()

    def finish(self, state, result):
        with self.lock:
            self.data.update(state=state, result=result, finished=time.time())
            self.save()


def recover(directory):
    """Do not replay a render after a crash: it may still run in ComfyUI."""
    for path in (Path(directory) / 'productions').glob('*.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('state') != 'running':
                continue
            data['state'] = 'interrupted'
            data['result'] = 'Aplikację zamknięto podczas pracy. Sprawdź kolejkę i historię ComfyUI przed ponownym zleceniem.'
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(path)
        except (OSError, ValueError):
            continue
