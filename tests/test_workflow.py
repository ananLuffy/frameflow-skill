import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from frameflow.__main__ import Invalid, STAGES, scope, validate, verify, next_step

ROOT = pathlib.Path(__file__).resolve().parents[1]
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root/'asset.txt').write_text('synthetic asset')
        (self.root/'evidence.txt').write_text('synthetic test evidence; not an artistic review')
        self.asset = {'id':'asset','path':'asset.txt','sha256':self.hash('asset.txt'),'dependencies':[]}
        self.doc = {'schema_version':1,'project_id':'test','mode':'production','author_id':'author','artifacts':[self.asset],
            'actions':[{'id':s,'kind':s,'artifact_ids':['asset'],'status':'pending','evidence':None,'scope_sha256':None} for s in STAGES],
            'reviews':[{'id':'r1','reviewer_id':'reviewer','artifact_ids':['asset'],'status':'pending','evidence':None,'scope_sha256':None}]}
    def hash(self,p): return hashlib.sha256((self.root/p).read_bytes()).hexdigest()
    def finish(self):
        for group in ['actions','reviews']:
            for row in self.doc[group]:
                row.update(status='done' if group=='actions' else 'pass',evidence={'path':'evidence.txt','sha256':self.hash('evidence.txt')})
                row['scope_sha256']=scope(self.doc,row)
    def test_pending(self):
        verify(validate(self.doc),self.root)
        self.assertEqual(next_step(self.doc)['id'],'brief')
    def test_complete_is_only_recorded(self):
        self.finish(); verify(validate(self.doc),self.root)
        self.assertEqual(next_step(self.doc)['state'],'RECORDED_OBLIGATIONS_COMPLETE')
    def test_missing_stage(self):
        self.doc['actions'].pop()
        with self.assertRaises(Invalid): validate(self.doc)
    def test_missing_review(self):
        self.doc['reviews']=[]
        with self.assertRaises(Invalid): validate(self.doc)
    def test_multiple_reviews_all_required(self):
        self.finish(); r=copy.deepcopy(self.doc['reviews'][0]); r.update(id='r2',status='pending',evidence=None,scope_sha256=None)
        self.doc['reviews'].append(r); validate(self.doc)
        self.assertEqual(next_step(self.doc)['id'],'r2')
    def test_multiple_actions_all_required(self):
        self.finish(); a=copy.deepcopy(self.doc['actions'][0]); a.update(id='extra',status='pending',evidence=None,scope_sha256=None)
        self.doc['actions'].append(a); validate(self.doc)
        self.assertEqual(next_step(self.doc)['id'],'extra')
    def test_mode_allowlist(self):
        self.doc['mode']='review'
        with self.assertRaises(Invalid): validate(self.doc)
    def test_review_only_does_not_generate(self):
        self.doc['mode']='review'; self.doc['actions']=[self.doc['actions'][-2]]
        validate(self.doc); self.assertEqual(next_step(self.doc)['kind'],'review')
    def test_unknown_field(self):
        self.doc['approved']=True
        with self.assertRaises(Invalid): validate(self.doc)
    def test_bool_schema(self):
        self.doc['schema_version']=True
        with self.assertRaises(Invalid): validate(self.doc)
    def test_bad_status(self):
        self.doc['actions'][0]['status']='pass'
        with self.assertRaises(Invalid): validate(self.doc)
    def test_stale_scope(self):
        self.finish(); self.asset['sha256']='0'*64
        with self.assertRaises(Invalid): validate(self.doc)
    def test_dependency_binding(self):
        b=copy.deepcopy(self.asset); b['id']='dependency'; self.doc['artifacts'].append(b)
        self.asset['dependencies']=['dependency']; self.doc['reviews'][0]['artifact_ids'].append('dependency')
        self.finish(); b['sha256']='0'*64
        with self.assertRaises(Invalid): validate(self.doc)
    def test_cycle(self):
        self.asset['dependencies']=['asset']
        with self.assertRaises(Invalid): validate(self.doc)
    def test_unknown_dependency(self):
        self.asset['dependencies']=['missing']
        with self.assertRaises(Invalid): validate(self.doc)
    def test_author_not_reviewer(self):
        self.doc['reviews'][0]['reviewer_id']='author'
        with self.assertRaises(Invalid): validate(self.doc)
    def test_failed_review_blocks(self):
        self.finish(); self.doc['reviews'][0]['status']='fail'; self.doc['reviews'][0]['scope_sha256']=scope(self.doc,self.doc['reviews'][0]); validate(self.doc)
        self.assertEqual(next_step(self.doc)['state'],'REPAIR_REQUIRED')
    def test_result_change_invalidates_binding(self):
        self.finish(); self.doc['reviews'][0]['status']='fail'
        with self.assertRaises(Invalid): validate(self.doc)
    def test_review_mode_failure_never_orders_repair(self):
        self.doc['mode']='review'; self.doc['actions']=[self.doc['actions'][-2]]
        self.finish(); row=self.doc['reviews'][0]; row['status']='fail'; row['scope_sha256']=scope(self.doc,row)
        validate(self.doc)
        self.assertEqual(next_step(self.doc)['state'],'REVIEW_FAILED')
    def test_tampered_artifact(self):
        (self.root/'asset.txt').write_text('changed')
        with self.assertRaises(Invalid): verify(validate(self.doc),self.root)
    def test_tampered_evidence(self):
        self.finish(); (self.root/'evidence.txt').write_text('changed')
        with self.assertRaises(Invalid): verify(validate(self.doc),self.root)
    def test_paths(self):
        for path in ['../escape','/etc/passwd','a/../b','a//b','./a','a\\b']:
            with self.subTest(path=path):
                self.asset['path']=path
                with self.assertRaises(Invalid): validate(self.doc)
    def test_symlink(self):
        (self.root/'link').symlink_to(self.root/'asset.txt'); self.asset['path']='link'
        with self.assertRaises(Invalid): verify(validate(self.doc),self.root)
    def test_symlink_directory(self):
        (self.root/'dir').symlink_to(self.root,target_is_directory=True); self.asset['path']='dir/asset.txt'
        with self.assertRaises(Invalid): verify(validate(self.doc),self.root)
    def make_root_alias(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        alias = pathlib.Path(temp.name) / 'root-alias'
        alias.symlink_to(self.root.resolve(), target_is_directory=True)
        return alias
    def test_root_alias_helper(self):
        self.finish()
        verify(validate(self.doc), self.make_root_alias())
    def test_root_alias_cli(self):
        alias = self.make_root_alias()
        (self.root/'manifest.json').write_text(json.dumps(self.doc))
        p = subprocess.run([sys.executable, '-m', 'frameflow', 'verify', str(alias/'manifest.json')], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['state'], 'VERIFIED_BYTES')
    def test_root_alias_still_rejects_internal_symlink(self):
        alias = self.make_root_alias()
        (self.root/'link').symlink_to(self.root/'asset.txt')
        self.asset['path'] = 'link'
        with self.assertRaises(Invalid): verify(validate(self.doc), alias)
    def test_root_alias_still_rejects_escape(self):
        alias = self.make_root_alias()
        outside = alias.parent/'outside.txt'
        outside.write_text('synthetic asset')
        (self.root/'escape').symlink_to(outside)
        self.asset['path'] = 'escape'
        with self.assertRaises(Invalid): verify(validate(self.doc), alias)
    def test_missing_file(self):
        (self.root/'asset.txt').unlink()
        with self.assertRaises(Invalid): verify(validate(self.doc),self.root)
    def test_cli_malformed_no_traceback(self):
        for content in ['{','[]','{"schema_version":1,"schema_version":1}', '{"schema_version": []}']:
            (self.root/'bad.json').write_text(content)
            p=subprocess.run([sys.executable,'-m','frameflow','next',str(self.root/'bad.json')],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,2); self.assertNotIn('Traceback',p.stderr)
    def test_example(self):
        p=subprocess.run([sys.executable,'-m','frameflow','next','examples/demo/manifest.json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(json.loads(p.stdout)['state'],'ACTION_REQUIRED')

if __name__=='__main__': unittest.main()
