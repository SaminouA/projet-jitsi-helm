"""Local Helm renders only; never contact Kubernetes."""
from pathlib import Path
import subprocess
import unittest
import yaml

CHART = 'charts/jitsi-load-test'
IMAGE = 'ghcr.io/example/test@sha256:' + 'a' * 64


def render(*settings):
    command = ['helm', 'template', 'load', CHART]
    for setting in settings:
        command += ['--set', setting]
    return subprocess.run(command, capture_output=True, text=True)


GRID = ('selenium.enabled=true', 'selenium.imageValidated=true', 'selenium.image=' + IMAGE)
JOB = ('malleus.enabled=true', 'malleus.imageValidated=true', 'malleus.image=' + IMAGE)


class LoadHelm(unittest.TestCase):
    def test_default_is_inert(self):
        result = render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(yaml.safe_load_all(result.stdout)), [])

    def test_grid_internal_and_bounded(self):
        result = render(*GRID)
        self.assertEqual(result.returncode, 0, result.stderr)
        deployment, service = list(yaml.safe_load_all(result.stdout))
        # Helm orders Services before Deployments.
        objects = {obj['kind']: obj for obj in [deployment, service]}
        service = objects['Service']
        pod = objects['Deployment']['spec']['template']['spec']
        self.assertEqual(service['spec']['type'], 'ClusterIP')
        self.assertEqual(service['spec']['ports'][0]['port'], 4444)
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(objects['Deployment']['spec']['replicas'], 1)
        self.assertEqual(pod['volumes'][0]['emptyDir']['medium'], 'Memory')
        self.assertIn('resources', pod['containers'][0])
        self.assertEqual(service['spec']['selector'], objects['Deployment']['spec']['selector']['matchLabels'])

    def test_job_suspended_no_retry_preserves_image_dependencies(self):
        result = render(*GRID, *JOB)
        self.assertEqual(result.returncode, 0, result.stderr)
        objects = {o['kind']: o for o in yaml.safe_load_all(result.stdout)}
        job = objects['Job']['spec']
        self.assertTrue(job['suspend'])
        self.assertEqual(job['backoffLimit'], 0)
        self.assertEqual(job['activeDeadlineSeconds'], 240)
        pod = job['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        env = {v['name']: v['value'] for v in pod['containers'][0]['env']}
        self.assertEqual(env['GRID_URL'], 'http://load-selenium:4444/wd/hub')
        mounts = {m['mountPath'] for m in pod['containers'][0]['volumeMounts']}
        self.assertNotIn('/opt/malleus/torture/target', mounts)
        self.assertNotIn('/opt/malleus/repository', mounts)
        self.assertNotIn('/opt/malleus/driver-cache', mounts)
        self.assertTrue(all('emptyDir' in v for v in pod['volumes']))

    def test_invalid_or_unvalidated_images_and_load_are_blocked(self):
        for settings in [('selenium.enabled=true',), (*GRID, 'selenium.sessions=10'),
                         (*JOB,), (*GRID, *JOB, 'malleus.participants=3'),
                         (*GRID, *JOB, 'malleus.duration=600'),
                         (*GRID, 'selenium.image=example:latest')]:
            with self.subTest(settings=settings):
                self.assertNotEqual(render(*settings).returncode, 0)
