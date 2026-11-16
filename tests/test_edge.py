"""Tests statiques edge : ni cluster, ni DNS, ni certificat reel."""
import copy
import importlib.util
from pathlib import Path
import subprocess
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

edge = load('edge_check', 'scripts/check-edge-render.py')
public_values = load('public_values', 'scripts/public-values.py')


class EdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = subprocess.check_output(['helm', 'template', 'jitsi-edge', str(ROOT / 'charts/jitsi-edge'),
            '-n', 'jitsi', '-f', str(ROOT / 'tests/fixtures/edge-values.yaml')], text=True)
        cls.template = [d for d in yaml.safe_load_all(output) if d]

    def setUp(self):
        self.docs = copy.deepcopy(self.template)

    def verify(self):
        edge.verify(self.docs, 'jitsi.invalid')

    def service(self):
        return next(d for d in self.docs if d['kind'] == 'Service')

    def deployment(self):
        return next(d for d in self.docs if d['kind'] == 'Deployment')

    def test_valid_network_boundary(self):
        self.verify()

    def test_private_or_udp_port_cannot_be_published(self):
        for port, protocol in [(8080, 'TCP'), (8082, 'TCP'), (2019, 'TCP'), (10000, 'UDP'), (443, 'UDP')]:
            with self.subTest(port=port, protocol=protocol):
                self.docs = copy.deepcopy(self.template)
                self.service()['spec']['ports'].append({'port': port, 'targetPort': port, 'protocol': protocol})
                with self.assertRaises(SystemExit): self.verify()

    def test_host_network_and_token_rejected(self):
        for field, value in [('hostNetwork', True), ('automountServiceAccountToken', True)]:
            self.docs = copy.deepcopy(self.template)
            self.deployment()['spec']['template']['spec'][field] = value
            with self.assertRaises(SystemExit): self.verify()

    def test_ephemeral_certificate_storage_rejected(self):
        volumes = self.deployment()['spec']['template']['spec']['volumes']
        volumes[:] = [v for v in volumes if v['name'] != 'data']
        with self.assertRaises(SystemExit): self.verify()

    def test_health_probe_not_tied_to_public_tls(self):
        container = self.deployment()['spec']['template']['spec']['containers'][0]
        container['readinessProbe']['httpGet']['port'] = 'https'
        with self.assertRaises(SystemExit): self.verify()

    def test_domain_consistency(self):
        with self.assertRaises(SystemExit): edge.verify(self.docs, 'other.invalid')

    def test_no_control_jvb_upstream(self):
        config = next(d for d in self.docs if d['kind'] == 'ConfigMap')['data']
        config['Caddyfile'] = config['Caddyfile'].replace('jitsi-jitsi-meet-web', 'jitsi-jitsi-meet-jvb')
        with self.assertRaises(SystemExit): self.verify()

    def test_admin_api_not_activated(self):
        config = next(d for d in self.docs if d['kind'] == 'ConfigMap')['data']
        config['Caddyfile'] = config['Caddyfile'].replace('admin off', 'admin :2019')
        with self.assertRaises(SystemExit): self.verify()

    def test_public_profile_requires_explicit_domain(self):
        p = subprocess.run(['helm', 'template', 'jitsi-edge', str(ROOT / 'charts/jitsi-edge'), '-n', 'jitsi'],
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        for domain in ['jitsi.invalid', 'x.test', 'localhost', '127.0.0.1', 'https://x.duckdns.org', 'UPPER.duckdns.org']:
            self.assertFalse(public_values.valid_domain(domain))

    def test_pvc_not_owned_by_release(self):
        self.assertNotIn('PersistentVolumeClaim', [d['kind'] for d in self.docs])
        pvc = yaml.safe_load((ROOT / 'deploy/jitsi-edge-storage.yaml').read_text())
        self.assertEqual(pvc['spec']['accessModes'], ['ReadWriteOnce'])
        self.assertEqual(pvc['metadata']['name'], 'jitsi-edge-data')

    def test_default_cd_does_not_enable_public_mode(self):
        workflow = yaml.load((ROOT / '.github/workflows/deploy-gke.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(workflow['jobs']['deploy']['env']['JITSI_ACCESS_PROFILE'], '${{ vars.JITSI_ACCESS_PROFILE }}')
        self.assertIn("|| 'false'", workflow['jobs']['deploy']['env']['JITSI_EDGE_CD_ENABLED'])
        guard = (ROOT / 'scripts/check-edge-live.py').read_text()
        self.assertIn('Bound', guard)
        self.assertNotIn('apply', guard.split('if __name__')[1])


if __name__ == '__main__':
    unittest.main()
