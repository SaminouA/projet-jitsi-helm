"""Diagnostic simule : aucun runner distant, compte cloud ou secret reel."""
import importlib.util
import json
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diag = load('diagnostic', 'scripts/diagnose-cd.py')
apis = load('api_check', 'scripts/check-gcp-apis.py')


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a' * 40
        self.env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
                    'GITHUB_REPOSITORY': diag.REPO, 'GITHUB_REF': 'refs/heads/main',
                    'GITHUB_SHA': self.sha, 'EXPECTED_SHA': self.sha,
                    'JITSI_ACCESS_PROFILE': 'public-edge'}
        self.payload = {'repository': {'full_name': diag.REPO},
                        'inputs': {'confirm_read_only': 'true'}}

    def test_dispatch_exact_main_accepted(self):
        diag.verify_guard(self.env, self.payload, self.sha, self.sha)

    def test_untrusted_context_or_stale_main_rejected(self):
        for key, value in [('GITHUB_EVENT_NAME', 'push'), ('GITHUB_REF', 'refs/heads/feature/x'),
                           ('GITHUB_REPOSITORY', 'fork/repo'), ('EXPECTED_SHA', 'bad'),
                           ('GITHUB_SHA', 'b' * 40), ('JITSI_ACCESS_PROFILE', 'localhost')]:
            with self.subTest(key=key):
                with self.assertRaises(SystemExit):
                    diag.verify_guard(dict(self.env, **{key: value}), self.payload, self.sha, self.sha)
        for main, local in [('b' * 40, self.sha), (self.sha, 'b' * 40)]:
            with self.assertRaises(SystemExit):
                diag.verify_guard(self.env, self.payload, main, local)
        for inputs in [{}, {'confirm_read_only': 'false'}]:
            p = dict(self.payload, inputs=inputs)
            with self.assertRaises(SystemExit): diag.verify_guard(self.env, p, self.sha, self.sha)

    def test_api_missing_is_reported_without_activation(self):
        self.assertEqual(apis.missing_apis(apis.REQUIRED), [])
        missing = apis.missing_apis(apis.REQUIRED - {'sts.googleapis.com', 'cloudresourcemanager.googleapis.com'})
        self.assertEqual(missing, ['cloudresourcemanager.googleapis.com', 'sts.googleapis.com'])

    def test_rbac_requires_named_pvc_only(self):
        queries = []
        self.assertEqual(diag.check_rbac(lambda v, r: queries.append((v, r)) or True), 49)
        self.assertEqual([x for x in queries if 'persistentvolumeclaims' in x[1]],
                         [('get', 'persistentvolumeclaims/jitsi-edge-data')])
        with self.assertRaises(SystemExit):
            diag.check_rbac(lambda v, r: r != 'persistentvolumeclaims/jitsi-edge-data')

    def test_mutating_commands_are_rejected_before_execution(self):
        for args in [['helm', 'upgrade', 'jitsi'], ['helm', 'install', 'x'],
                     ['kubectl', 'apply', '-f', 'x'], ['kubectl', 'delete', 'pods'],
                     ['gcloud', 'services', 'enable', 'sts.googleapis.com'],
                     ['gh', 'api', '--method', 'POST', 'repos/x/actions/workflows/x/dispatches']]:
            with self.subTest(args=args), patch.object(diag.subprocess, 'run') as run:
                with self.assertRaises(SystemExit): diag.read_command('test', args)
                run.assert_not_called()

    def test_sensitive_errors_are_not_published(self):
        failed = subprocess.CompletedProcess([], 1, stdout='fixture-password', stderr='fixture-token')
        with patch.object(diag.subprocess, 'run', return_value=failed):
            with self.assertRaises(SystemExit) as error:
                diag.read_command('dechiffrement SOPS/KMS', ['sops', '--decrypt', 'fixture'])
        self.assertNotIn('fixture-password', str(error.exception))
        self.assertNotIn('fixture-token', str(error.exception))

    def simulated_run(self, directory, fail_sops=False):
        calls = []
        temp = Path(directory)
        env_file = temp / 'github-env'
        def fake(label, args):
            calls.append(args)
            if args[:3] == ['kubectl', 'config', 'current-context']: return diag.CONTEXT
            if args[:3] == ['kubectl', 'config', 'view']:
                metadata = {diag.AUTH_FIELDS['provider']: '',
                            diag.AUTH_FIELDS['command']: 'gke-gcloud-auth-plugin',
                            diag.AUTH_FIELDS['api']: 'client.authentication.k8s.io/v1beta1',
                            diag.AUTH_FIELDS['args']: '["--use_application_default_credentials"]'}
                return metadata.get(args[-1], 'https://192.0.2.10')
            if args[:3] == ['kubectl', 'auth', 'whoami']:
                return json.dumps({'status': {'userInfo': {'username': diag.ACCOUNT}}})
            if args[:3] == ['kubectl', 'auth', 'can-i']: return 'yes'
            if args[:2] == ['helm', 'list']:
                return json.dumps([{'name': n, 'status': 'deployed'} for n in ['jitsi', 'jitsi-edge']])
            if args[:2] == ['sops', '--decrypt']:
                if fail_sops: raise SystemExit('Echec diagnostic : SOPS')
                Path(args[args.index('--output') + 1]).write_text('fixture: private')
                return ''
            if args[:4] == ['kubectl', '-n', 'jitsi', 'get']:
                if args[4] == 'configmaps':
                    return json.dumps({'items': [{'data': {'PUBLIC_URL': 'https://' + diag.DOMAIN}}]})
                if args[4] == 'configmap':
                    return json.dumps({'data': {'Caddyfile': 'acme_ca https://acme-v02.api.letsencrypt.org/directory'}})
                return json.dumps({'status': {'loadBalancer': {'ingress': [{'ip': '34.62.165.81'}]}}})
            return ''
        with patch.dict(os.environ, RUNNER_TEMP=str(temp), GITHUB_ENV=str(env_file)), \
             patch.object(diag, 'guard'), patch.object(diag, 'read_command', side_effect=fake), \
             patch.object(diag.shutil, 'which', return_value='/fixture/gke-gcloud-auth-plugin'), \
             patch.object(diag, 'probe_api_tcp', return_value='OK'), \
             patch('sys.stdout', new_callable=io.StringIO):
            if fail_sops:
                with self.assertRaises(SystemExit): diag.diagnose()
            else:
                diag.diagnose()
        self.assertFalse(list(temp.glob('jitsi-diagnostic.*')))
        return calls

    def test_simulated_success_and_private_cleanup(self):
        with tempfile.TemporaryDirectory() as directory: calls = self.simulated_run(directory)
        self.assertTrue(any(c[:2] == ['sops', '--decrypt'] for c in calls))
        self.assertFalse(any(c[:2] in [['helm', 'upgrade'], ['kubectl', 'apply']] for c in calls))

    def test_sops_failure_cleans_temporary_data_and_stops(self):
        with tempfile.TemporaryDirectory() as directory: calls = self.simulated_run(directory, fail_sops=True)
        self.assertFalse(any(c[:2] == ['helm', 'lint'] for c in calls))

    def test_workflow_is_manual_main_pinned_and_has_no_deployment(self):
        w = yaml.safe_load((ROOT / '.github/workflows/diagnose-gke.yml').read_text())
        self.assertEqual(set(w['on']), {'workflow_dispatch'})
        self.assertFalse(w['on']['workflow_dispatch']['inputs']['confirm_read_only']['default'])
        j = w['jobs']['diagnose']
        self.assertIn("github.ref == 'refs/heads/main'", j['if'])
        self.assertIn("github.repository == 'SaminouA/projet-jitsi-helm'", j['if'])
        self.assertEqual(j['permissions'], {'contents': 'read', 'id-token': 'write'})
        self.assertEqual(w['concurrency']['group'], 'deploy-jitsi-gke-main')
        auth = next(i for i,s in enumerate(j['steps']) if 'google-github-actions/auth@' in s.get('uses',''))
        guard = next(i for i,s in enumerate(j['steps']) if '--guard-only' in s.get('run',''))
        self.assertLess(guard, auth)
        for step in j['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')
                self.assertNotIn('upload-artifact', step['uses'])
            self.assertNotRegex(step.get('run', ''), r'helm\s+(upgrade|install)|kubectl\s+(apply|delete)|sops\s+--decrypt')
        for run in [s['run'] for s in j['steps'] if s.get('shell') == 'bash']:
            p = subprocess.run(['bash', '-n'], input=run, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_pvc_role_is_additive_and_scoped(self):
        role, binding = list(yaml.safe_load_all((ROOT / 'deploy/cd-pvc-reader.yaml').read_text()))
        self.assertEqual(role['metadata']['namespace'], 'jitsi')
        self.assertNotEqual(role['metadata']['name'], 'github-jitsi-deployer')
        self.assertEqual(role['rules'], [{'apiGroups':[''], 'resources':['persistentvolumeclaims'],
                         'resourceNames':['jitsi-edge-data'], 'verbs':['get']}])
        self.assertEqual(binding['roleRef']['name'], role['metadata']['name'])
        self.assertEqual(binding['subjects'][0]['name'], diag.ACCOUNT)

    def test_cd_profiles_are_explicit_and_local_is_overridden(self):
        w = yaml.load((ROOT / '.github/workflows/deploy-gke.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(w['jobs']['deploy']['env']['JITSI_ACCESS_PROFILE'], '${{ vars.JITSI_ACCESS_PROFILE }}')
        script = (ROOT / 'scripts/deploy-gke.sh').read_text()
        self.assertIn('JITSI_ACCESS_PROFILE:?', script)
        self.assertIn('localhost) profile_values=(--set-string publicURL=http://localhost:8081)', script)
        self.assertIn('persistentvolumeclaims/jitsi-edge-data', script)


    def test_identity_error_categories_never_include_input(self):
        samples = [
            ('no Auth Provider found for name "gcp"', 'AUTH_PROVIDER_LEGACY'),
            ('exec: executable gke-gcloud-auth-plugin not found', 'PLUGIN_ABSENT'),
            ('getting credentials: exec: executable gke-gcloud-auth-plugin failed with exit code 1', 'PLUGIN_EXECUTION'),
            ('invalid_grant: fixture-token', 'AUTHENTIFICATION_CREDENTIALS'),
            ('Error from server (Unauthorized): fixture-token', 'AUTHENTIFICATION_401'),
            ('Error from server (Forbidden): selfsubjectreviews cannot create', 'RBAC_403'),
            ('x509: certificate signed by unknown authority', 'RESEAU_TLS'),
            ('dial tcp: lookup cluster.example: no such host', 'RESEAU_DNS'),
            ('dial tcp: i/o timeout', 'RESEAU_TIMEOUT'),
            ('dial tcp: connection refused', 'RESEAU_CONNEXION_REFUSEE'),
            ('dial tcp: no route to host', 'RESEAU_TRANSPORT'),
            ('unexpected fixture-password fixture-token', 'INDETERMINE'),
        ]
        for message, category in samples:
            with self.subTest(category=category):
                self.assertEqual(diag.identity_error_category(message), category)
                failure = subprocess.CompletedProcess([], 1, 'fixture-password', message)
                with patch.object(diag.subprocess, 'run', return_value=failure):
                    with self.assertRaises(SystemExit) as error:
                        diag.read_command('identite GKE', ['kubectl', 'auth', 'whoami', '-o', 'json'])
                self.assertEqual(str(error.exception), 'Diagnostic identite GKE : ' + category)

    def test_plugin_absent_stops_before_commands_or_network(self):
        with patch.object(diag.shutil, 'which', return_value=None), \
             patch.object(diag, 'read_command') as command, \
             patch.object(diag, 'probe_api_tcp') as network:
            with self.assertRaisesRegex(SystemExit, 'PLUGIN_ABSENT'): diag.check_identity()
            command.assert_not_called()
            network.assert_not_called()

    def test_plugin_failure_and_timeout_are_redacted(self):
        args = ['gke-gcloud-auth-plugin', '--version']
        for result in [subprocess.CompletedProcess(args, 1, 'fixture-secret', 'fixture-token'),
                       subprocess.TimeoutExpired(args, 10, output='fixture-secret', stderr='fixture-token'),
                       OSError('fixture-secret')]:
            with self.subTest(result=type(result).__name__):
                kwargs = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
                with patch.object(diag.subprocess, 'run', **kwargs):
                    with self.assertRaises(SystemExit) as error: diag.read_command('controle plugin', args)
                self.assertIn(str(error.exception), ['Diagnostic identite GKE : PLUGIN_EXECUTION',
                                                   'Diagnostic identite GKE : PLUGIN_TIMEOUT'])
                self.assertNotIn('fixture', str(error.exception))

    def test_network_probe_categories_and_invalid_config(self):
        failures = [(diag.socket.gaierror('fixture-token'), 'RESEAU_DNS'),
                    (TimeoutError('fixture-token'), 'RESEAU_TIMEOUT'),
                    (ConnectionRefusedError('fixture-token'), 'RESEAU_CONNEXION_REFUSEE'),
                    (OSError('fixture-token'), 'RESEAU_TRANSPORT')]
        for error, expected in failures:
            with patch.object(diag.socket, 'create_connection', side_effect=error):
                self.assertEqual(diag.probe_api_tcp('https://192.0.2.10'), expected)
        for url in ['http://192.0.2.10', 'https://user:fixture-token@cluster.example',
                    'https://cluster.example/path', 'https://cluster.example?token=fixture',
                    'https://[broken', 'https://cluster.example:bad']:
            with self.subTest(url=url), patch.object(diag.socket, 'create_connection') as connect:
                self.assertEqual(diag.probe_api_tcp(url), 'CONFIG_ENDPOINT_INVALIDE')
                connect.assert_not_called()

    def test_network_tcp_success_is_not_an_authentication_test(self):
        with patch.object(diag.socket, 'create_connection') as connect:
            self.assertEqual(diag.probe_api_tcp('https://192.0.2.10:443'), 'OK')
            connect.assert_called_once_with(('192.0.2.10', 443), timeout=5)

    def test_identity_timeout_and_malformed_response_are_redacted(self):
        args = ['kubectl', 'auth', 'whoami', '-o', 'json']
        with patch.object(diag.subprocess, 'run', side_effect=subprocess.TimeoutExpired(args, 30, output='fixture-token')):
            with self.assertRaisesRegex(SystemExit, 'DELAI_INDETERMINE'): diag.read_command('identite GKE', args)
        with patch.object(diag.shutil, 'which', return_value='/fixture/plugin'), \
             patch.object(diag, 'probe_api_tcp', return_value='OK'), \
             patch.object(diag, 'verify_exec_kubeconfig'), \
             patch.object(diag, 'read_command', side_effect=['version-not-printed', 'https://192.0.2.10', 'fixture-token']), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            with self.assertRaisesRegex(SystemExit, 'REPONSE_INVALIDE'): diag.check_identity()
            self.assertNotIn('fixture-token', output.getvalue())
            self.assertNotIn('version-not-printed', output.getvalue())

    def test_tcp_failure_does_not_override_authoritative_whoami_success(self):
        identity = json.dumps({'status': {'userInfo': {'username': diag.ACCOUNT}}})
        with patch.object(diag.shutil, 'which', return_value='/fixture/plugin'), \
             patch.object(diag, 'probe_api_tcp', return_value='RESEAU_TIMEOUT'), \
             patch.object(diag, 'verify_exec_kubeconfig'), \
             patch.object(diag, 'read_command', side_effect=['version-not-printed', 'https://192.0.2.10', identity]) as command, \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            diag.check_identity()
            self.assertIn('CONFIRMEE', output.getvalue())
            self.assertNotIn(diag.ACCOUNT, output.getvalue())
            self.assertNotIn('192.0.2.10', output.getvalue())
            self.assertIn('--request-timeout=15s', command.call_args.args[1])

    def test_wrong_identity_rejected_without_printing_it(self):
        value = json.dumps({'status': {'userInfo': {'username': 'fixture-sensitive-user'}}})
        with patch.object(diag.shutil, 'which', return_value='/fixture/plugin'), \
             patch.object(diag, 'probe_api_tcp', return_value='OK'), \
             patch.object(diag, 'verify_exec_kubeconfig'), \
             patch.object(diag, 'read_command', side_effect=['version', 'https://192.0.2.10', value]), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            with self.assertRaisesRegex(SystemExit, 'IDENTITE_INATTENDUE'): diag.check_identity()
            self.assertNotIn('fixture-sensitive-user', output.getvalue())

    def test_identity_failure_stops_before_rbac_or_sops(self):
        with patch.object(diag, 'guard'), patch.object(diag, 'read_command', return_value=diag.CONTEXT), \
             patch.object(diag, 'check_identity', side_effect=SystemExit('Diagnostic identite GKE : INDETERMINE')), \
             patch.object(diag, 'check_rbac') as rbac, patch.object(diag.tempfile, 'TemporaryDirectory') as tmp:
            with self.assertRaises(SystemExit): diag.diagnose()
            rbac.assert_not_called()
            tmp.assert_not_called()


    def test_exec_metadata_requires_modern_plugin_with_adc(self):
        for version in ['client.authentication.k8s.io/v1', 'client.authentication.k8s.io/v1beta1']:
            diag.verify_exec_metadata('', '/fixture/bin/gke-gcloud-auth-plugin', version,
                                      ['--use_application_default_credentials'])
        for provider, command, api_version, args in [
            ('gcp', '', '', []), ('gcp', 'gke-gcloud-auth-plugin', 'client.authentication.k8s.io/v1', []),
            ('', 'other-plugin', 'client.authentication.k8s.io/v1', []),
            ('', 'gke-gcloud-auth-plugin', 'client.authentication.k8s.io/v1alpha1', []),
            ('', 'gke-gcloud-auth-plugin', 'client.authentication.k8s.io/v1', ['fixture-token']),
        ]:
            with self.subTest(provider=provider), self.assertRaises(SystemExit) as error:
                diag.verify_exec_metadata(provider, command, api_version, args)
            self.assertNotIn('fixture-token', str(error.exception))

    def test_exec_mode_check_never_exports_full_kubeconfig(self):
        values = ['', 'gke-gcloud-auth-plugin', 'client.authentication.k8s.io/v1beta1',
                  '["--use_application_default_credentials"]']
        with patch.object(diag, 'read_command', side_effect=values) as read, \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            diag.verify_exec_kubeconfig()
            self.assertEqual(output.getvalue(), 'Diagnostic auth GKE : EXEC_ADC\n')
        self.assertEqual(len(read.call_args_list), 4)
        for call in read.call_args_list:
            self.assertEqual(call.args[1][:5], ['kubectl', 'config', 'view', '--minify', '-o'])
            self.assertIn(call.args[1][-1], diag.AUTH_FIELDS.values())
            self.assertNotIn('--raw', call.args[1])
        with patch.object(diag, 'read_command', side_effect=['gcp', '', '', '[]']), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            with self.assertRaisesRegex(SystemExit, 'AUTH_PROVIDER_LEGACY'):
                diag.verify_exec_kubeconfig()
            self.assertEqual(output.getvalue(), '')

    def configure_environment(self, root):
        return {'RUNNER_TEMP': str(root), 'KUBECONFIG': str(root / 'jitsi-diagnostic-kubeconfig'),
                'GITHUB_ENV': str(root / 'github-env'),
                'USE_GKE_GCLOUD_AUTH_PLUGIN': 'True',
                'CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS': 'true'}

    def test_configure_gke_only_writes_private_runner_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            env = self.configure_environment(root)
            calls = []
            def fake(label, args):
                calls.append(args)
                if args == diag.GKE_CREDENTIALS:
                    Path(env['KUBECONFIG']).write_text('fixture: private runner config')
                    return 'fixture-sensitive-tool-output'
                values = {diag.AUTH_FIELDS['provider']: '', diag.AUTH_FIELDS['command']: 'gke-gcloud-auth-plugin',
                          diag.AUTH_FIELDS['api']: 'client.authentication.k8s.io/v1beta1',
                          diag.AUTH_FIELDS['args']: '["--use_application_default_credentials"]'}
                return values[args[-1]]
            with patch.dict(os.environ, env), patch.object(diag, 'guard') as guard, \
                 patch.object(diag, 'read_command', side_effect=fake), \
                 patch('sys.stdout', new_callable=io.StringIO) as output:
                diag.configure_gke()
                guard.assert_called_once()
                self.assertNotIn('fixture-sensitive-tool-output', output.getvalue())
                self.assertNotIn(str(root), output.getvalue())
            self.assertEqual(Path(env['KUBECONFIG']).stat().st_mode & 0o777, 0o600)
            self.assertIn('KUBECONFIG=' + env['KUBECONFIG'], Path(env['GITHUB_ENV']).read_text())
            self.assertEqual(calls[0], diag.GKE_CREDENTIALS)
            self.assertEqual(len(calls), 5)

    def test_configure_rejects_existing_or_external_kubeconfig(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            env = self.configure_environment(root)
            file = Path(env['KUBECONFIG']); file.write_text('existing-config')
            with patch.dict(os.environ, env), patch.object(diag, 'guard'), patch.object(diag, 'read_command') as run:
                with self.assertRaises(FileExistsError): diag.configure_gke()
                run.assert_not_called()
            self.assertEqual(file.read_text(), 'existing-config')
            env['KUBECONFIG'] = str(root / 'other-config')
            with patch.dict(os.environ, env), patch.object(diag, 'guard'), patch.object(diag, 'read_command') as run:
                with self.assertRaisesRegex(SystemExit, 'KUBECONFIG_TEMPORAIRE_REQUIS'): diag.configure_gke()
                run.assert_not_called()
            env = self.configure_environment(root); env['CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS'] = 'false'
            with patch.dict(os.environ, env), patch.object(diag, 'guard'):
                with self.assertRaisesRegex(SystemExit, 'EXEC_ADC_NON_SELECTIONNE'): diag.configure_gke()

    def test_configuration_failure_removes_partial_kubeconfig(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(); env = self.configure_environment(root)
            with patch.dict(os.environ, env), patch.object(diag, 'guard'), \
                 patch.object(diag, 'read_command', side_effect=SystemExit('opaque')):
                with self.assertRaises(SystemExit): diag.configure_gke()
            self.assertFalse(Path(env['KUBECONFIG']).exists())

    def test_workflow_uses_exec_adc_without_changing_oidc_or_permissions(self):
        w = yaml.safe_load((ROOT / '.github/workflows/diagnose-gke.yml').read_text())
        j = w['jobs']['diagnose']; env = j['env']
        self.assertNotIn('KUBECONFIG', env)
        self.assertEqual(env['CLOUDSDK_CONTAINER_USE_APPLICATION_DEFAULT_CREDENTIALS'], 'true')
        self.assertEqual(env['USE_GKE_GCLOUD_AUTH_PLUGIN'], 'True')
        self.assertEqual(j['permissions'], {'contents': 'read', 'id-token': 'write'})
        self.assertFalse(any('get-gke-credentials@' in s.get('uses', '') for s in j['steps']))
        auth = next(s for s in j['steps'] if 'google-github-actions/auth@' in s.get('uses', ''))
        self.assertIn('workload_identity_provider', auth['with'])
        self.assertNotIn('credentials_json', auth['with'])
        configure = next(i for i,s in enumerate(j['steps']) if '--configure-gke' in s.get('run', ''))
        diagnose = next(i for i,s in enumerate(j['steps']) if s.get('run') == 'python3 scripts/diagnose-cd.py')
        self.assertLess(configure, diagnose)
        self.assertEqual(j['steps'][configure]['env']['KUBECONFIG'], '${{ runner.temp }}/jitsi-diagnostic-kubeconfig')
        cleanup = j['steps'][-1]
        self.assertEqual(cleanup['if'], '${{ always() }}')
        self.assertIn('rm -f -- "$KUBECONFIG"', cleanup['run'])
        self.assertIn('"$RUNNER_TEMP"/jitsi-diagnostic-kubeconfig', cleanup['run'])

    def test_gcloud_whitelist_is_limited_to_one_read_operation(self):
        result = subprocess.CompletedProcess([], 0, stdout='fixture', stderr='')
        with patch.object(diag.subprocess, 'run', return_value=result):
            self.assertEqual(diag.read_command('configuration', diag.GKE_CREDENTIALS), 'fixture')
        for args in [diag.GKE_CREDENTIALS + ['--log-http'],
                     ['gcloud', 'container', 'clusters', 'delete', 'jitsi-cluster']]:
            with patch.object(diag.subprocess, 'run') as run:
                with self.assertRaises(SystemExit): diag.read_command('interdit', args)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
