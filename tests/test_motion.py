import unittest
from motion import Motion, DEMO

class MotionTests(unittest.TestCase):
    def test_trip_visits_recipient_then_returns(self):
        actor = Motion(0)
        target = Motion(5).home
        actor.visit(target)
        visited = False
        positions = set()
        for _ in range(2000):
            actor.step(.05)
            positions.add(actor.position)
            visited |= actor.position == target
            if not actor.route: break
        self.assertTrue(visited)
        self.assertGreater(len(positions), 20)
        self.assertEqual(actor.position, actor.home)

    def test_work_redirects_patrol_to_own_station(self):
        actor = Motion(0)
        actor.visit(Motion(4).home)
        actor.step(.2)
        actor.visit(actor.home)
        for _ in range(400): actor.step(.05)
        self.assertEqual(actor.position, actor.home)
        self.assertFalse(actor.walking)

    def test_all_directions_and_no_overshoot(self):
        actor = Motion(0)
        for target, direction in [((.5,.52),'Right'), ((.1,.52),'Left'), ((.1,.2),'Back'), ((.1,.8),'Front')]:
            actor.route = [target]
            actor.step(.01)
            self.assertEqual(actor.direction, direction)
            for _ in range(1000): actor.step(.05)
            self.assertEqual(actor.position, target)

    def test_demo_finishes_every_role_and_overlaps_work(self):
        states = {}
        overlap = False
        for _, role, state, _ in DEMO:
            if state != 'handoff': states[role] = state
            overlap |= sum(s == 'working' for s in states.values()) >= 2
        self.assertTrue(overlap)
        self.assertEqual(set(states.values()), {'done'})
        self.assertEqual(len(states), 6)
