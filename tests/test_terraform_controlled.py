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
        self.env = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': self.sha, 'TF_OPERATION': 'apply-label', 'GITHUB_REPOSITORY': tf.REPO,
                    'EXPECTED_SHA': self.sha, 'TF_APPROVED_SHA': self.sha, 'TF_CD_ENABLED': 'true',
                    'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1', 'HELM_CD_ENABLED': 'false', 'TF_STATE_BUCKET': tf.BUCKET, 'TF_STATE_LINEAGE': self.lineage}
        self.payload = {'inputs': {'operation': 'apply-label'}, 'repository': {'full_name': tf.REPO}, 'workflow_run': {
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

    def test_preflight_does_not_require_environment_scoped_backend_variables(self):
        env = dict(self.env)
        env.pop('TF_STATE_BUCKET'); env.pop('TF_STATE_LINEAGE')
        self.assertEqual(tf.verify_context(self.payload, env, self.sha, self.sha, check_backend=False), self.sha)
        with self.assertRaises(SystemExit): tf.verify_context(self.payload, env, self.sha, self.sha)

    def test_absent_flag_bad_sha_wrong_backend_or_helm_active_rejected(self):
        for key, value in [('TF_CD_ENABLED', ''), ('TF_CD_ENABLED', 'false'), ('TF_APPROVED_SHA', 'b' * 40),
                           ('HELM_CD_ENABLED', 'true'), ('HELM_CD_ENABLED', 'TRUE'),
                           ('TF_STATE_BUCKET', 'other'), ('TF_STATE_LINEAGE', '')]:
            with self.subTest(key=key), self.assertRaises(SystemExit):
                tf.verify_context(self.payload, dict(self.env, **{key: value}), self.sha, self.sha)
        with self.assertRaises(SystemExit): tf.verify_context(self.payload, self.env, 'b' * 40, self.sha)

    def test_untrusted_event_rejected(self):
        for key, value in [('GITHUB_EVENT_NAME', 'workflow_run'), ('GITHUB_REF', 'refs/heads/feature'),
                           ('GITHUB_REPOSITORY', 'fork/other'), ('TF_OPERATION', 'readonly')]:
            with self.subTest(key=key), self.assertRaises(SystemExit):
                tf.verify_context(self.payload, dict(self.env, **{key: value}), self.sha, self.sha)
        with self.assertRaises(SystemExit): tf.verify_context({'inputs': {'operation': 'readonly'}}, self.env, self.sha, self.sha)

    def test_human_review_and_main_branch_policy_required(self):
        environment = {'can_admins_bypass': False, 'protection_rules': [{'type': 'required_reviewers', 'reviewers': [{'type': 'User'}]}],
                       'deployment_branch_policy': {'custom_branch_policies': True}}
        branches = {'branch_policies': [{'name': 'main', 'type': 'branch'}]}
        tf.verify_environment(environment, branches)
        for field, value in [('can_admins_bypass', True), ('protection_rules', [])]:
            with self.assertRaises(SystemExit): tf.verify_environment(dict(environment, **{field: value}), branches)
        with self.assertRaises(SystemExit): tf.verify_environment(environment, {'branch_policies': [{'name': '*', 'type': 'branch'}]})

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
            credential = Path(tmp) / 'credentials.json'
            credential.write_text(json.dumps({'type': 'external_account', 'service_account_impersonation_url': 'https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/' + tf.ACCOUNT + ':generateAccessToken'}))
            env = dict(self.env, RUNNER_TEMP=tmp, GITHUB_ENV=str(Path(tmp) / 'env'), GOOGLE_APPLICATION_CREDENTIALS=str(credential))
            binary = b'fixture-private-binary-plan'
            key = '01' * 64
            review = tf.bundle.seal(binary, self.state, tf.public_changes(plan_fixture()), key, env, Path(tmp) / 'reviewed-plan-download')
            env.update(TF_PLAN_TRANSPORT_KEY=key, TF_EXPECTED_PLAN_SHA256=review['plan_sha256'], TF_REVIEWED_PLAN_SHA256=review['plan_sha256'])
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

    def test_changed_state_is_rejected_before_apply_or_replan(self):
        from contextlib import nullcontext
        with tempfile.TemporaryDirectory() as tmp:
            state = copy.deepcopy(self.state); state['serial'] += 1
            review = {'changes': tf.public_changes(plan_fixture())}
            env = dict(self.env, RUNNER_TEMP=tmp)
            with patch.dict(os.environ, env), patch.object(tf.bundle, 'unseal', return_value=(b'plan', self.state, review)), \
                 patch.object(tf, 'workspace', return_value=nullcontext((Path(tmp), ['terraform']))), \
                 patch.object(tf, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(state))) as call:
                with self.assertRaises(SystemExit): tf.controlled_apply()
                self.assertEqual(call.call_args_list[0].args[0], ['terraform', 'state', 'pull'])
                self.assertEqual(call.call_count, 1)

    def test_real_tool_failure_is_sanitized_and_tf_injection_removed(self):
        completed = subprocess.CompletedProcess([], 1, stdout='fixture-private', stderr='fixture-token')
        with patch.dict(os.environ, TF_CLI_ARGS_apply='-destroy', TF_WORKSPACE='other'), \
             patch.object(tf.subprocess, 'run', return_value=completed) as tool:
            with self.assertRaises(SystemExit) as error: tf.run(['terraform', 'validate'])
            self.assertNotIn('fixture', str(error.exception))
            env = tool.call_args.kwargs['env']
            self.assertNotIn('TF_CLI_ARGS_apply', env); self.assertNotIn('TF_WORKSPACE', env)

    def test_workflow_is_optin_pinned_serialized_and_downloads_only_reviewed_artifact(self):
        w = yaml.load((ROOT / '.github/workflows/terraform-gke.yml').read_text(), Loader=yaml.BaseLoader)
        j = w['jobs']['apply']
        self.assertEqual(set(w['on']), {'workflow_dispatch'})
        self.assertEqual(j['environment'], 'terraform-controlled')
        self.assertIn("vars.TF_CD_ENABLED == 'true'", w['jobs']['apply-preflight']['if'])
        self.assertEqual(j['needs'], ['prepare-plan', 'review-plan'])
        self.assertEqual(w['jobs']['review-plan']['needs'], 'prepare-plan')
        self.assertEqual(w['jobs']['review-plan']['environment']['name'], 'terraform-apply-review')
        self.assertEqual(w['jobs']['review-plan']['permissions'], {})
        self.assertEqual(j['env']['TF_APPROVED_SHA'], '${{ inputs.approved_sha }}')
        self.assertEqual(w['concurrency']['group'], 'deploy-jitsi-gke-main')
        self.assertEqual(j['permissions'], {'contents': 'read', 'actions': 'read', 'id-token': 'write'})
        for step in j['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')
                self.assertNotIn('upload-artifact', step['uses'])
        auth = next(s for s in j['steps'] if 'google-github-actions/auth@' in s.get('uses', ''))
        self.assertTrue(auth['with']['workload_identity_provider'].endswith('/github-terraform-provider'))
        self.assertNotIn('credentials_json', auth['with'])
        self.assertEqual(j['steps'][-1]['if'], '${{ always() }}')
        download = next(s for s in j['steps'] if 'actions/download-artifact@' in s.get('uses', ''))
        self.assertEqual(download['with']['artifact-ids'], '${{ needs.prepare-plan.outputs.artifact_id }}')
        self.assertNotIn('run-id', download['with'])
        self.assertNotIn('repository', download['with'])
        self.assertNotIn('github-token', download['with'])
        self.assertIn('--apply-reviewed-plan', '\n'.join(s.get('run', '') for s in j['steps']))


class ReviewedBundleTests(unittest.TestCase):
    def fixture(self, directory):
        env = {'GITHUB_SHA': 'a'*40, 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1'}
        key = '01' * 64
        state = {'private': 'fixture-super-private-state'}
        path = Path(directory) / 'artifact'
        review = tf.bundle.seal(b'fixture-super-private-plan', state, tf.public_changes(plan_fixture()), key, env, path)
        env['TF_REVIEWED_PLAN_SHA256'] = review['plan_sha256']
        return env, key, state, path, review

    def test_exact_binary_roundtrip_without_public_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            env, key, state, path, review = self.fixture(tmp)
            binary, actual_state, actual_review = tf.bundle.unseal(path, key, env, review['plan_sha256'])
            self.assertEqual(binary, b'fixture-super-private-plan'); self.assertEqual(actual_state, state)
            self.assertEqual(actual_review, review)
            for p in path.iterdir():
                self.assertNotIn(b'fixture-super-private', p.read_bytes())

    def test_tamper_ciphertext_mac_and_manifest_refused_before_decryption(self):
        for filename in ['bundle.enc', 'bundle.hmac', 'review.json']:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                env, key, state, path, review = self.fixture(tmp)
                p = path/filename
                if filename == 'review.json':
                    data=json.loads(p.read_text());data['changes']['after']='unapproved';p.write_text(json.dumps(data))
                else:p.write_bytes(p.read_bytes()+b'X')
                with patch.object(tf.bundle, 'crypt') as decrypt:
                    with self.assertRaises(SystemExit):tf.bundle.unseal(path,key,env,review['plan_sha256'])
                    decrypt.assert_not_called()

    def test_wrong_key_sha_run_attempt_and_missing_review_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            env,key,state,path,review=self.fixture(tmp)
            variants=[(dict(env,GITHUB_SHA='b'*40),key,review['plan_sha256']),
                      (dict(env,GITHUB_RUN_ID='124'),key,review['plan_sha256']),
                      (dict(env,GITHUB_RUN_ATTEMPT='2'),key,review['plan_sha256']),
                      (dict(env,TF_REVIEWED_PLAN_SHA256=''),key,review['plan_sha256']),
                      (env,'02'*64,review['plan_sha256']), (env,key,'f'*64)]
            for changed,k,digest in variants:
                with self.assertRaises(SystemExit):tf.bundle.unseal(path,k,changed,digest)

    def test_missing_transport_key_and_existing_proof_label_refused(self):
        for key in ['', 'fixture', '01'*32]:
            with self.assertRaises(SystemExit):tf.bundle.key_material(key)
        p=plan_fixture()
        for field in tf.plan_guard.LABEL_FIELDS:
            p['resource_changes'][0]['change']['before'][field][tf.plan_guard.LABEL]='old'
        with self.assertRaises(SystemExit):tf.public_changes(p)

    def test_cli_has_no_default_apply(self):
        p=subprocess.run(['python3',str(ROOT/'scripts/terraform-controlled.py')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Action explicite requise',p.stderr)

    def test_prepare_plan_cannot_apply(self):
        import ast
        tree=ast.parse((ROOT/'scripts/terraform-controlled.py').read_text())
        prepare=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_plan')
        literal=[n.value for n in ast.walk(prepare) if isinstance(n,ast.Constant)]
        self.assertNotIn('apply',literal)
        apply=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='controlled_apply')
        for n in ast.walk(apply):
            if isinstance(n,ast.List):
                values=[e.value for e in n.elts if isinstance(e,ast.Constant)]
                if 'plan' in values:self.assertNotIn('-out=',values)
