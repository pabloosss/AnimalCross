"""Deterministic NPC movement on village paths, independent of Tk and AI."""
import math


class Motion:
    def __init__(self, index):
        self.home = (.17 + index % 3 * .30, .25 if index < 3 else .75)
        self.position = (self.home[0], .52)
        self.route = []
        self.direction = 'Front'
        self.walking = False

    def visit(self, target):
        x, y = self.position
        tx, ty = target
        self.route = [(x, .52), (tx, .52), (tx, ty)]
        if target != self.home:
            self.route += [(tx, .52), (self.home[0], .52), self.home]

    def step(self, seconds):
        distance = .24 * min(seconds, .25)
        self.walking = False
        while self.route and distance > 0:
            x, y = self.position
            tx, ty = self.route[0]
            dx, dy = tx-x, ty-y
            length = math.hypot(dx, dy)
            if length < .00001:
                self.route.pop(0)
                continue
            self.walking = True
            self.direction = ('Right' if dx > 0 else 'Left') if abs(dx) > abs(dy) else ('Front' if dy > 0 else 'Back')
            step = min(distance, length)
            self.position = (x+dx/length*step, y+dy/length*step)
            distance -= step
            if step == length:
                self.position = (tx, ty)
                self.route.pop(0)
                break
        return self.position


# Display-only events. No API, filesystem, memory, or render operations.
DEMO = [
    (0, 'Koordynator', 'working', 'TEST: układa plan filmu'),
    (4, 'Koordynator', 'done', 'TEST: plan gotowy'),
    (4, 'Koordynator', 'handoff', 'Scenarzysta'),
    (5, 'Scenarzysta', 'working', 'TEST: pisze scenariusz'),
    (5, 'Technik', 'working', 'TEST: symulacja diagnostyki'),
    (10, 'Technik', 'done', 'TEST: diagnostyka zakończona'),
    (10, 'Technik', 'handoff', 'Operator'),
    (12, 'Scenarzysta', 'done', 'TEST: scena gotowa'),
    (12, 'Scenarzysta', 'handoff', 'Operator'),
    (13, 'Operator', 'working', 'TEST: symulacja renderowania — film nie powstaje'),
    (20, 'Operator', 'done', 'TEST: koniec symulacji renderu'),
    (20, 'Operator', 'handoff', 'Kontroler'),
    (21, 'Kontroler', 'working', 'TEST: symulacja kontroli'),
    (21, 'Pamięć', 'working', 'TEST: symulacja zapisu — pamięć nie jest zmieniana'),
    (26, 'Kontroler', 'done', 'TEST: kontrola zakończona'),
    (26, 'Pamięć', 'done', 'TEST: koniec symulacji pamięci'),
    (26, 'Kontroler', 'handoff', 'Koordynator'),
]
