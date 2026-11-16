"""Regressions des profils CI : rendus uniquement, aucun acces cluster/reseau."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = 'https://jitsi-meet-m2.duckdns.org'
LOCAL = 'http://localhost:8081'


class RenderProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rendered = subprocess.check_output([
            'helm', 'template', 'jitsi', str(ROOT / 'charts-officiels/jitsi-meet'),
            '-n', 'jitsi', '--skip-tests', '-f', str(ROOT / 'values-gke.yaml'),
        ], text=True)
        cls.template = [doc for doc in yaml.safe_load_all(rendered) if doc]

    def validate(self, url, *flags, mutate=None):
        docs = copy.deepcopy(self.template)
        common = next(d['data'] for d in docs if d['kind'] == 'ConfigMap'
                      and 'PUBLIC_URL' in (d.get('data') or {}))
        common['PUBLIC_URL'] = url
        if mutate:
            mutate(docs)
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'render.yaml'
            manifest.write_text(yaml.safe_dump_all(docs))
            return subprocess.run(['python3', str(ROOT / 'scripts/check-render.py'),
                                   str(manifest), *flags], capture_output=True, text=True)

    def test_auto_accepts_local_and_https_edge(self):
        for url in [LOCAL, PUBLIC]:
            with self.subTest(url=url):
                p = self.validate(url, '--auto-profile')
                self.assertEqual(p.returncode, 0, p.stderr)

    def test_explicit_profiles_remain_strict(self):
        for url, flags, succeeds in [
            (LOCAL, [], True), (PUBLIC, [], False),
            (LOCAL, ['--edge'], False), (PUBLIC, ['--edge'], True),
            (PUBLIC, ['--public'], False),  # Aucun Ingress dans le profil Caddy.
        ]:
            with self.subTest(url=url, flags=flags):
                p = self.validate(url, *flags)
                self.assertEqual(p.returncode == 0, succeeds)

    def test_auto_rejects_unsafe_or_malformed_origins(self):
        for url in ['http://jitsi.example.org', 'https://127.0.0.1',
                    'https://localhost', 'http://localhost:8082',
                    PUBLIC + ':8443', PUBLIC + '/room', PUBLIC + '?x=1',
                    PUBLIC + '#fragment', 'https://user:pass@jitsi.example.org',
                    'https://bad_name.example.org', 'https://[broken']:
            with self.subTest(url=url):
                self.assertNotEqual(self.validate(url, '--auto-profile').returncode, 0)

    def test_auto_keeps_private_web_and_bosh_invariants(self):
        def expose_web(docs):
            next(d for d in docs if d['kind'] == 'Service'
                 and d['metadata']['name'].endswith('-web'))['spec']['type'] = 'LoadBalancer'

        def break_bosh(docs):
            next(d['data'] for d in docs if d['kind'] == 'ConfigMap'
                 and 'custom-config.js' in (d.get('data') or {}))['custom-config.js'] = ''

        for url in [LOCAL, PUBLIC]:
            for mutation in [expose_web, break_bosh]:
                with self.subTest(url=url, mutation=mutation.__name__):
                    self.assertNotEqual(self.validate(url, '--auto-profile', mutate=mutation).returncode, 0)

    def test_ready_still_requires_jvb_advertised_ip(self):
        def advertise(docs):
            bridge = next(d for d in docs if d['kind'] == 'Deployment'
                          and d['metadata']['name'].endswith('-jvb-0'))
            env = bridge['spec']['template']['spec']['containers'][0]['env']
            env[:] = [item for item in env if item['name'] != 'JVB_ADVERTISE_IPS']
            env.append({'name': 'JVB_ADVERTISE_IPS', 'value': '34.62.165.81'})

        self.assertNotEqual(self.validate(PUBLIC, '--auto-profile', '--ready').returncode, 0)
        p = self.validate(PUBLIC, '--auto-profile', '--ready', mutate=advertise)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_conflicting_profile_flags_rejected(self):
        self.assertNotEqual(self.validate(PUBLIC, '--auto-profile', '--public').returncode, 0)


if __name__ == '__main__':
    unittest.main()
