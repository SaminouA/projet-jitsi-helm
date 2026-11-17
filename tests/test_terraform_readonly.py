import copy
import importlib.util
from pathlib import Path
import unittest
import yaml

spec=importlib.util.spec_from_file_location('readonly','scripts/terraform-readonly.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ReadonlyTerraform(unittest.TestCase):
    def test_only_zero_change_plan_is_accepted(self):
        p={'complete':True,'resource_changes':[{'address':a,'mode':'managed','change':{'actions':['no-op']}} for a in [m.CLUSTER,m.POOL]]}
        self.assertEqual(m.verify_plan(p)['replace'],0)
        for actions in [['create'],['update'],['delete'],['delete','create']]:
            altered=copy.deepcopy(p);altered['resource_changes'][0]['change']['actions']=actions
            with self.subTest(actions=actions),self.assertRaises(RuntimeError):m.verify_plan(altered)

    def test_context_refuses_automatic_event_or_enabled_apply(self):
        env=dict(GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY='SaminouA/projet-jitsi-helm',GITHUB_REF='refs/heads/main',GITHUB_SHA='a'*40,TF_STATE_BUCKET=m.BUCKET,TF_STATE_LINEAGE='12345678-1234-1234-1234-123456789abc')
        m.verify_context(env,'a'*40)
        for key,value in [('GITHUB_EVENT_NAME','push'),('TF_CD_ENABLED','true'),('GKE_CD_ENABLED','true'),('GITHUB_REF','refs/heads/feature')]:
            with self.subTest(key=key),self.assertRaises(RuntimeError):m.verify_context(dict(env,**{key:value}),'a'*40)

    def test_workflow_manual_protected_and_has_no_infrastructure_commands(self):
        w=yaml.safe_load(Path('.github/workflows/terraform-gke.yml').read_text())
        self.assertEqual(set(w.get('on',w.get(True))),{'workflow_dispatch'})
        self.assertEqual(w['jobs']['plan']['environment'],'terraform-controlled')
        self.assertEqual(w['jobs']['plan']['permissions'],{'contents':'read','id-token':'write'})
        import ast
        tree=ast.parse(Path('scripts/terraform-readonly.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.List):
                strings=[e.value for e in node.elts if isinstance(e,ast.Constant) and isinstance(e.value,str)]
                self.assertFalse(any(s in ['apply','destroy','import','-migrate-state','-force-copy','-lock=false'] for s in strings))

    def test_error_reports_plan_permission_without_secret_payload(self):
        text="Error 403: Required 'compute.instanceGroupManagers.list' permission. private_key=SECRET_SENTINEL token=TOKEN_SENTINEL"
        error=m.safe_command_error(['terraform','-chdir=/private/path','plan'],text)
        self.assertEqual(error,'READONLY_plan_IAM_DENIED:compute.instanceGroupManagers.list')
        for private in ['SECRET_SENTINEL','TOKEN_SENTINEL','/private/path','private_key']:
            self.assertNotIn(private,error)

    def test_safe_error_distinguishes_subcommands_and_quota(self):
        self.assertEqual(m.safe_command_error(['terraform','-chdir=/private','init'],'Error 429 quota exceeded'), 'READONLY_init_QUOTA_EXCEEDED')
        self.assertEqual(m.safe_command_error(['terraform','-chdir=/private','state','pull'],'Error acquiring the state lock'), 'READONLY_state_STATE_LOCK')
        self.assertEqual(m.safe_command_error(['terraform','-chdir=/private','validate'],'opaque content SECRET_SENTINEL'), 'READONLY_validate_UNCLASSIFIED')

    def test_iam_patch_adds_only_required_compute_read(self):
        patch=yaml.safe_load(Path('deploy/terraform/gke-label-role-read-fix.yaml').read_text())
        original={'container.clusters.get','container.clusters.update','container.operations.get',
                  'resourcemanager.projects.get','serviceusage.services.use'}
        self.assertEqual(set(patch['includedPermissions'])-original,{'compute.instanceGroupManagers.list'})
        self.assertTrue(original.issubset(patch['includedPermissions']))
