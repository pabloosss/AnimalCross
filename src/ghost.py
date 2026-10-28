"""User-owned PNGTuber ZIP importer. Artwork is never bundled or uploaded."""
import math
import time
import tkinter as tk
from pathlib import Path
from zipfile import ZipFile

STATES={'waiting':('Happy','Czekam na zadanie'), 'working':('Happy','Myślę i pracuję'),
        'generating':('Angry','Skupienie • generuję'), 'done':('Happy','Gotowe!'), 'error':('Sad','Potrzebuję uwagi')}

class Ghost(tk.Canvas):
    def __init__(self,parent,folder):
        super().__init__(parent,width=160,height=155,bg='#edf2f7',highlightthickness=0)
        self.folder=Path(folder); self.frames={}; self.state='waiting'; self.tick=0
        self.reload(); self.animate()

    def reload(self):
        self.frames={}
        for emotion in ('Happy','Sad','Angry','Fearful'):
            for pose in ('Silent','Silent Blink','Speaking','Speaking Blink'):
                path=self.folder/(emotion+' '+pose+'.png')
                if path.is_file():
                    image=tk.PhotoImage(file=str(path))
                    divisor=max(1,math.ceil(max(image.width(),image.height())/125))
                    self.frames[(emotion,pose)]=image.subsample(divisor)

    def import_zip(self,path):
        # Only known PNGs, no arbitrary archive extraction.
        expected=[f'{e} {p}.png' for e in ('Happy','Sad','Angry','Fearful') for p in ('Silent','Silent Blink','Speaking','Speaking Blink')]
        with ZipFile(path) as z:
            files={Path(i.filename).name:i for i in z.infolist() if i.filename.startswith('PNGs/')}
            if any(name not in files for name in expected): raise ValueError('ZIP nie zawiera kompletu 16 obrazów duszka.')
            blobs={}
            for name in expected:
                if files[name].file_size>8_000_000: raise ValueError('Zbyt duży obraz.')
                content=z.read(files[name])
                if not content.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Nieprawidłowy PNG.')
                blobs[name]=content
        self.folder.mkdir(parents=True,exist_ok=True)
        for name,content in blobs.items(): (self.folder/name).write_bytes(content)
        self.reload()

    def animate(self):
        self.tick+=1; self.delete('all')
        emotion,label=STATES.get(self.state,STATES['waiting'])
        speaking=self.state in ('working','generating') and self.tick%6<3
        pose='Speaking' if speaking else 'Silent'
        if self.tick%37 in (0,1): pose+=' Blink'
        frame=self.frames.get((emotion,pose))
        if frame: self.create_image(80,66+math.sin(self.tick/7)*4,image=frame)
        else:
            self.create_oval(40,22,120,104,fill='white',outline='#376291',width=3)
            self.create_oval(60,48,67,61,fill='#376291'); self.create_oval(92,48,99,61,fill='#376291')
        self.create_text(80,140,text=label,fill='#203047',font=('Segoe UI',9))
        self.after(100,self.animate)

