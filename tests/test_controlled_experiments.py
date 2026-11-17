"""Fixtures and local YAML only. No experiment, network, or cloud request."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml

spec = importlib.util.spec_from_file_location('experiment', 'scripts/controlled-experiment.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ExperimentGuards(unittest.TestCase):
    def setUp(self):
        self.env = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch',
                        GITHUB_REPOSITORY=m.REPO, GITHUB_REF='refs/heads/main', GITHUB_SHA='a'*40,
                        EXPERIMENTS_ENABLED='true', EXPERIMENT_CONFIRM='true', GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1')

    def test_manual_main_explicit_confirmation_only(self):
        m.context(self.env, 'malleus')
        for key, value in [('GITHUB_EVENT_NAME', 'push'), ('GITHUB_REF', 'refs/heads/pr'),
                           ('GITHUB_REPOSITORY', 'fork/repo'), ('EXPERIMENTS_ENABLED', 'false'),
                           ('EXPERIMENT_CONFIRM', 'false'), ('GITHUB_RUN_ID', '../unsafe')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError): m.context(dict(self.env, **{key:value}), 'malleus')

    def test_human_review_admin_bypass_and_main_only(self):
        e = {'can_admins_bypass':False, 'protection_rules':[{'type':'required_reviewers','reviewers':[{}]}],
             'deployment_branch_policy':{'custom_branch_policies':True}}
        b = {'branch_policies':[{'name':'main','type':'branch'}]}
        m.verify_environment(e,b)
        for key,value in [('can_admins_bypass',True),('protection_rules',[])]:
            with self.assertRaises(RuntimeError):m.verify_environment(dict(e,**{key:value}),b)
        with self.assertRaises(RuntimeError):m.verify_environment(e,{'branch_policies':[{'name':'*','type':'branch'}]})

    def test_exact_web_uid_and_component_required(self):
        name='jitsi-jitsi-meet-web-abc-def'
        pods={name:{'component':'web','uid':'approved','restarts':0}}
        m.exact_web(pods,name,'approved')
        for n,u in [(name,'old'),('jitsi-jitsi-meet-jvb-0-abc-def','approved'),('jitsi-edge-abc-def','approved')]:
            with self.assertRaises(RuntimeError):m.exact_web(pods,n,u)
        manifest=m.experiment(name,'approved','123-1')
        self.assertEqual(manifest['spec']['selector']['pods'],{'jitsi':[name]})
        self.assertEqual(manifest['spec']['selector']['labelSelectors']['app.kubernetes.io/component'],'web')
        self.assertEqual(manifest['spec']['mode'],'one')
        self.assertEqual(manifest['spec']['action'],'pod-kill')

    def test_production_identity_and_restart_changes_abort(self):
        p={'jvb':{'uid':'a','component':'jvb','restarts':0},'web':{'uid':'b','component':'web','restarts':0}}
        q=copy.deepcopy(p); q['web']['uid']='c'
        m.stable(p,q,chaos=True)
        with self.assertRaises(RuntimeError):m.stable(p,q)
        q['jvb']['restarts']=1
        with self.assertRaises(RuntimeError):m.stable(p,q,chaos=True)

    def test_no_existing_meeting(self):
        s={'conferences':0,'participants':0,'local_active_endpoints':0};m.require_idle(s)
        for key in s:
            with self.assertRaises(RuntimeError):m.require_idle(dict(s,**{key:1}))
        with self.assertRaises(RuntimeError):m.require_idle({})

    def test_controller_broad_delete_exec_or_eviction_refused(self):
        binding={'kind':'RoleBinding','metadata':{'namespace':'jitsi'},'roleRef':{'kind':'ClusterRole','name':'target'},
                 'subjects':[{'kind':'ServiceAccount','namespace':'chaos-testing','name':'chaos-controller-manager'}]}
        rule={'apiGroups':[''],'resources':['pods'],'verbs':['delete'],'resourceNames':['approved']}
        def reader(kind, namespace=None):
            if kind.startswith('rolebindings'):return {'items':[binding]}
            if kind=='clusterrolebindings':return {'items':[]}
            return {'rules':[rule]}
        with patch.object(m,'read',side_effect=reader):
            m.controller_permissions('approved')
            for field,value in [('verbs',['deletecollection']),('resourceNames',[]),('resources',['*']),('resources',['pods/exec']),('resources',['pods/eviction']),('resources',['pods/*'])]:
                old=copy.deepcopy(rule);rule[field]=value
                with self.assertRaises(RuntimeError):m.controller_permissions('approved')
                rule.clear();rule.update(old)

    def test_logs_export_only_allowlisted_counters(self):
        safe=m.sanitize_log('token=SECRET user=person room=private\nTests run: 1, Failures: 0, Errors: 0, Skipped: 0\nBUILD SUCCESS')
        self.assertIn('Tests run: 1',safe)
        for forbidden in ['SECRET','private','person','token']:self.assertNotIn(forbidden,safe)

    def test_cleanup_cannot_target_production_release(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,dict(self.env,RUNNER_TEMP=tmp)):
            m.folder().mkdir()
            (m.folder()/'ownership.json').write_text(json.dumps({'run':'123-1','mode':'malleus','name':'jitsi','namespace':'jitsi'}))
            with patch.object(m,'run') as call:
                with self.assertRaises(RuntimeError):m.cleanup()
                call.assert_not_called()

    def test_workflows_manual_reviewed_serialized_and_pinned(self):
        for mode in ['malleus','chaos']:
            w=yaml.load(Path('.github/workflows/'+mode+'-controlled.yml').read_text(),Loader=yaml.BaseLoader)
            self.assertEqual(set(w['on']),{'workflow_dispatch'})
            self.assertEqual(w['on']['workflow_dispatch']['inputs']['confirm_execution']['default'],'false')
            self.assertIn("vars.EXPERIMENTS_ENABLED == 'true'",w['jobs']['preflight']['if'])
            self.assertNotIn('id-token',w['jobs']['preflight']['permissions'])
            j=w['jobs']['experiment'];self.assertEqual(j['needs'],'preflight')
            self.assertEqual(j['environment'],'experiments-controlled')
            self.assertEqual(w['concurrency']['group'],'deploy-jitsi-gke-main')
            self.assertEqual(j['timeout-minutes'],'12')
            for step in j['steps']:
                if 'uses' in step:self.assertRegex(step['uses'],r'@[a-f0-9]{40}$')
            cleanup=next(s for s in j['steps'] if '--cleanup' in s.get('run',''))
            self.assertEqual(cleanup['if'],'${{ always() }}')
            artifact=next(s for s in j['steps'] if 'upload-artifact' in s.get('uses',''))
            self.assertNotIn('ownership',artifact['with']['path'])
            self.assertNotIn('**',artifact['with']['path'])

    def test_node_threshold_aborts_and_missing_metrics_refuses(self):
        nodes={'items':[{'status':{'conditions':[{'type':k,'status':v} for k,v in [('Ready','True'),('MemoryPressure','False'),('DiskPressure','False'),('PIDPressure','False')]]}}]*2}
        with patch.object(m,'read',return_value=nodes),patch.object(m,'kubectl',return_value='n1 100m 6% 2000Mi 40%\nn2 100m 6% 2000Mi 40%'):
            self.assertEqual(len(m.capacity(projected=True)),2)
        with patch.object(m,'read',return_value=nodes),patch.object(m,'kubectl',return_value='n1 1800m 80% 2000Mi 40%\nn2 100m 6% 2000Mi 40%'):
            with self.assertRaises(RuntimeError):m.capacity()
        with patch.object(m,'read',return_value=nodes),patch.object(m,'kubectl',return_value=''):
            with self.assertRaises(RuntimeError):m.capacity()

    def test_metrics_units(self):
        with patch.object(m,'kubectl',return_value='p1 0.25 1Gi\np2 50m 1024Ki'):
            self.assertEqual(m.pod_metrics('jitsi'),[{'pod':'p1','cpu_m':250,'memory_mib':1024},{'pod':'p2','cpu_m':50,'memory_mib':1}])

    def test_cleanup_is_attempted_if_helm_install_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cred=Path(tmp)/'adc.json';cred.write_text('{"type":"external_account"}')
            env=dict(self.env,RUNNER_TEMP=tmp,GOOGLE_APPLICATION_CREDENTIALS=str(cred))
            def command(args,**kwargs):
                if args[0]=='gcloud':return m.ACCOUNT
                if args[:2]==['helm','list']:return '[]'
                if args[:2]==['helm','template']:return '[]'
                if args[:2]==['helm','install']:raise RuntimeError('SIMULATED_INSTALL_FAILURE')
                raise AssertionError(args)
            def kube(*args,**kwargs):
                if args[:2]==('auth','whoami'):return json.dumps({'status':{'userInfo':{'username':m.ACCOUNT}}})
                if args[:2]==('auth','can-i'):return 'no'
                raise AssertionError(args)
            def reader(kind,namespace=None):
                if kind=='namespace jitsi-load-test':return {'metadata':{'name':'jitsi-load-test'}}
                if kind=='pods':return {'items':[]}
                raise AssertionError(kind)
            pods={'jvb':{'component':'jvb','uid':'a','restarts':0}}
            with patch.dict(os.environ,env),patch.object(m,'verify_load_render'),patch.object(m,'guard'),patch.object(m,'run',side_effect=command),patch.object(m,'kubectl',side_effect=kube),patch.object(m,'read',side_effect=reader),patch.object(m,'production',return_value=pods),patch.object(m,'capacity'),patch.object(m,'https'),patch.object(m,'forward'),patch.object(m,'stats',return_value={'conferences':0,'participants':0,'local_active_endpoints':0}),patch.object(m,'cleanup') as clean:
                with self.assertRaises(RuntimeError):m.execute('malleus')
                clean.assert_called_once()
                summary=json.loads((m.folder()/'summary.json').read_text())
                self.assertFalse(summary['success']);self.assertTrue(summary['cleanup'])


    def test_merged_helm_profile_and_network_mutations(self):
        import subprocess
        rendered = subprocess.check_output(['helm','template','m2-test','charts/jitsi-load-test','-n','jitsi-load-test',
                    '-f','tests/load/values-video-2x90.yaml','-f','tests/load/values-video-2x90-low-cpu.yaml'],text=True)
        docs = [d for d in yaml.safe_load_all(rendered) if d]
        m.verify_load_render(docs,'m2-test')
        service = next(d for d in docs if d['kind']=='Service')
        service['spec']['type']='LoadBalancer'
        with self.assertRaises(RuntimeError):m.verify_load_render(docs,'m2-test')
        service['spec']['type']='ClusterIP'
        job = next(d for d in docs if d['kind']=='Job')
        job['spec']['suspend']=False
        with self.assertRaises(RuntimeError):m.verify_load_render(docs,'m2-test')


    def test_chaos_recovery_alone_is_not_injection_evidence(self):
        self.assertFalse(m.injection_verified({}))
        s={'conditions':[{'type':'AllInjected','status':'True'}], 'experiment':{'containerRecords':[{'phase':'Injected','injectedCount':1}]}}
        self.assertTrue(m.injection_verified(s))
        s['experiment']['containerRecords'][0]['injectedCount']=0
        self.assertFalse(m.injection_verified(s))
        s['experiment']['containerRecords'][0]['injectedCount']=2
        with self.assertRaises(RuntimeError):m.injection_verified(s)
