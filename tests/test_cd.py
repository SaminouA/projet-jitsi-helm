"""Tests locaux des garde-fous CD. Donnees synthetiques, aucun acces cloud."""
import base64
import copy
import importlib.util
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cd_check', ROOT / 'scripts/check-cd-render.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CDGuardTests(unittest.TestCase):
    def setUp(self):
        # IP RFC 5737 : seulement une fixture hors reseau, jamais un deploiement.
        self.ip = '192.0.2.1'
        self.values = {c: {'xmpp': {'password': 'fixture-' + c}} for c in ['jicofo', 'jvb']}
        meta = lambda name: {'name': name, 'labels': {'app.kubernetes.io/instance': 'jitsi'},
                             'annotations': {'meta.helm.sh/release-name': 'jitsi',
                                             'meta.helm.sh/release-namespace': 'jitsi'}}
        self.render = [
            {'kind': 'Service', 'metadata': meta('jitsi-jitsi-meet-jvb'),
             'spec': {'type': 'LoadBalancer', 'ports': [{'port': 10000, 'protocol': 'UDP', 'targetPort': 'rtp-udp-0'}]}},
            {'kind': 'Deployment', 'metadata': meta('jitsi-jitsi-meet-jvb-0'),
             'spec': {'replicas': 1, 'template': {'spec': {'containers': [{'env': [
                 {'name': 'JVB_ADVERTISE_IPS', 'value': self.ip}]}]}}}},
        ]
        self.live = {}
        for d in self.render:
            key = ('services' if d['kind'] == 'Service' else 'deployments.apps', d['metadata']['name'])
            self.live[key] = copy.deepcopy(d)
        self.live['services', 'jitsi-jitsi-meet-jvb']['status'] = {'loadBalancer': {'ingress': [{'ip': self.ip}]}}
        self.live['deployments.apps', 'jitsi-jitsi-meet-jvb-0']['metadata']['generation'] = 2
        self.live['deployments.apps', 'jitsi-jitsi-meet-jvb-0']['status'] = {'readyReplicas': 1, 'observedGeneration': 2}
        for component in ['jicofo', 'jvb']:
            key = 'JICOFO_AUTH_PASSWORD' if component == 'jicofo' else 'JVB_AUTH_PASSWORD'
            self.live['secrets', 'jitsi-jitsi-meet-' + component + '-secret'] = {
                'data': {key: base64.b64encode(self.values[component]['xmpp']['password'].encode()).decode()}}

    def getter(self, kind, name):
        if (kind, name) not in self.live:
            raise SystemExit('Ressource absente : fixture')
        return self.live[kind, name]

    def verify(self, after=False):
        module.verify(self.render, self.values, self.getter, after)

    def test_existing_release_and_consistent_values(self):
        self.verify()
        self.verify(after=True)

    def test_rotation_rejected_without_password_in_error(self):
        self.values['jvb']['xmpp']['password'] = 'changed-fixture-value'
        with self.assertRaises(SystemExit) as error:
            self.verify()
        self.assertNotIn('changed-fixture-value', str(error.exception))

    def test_unexpected_secret_fields_rejected(self):
        self.values['jvb']['extraEnvs'] = {'UNEXPECTED': 'fixture'}
        with self.assertRaises(SystemExit):
            self.verify()

    def test_new_resource_rejected(self):
        self.render[0]['metadata']['name'] = 'new-service'
        with self.assertRaises(SystemExit):
            self.verify()

    def test_other_release_rejected(self):
        self.live['services', 'jitsi-jitsi-meet-jvb']['metadata']['annotations']['meta.helm.sh/release-name'] = 'other'
        with self.assertRaises(SystemExit):
            self.verify()

    def test_service_port_change_rejected(self):
        self.render[0]['spec']['ports'][0]['port'] = 10001
        with self.assertRaises(SystemExit):
            self.verify()

    def test_ip_mismatch_rejected(self):
        self.live['services', 'jitsi-jitsi-meet-jvb']['status']['loadBalancer']['ingress'][0]['ip'] = '192.0.2.2'
        with self.assertRaises(SystemExit):
            self.verify()

    def test_unready_workload_rejected(self):
        self.live['deployments.apps', 'jitsi-jitsi-meet-jvb-0']['status']['readyReplicas'] = 0
        with self.assertRaises(SystemExit):
            self.verify(after=True)

    def test_workflow_trust_boundary(self):
        workflow = yaml.load((ROOT / '.github/workflows/deploy-gke.yml').read_text(), Loader=yaml.BaseLoader)
        trigger = workflow['on']['workflow_run']
        self.assertEqual(trigger, {'workflows': ['Validation Helm et Terraform'], 'types': ['completed'], 'branches': ['main']})
        job = workflow['jobs']['deploy']
        for guard in ["conclusion == 'success'", "event == 'push'", "head_branch == 'main'",
                      'head_repository.full_name == github.repository',
                      'repository.full_name == github.repository', "vars.GKE_CD_ENABLED == 'true'"]:
            self.assertIn(guard, job['if'])
        self.assertEqual(job['permissions'], {'contents': 'read', 'id-token': 'write'})
        self.assertEqual(workflow['concurrency']['cancel-in-progress'], 'false')
        checkout = next(s for s in job['steps'] if s.get('uses', '').startswith('actions/checkout@'))
        self.assertEqual(checkout['with']['ref'], '${{ github.event.workflow_run.head_sha }}')
        self.assertEqual(checkout['with']['persist-credentials'], 'false')
        for step in job['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')
                self.assertNotIn('download-artifact', step['uses'])


class WorkflowEventTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('cd_event', ROOT / 'scripts/check-cd-event.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.sha = 'a' * 40
        self.env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_run',
                    'GITHUB_REPOSITORY': 'SaminouA/projet-jitsi-helm', 'CD_ENABLE': 'true',
                    'EXPECTED_SHA': self.sha, 'GITHUB_REF': 'refs/heads/default-workflow-branch'}
        self.payload = {'repository': {'full_name': 'SaminouA/projet-jitsi-helm'}, 'workflow_run': {
            'repository': {'full_name': 'SaminouA/projet-jitsi-helm'},
            'head_repository': {'full_name': 'SaminouA/projet-jitsi-helm'},
            'name': 'Validation Helm et Terraform', 'event': 'push', 'status': 'completed',
            'conclusion': 'success', 'head_branch': 'main', 'head_sha': self.sha}}

    def test_validated_run_controls_branch_not_github_ref(self):
        self.assertEqual(self.module.verify_event(self.payload, self.env), self.sha)

    def test_untrusted_or_failed_run_rejected(self):
        for field, value in [('event', 'pull_request'), ('head_branch', 'feature/untrusted'),
                             ('conclusion', 'failure'), ('status', 'in_progress'),
                             ('head_sha', 'b' * 40), ('name', 'Other workflow'),
                             ('head_repository', {'full_name': 'fork/other'}),
                             ('repository', {'full_name': 'fork/other'})]:
            with self.subTest(field=field):
                payload = copy.deepcopy(self.payload)
                payload['workflow_run'][field] = value
                with self.assertRaises(SystemExit):
                    self.module.verify_event(payload, self.env)

    def test_wrong_event_disabled_or_wrong_repo_rejected(self):
        for field, value in [('GITHUB_EVENT_NAME', 'push'), ('CD_ENABLE', 'false'),
                             ('GITHUB_REPOSITORY', 'fork/other'), ('EXPECTED_SHA', 'not-a-sha')]:
            with self.subTest(field=field):
                env = dict(self.env, **{field: value})
                with self.assertRaises(SystemExit):
                    self.module.verify_event(self.payload, env)
        self.payload['repository']['full_name'] = 'fork/other'
        with self.assertRaises(SystemExit):
            self.module.verify_event(self.payload, self.env)

    def test_shell_arguments_and_workflow_test_command(self):
        script = (ROOT / 'scripts/deploy-gke.sh').read_text()
        # shlex verifie les frontieres des arguments, que bash -n ne detecte pas.
        for line in script.splitlines():
            if 'kubectl auth can-i' in line:
                tokens = shlex.split(line)
                self.assertIn('$resource', tokens)
                self.assertIn('-n', tokens)
            if "quiet 'mise a jour Helm'" in line:
                tokens = shlex.split(line.rstrip('\\'))
                self.assertEqual(tokens[tokens.index('--install') + 1], '$release')
            if 'Commit main depasse' in line:
                self.assertIn('echo Commit main depasse', ' '.join(shlex.split(line)))
        workflow = yaml.load((ROOT / '.github/workflows/deploy-gke.yml').read_text(), Loader=yaml.BaseLoader)
        steps = workflow['jobs']['deploy']['steps']
        run = next(s['run'] for s in steps if 'unittest discover' in s.get('run', ''))
        self.assertIn('python3 -m unittest discover -s tests -p test_cd.py -v', run)
        self.assertIn('for verb in get list watch create update patch delete;', script)

    def test_missing_delete_stops_before_secret_or_deployment(self):
        # Executer les gardes Bash avec uniquement des faux outils locaux.
        # Aucun kubectl, gh, helm ou sops reel n'est appele.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            event = tmp / 'event.json'
            event.write_text(json.dumps(self.payload))
            driver = tmp / 'driver'
            driver.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['MOCK_LOG'], 'a') as f: f.write(json.dumps([name, args]) + '\\n')
if name in ('git', 'gh'): print('a' * 40)
elif name == 'kubectl':
    if args[:2] == ['config', 'current-context']:
        print('gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster')
    elif args[:2] == ['auth', 'whoami']:
        print(json.dumps({'status': {'userInfo': {'username': 'github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com'}}}))
    elif args[:2] == ['auth', 'can-i']:
        assert len(args) == 6 and args[4:] == ['-n', 'jitsi']
        print('no' if args[2] == 'delete' else 'yes')
    else: sys.exit(98)
else: sys.exit(99)
""")
            driver.chmod(0o700)
            for command in ['git', 'gh', 'kubectl', 'helm', 'sops']:
                (tmp / command).symlink_to(driver)
            env = dict(os.environ, **self.env, GITHUB_EVENT_PATH=str(event),
                       MOCK_LOG=str(tmp / 'calls.jsonl'), PATH=str(tmp) + os.pathsep + os.environ['PATH'])
            result = subprocess.run(['bash', str(ROOT / 'scripts/deploy-gke.sh')], cwd=ROOT,
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Permission RBAC manquante : delete configmaps', result.stderr)
            calls = [json.loads(l) for l in (tmp / 'calls.jsonl').read_text().splitlines()]
            self.assertFalse(any(name in ('sops', 'helm') for name, args in calls))


if __name__ == '__main__':
    unittest.main()
