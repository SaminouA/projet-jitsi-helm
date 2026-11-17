"""Auth CD : outils distants simules, aucune modification du cluster."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cd_auth', ROOT / 'scripts/configure-cd-gke.py')
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)


class CDAuthTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a' * 40
        self.env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_run',
                    'GITHUB_REPOSITORY': cd.auth.REPO, 'CD_ENABLE': 'true',
                    'EXPECTED_SHA': self.sha, 'JITSI_ACCESS_PROFILE': 'public-edge',
                    'JITSI_EDGE_CD_ENABLED': 'true', 'JITSI_PUBLIC_DOMAIN': cd.auth.DOMAIN,
                    'JITSI_EDGE_ADDRESS_NAME': 'jitsi-edge-ip'}
        self.payload = {'repository': {'full_name': cd.auth.REPO}, 'workflow_run': {
            'repository': {'full_name': cd.auth.REPO}, 'head_repository': {'full_name': cd.auth.REPO},
            'name': cd.event.CI_NAME, 'event': 'push', 'status': 'completed',
            'conclusion': 'success', 'head_branch': 'main', 'head_sha': self.sha}}

    def guard(self, folder, env=None, payload=None, outputs=None):
        path = folder / 'event.json'
        path.write_text(json.dumps(payload or self.payload))
        with patch.dict(os.environ, dict(env or self.env, GITHUB_EVENT_PATH=str(path)), clear=True), \
             patch.object(cd.auth, 'read_command', side_effect=outputs or [self.sha, self.sha]) as read:
            self.read_mock = read
            cd.guard_cd()
            return read

    def test_trusted_main_and_localhost_are_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            for profile in ('public-edge', 'localhost'):
                self.guard(Path(tmp), env=dict(self.env, JITSI_ACCESS_PROFILE=profile))

    def test_disabled_or_absent_flag_never_reaches_cloud(self):
        with tempfile.TemporaryDirectory() as tmp:
            for flag in (None, '', 'false', 'TRUE', '1'):
                env = self.env.copy()
                if flag is None: env.pop('CD_ENABLE')
                else: env['CD_ENABLE'] = flag
                with self.assertRaises(SystemExit): self.guard(Path(tmp), env=env)
                self.read_mock.assert_not_called()

    def test_untrusted_ci_and_stale_main_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for field, value in [('event', 'pull_request'), ('conclusion', 'failure'),
                                 ('head_branch', 'feature/other'), ('head_repository', {'full_name': 'fork/other'})]:
                payload = copy.deepcopy(self.payload); payload['workflow_run'][field] = value
                with self.assertRaises(SystemExit): self.guard(Path(tmp), payload=payload)
            for values in [['b' * 40, self.sha], [self.sha, 'b' * 40]]:
                with self.assertRaisesRegex(SystemExit, 'SHA main depasse'):
                    self.guard(Path(tmp), outputs=values)

    def test_public_profile_must_be_explicit_and_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            for key, value in [('JITSI_ACCESS_PROFILE', ''), ('JITSI_EDGE_CD_ENABLED', 'false'),
                               ('JITSI_PUBLIC_DOMAIN', 'other.invalid'), ('JITSI_EDGE_ADDRESS_NAME', 'other')]:
                with self.assertRaises(SystemExit): self.guard(Path(tmp), env=dict(self.env, **{key: value}))

    def test_cd_uses_shared_private_exec_configuration_and_cd_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            event_path = root / 'event.json'; event_path.write_text(json.dumps(self.payload))
            env = dict(self.env, GITHUB_EVENT_PATH=str(event_path), RUNNER_TEMP=str(root),
                       KUBECONFIG=str(root / 'jitsi-cd-kubeconfig'), GITHUB_ENV=str(root / 'github-env'),
                       USE_GKE_GCLOUD_AUTH_PLUGIN='True', CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS='true')
            calls = []
            def fake(label, args):
                calls.append(args)
                if args[0] in ('git', 'gh'): return self.sha
                if args == cd.auth.GKE_CREDENTIALS: return 'private-output'
                fields = {cd.auth.AUTH_FIELDS['provider']: '', cd.auth.AUTH_FIELDS['command']: 'gke-gcloud-auth-plugin',
                          cd.auth.AUTH_FIELDS['api']: 'client.authentication.k8s.io/v1beta1',
                          cd.auth.AUTH_FIELDS['args']: '["--use_application_default_credentials"]'}
                return fields[args[-1]]
            with patch.dict(os.environ, env, clear=True), patch.object(cd.auth, 'read_command', side_effect=fake):
                cd.main()
                self.assertEqual(Path(env['KUBECONFIG']).stat().st_mode & 0o777, 0o600)
                with self.assertRaisesRegex(SystemExit, 'details sensibles non publies'): cd.main()
            self.assertEqual(sum(args == cd.auth.GKE_CREDENTIALS for args in calls), 1)
            self.assertIn('KUBECONFIG=' + env['KUBECONFIG'], Path(env['GITHUB_ENV']).read_text())

    def test_workflow_selects_exec_adc_with_cleanup_and_no_legacy(self):
        w = yaml.load((ROOT / '.github/workflows/deploy-gke.yml').read_text(), Loader=yaml.BaseLoader)
        j = w['jobs']['deploy']; steps = j['steps']
        self.assertIn("vars.GKE_CD_ENABLED == 'true'", j['if'])
        self.assertEqual(w['permissions'], {})
        self.assertEqual(j['permissions'], {'contents': 'read', 'id-token': 'write'})
        self.assertNotIn('KUBECONFIG', j['env'])
        self.assertEqual(j['env']['CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS'], 'true')
        self.assertEqual(j['env']['USE_GKE_GCLOUD_AUTH_PLUGIN'], 'True')
        self.assertFalse(any('get-gke-credentials@' in s.get('uses', '') for s in steps))
        config = next(i for i,s in enumerate(steps) if s.get('run') == 'python3 scripts/configure-cd-gke.py')
        deploy = next(i for i,s in enumerate(steps) if s.get('run') == 'bash scripts/deploy-gke.sh')
        self.assertLess(config, deploy)
        self.assertEqual(steps[config]['env']['KUBECONFIG'], '${{ runner.temp }}/jitsi-cd-kubeconfig')
        self.assertEqual(steps[-1]['if'], '${{ always() }}')
        self.assertIn('rm -f -- "$KUBECONFIG"', steps[-1]['run'])
        self.assertIn('"$RUNNER_TEMP"/jitsi-cd-kubeconfig', steps[-1]['run'])
