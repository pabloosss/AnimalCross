import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from team import Team

class TeamTests(unittest.TestCase):
    def test_handoffs_have_one_task_and_real_order(self):
        events=[]
        class Operator:
            evidence=[{'tool':'list_models','result':['wan']}]
            def __init__(self,*a): pass
            def run(self,*a): return 'Wykryto wan'
        with tempfile.TemporaryDirectory() as root:
            team=Team(None,{},Path(root),lambda *e:events.append(e),lambda:None)
            with patch.object(team,'ask',side_effect=['Plan','Nie wymaga scenariusza','Potwierdzono odczyt']), patch('team.Agent',Operator):
                result=team.run([{'role':'user','content':'sprawdź modele'}],'')
            messages=[json.loads(x) for x in (Path(root)/'agent_messages.jsonl').read_text().splitlines()]
            self.assertEqual([(m['from'],m['to']) for m in messages],[('Koordynator','Scenarzysta'),('Scenarzysta','Operator'),('Operator','Kontroler'),('Kontroler','Koordynator')])
            self.assertEqual(len(set(m['task'] for m in messages)),1)
            self.assertIn('Potwierdzono',result)

    def test_failure_is_visible_and_does_not_run_later_roles(self):
        events=[]
        with tempfile.TemporaryDirectory() as root:
            team=Team(None,{},Path(root),lambda *e:events.append(e),lambda:None)
            with patch.object(team,'ask',side_effect=RuntimeError('offline')) as ask:
                with self.assertRaises(RuntimeError): team.run([{'role':'user','content':'hej'}],'')
            self.assertEqual(ask.call_count,1)
            self.assertTrue(any(e[0]=='team' and e[1]['state']=='error' for e in events))

