"""AnimalCross 0.6 — local Windows control panel, Python standard library only."""
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from team import Team, ROLES
from ghost import Ghost
from services import stop_service
from village import Village
from production import recover
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
DEFAULTS = {'ollama': 'http://127.0.0.1:11434', 'comfy': 'http://127.0.0.1:8188',
            'model': 'qwen3.5:35b', 'ollama_exe': r'C:\Users\Pablo\AppData\Local\Programs\Ollama',
            'comfy_launcher': r'C:\Users\Pablo\AppData\Local\Programs\Comfy Desktop', 'context': '8192'}


def resolve_launcher(value, names):
    path = Path(value)
    if path.is_file():
        return str(path)
    if path.is_dir():
        candidates = {p.name.lower(): p for p in path.iterdir() if p.is_file()}
        for name in names:
            if name.lower() in candidates:
                return str(candidates[name.lower()])
        raise ValueError(f'Nie znaleziono pliku uruchamiającego w {path}. Wybierz właściwy EXE lub skrót.')
    raise ValueError(f'Nie znaleziono lokalizacji: {path}')


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def api(base, route, payload=None, timeout=15):
    req = urllib.request.Request(base.rstrip('/') + route,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'HTTP {exc.code}: {exc.read().decode(errors="replace")[:1500]}') from exc


