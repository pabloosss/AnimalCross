"""Live village: artwork from the repository, states from actual worker events."""
import json
import math
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
    def __init__(self, parent, base, submit, stop, start, cfg):
        super().__init__(parent, padding=10)
        self.base, self.submit, self.cfg = base, submit, cfg
        self.states = {r: ('waiting', 'Czeka na zadanie') for r in ROLES}
        self.tick = 0
        self.deliveries = []
        self.frames, self.buildings = {}, {}
        self.selected = ROLES[0]
        header = ttk.Frame(self); header.pack(fill='x')
        ttk.Label(header, text='Twoja wioska filmowa', font=('Segoe UI', 20, 'bold')).pack(side='left')
        ttk.Button(header, text='Uruchom usługi', command=start).pack(side='right')
        ttk.Button(header, text='Przerwij pracę', command=stop).pack(side='right', padx=6)
        self.summary = tk.StringVar(value='Opisz krótki film. Mieszkańcy podzielą się pracą.')
        ttk.Label(self, textvariable=self.summary).pack(anchor='w', pady=5)
        self.progress = ttk.Progressbar(self, maximum=len(ROLES))
        self.progress.pack(fill='x')
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
            folder = base/'assets'/'characters'/'bandits'/actors[i % 3]/'PNG'/'PNG Sequences'/'Front - Idle'
            self.frames[role] = [im for p in sorted(folder.glob('*.png'))[:16] if (im := self.load(p, 60))]
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
        for button in (self.plan_button, self.film_button):
            button.state(['disabled' if value else '!disabled'])

    def update_role(self, value):
        role = value['role']
        self.states[role] = (value['state'], value['detail'])
        self.summary.set(role + ' · ' + value['detail'][:110])
        self.ghost.state = 'generating' if 'Generowanie ' in value['detail'] else value['state']
        self.progress['value'] = sum(s == 'done' for s, _ in self.states.values())
        self.inspect(self.selected)

    def handoff(self, envelope):
        self.message.set(envelope['from']+' → '+envelope['to']+': '+envelope['message'][:130])
        self.deliveries.append((envelope['from'], envelope['to'], self.tick))

    def inspect(self, role):
        self.selected = role
        state, detail = self.states[role]
        self.detail.set(role + ' — ' + LABELS.get(state, state) + ': ' + detail)

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
            frames = self.frames[role]
            bob = math.sin(self.tick*.6)*3 if state == 'working' else 0
            if frames:
                c.create_image(x+40, y+5+bob, image=frames[self.tick % len(frames)], tags=tags)
            else:
                c.create_oval(x+24, y-14+bob, x+52, y+17+bob, fill='#627b99', outline='white', tags=tags)
            c.create_text(x, y-70, text=TITLES[i], fill='#263c31', font=('Segoe UI', 10, 'bold'), tags=tags)
            c.create_rectangle(x-76, y+43, x+76, y+65, fill=COLORS.get(state, '#ffffff'), outline='', tags=tags)
            c.create_text(x, y+54, text=role+' · '+LABELS.get(state, state), font=('Segoe UI', 9), tags=tags)
            c.tag_bind(tag, '<Button-1>', lambda e, r=role: self.inspect(r))

        self.deliveries = [(a, b, t) for a, b, t in self.deliveries if self.tick-t < 20]
        for sender, recipient, tick in self.deliveries:
            if sender not in ROLES or recipient not in ROLES: continue
            a, b = ROLES.index(sender), ROLES.index(recipient)
            phase = (self.tick-tick)/20
            ax, ay = w*(.17+(a%3)*.30), h*(.25 if a<3 else .75)
            bx, by = w*(.17+(b%3)*.30), h*(.25 if b<3 else .75)
            x, y = ax+(bx-ax)*phase, ay+(by-ay)*phase
            c.create_oval(x-6, y-6, x+6, y+6, fill='#fff6ad', outline='#8a6e32', tags='scene')

    def animate(self):
        self.tick += 1
        self.draw()
        self.after(150, self.animate)

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
