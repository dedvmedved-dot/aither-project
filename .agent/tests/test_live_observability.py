#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, os, unittest
from pathlib import Path
AGENT=Path(__file__).resolve().parents[1]
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,AGENT/filename); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
runner_live=load('runner_live','runner_live.py'); codex_observer=load('codex_observer','codex_observer.py')
class Tests(unittest.TestCase):
    def test_sanitizer(self):
        safe=runner_live.sanitize_status({'task_id':'T','state':'RUNNING','reasoning':'PRIVATE','command':'cat token','stdout':'secret'})
        self.assertNotIn('reasoning',safe); self.assertNotIn('command',safe); self.assertNotIn('stdout',safe)
    def test_event_metadata(self):
        self.assertEqual(codex_observer.event_metadata('{"type":"item.completed","item":{"type":"reasoning","text":"PRIVATE"}}'),('item.completed','reasoning'))
    def test_json_flag(self):
        old=os.environ.get('AITHER_REAL_CODEX_BIN'); os.environ['AITHER_REAL_CODEX_BIN']='/opt/codex'
        try: argv=codex_observer.build_real_argv(['--ask-for-approval','never','exec','--sandbox','workspace-write','prompt'])
        finally:
            if old is None: os.environ.pop('AITHER_REAL_CODEX_BIN',None)
            else: os.environ['AITHER_REAL_CODEX_BIN']=old
        self.assertEqual(argv[:5],['/opt/codex','--ask-for-approval','never','exec','--json'])
if __name__=='__main__': unittest.main(verbosity=2)
