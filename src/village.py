"""Live village: artwork from the repository, states from actual worker events."""
import json
import math
import time
from motion import Motion, DEMO
import tkinter as tk
from tkinter import ttk
import webbrowser
from urllib.parse import urlencode
from ghost import Ghost
from team import ROLES

COLORS = {'waiting': '#dbe5cf', 'working': '#ffd878', 'done': '#b3e5ca', 'error': '#ffc0ad'}
LABELS = {'waiting': 'Czeka', 'working': 'Pracuje', 'done': 'Gotowe', 'error': 'Błąd'}
BUILDINGS = ['Castle Round', 'House', 'Windmill', 'Watchtower Short', 'Magic Stone Tower', 'Tent']
TITLES = ['Ratusz · plan', 'Pracownia scenariusza', 'Studio · ComfyUI', 'Kontrola wyniku', 'Biblioteka pamięci', 'Warsztat technika']


class Village(ttk.Frame):
    def __init__(self, parent, base, submit, stop, start, cfg, continuous=None):
        super().__init__(parent, padding=10)
        self.base, self.submit, self.cfg = base, submit, cfg
        self.continuous_callback = continuous
        self.log_lines = []
        self.log_window = None
        self.patrol_count = {r: 0 for r in ROLES}
        self.states = {r: ('waiting', 'Czeka na zadanie') for r in ROLES}
        self.tick = 0
        self.motions = {r: Motion(i) for i, r in enumerate(ROLES)}
        self.is_busy = False
        self.demo_started = None
        self.demo_index = 0
        self.demo_paused = None
        self.last_frame = time.monotonic()
        self.deliveries = []
        self.frames, self.buildings = {}, {}
        self.selected = ROLES[0]
        header = ttk.Frame(self); header.pack(fill='x')
        ttk.Label(header, text='Twoja wioska filmowa', font=('Segoe UI', 20, 'bold')).pack(side='left')
        ttk.Button(header, text='Uruchom usługi', command=start).pack(side='right')
        ttk.Button(header, text='Przerwij pracę', command=stop).pack(side='right', padx=6)
        self.auto = tk.BooleanVar(value=False)
        ttk.Checkbutton(header, text='Stała praca AI: pomysły', variable=self.auto, command=self.toggle_continuous).pack(side='right', padx=8)
        self.summary = tk.StringVar(value='Opisz krótki film. Mieszkańcy podzielą się pracą.')
        ttk.Label(self, textvariable=self.summary).pack(anchor='w', pady=5)
        self.progress = ttk.Progressbar(self, maximum=len(ROLES))
        self.progress.pack(fill='x')
        tests = ttk.Frame(self); tests.pack(fill='x', pady=4)
        self.test_button = ttk.Button(tests, text='Test wioski · bez AI', command=self.start_demo)
        self.test_button.pack(side='left')
        ttk.Button(tests, text='Dziennik zadań', command=self.show_log).pack(side='right')
        self.pause_button = ttk.Button(tests, text='Pauza testu', command=self.pause_demo)
        self.pause_button.pack(side='left', padx=5)
        ttk.Button(tests, text='Zakończ test', command=self.stop_demo).pack(side='left')
        self.mode = tk.StringVar(value='TRYB RZECZYWISTY · oczekuje na zlecenie')
        ttk.Label(tests, textvariable=self.mode).pack(side='left', padx=8)

        bottom = ttk.Frame(self); bottom.pack(side='bottom', fill='x')
        self.prompt = tk.Text(bottom, height=2, wrap='word', font=('Segoe UI', 11))
        self.prompt.pack(fill='x', pady=4)
        row = ttk.Frame(bottom); row.pack(fill='x')
        self.plan_button = ttk.Button(row, text='Przygotuj pomysł', command=lambda: self.send(False))
        self.plan_button.pack(side='left')
        self.film_button = ttk.Button(row, text='Stwórz krótki film', style='Accent.TButton', command=lambda: self.send(True))
        self.film_button.pack(side='left', padx=6)
        ttk.Button(row, text='Wyniki i historia', command=self.history).pack(side='right')
        ttk.Label(bottom, text='Jeden krótki klip na zlecenie • kliknij mieszkańca, aby zobaczyć jego pracę.', font=('Segoe UI', 9)).pack(anchor='w', pady=3)
        self.message = tk.StringVar(value='Wiadomości mieszkańców pojawią się tutaj.')
        ttk.Label(bottom, textvariable=self.message, wraplength=920, font=('Segoe UI', 9)).pack(anchor='w', pady=3)
        self.detail = tk.StringVar(value='Ratusz czeka na pierwsze zlecenie.')
        ttk.Label(bottom, textvariable=self.detail, wraplength=920).pack(anchor='w')
        self.canvas = tk.Canvas(self, bg='#a8c98c', highlightthickness=0, height=380)
        self.canvas.pack(fill='both', expand=True, pady=6)
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, 'units'))
        self.ghost = Ghost(self.canvas, base/'assets'/'ghost'/'PNGs' if (base/'assets'/'ghost'/'PNGs').is_dir() else base/'data'/'ghost')
        self.ghost.configure(bg='#a8c98c', width=155)
        self.ghost.place(relx=1, x=-158, y=5)
        for name in BUILDINGS:
            self.buildings[name] = self.load(base/'assets'/'world'/'town'/'PNG'/f'Top-Down Simple Summer_Prop - {name}.png', 100)
        actors = ['Assassin', 'Robber', 'Thug']
        for i, role in enumerate(ROLES):
            folder = base/'assets'/'characters'/'bandits'/actors[i % 3]/'PNG'/'PNG Sequences'
            self.frames[role] = {}
            for pose in ['Front - Idle'] + [d+' - Walking' for d in ('Front', 'Back', 'Left', 'Right')]:
                self.frames[role][pose] = [im for p in sorted((folder/pose).glob('*.png'))[::2] if (im := self.load(p, 60))]
        self.canvas.bind('<Configure>', lambda e: self.draw())
        self.animate()

    def load(self, path, size):
        try:
            im = tk.PhotoImage(file=str(path), master=self)
            return im.subsample(max(1, math.ceil(max(im.width(), im.height()) / size)))
        except (tk.TclError, OSError):
            return None

    def send(self, generate):
        value = self.prompt.get('1.0', 'end').strip()
        if not value:
            self.summary.set('Najpierw wpisz temat, np. „Duszek otwiera kawiarnię w lesie”.')
            self.prompt.focus_set()
            return
        instruction = ('Wygeneruj jeden krótki film w ComfyUI na podstawie tego opisu. Sprawdź dostępne modele i node, przygotuj workflow i uruchom generowanie. ' if generate else 'Przygotuj pomysł i scenariusz krótkiego filmu. Nie generuj jeszcze filmu. ')
        self.submit(instruction + value)

    def busy(self, value):
        if value: self.stop_demo()
        self.is_busy = value
        self.test_button.state(['disabled' if value else '!disabled'])
        for button in (self.plan_button, self.film_button):
            button.state(['disabled' if value else '!disabled'])

    def update_role(self, value):
        role = value['role']
        previous = self.states[role][0]
        if self.states[role] != (value['state'], value['detail']):
            self.log(role, value['detail'])
        self.states[role] = (value['state'], value['detail'])
        if value['state'] == 'working' and previous != 'working':
            self.motions[role].visit(self.motions[role].home)
        self.summary.set(role + ' · ' + value['detail'][:110])
        self.ghost.state = 'generating' if 'Generowanie ' in value['detail'] else value['state']
        self.progress['value'] = sum(s == 'done' for s, _ in self.states.values())
        self.inspect(self.selected)

    def handoff(self, envelope):
        self.log(envelope['from']+' → '+envelope['to'], envelope['message'])
        self.message.set(envelope['from']+' → '+envelope['to']+': '+envelope['message'][:130])
        self.deliveries.append((envelope['from'], envelope['to'], self.tick))
        sender, recipient = envelope['from'], envelope['to']
        if sender in self.motions and recipient in self.motions:
            self.motions[sender].visit(self.motions[recipient].home)

    def inspect(self, role):
        self.selected = role
        state, detail = self.states[role]
        movement = ' · w drodze' if self.motions[role].walking else ''
        self.detail.set(role + ' — ' + LABELS.get(state, state) + movement + ': ' + detail)

    def draw(self):
        c = self.canvas
        c.delete('scene')
        w, h = max(c.winfo_width(), 700), max(c.winfo_height(), 340)
        c.configure(scrollregion=(0, 0, w, h))
        c.create_line(40, h*.52, w-35, h*.52, width=24, fill='#e4d3a4', tags='scene')
        for i, role in enumerate(ROLES):
            x, y = w*(.17 + (i % 3)*.30), h*(.25 if i < 3 else .75)
            tag = 'npc' + str(i)
            tags = ('scene', tag)
            state, _ = self.states[role]
            c.create_line(x, y, x, h*.52, width=13, fill='#e4d3a4', tags=tags)
            c.create_oval(x-75, y-60, x+75, y+55, fill='#c1dba6', outline='', tags=tags)
            building = self.buildings[BUILDINGS[i]]
            if building:
                c.create_image(x-23, y-15, image=building, tags=tags)
            else:
                c.create_rectangle(x-56, y-42, x+10, y+14, fill='#f8efd8', outline='#707e55', tags=tags)
                c.create_polygon(x-65, y-42, x-23, y-69, x+20, y-42, fill='#b8755d', tags=tags)
            c.create_text(x, y-70, text=TITLES[i], fill='#263c31', font=('Segoe UI', 10, 'bold'), tags=tags)
            c.create_rectangle(x-76, y+43, x+76, y+65, fill=COLORS.get(state, '#ffffff'), outline='', tags=tags)
            c.create_text(x, y+54, text=role+' · '+LABELS.get(state, state), font=('Segoe UI', 9), tags=tags)
            c.tag_bind(tag, '<Button-1>', lambda e, r=role: self.inspect(r))

        # Actors are drawn after all buildings, at actual moving coordinates.
        for i, role in enumerate(ROLES):
            motion = self.motions[role]
            px, py = motion.position
            px, py = px*w+40, py*h+5
            state, _ = self.states[role]
            pose = motion.direction+' - Walking' if motion.walking else 'Front - Idle'
            frames = self.frames[role].get(pose) or self.frames[role].get('Front - Idle', [])
            tags = ('scene', 'actor'+str(i))
            if frames:
                c.create_image(px, py, image=frames[(self.tick//2) % len(frames)], tags=tags)
            else:
                c.create_oval(px-14, py-20, px+14, py+12, fill='#627b99', outline='white', tags=tags)
                stride = 5 if self.tick % 4 < 2 else -5
                c.create_line(px-6, py+10, px-6+(stride if motion.walking else 0), py+23, width=3, tags=tags)
                c.create_line(px+6, py+10, px+6-(stride if motion.walking else 0), py+23, width=3, tags=tags)
            if state == 'working' and not motion.walking:
                # Work prop: desk, document and moving pen; not a combat animation.
                c.create_rectangle(px-20, py+13, px+20, py+26, fill='#926644', outline='#63472e', tags=tags)
                c.create_rectangle(px-9, py+14, px+10, py+23, fill='#fff7db', tags=tags)
                offset = self.tick % 6
                c.create_line(px-5+offset, py+20, px+3+offset, py+11, fill='#25485a', width=3, tags=tags)
            c.create_oval(px-4, py-32, px+4, py-24, fill=COLORS.get(state, '#ffffff'), outline='#47613c', tags=tags)
            c.tag_bind(tags[1], '<Button-1>', lambda e, r=role: self.inspect(r))

        self.deliveries = [(a, b, t) for a, b, t in self.deliveries if self.tick-t < 20]
        for sender, recipient, tick in self.deliveries:
            if sender not in ROLES or recipient not in ROLES: continue
            a, b = ROLES.index(sender), ROLES.index(recipient)
            phase = (self.tick-tick)/20
            ax, ay = w*(.17+(a%3)*.30), h*(.25 if a<3 else .75)
            bx, by = w*(.17+(b%3)*.30), h*(.25 if b<3 else .75)
            x, y = ax+(bx-ax)*phase, ay+(by-ay)*phase
            c.create_oval(x-6, y-6, x+6, y+6, fill='#fff6ad', outline='#8a6e32', tags='scene')

    def start_demo(self):
        if self.is_busy or self.auto.get():
            self.summary.set('Wyłącz stałą pracę AI i poczekaj na zakończenie zadania, aby uruchomić test.')
            return
        self.stop_demo()
        self.demo_started = time.monotonic()
        self.mode.set('TEST · symulacja, bez AI i bez generowania')
        self.plan_button.state(['disabled']); self.film_button.state(['disabled'])

    def pause_demo(self):
        if self.demo_started is None: return
        now = time.monotonic()
        if self.demo_paused is None:
            self.demo_paused = now
            self.pause_button.configure(text='Wznów test')
        else:
            self.demo_started += now-self.demo_paused
            self.demo_paused = None
            self.pause_button.configure(text='Pauza testu')

    def stop_demo(self):
        if self.demo_started is None: return
        self.demo_started = self.demo_paused = None
        self.demo_index = 0
        self.pause_button.configure(text='Pauza testu')
        self.mode.set('TRYB RZECZYWISTY · test zakończony')
        self.motions = {r: Motion(i) for i, r in enumerate(ROLES)}
        self.states = {r: ('waiting', 'Czeka na zadanie') for r in ROLES}
        self.deliveries.clear()
        self.progress['value'] = 0
        self.ghost.state = 'waiting'
        self.summary.set('Test zakończony. Nie wygenerowano filmu.')
        self.message.set('Wiadomości mieszkańców pojawią się tutaj.')
        self.inspect(self.selected)
        if not self.is_busy:
            self.plan_button.state(['!disabled']); self.film_button.state(['!disabled'])

    def animate(self):
        now = time.monotonic()
        dt, self.last_frame = now-self.last_frame, now
        if self.demo_paused is not None:
            self.after(50, self.animate)
            return
        if self.demo_started is not None:
            elapsed = now-self.demo_started
            while self.demo_index < len(DEMO) and elapsed >= DEMO[self.demo_index][0]:
                _, role, state, detail = DEMO[self.demo_index]
                self.demo_index += 1
                if state == 'handoff':
                    self.handoff({'from': role, 'to': detail, 'message': 'TEST: przekazuję przykładowe zadanie'})
                else: self.update_role({'role': role, 'state': state, 'detail': detail})
            if elapsed >= 38:
                self.stop_demo()
        for role, motion in self.motions.items():
            state, _ = self.states[role]
            if not motion.route and state != 'working':
                self.patrol_count[role] += 1
                index = (ROLES.index(role) + self.patrol_count[role]) % len(ROLES)
                motion.visit(self.motions[ROLES[index]].home)
            motion.step(dt)
        self.tick += 1
        self.draw()
        self.after(50, self.animate)

    def toggle_continuous(self):
        self.stop_demo()
        if self.continuous_callback: self.continuous_callback(self.auto.get())

    def log(self, role, text):
        line = time.strftime('%H:%M:%S')+' | '+role+' | '+text.replace('\n', ' ')[:1600]
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-500:]
        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_box.configure(state='normal')
            self.log_box.delete('1.0', 'end')
            self.log_box.insert('end', '\n'.join(self.log_lines))
            self.log_box.see('end'); self.log_box.configure(state='disabled')

    def show_log(self):
        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_window.lift(); return
        self.log_window = tk.Toplevel(self); self.log_window.title('Dziennik zadań — na żywo')
        self.log_window.geometry('900x500')
        ttk.Label(self.log_window, text='Bieżąca sesja · wpisy TEST są symulacją · trwałe zlecenia: Wyniki i historia').pack(anchor='w')
        self.log_box = tk.Text(self.log_window, wrap='word')
        bar = ttk.Scrollbar(self.log_window, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y'); self.log_box.pack(fill='both', expand=True)
        self.log_box.insert('end', '\n'.join(self.log_lines)); self.log_box.configure(state='disabled')

    def history(self):
        window = tk.Toplevel(self); window.title('Wyniki pracy wioski'); window.geometry('820x560')
        tabs = ttk.Notebook(window); tabs.pack(fill='both', expand=True)
        productions, films = ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(productions, text='Zlecenia i rozmowy agentów'); tabs.add(films, text='Pliki z ComfyUI')
        records = []
        for path in sorted((self.base/'data'/'productions').glob('*.json'), reverse=True):
            try: records.append(json.loads(path.read_text(encoding='utf-8')))
            except (OSError, ValueError): continue
        listing = tk.Listbox(productions, height=7); listing.pack(fill='x')
        text = tk.Text(productions, wrap='word'); text.pack(fill='both', expand=True)
        for record in records:
            label = {'running': 'W toku', 'done': 'Zakończono obsługę', 'error': 'Błąd', 'interrupted': 'Przerwane'}.get(record['state'], record['state'])
            listing.insert('end', label+' · '+record['request'][:95])
        def select(event):
            if not listing.curselection(): return
            record = records[listing.curselection()[0]]
            text.configure(state='normal'); text.delete('1.0', 'end')
            text.insert('end', record['request']+'\n\n'+record['result']+'\n\nROZMOWY MIESZKAŃCÓW\n')
            for msg in record['messages']:
                text.insert('end', msg['from']+' → '+msg['to']+'\n'+msg['message']+'\n\n')
            text.configure(state='disabled')
        listing.bind('<<ListboxSelect>>', select)
        ttk.Label(films, text='Rzeczywiste wyjścia narzędzia generowania. Otwieranie używa adresu ComfyUI.').pack(anchor='w')
        output_list = tk.Listbox(films); output_list.pack(fill='both', expand=True)
        urls = []
        for path in sorted((self.base/'data'/'renders').glob('*.json'), reverse=True):
            try:
                render = json.loads(path.read_text(encoding='utf-8'))
                for output in (render.get('outputs') or {}).values():
                    for values in output.values():
                        if not isinstance(values, list): continue
                        for item in values:
                            if not isinstance(item, dict) or not item.get('filename'): continue
                            query = {k: item[k] for k in ('filename', 'subfolder', 'type') if k in item}
                            urls.append(self.cfg()['comfy'].rstrip('/')+'/view?'+urlencode(query))
                            output_list.insert('end', item['filename'])
            except (OSError, ValueError, AttributeError): continue
        def open_file():
            if urls and output_list.curselection(): webbrowser.open(urls[output_list.curselection()[0]])
        ttk.Button(films, text='Otwórz wybrany plik', command=open_file).pack(pady=8)
        if not urls: output_list.insert('end', 'Brak zapisanych wyjść. Najpierw zleć generowanie filmu.')
        output_list.bind('<Double-1>', lambda e: open_file() if urls else None)
        if records: listing.selection_set(0); select(None)