def workflow_from(value):
    graph = value.get('prompt', value)
    if not isinstance(graph, dict) or not graph or any(
            not isinstance(node, dict) or 'class_type' not in node or 'inputs' not in node
            for node in graph.values()):
        raise ValueError('Potrzebny workflow API JSON (node: class_type + inputs). Eksport widoku edytora nie wystarczy.')
    return graph


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('AnimalCross • wioska filmowa AI • 0.7')
        self.geometry('1100x760')
        self.minsize(850, 600)
        DATA.mkdir(exist_ok=True)
        recover(DATA)
        self.cfg = dict(DEFAULTS)
        if (DATA / 'settings.json').exists():
            self.cfg.update(json.loads((DATA / 'settings.json').read_text(encoding='utf-8')))
        for key in ('ollama_exe', 'comfy_launcher'):
            if not self.cfg.get(key): self.cfg[key] = DEFAULTS[key]
        atomic_json(DATA / 'settings.json', self.cfg)
        self.events = queue.Queue()
        self.cancel_task = threading.Event()
        self.stopping_services = False
        self.busy = False
        self.continuous_enabled = False
        self.continuous_count = 0
        self.messages = []
        self.processes = {}
        self.workflow = None
        self.status = tk.StringVar(value='Gotowe. Ustaw ścieżki i sprawdź połączenia.')
        style = ttk.Style(self)
        style.theme_use('clam')
        self.configure(bg='#edf2f7')
        style.configure('.', font=('Segoe UI', 11), background='#edf2f7', foreground='#203047')
        style.configure('TNotebook', background='#edf2f7', borderwidth=0)
        style.configure('TFrame', background='#edf2f7')
        style.map('TNotebook.Tab', background=[('selected', '#d8e8ff')])
        style.configure('Accent.TButton', background='#245ec7', foreground='white', padding=(20, 10))
        style.map('Accent.TButton', background=[('active', '#17489e'), ('disabled', '#b5bfd0')])
        style.configure('TButton', padding=8)
        style.configure('TNotebook.Tab', padding=(16, 9))
        ttk.Label(self, text='AnimalCross', font=('Segoe UI', 24, 'bold')).pack(anchor='w', padx=20, pady=(16, 0))
        ttk.Label(self, text='Twoja wioska • wspólne zlecenia • lokalne modele AI').pack(anchor='w', padx=22, pady=(0, 12))
        ttk.Label(self, textvariable=self.status, relief='sunken', padding=8, wraplength=800).pack(side='bottom', fill='x', pady=(8, 0))
        tabs = ttk.Notebook(self)
        tabs.pack(fill='both', expand=True, padx=16)
        chat, services = [ttk.Frame(tabs, padding=12) for _ in range(2)]
        self.village = Village(tabs, BASE, self.quick_prompt, self.interrupt_video, self.start, lambda: self.cfg, self.set_continuous)
        tabs.add(self.village, text='Wioska AI')
        tabs.add(chat, text='Rozmowa')
        tabs.add(services, text='Panel sterowania')
        self.service_states = {key: tk.StringVar(value='Sprawdzam…') for key in ('ollama', 'comfy', 'model')}
        for key, title in [('ollama', 'Ollama • silnik AI'), ('comfy', 'ComfyUI • generator filmów'), ('model', 'Qwen • model rozmowy')]:
            card = ttk.Frame(services, padding=8); card.pack(fill='x', pady=3)
            ttk.Label(card, text=title, width=30, font=('Segoe UI', 12, 'bold')).pack(side='left')
            ttk.Label(card, textvariable=self.service_states[key]).pack(side='left', padx=10)
            if key != 'model':
                ttk.Button(card, text='Zatrzymaj', command=lambda k=key: self.stop_selected(k)).pack(side='right',padx=4)
                ttk.Button(card, text='Uruchom', command=lambda k=key: self.start(k)).pack(side='right')
            else:
                ttk.Button(card,text='Zwolnij model',command=self.unload).pack(side='right')
        actions = ttk.Frame(services); actions.pack(fill='x', pady=8)
        ttk.Button(actions, text='Uruchom wszystko', style='Accent.TButton', command=self.start).pack(side='left')
        ttk.Button(actions, text='Odśwież statusy', command=self.poll_services).pack(side='left', padx=8)
        ttk.Button(actions,text='Zatrzymaj usługi',command=lambda: self.stop_selected('all')).pack(side='left',padx=8)
        ttk.Button(actions,text='Przerwij film',command=self.interrupt_video).pack(side='left')
        self.components = tk.StringVar(value='Wan / enkoder / VAE: sprawdzam dostępność…')
        ttk.Label(services,textvariable=self.components,wraplength=950).pack(anchor='w',pady=4)
        details = ttk.Notebook(services); details.pack(fill='both', expand=True)
        logs, memory, settings, video = [ttk.Frame(details, padding=8) for _ in range(4)]
        for frame, title in [(logs, 'Działania AI'), (memory, 'Pamięć AI'), (settings, 'Ustawienia'), (video, 'Zaawansowane')]:
            details.add(frame, text=title)
        stage = ttk.Frame(chat); stage.pack(side='top',fill='x')
        self.ghost = Ghost(stage, BASE / 'assets' / 'ghost' / 'PNGs' if (BASE / 'assets' / 'ghost' / 'PNGs').is_dir() else DATA / 'ghost'); self.ghost.pack(side='right')
        self.team_states = {}
        self.stage_label = tk.StringVar(value='Gotowy do pracy • napisz polecenie')
        ttk.Label(stage,textvariable=self.stage_label,font=('Segoe UI',12,'bold'),wraplength=600).pack(anchor='w',pady=6)
        for role in ROLES:
            var=tk.StringVar(value=role+' • czeka'); self.team_states[role]=var
            ttk.Label(stage,textvariable=var,wraplength=600).pack(anchor='w')
        ttk.Button(settings,text='Importuj duszka z ZIP',command=self.import_ghost).pack(anchor='w',pady=5)
        ttk.Label(settings,text='Duch: SarahJK • grafiki importowane lokalnie z własnej paczki.').pack(anchor='w')
        composer = ttk.Frame(chat)
        composer.pack(side='bottom', fill='x', pady=(8, 0))
        ttk.Label(composer, text='Wiadomość • Enter wysyła, Shift+Enter dodaje nową linię').pack(anchor='w')
        self.entry = tk.Text(composer, height=3, wrap='word', font=('Segoe UI', 11),
                             bg='white', fg='#111111', insertbackground='#111111', relief='solid', bd=1)
        self.entry.pack(fill='x', pady=6)
        self.entry.bind('<Return>', self.enter_send)
        self.entry.bind('<Shift-Return>', lambda event: None)
        row = ttk.Frame(composer); row.pack(fill='x')
        self.send_button = ttk.Button(row, text='Wyślij do AI  →', style='Accent.TButton', command=self.send)
        self.send_button.pack(side='left')
        ttk.Button(row, text='Nowa rozmowa', command=self.new_chat).pack(side='left', padx=8)
        shortcuts = ttk.Frame(chat); shortcuts.pack(side='top', fill='x', pady=6)
        ttk.Button(shortcuts, text='Sprawdź moje środowisko', command=lambda: self.quick_prompt('Sprawdź ComfyUI i dostępność modeli Wan. Zapisz potwierdzone informacje do pamięci. Nie generuj filmu.')).pack(side='left')
        ttk.Button(shortcuts, text='Zaproponuj film', command=lambda: self.quick_prompt('Zaproponuj pomysł na krótki film AnimalCross. Na razie tylko plan, bez generowania.')).pack(side='left', padx=8)
        self.chat = self.textbox(chat)
        self.write('chat', 'Witaj w AnimalCross! Opisz, co chcesz zrobić. AI może sprawdzić modele, zapamiętać ustalenia i przygotować generowanie. Działania narzędzi zobaczysz w Panel sterowania → Działania AI.')
        service_buttons = ttk.Frame(logs)
        service_buttons.pack(side='bottom', fill='x')
        for title, cmd in [('Zwolnij pamięć Qwena', self.unload), ('Zatrzymaj własne procesy', self.stop_owned)]:
            ttk.Button(service_buttons, text=title, command=cmd).pack(side='left', padx=3, pady=8)
        self.service_log = self.textbox(logs)
        ttk.Label(video, text='Wczytaj sprawdzony workflow eksportowany z ComfyUI w formacie API JSON.').pack(anchor='w')
        self.workflow_label = tk.StringVar(value='Brak workflow')
        ttk.Label(video, textvariable=self.workflow_label).pack(anchor='w', pady=8)
        row = ttk.Frame(video); row.pack(fill='x')
        ttk.Button(row, text='Wczytaj API JSON', command=self.load_workflow).pack(side='left')
        ttk.Button(row, text='Zwolnij Qwena i generuj', command=self.generate).pack(side='left', padx=8)
        self.video_log = self.textbox(video)
        ttk.Label(video, text='Ta wersja wysyła niezmieniony workflow. Montaż i galeria będą kolejnym etapem.').pack(anchor='w')
        ttk.Label(memory, text='AI samo dopisuje ustalenia. Tutaj możesz je podejrzeć.').pack(anchor='w')
        ttk.Button(memory, text='Otwórz pamięć w Notatniku', command=self.open_memory).pack(side='bottom', anchor='w', pady=8)
        self.memory = self.textbox(memory)
        memfile = DATA / 'project.md'
        if not memfile.exists():
            memfile.write_text('AnimalCross — lokalny projekt filmowy.\nModel: qwen3.5:35b.\nWan: wan2.2_ti2v_5B_fp16.safetensors.\nZasady treści kanału: do ustalenia.\n', encoding='utf-8')
        self.refresh_memory()
        self.fields = {}
        labels = {'ollama': 'Adres Ollama', 'comfy': 'Adres ComfyUI', 'model': 'Model',
                  'ollama_exe': 'Folder Ollama lub plik ollama.exe', 'comfy_launcher': 'Folder Comfy Desktop lub jego plik EXE / skrót',
                  'context': 'Kontekst AI: 4096–32768 (więcej = większa pamięć)'}
        for key, label in labels.items():
            ttk.Label(settings, text=label).pack(anchor='w', pady=(6, 1))
            row = ttk.Frame(settings); row.pack(fill='x')
            var = tk.StringVar(value=str(self.cfg[key])); self.fields[key] = var
            ttk.Entry(row, textvariable=var).pack(side='left', fill='x', expand=True)
            if key in ('ollama_exe', 'comfy_launcher'):
                ttk.Button(row, text='Wybierz', command=lambda v=var: self.pick(v)).pack(side='left')
        ttk.Button(settings, text='Zapisz ustawienia', command=self.save_settings).pack(anchor='w', pady=12)
        ttk.Label(settings, text='Limit GPU 80%: jeszcze niewdrożony. Ten panel nie zmienia sterownika AMD.\nCzat i generowanie działają kolejno. Zamknij Cline, by nie ładował Qwena podczas pracy Wan.').pack(anchor='w')
        self.after(100, self.pump)
        self.after(1000, self.continuous_tick)
        self.checking_services = False
        self.after(500, self.poll_services)
        self.after(15000, self.periodic_services)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def set_continuous(self, enabled):
        self.continuous_enabled = enabled
        self.village.log('System', 'Stała praca AI włączona: kolejne pomysły i scenariusze.' if enabled else 'Wyłączono nowe zlecenia. Bieżące zadanie może dokończyć pracę.')
        self.village.mode.set('STAŁA PRACA AI · pomysły i scenariusze' if enabled else 'TRYB RZECZYWISTY · zlecenia ręczne')

    def continuous_tick(self):
        if self.continuous_enabled and not self.busy and not self.stopping_services:
            self.continuous_count += 1
            number = self.continuous_count
            request = ('Zadanie ciągłe nr '+str(number)+': przygotuj jeden nowy pomysł i konkretny scenariusz zabawnego filmu AnimalCross z kotem lub psem. '
                       'Klip 4–6 sekund, pion 9:16, jedna czytelna akcja, bez lektora. Unikaj powtarzania pomysłów zapisanych w pamięci. '
                       'Sprawdź środowisko. Zapisz krótki opis zaproponowanego pomysłu do pamięci jako propozycję, nie wykonany film. '
                       'Nie uruchamiaj generowania i nie publikuj.')
            memory = (DATA / 'project.md').read_text(encoding='utf-8')
            def work():
                q = self.task_api(self.cfg['comfy'], '/queue', timeout=5)
                if q.get('queue_running') or q.get('queue_pending'):
                    raise RuntimeError('ComfyUI zajęte. Stała praca wstrzymana, aby nie ładować Qwena obok Wan.')
                team = Team(self.task_api, dict(self.cfg), DATA, lambda k, v: self.events.put((k, v)), self.unload_impl)
                result = team.run([{'role': 'user', 'content': request}], memory)
                self.events.put(('chat', 'Stała praca AI #'+str(number)+': '+result))
            self.village.log('Kolejka', 'Rozpoczynam zadanie ciągłe #'+str(number))
            self.run_job('Stała praca AI • zadanie '+str(number), work)
        self.after(10000, self.continuous_tick)

    def task_api(self, *args, **kwargs):
        if self.cancel_task.is_set(): raise RuntimeError('Zadanie zatrzymane przez użytkownika.')
        result=api(*args, **kwargs)
        if self.cancel_task.is_set(): raise RuntimeError('Zadanie zatrzymane przez użytkownika.')
        return result

    def stop_selected(self, kind):
        self.village.auto.set(False)
        self.set_continuous(False)
        if self.stopping_services: return
        self.stopping_services = True
        self.cancel_task.set()
        self.status.set('Zatrzymuję usługi i dalszą pracę agentów…')
        cfg=dict(self.cfg)
        def work():
            results=[]
            for key in (('comfy','ollama') if kind=='all' else (kind,)):
                try:
                    if key=='comfy':
                        try: api(cfg[key],'/interrupt',{},timeout=3)
                        except Exception: pass
                    result=stop_service(cfg[key],key)
                    results.append(key+': zakończono PID '+str(result['stopped']))
                except Exception as exc: results.append(key+': '+str(exc))
            self.events.put(('service_log','\n'.join(results)))
            self.events.put(('stop_done','Zakończono próbę zatrzymania. Sprawdź statusy i dziennik.'))
        threading.Thread(target=work,daemon=True).start()

    def interrupt_video(self):
        self.village.auto.set(False)
        self.set_continuous(False)
        self.village.stop_demo()
        self.cancel_task.set()
        def work():
            try:
                api(self.cfg['comfy'],'/interrupt',{},timeout=5)
                self.events.put(('service_log','Wysłano przerwanie aktualnego filmu. Oczekujące zadania w kolejce pozostają.'))
            except Exception as exc: self.events.put(('service_log','Nie udało się przerwać: '+str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def import_ghost(self):
        path=filedialog.askopenfilename(title='Wybierz Ghost PNGTuber Model.zip',filetypes=[('ZIP','*.zip')])
        if not path: return
        try:
            self.ghost.import_zip(path)
            self.status.set('Duszek zaimportowany. Autor: SarahJK.')
        except Exception as exc: messagebox.showerror('Import duszka',str(exc))

    def refresh_memory(self):
        notes = DATA / 'pamiec_ai.txt'
        if not notes.exists():
            content = 'PAMIĘĆ ANIMALCROSS — ustalenia dopisywane przez AI\n'
            old = DATA / 'project.md'
            if old.exists(): content += '\n'+old.read_text(encoding='utf-8')
            old = DATA / 'agent_memory.jsonl'
            if old.exists():
                for line in old.read_text(encoding='utf-8').splitlines():
                    try: content += '\n'+json.loads(line).get('note', '')+'\n'
                    except (ValueError, AttributeError): pass
            notes.write_text(content, encoding='utf-8')
        self.memory.configure(state='normal')
        self.memory.delete('1.0', 'end')
        self.memory.insert('end', notes.read_text(encoding='utf-8'))
        self.memory.configure(state='disabled')

    def open_memory(self):
        if os.name == 'nt': subprocess.Popen(['notepad.exe', str(DATA / 'pamiec_ai.txt')])
        else: messagebox.showinfo('Pamięć', str(DATA / 'pamiec_ai.txt'))

    def periodic_services(self):
        self.poll_services()
        self.after(15000, self.periodic_services)

    def poll_services(self):
        if self.checking_services: return
        self.checking_services = True
        cfg = dict(self.cfg)
        def work():
            result = {}
            for key, route in [('ollama', '/api/tags'), ('comfy', '/system_stats')]:
                try:
                    api(cfg[key], route, timeout=3)
                    result[key] = '● Działa'
                except Exception: result[key] = '○ Niedostępny'
            try:
                names = [m.get('name', m.get('model')) for m in api(cfg['ollama'], '/api/ps', timeout=3).get('models', [])]
                result['model'] = '● Załadowany' if cfg['model'] in names else '○ Wczyta się przy rozmowie'
            except Exception: result['model'] = '○ Brak połączenia z Ollama'
            parts=[]
            for category, filename, title in [('diffusion_models','wan2.2_ti2v_5B_fp16.safetensors','Wan'),('text_encoders','umt5_xxl_fp8_e4m3fn_scaled.safetensors','Enkoder tekstu'),('vae','wan2.2_vae.safetensors','VAE')]:
                try:
                    models=api(cfg['comfy'],'/models/'+category,timeout=3)
                    parts.append(title+(': dostępny' if filename in models else ': nie znaleziono'))
                except Exception: parts.append(title+': stan nieznany')
            parts.append('Ghost: '+('pliki w repozytorium' if (BASE/'assets'/'ghost'/'PNGs').is_dir() else 'import lokalny / symbol zastępczy'))
            parts.append('Python: uruchomiony')
            result['components']=' • '.join(parts)+'\nWan, enkoder i VAE są modelami ComfyUI, nie osobnymi programami.'
            self.events.put(('service_states', result))
        threading.Thread(target=work, daemon=True).start()

    def textbox(self, parent):
        frame = ttk.Frame(parent); frame.pack(fill='both', expand=True, pady=6)
        box = tk.Text(frame, background='white', foreground='#203047', relief='flat', height=8, width=40, wrap='word', font=('Segoe UI', 11), padx=10, pady=10)
        bar = ttk.Scrollbar(frame, command=box.yview); box.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y'); box.pack(fill='both', expand=True)
        return box

    def pick(self, var):
        path = filedialog.askopenfilename()
        if path: var.set(path)

    def write(self, target, text):
        box = getattr(self, target); box.insert('end', text + '\n'); box.see('end')

    def pump(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'done':
                    self.busy = False; self.status.set(value)
                    self.village.busy(False)
                    self.village.log('System', value)
                    if value.startswith('Błąd') and self.continuous_enabled:
                        self.village.auto.set(False)
                        self.set_continuous(False)
                    self.village.summary.set(value + ' Wynik znajdziesz w historii lub rozmowie.')
                    self.village.ghost.state = 'error' if value.startswith('Błąd') else 'done'
                    self.send_button.state(['!disabled'])
                    self.refresh_memory()
                    self.poll_services()
                    self.ghost.state = 'error' if value.startswith('Błąd') else 'done'
                elif kind == 'handoff':
                    self.village.handoff(value)
                elif kind == 'team':
                    self.village.update_role(value)
                    role, state, detail = value['role'], value['state'], value['detail']
                    names={'waiting':'czeka','working':'pracuje','done':'gotowe','error':'błąd'}
                    self.team_states[role].set(role+' • '+names.get(state,state)+' • '+detail[:80])
                    self.stage_label.set(role+' — '+detail[:100])
                    self.ghost.state = 'generating' if 'Generowanie ' in detail else state
                elif kind == 'stop_done':
                    self.stopping_services = False
                    self.status.set(value)
                    self.poll_services()
                elif kind == 'service_states':
                    for key, state in value.items():
                        if key == 'components': self.components.set(state)
                        else: self.service_states[key].set(state)
                    self.checking_services = False
                else: self.write(kind, value)
        except queue.Empty: pass
        self.after(100, self.pump)

    def run_job(self, description, fn):
        if self.busy:
            messagebox.showinfo('Trwa zadanie', 'Poczekaj na zakończenie bieżącej operacji.'); return
        if self.stopping_services: return
        self.cancel_task.clear()
        self.busy = True; self.status.set(description)
        self.village.busy(True)
        self.village.summary.set(description)
        self.send_button.state(['disabled'])
        def worker():
            try:
                fn(); self.events.put(('done', 'Zadanie zakończone.'))
            except Exception as exc:
                self.events.put(('service_log', f'BŁĄD: {exc}'))
                self.events.put(('chat', f'BŁĄD: {exc}'))
                self.events.put(('done', f'Błąd: {str(exc)[:180]}'))
        threading.Thread(target=worker, daemon=True).start()

    def save_settings(self):
        try:
            cfg = {k: v.get().strip() for k, v in self.fields.items()}
            if not 4096 <= int(cfg['context']) <= 32768: raise ValueError('Kontekst musi być od 4096 do 32768.')
            for key in ('ollama', 'comfy'):
                if not cfg[key].startswith(('http://127.0.0.1:', 'http://localhost:')):
                    raise ValueError('Ta wersja obsługuje lokalne adresy http://127.0.0.1:PORT.')
            if self.busy: raise ValueError('Zapisz ustawienia po zakończeniu zadania.')
            atomic_json(DATA / 'settings.json', cfg); self.cfg = cfg; self.status.set('Ustawienia zapisane.')
        except Exception as exc: messagebox.showerror('Ustawienia', str(exc))

    def start(self, only=None):
        def work():
            for key, route in [('ollama', '/api/tags'), ('comfy', '/system_stats')]:
                if only and key != only: continue
                try: api(self.cfg[key], route, timeout=2); self.events.put(('service_log', f'{key}: już działa')); continue
                except Exception: pass
                if key == 'ollama':
                    exe = self.cfg['ollama_exe'] or shutil.which('ollama')
                    if not exe:
                        candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Ollama/ollama.exe'
                        if candidate.is_file(): exe = str(candidate)
                    if not exe: raise ValueError('Wskaż folder Ollama w ustawieniach.')
                    exe = resolve_launcher(exe, ['ollama.exe'])
                    command = [exe, 'serve']
                else:
                    launcher = self.cfg['comfy_launcher']
                    launcher = resolve_launcher(launcher, ['ComfyUI.exe', 'Comfy Desktop.exe', 'ComfyUI Desktop.exe', 'Comfy.exe'])
                    if Path(launcher).suffix.lower() == '.lnk':
                        os.startfile(launcher)
                        command = None
                        self.events.put(('service_log', 'Uruchomiono skrót. Proces nie jest zarządzany przez panel.'))
                    else:
                        command = [launcher]
                        if Path(launcher).suffix.lower() in ('.bat', '.cmd'):
                            command = [os.environ.get('COMSPEC', 'cmd.exe'), '/c', launcher]
                if command:
                    log = (DATA / f'{key}.log').open('ab')
                    try:
                        self.processes[key] = subprocess.Popen(command, cwd=str(Path(command[-1]).parent) if key == 'comfy' else None,
                            stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
                    finally: log.close()
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    try: api(self.cfg[key], route, timeout=2); break
                    except Exception: time.sleep(1)
                else: raise TimeoutError(f'{key}: brak gotowości po 120 s. Sprawdź log lub okno programu.')
                self.events.put(('service_log', f'{key}: gotowe'))
        self.run_job('Uruchamiam środowisko…', work)

    def unload_impl(self):
        loaded = api(self.cfg['ollama'], '/api/ps').get('models', [])
        name = self.cfg['model']
        api(self.cfg['ollama'], '/api/generate', {'model': name, 'keep_alive': 0}, timeout=120)
        remaining = api(self.cfg['ollama'], '/api/ps').get('models', [])
        if remaining: raise RuntimeError('Ollama nadal ma załadowane modele. Zamknij inne klienty i zwolnij je przed generowaniem.')
        self.events.put(('service_log', f'Zwolniono pamięć Ollama. Wcześniej załadowane: {len(loaded)}'))

    def unload(self): self.run_job('Zwalniam model…', self.unload_impl)

    def stop_owned(self):
        if self.busy: messagebox.showinfo('Trwa zadanie', 'Najpierw poczekaj na zakończenie operacji.'); return
        for key, process in list(self.processes.items()):
            if process.poll() is None:
                if os.name == 'nt': subprocess.run(['taskkill', '/PID', str(process.pid), '/T'], capture_output=True)
                else: process.terminate()
            self.write('service_log', f'{key}: wysłano żądanie zatrzymania własnego procesu.')
        self.processes.clear()

    def quick_prompt(self, text):
        if self.busy: return
        self.entry.delete('1.0', 'end'); self.entry.insert('1.0', text); self.send()

    def enter_send(self, event):
        self.send()
        return 'break'

    def send(self):
        if self.busy: return
        text = self.entry.get('1.0', 'end').strip()
        if not text: return
        self.entry.delete('1.0', 'end'); self.write('chat', 'Ty: ' + text)
        if len(self.messages) >= 12:
            messagebox.showinfo('Kontekst rozmowy', 'Zapisz ważne ustalenia w zakładce Pamięć i rozpocznij nową rozmowę. Archiwum pozostanie na dysku.')
            self.entry.insert('1.0', text)
            return
        history = self.messages + [{'role': 'user', 'content': text}]
        memory = (DATA / 'project.md').read_text(encoding='utf-8')
        def work():
            try:
                q = api(self.cfg['comfy'], '/queue', timeout=3)
            except (urllib.error.URLError, TimeoutError, OSError):
                q = {}
            if q.get('queue_running') or q.get('queue_pending'):
                raise RuntimeError('ComfyUI ma aktywną kolejkę. Czat poczeka, aby nie ładować Qwena obok Wan.')
            agent = Team(self.task_api, self.cfg, DATA, lambda kind, value: self.events.put((kind, value)), self.unload_impl)
            content = agent.run(history, memory)
            self.messages = history + [{'role': 'assistant', 'content': content}]
            with (DATA / 'chats.jsonl').open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({'time': time.time(), 'user': text, 'assistant': content}, ensure_ascii=False) + '\n')
            self.events.put(('chat', 'AI: ' + content))
        # ComfyUI may be off while chatting; queue check is attempted only if reachable.
        self.run_job('AI odpowiada lokalnie… (pierwsze ładowanie może potrwać)', work)

    def new_chat(self):
        if self.busy: return
        self.messages = []; self.chat.delete('1.0', 'end')
        self.status.set('Nowa rozmowa. Pamięć projektu zostaje; archiwum jest w data/chats.jsonl.')

    def load_workflow(self):
        if self.busy: return
        path = filedialog.askopenfilename(filetypes=[('Workflow API JSON', '*.json')])
        if not path: return
        try:
            self.workflow = workflow_from(json.loads(Path(path).read_text(encoding='utf-8-sig')))
            self.workflow_label.set(path)
        except Exception as exc: messagebox.showerror('Workflow', str(exc))

    def generate(self):
        if self.workflow is None: messagebox.showinfo('Workflow', 'Najpierw wczytaj workflow API JSON.'); return
        graph = json.loads(json.dumps(self.workflow))
        def work():
            q = api(self.cfg['comfy'], '/queue')
            if q.get('queue_running') or q.get('queue_pending'): raise RuntimeError('Kolejka ComfyUI jest zajęta.')
            self.unload_impl()
            result = api(self.cfg['comfy'], '/prompt', {'prompt': graph}, timeout=120)
            if result.get('error') or result.get('node_errors'): raise RuntimeError(json.dumps(result, ensure_ascii=False))
            ident = result['prompt_id']
            self.events.put(('video_log', f'W kolejce: {ident}. Czekam na rzeczywisty wynik…'))
            while True:
                item = api(self.cfg['comfy'], '/history/' + ident).get(ident)
                if item:
                    status = item.get('status', {})
                    if status.get('status_str') == 'error': raise RuntimeError(json.dumps(status, ensure_ascii=False))
                    if status.get('completed'):
                        self.events.put(('video_log', 'Wykonanie zakończone. Wyjścia zgłoszone przez ComfyUI:\n' + json.dumps(item.get('outputs', {}), ensure_ascii=False, indent=2)))
                        return
                if self.cancel_task.wait(2): raise RuntimeError('Zadanie przerwane.')
        self.run_job('Wan generuje. Czat jest zablokowany do końca zadania.', work)

    def close(self):
        if self.busy and not messagebox.askyesno('Trwa zadanie', 'Zamknąć panel? Usługi i generowanie mogą działać dalej.'): return
        self.destroy()


if __name__ == '__main__':
    App().mainloop()

