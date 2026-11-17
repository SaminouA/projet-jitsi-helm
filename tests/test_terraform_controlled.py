"""Terraform : fixtures et outils simules uniquement ; aucun apply reel."""
import copy
from contextlib import redirect_stdout
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tf_controlled', ROOT / 'scripts/terraform-controlled.py')
tf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tf)


def plan_fixture():
    cluster = {'project': tf.PROJECT, 'location': 'europe-west1-b', 'name': 'jitsi-cluster',
               'resource_labels': {}, 'terraform_labels': {}, 'effective_labels': {'goog-terraform-provisioned': 'true'},
               'deletion_protection': False}
    updated = copy.deepcopy(cluster)
    for field in tf.plan_guard.LABEL_FIELDS:
        updated[field][tf.plan_guard.LABEL] = tf.plan_guard.VALUE
    pool = {'project': tf.PROJECT, 'location': 'europe-west1-b', 'name': 'jitsi-node-pool', 'node_count': 2}
    return {'complete': True, 'resource_changes': [
        {'address': tf.plan_guard.CLUSTER, 'mode': 'managed', 'change': {'actions': ['update'], 'before': cluster, 'after': updated, 'after_unknown': {}}},
        {'address': tf.plan_guard.POOL, 'mode': 'managed', 'change': {'actions': ['no-op'], 'before': pool, 'after': copy.deepcopy(pool), 'after_unknown': {}}}]}


class TerraformPlanTests(unittest.TestCase):
    def test_only_expected_label_update_accepted(self):
        self.assertIn('0 replace', tf.plan_guard.verify(plan_fixture()))

    def test_destroy_create_replace_and_noop_proof_rejected(self):
        for actions in [['delete'], ['create'], ['delete', 'create'], ['create', 'delete'], ['no-op']]:
            p = plan_fixture(); p['resource_changes'][0]['change']['actions'] = actions
            with self.subTest(actions=actions), self.assertRaises(SystemExit): tf.plan_guard.verify(p)

    def test_pool_update_rejected(self):
        p = plan_fixture(); p['resource_changes'][1]['change']['actions'] = ['update']
        with self.assertRaises(SystemExit): tf.plan_guard.verify(p)

    def test_other_cluster_change_and_label_removal_rejected(self):
        for field, value in [('deletion_protection', True), ('location', 'other-zone'), ('resource_labels', {tf.plan_guard.LABEL: 'other'})]:
            p = plan_fixture(); p['resource_changes'][0]['change']['after'][field] = value
            with self.assertRaises(SystemExit): tf.plan_guard.verify(p)
        p = plan_fixture(); p['resource_changes'][0]['change']['after']['effective_labels'].pop('goog-terraform-provisioned')
        with self.assertRaises(SystemExit): tf.plan_guard.verify(p)

    def test_missing_extra_deferred_and_unknown_resources_rejected(self):
        variants = []
        p = plan_fixture(); p['resource_changes'].pop(); variants.append(p)
        p = plan_fixture(); p['resource_changes'].append(copy.deepcopy(p['resource_changes'][0])); variants.append(p)
        p = plan_fixture(); p['deferred_changes'] = [{}]; variants.append(p)
        p = plan_fixture(); p['complete'] = False; variants.append(p)
        p = plan_fixture(); p['resource_changes'][0]['change']['after_unknown'] = {'secret': True}; variants.append(p)
        p = plan_fixture(); p['resource_changes'][0]['change']['replace_paths'] = [['name']]; variants.append(p)
        for p in variants:
            with self.assertRaises(SystemExit): tf.plan_guard.verify(p)

    def test_error_never_discloses_values(self):
        p = plan_fixture(); p['resource_changes'][0]['change']['after']['private_value'] = 'fixture-sensitive'
        with self.assertRaises(SystemExit) as error: tf.plan_guard.verify(p)
        self.assertNotIn('fixture-sensitive', str(error.exception))


class TerraformRunnerTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a' * 40
        self.lineage = '11111111-1111-1111-1111-111111111111'
        self.env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_run', 'GITHUB_REPOSITORY': tf.REPO,
                    'EXPECTED_SHA': self.sha, 'TF_APPROVED_SHA': self.sha, 'TF_CD_ENABLED': 'true',
                    'HELM_CD_ENABLED': 'false', 'TF_STATE_BUCKET': tf.BUCKET, 'TF_STATE_LINEAGE': self.lineage}
        self.payload = {'repository': {'full_name': tf.REPO}, 'workflow_run': {
            'repository': {'full_name': tf.REPO}, 'head_repository': {'full_name': tf.REPO},
            'name': tf.event.CI_NAME, 'event': 'push', 'status': 'completed', 'conclusion': 'success',
            'head_branch': 'main', 'head_sha': self.sha}}
        self.bucket = {'name': tf.BUCKET, 'projectNumber': '198310729956', 'location': 'EUROPE-WEST1',
                       'versioning': {'enabled': True}, 'iamConfiguration': {
                           'uniformBucketLevelAccess': {'enabled': True}, 'publicAccessPrevention': 'enforced'}}
        self.state = {'lineage': self.lineage, 'serial': 9, 'resources': [
            {'type': address.split('.')[0], 'name': address.split('.')[1], 'mode': 'managed',
             'instances': [{'attributes': {'project': tf.PROJECT, 'location': 'europe-west1-b', 'name': name,
                 'id': 'projects/' + tf.PROJECT + '/locations/europe-west1-b/clusters/jitsi-cluster' +
                       ('/nodePools/jitsi-node-pool' if address == tf.plan_guard.POOL else '')}}]}
            for address, name in [(tf.plan_guard.CLUSTER, 'jitsi-cluster'), (tf.plan_guard.POOL, 'jitsi-node-pool')]]}

    def test_valid_context(self):
        self.assertEqual(tf.verify_context(self.payload, self.env, self.sha, self.sha), self.sha)

    def test_absent_flag_bad_sha_wrong_backend_or_helm_active_rejected(self):
        for key, value in [('TF_CD_ENABLED', ''), ('TF_CD_ENABLED', 'false'), ('TF_APPROVED_SHA', 'b' * 40),
                           ('HELM_CD_ENABLED', 'true'), ('HELM_CD_ENABLED', 'TRUE'),
                           ('TF_STATE_BUCKET', 'other'), ('TF_STATE_LINEAGE', '')]:
            with self.subTest(key=key), self.assertRaises(SystemExit):
                tf.verify_context(self.payload, dict(self.env, **{key: value}), self.sha, self.sha)
        with self.assertRaises(SystemExit): tf.verify_context(self.payload, self.env, 'b' * 40, self.sha)

    def test_untrusted_event_rejected(self):
        for key, value in [('head_branch', 'feature/other'), ('event', 'workflow_dispatch'), ('conclusion', 'failure'),
                           ('head_repository', {'full_name': 'fork/other'})]:
            payload = copy.deepcopy(self.payload); payload['workflow_run'][key] = value
            with self.assertRaises(SystemExit): tf.verify_context(payload, self.env, self.sha, self.sha)

    def test_state_empty_wrong_lineage_and_other_project_rejected(self):
        with patch.dict(os.environ, self.env):
            tf.verify_state(self.state)
            for key, value in [('resources', []), ('lineage', 'different'), ('serial', 1)]:
                state = copy.deepcopy(self.state); state[key] = value
                with self.assertRaises(SystemExit): tf.verify_state(state)
            state = copy.deepcopy(self.state); state['resources'][0]['instances'][0]['attributes']['project'] = 'other'
            with self.assertRaises(SystemExit): tf.verify_state(state)

    def test_bucket_requires_versioning_private_access_and_no_retention_lock(self):
        tf.verify_bucket(self.bucket)
        for key, value in [('projectNumber', 'other'), ('location', 'US'), ('versioning', {}), ('retentionPolicy', {'retentionPeriod': '86400'}), ('iamConfiguration', {})]:
            bucket = copy.deepcopy(self.bucket); bucket[key] = value
            with self.assertRaises(SystemExit): tf.verify_bucket(bucket)

    def test_saved_plan_only_applied_then_verified_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(self.env, RUNNER_TEMP=tmp, GITHUB_ENV=str(Path(tmp) / 'env'))
            calls = []; pulls = 0
            def fake(args, accepted=(0,)):
                nonlocal pulls
                calls.append(args)
                stdout = ''
                if args[:3] == ['gcloud', 'auth', 'list']: stdout = tf.ACCOUNT
                elif args[:4] == ['gcloud', 'storage', 'buckets', 'describe']: stdout = json.dumps(self.bucket)
                elif 'workspace' in args: stdout = 'default'
                elif 'pull' in args:
                    pulls += 1; state = copy.deepcopy(self.state); state['serial'] = 10 if pulls == 3 else 9; stdout = json.dumps(state)
                elif 'plan' in args:
                    for arg in args:
                        if arg.startswith('-out='): Path(arg[5:]).write_bytes(b'fixture-private-binary-plan')
                elif 'show' in args: stdout = json.dumps(plan_fixture())
                elif args[:4] == ['gcloud', 'container', 'clusters', 'describe']:
                    stdout = json.dumps({'status': 'RUNNING', 'resourceLabels': {tf.plan_guard.LABEL: tf.plan_guard.VALUE}})
                return subprocess.CompletedProcess(args, 0, stdout=stdout)
            with patch.dict(os.environ, env), patch.object(tf, 'guard'), patch.object(tf, 'run', side_effect=fake), redirect_stdout(io.StringIO()):
                tf.controlled_apply()
            applies = [c for c in calls if 'apply' in c]
            self.assertEqual(len(applies), 1)
            self.assertTrue(applies[0][-1].endswith('/approved.tfplan'))
            self.assertNotIn('-auto-approve', applies[0])
            self.assertFalse(Path(applies[0][-1]).exists())
            self.assertFalse(any('-migrate-state' in c or '-lock=false' in c for c in calls))

    def test_real_tool_failure_is_sanitized_and_tf_injection_removed(self):
        completed = subprocess.CompletedProcess([], 1, stdout='fixture-private', stderr='fixture-token')
        with patch.dict(os.environ, TF_CLI_ARGS_apply='-destroy', TF_WORKSPACE='other'), \
             patch.object(tf.subprocess, 'run', return_value=completed) as tool:
            with self.assertRaises(SystemExit) as error: tf.run(['terraform', 'validate'])
            self.assertNotIn('fixture', str(error.exception))
            env = tool.call_args.kwargs['env']
            self.assertNotIn('TF_CLI_ARGS_apply', env); self.assertNotIn('TF_WORKSPACE', env)

    def test_workflow_is_optin_pinned_serialized_and_has_no_plan_artifact(self):
        w = yaml.load((ROOT / '.github/workflows/terraform-gke.yml').read_text(), Loader=yaml.BaseLoader)
        j = w['jobs']['terraform']
        self.assertEqual(set(w['on']), {'workflow_run'})
        self.assertEqual(j['environment'], 'terraform-controlled')
        self.assertIn("vars.TF_CD_ENABLED == 'true'", j['if'])
        self.assertIn('vars.TF_APPROVED_SHA == github.event.workflow_run.head_sha', j['if'])
        self.assertEqual(w['concurrency']['group'], 'deploy-jitsi-gke-main')
        self.assertEqual(j['permissions'], {'contents': 'read', 'id-token': 'write'})
        for step in j['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')
                self.assertNotIn('upload-artifact', step['uses'])
        auth = next(s for s in j['steps'] if 'google-github-actions/auth@' in s.get('uses', ''))
        self.assertTrue(auth['with']['workload_identity_provider'].endswith('/github-terraform-provider'))
        self.assertNotIn('credentials_json', auth['with'])
        self.assertEqual(j['steps'][-1]['if'], '${{ always() }}')
