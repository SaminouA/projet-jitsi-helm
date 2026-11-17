"""Garde de rendu Chaos Mesh, tests locaux sans installation ni faute."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('chaos_web', ROOT / 'scripts/chaos-web-postrender.py')
post = importlib.util.module_from_spec(spec)
spec.loader.exec_module(post)
TARGET = 'jitsi-jitsi-meet-web-8454659c99-gpjzl'
ROLE = 'chaos-mesh-chaos-controller-manager-target-namespace'


class ChaosWebSafetyTests(unittest.TestCase):
    def fixture(self):
        return [{'kind': 'ClusterRole', 'metadata': {'name': ROLE}, 'rules': []},
                {'kind': 'RoleBinding', 'metadata': {'name': 'binding', 'namespace': 'jitsi'}, 'roleRef': {'name': ROLE}},
                {'kind': 'Deployment', 'metadata': {'name': 'controller'}, 'spec': {'replicas': 1,
                 'template': {'spec': {'containers': [{'name': 'controller'}]}}}}]

    def test_delete_is_limited_to_exact_web_pod_and_no_secrets(self):
        docs = post.transform(self.fixture(), TARGET)
        rules = docs[0]['rules']
        delete = [r for r in rules if r['resources'] == ['pods'] and 'delete' in r['verbs']]
        self.assertEqual(delete, [{'apiGroups': [''], 'resources': ['pods'], 'verbs': ['delete'], 'resourceNames': [TARGET]}])
        self.assertFalse(any('secrets' in r['resources'] for r in rules))

    def test_other_component_and_wildcard_targets_rejected(self):
        for target in ['jitsi-jitsi-meet-jvb-0-test-test', 'jitsi-edge-test-test', 'jitsi-jitsi-meet-web-*', '']:
            with self.assertRaises(SystemExit): post.transform(self.fixture(), target)

    def test_daemon_and_dashboard_are_removed(self):
        docs = self.fixture() + [{'kind': 'DaemonSet', 'metadata': {'name': 'daemon'}},
                {'kind': 'ClusterRole', 'metadata': {'name': 'dashboard', 'labels': {'app.kubernetes.io/component': 'chaos-dashboard'}}}]
        self.assertEqual(len(post.transform(docs, TARGET)), 3)

    def test_clusterwide_binding_and_host_mount_rejected(self):
        docs = self.fixture(); docs[1]['kind'] = 'ClusterRoleBinding'
        with self.assertRaises(SystemExit): post.transform(docs, TARGET)
        docs = self.fixture(); docs[2]['spec']['template']['spec']['volumes'] = [{'name': 'host', 'hostPath': {'path': '/'}}]
        with self.assertRaises(SystemExit): post.transform(docs, TARGET)

    def test_missing_role_and_pvc_rejected(self):
        with self.assertRaises(SystemExit): post.transform(self.fixture()[1:], TARGET)
        with self.assertRaises(SystemExit): post.transform(self.fixture() + [{'kind': 'PersistentVolumeClaim','metadata': {'name': 'unexpected'}}], TARGET)
