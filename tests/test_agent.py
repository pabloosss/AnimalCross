import tempfile
import unittest
from pathlib import Path
from agent import Agent

class Tests(unittest.TestCase):
    def test_tool_result_returns_to_model(self):
        seen=[]
        def api(base, route, payload=None, **kw):
            if route == '/system_stats': return {'system': {'os':'test'}}
            seen.append(payload)
            if len(seen)==1:
                return {'message': {'role':'assistant','content':'','tool_calls':[{'function':{'name':'inspect_environment','arguments':{}}}]}}
            return {'message':{'role':'assistant','content':'Sprawdzono'}}
        with tempfile.TemporaryDirectory() as root:
            agent=Agent(api, {'ollama':'a','comfy':'b','model':'q','context':8192},Path(root),lambda x:None,lambda:None)
            self.assertEqual(agent.run([{'role':'user','content':'sprawdź'}],''),'Sprawdzono')
            self.assertTrue((Path(root)/'agent_memory.jsonl').exists())
            self.assertIn('test',seen[1]['messages'][-2]['content'])

    def test_invalid_graph_not_saved(self):
        with tempfile.TemporaryDirectory() as root:
            agent=Agent(lambda *args: {}, {'comfy':'b'},Path(root),lambda x:None,lambda:None)
            with self.assertRaises(ValueError): agent.execute('save_workflow',{'graph':{'1':{'class_type':'Invented','inputs':{}}}})
            self.assertFalse((Path(root)/'agent_workflow.json').exists())

    def test_unknown_tool_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            agent=Agent(None,{},Path(root),lambda x:None,lambda:None)
            with self.assertRaises(ValueError): agent.execute('shell',{'command':'test'})

    def test_memory_appends_without_overwriting(self):
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root)
            agent=Agent(None,{},directory,lambda x:None,lambda:None)
            agent.remember('Pierwsze ustalenie')
            agent.remember('Drugie ustalenie')
            text=(directory/'pamiec_ai.txt').read_text(encoding='utf-8')
            self.assertIn('Pierwsze ustalenie',text)
            self.assertIn('Drugie ustalenie',text)

    def test_automatic_memory_update(self):
        def api(*args, **kwargs):
            return {'message':{'content':'{"note":"Użytkownik chce filmy pionowe."}'}}
        with tempfile.TemporaryDirectory() as root:
            agent=Agent(api,{'ollama':'a','model':'q'},Path(root),lambda x:None,lambda:None)
            agent.update_memory('Chcę filmy pionowe','Zapisane')
            self.assertIn('pionowe',(Path(root)/'pamiec_ai.txt').read_text(encoding='utf-8'))

