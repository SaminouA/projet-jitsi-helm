#!/usr/bin/env python3
"""Manual guarded experiments. Import/tests never contact GCP or Kubernetes."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = 'SaminouA/projet-jitsi-helm'
CONTEXT = 'gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster'
ACCOUNT = 'github-jitsi-experiments@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com'
URL = 'https://jitsi-meet-m2.duckdns.org/'
ENVIRONMENT = 'experiments-controlled'
CONTROLLER = 'system:serviceaccount:chaos-testing:chaos-controller-manager'
PROCESSES = []


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def run(args, *, data=None, allowed=(0,), timeout=45):
    p = subprocess.run(args, input=data, capture_output=True, text=True, timeout=timeout)
    require(p.returncode in allowed, 'COMMAND_FAILED_' + args[0])
    return p.stdout


def kubectl(*args, data=None):
    return run(['kubectl', '--context', CONTEXT, '--request-timeout=20s', *args], data=data, timeout=90)


def read(kind, namespace=None):
    return json.loads(kubectl(*(['-n', namespace] if namespace else []), 'get', *kind.split(), '-o', 'json'))


def verify_environment(environment, branches):
    require(environment.get('can_admins_bypass') is False, 'ADMIN_BYPASS_REFUSED')
    require(any(r.get('type') == 'required_reviewers' and r.get('reviewers') for r in environment.get('protection_rules', [])), 'HUMAN_REVIEW_REQUIRED')
    require(environment.get('deployment_branch_policy', {}).get('custom_branch_policies') is True, 'BRANCH_POLICY_REQUIRED')
    require([(b.get('name'), b.get('type')) for b in branches.get('branch_policies', [])] == [('main', 'branch')], 'MAIN_ONLY')


def context(env, mode):
    require(env.get('GITHUB_ACTIONS') == 'true' and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch', 'MANUAL_ONLY')
    require(env.get('GITHUB_REPOSITORY') == REPO and env.get('GITHUB_REF') == 'refs/heads/main', 'TRUSTED_MAIN_ONLY')
    require(env.get('EXPERIMENTS_ENABLED') == 'true' and env.get('EXPERIMENT_CONFIRM') == 'true', 'EXPLICIT_AUTHORIZATION_REQUIRED')
    require(mode in ('malleus', 'chaos'), 'UNKNOWN_EXPERIMENT')
    require(re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')), 'SHA_REQUIRED')
    require(re.fullmatch(r'[0-9]+', env.get('GITHUB_RUN_ID', '')) and re.fullmatch(r'[0-9]+', env.get('GITHUB_RUN_ATTEMPT', '')), 'RUN_ID_REQUIRED')


def guard(mode):
    context(os.environ, mode)
    api = 'repos/' + REPO
    require(run(['git', 'rev-parse', 'HEAD']).strip() == os.environ['GITHUB_SHA'], 'CHECKOUT_MISMATCH')
    require(run(['gh', 'api', api + '/git/ref/heads/main', '--jq', '.object.sha']).strip() == os.environ['GITHUB_SHA'], 'MAIN_MOVED')
    environment = json.loads(run(['gh', 'api', api + '/environments/' + ENVIRONMENT]))
    branches = json.loads(run(['gh', 'api', api + '/environments/' + ENVIRONMENT + '/deployment-branch-policies']))
    verify_environment(environment, branches)
    runs = json.loads(run(['gh', 'api', api + '/actions/workflows/helm-ci.yml/runs?branch=main&event=push&status=success&per_page=100']))
    require(any(r.get('head_sha') == os.environ['GITHUB_SHA'] and r.get('conclusion') == 'success' and
                r.get('event') == 'push' and r.get('head_branch') == 'main' and
                r.get('head_repository', {}).get('full_name') == REPO for r in runs.get('workflow_runs', [])), 'SUCCESSFUL_MAIN_CI_REQUIRED')


def ready(pod):
    cs = pod.get('status', {}).get('containerStatuses', [])
    return bool(cs) and all(c.get('ready') for c in cs) and not pod['metadata'].get('deletionTimestamp')


def production():
    items = read('pods', 'jitsi')['items']
    require(len(items) == 5 and all(ready(p) for p in items), 'FIVE_READY_PRODUCTION_PODS_REQUIRED')
    return {p['metadata']['name']: {'uid': p['metadata']['uid'],
            'component': p['metadata'].get('labels', {}).get('app.kubernetes.io/component'),
            'restarts': sum(c['restartCount'] for c in p['status']['containerStatuses'])} for p in items}


def stable(before, after, chaos=False):
    before = {n: v for n, v in before.items() if not chaos or v['component'] != 'web'}
    after = {n: v for n, v in after.items() if not chaos or v['component'] != 'web'}
    require(before == after, 'PRODUCTION_CHANGED')


def capacity(projected=False):
    nodes = read('nodes')['items']
    require(len(nodes) == 2, 'TWO_NODES_REQUIRED')
    for node in nodes:
        conditions = {c['type']: c['status'] for c in node['status']['conditions']}
        require(conditions.get('Ready') == 'True' and all(conditions.get(k) == 'False' for k in ['MemoryPressure', 'DiskPressure', 'PIDPressure']), 'NODE_PRESSURE')
    samples = []
    for line in kubectl('top', 'nodes', '--no-headers').splitlines():
        fields = line.split()
        cpu, memory = int(fields[2].rstrip('%')), int(fields[4].rstrip('%'))
        require(cpu < (20 if projected else 80) and memory < (55 if projected else 80), 'CAPACITY_THRESHOLD')
        samples.append({'cpu_percent': cpu, 'memory_percent': memory})
    require(len(samples) == 2, 'METRICS_REQUIRED')
    return samples


def pod_metrics(namespace):
    result = []
    for line in kubectl('top', 'pods', '-n', namespace, '--no-headers').splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        cpu = float(fields[1][:-1]) if fields[1].endswith('m') else float(fields[1]) * 1000
        memory = fields[2]
        factors = {'Ki': 1/1024, 'Mi': 1, 'Gi': 1024}
        unit = next((u for u in factors if memory.endswith(u)), None)
        require(unit is not None, 'MEMORY_UNIT_UNSUPPORTED')
        result.append({'pod': fields[0], 'cpu_m': cpu, 'memory_mib': float(memory[:-len(unit)]) * factors[unit]})
    return result


def https():
    with urllib.request.urlopen(URL, timeout=5) as response:
        require(response.status == 200 and response.url.startswith(URL), 'HTTPS_NOT_HEALTHY')
    return 200


def forward(resource, namespace, local, remote):
    p = subprocess.Popen(['kubectl', '--context', CONTEXT, '-n', namespace, 'port-forward', resource,
                          str(local) + ':' + str(remote), '--address', '127.0.0.1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    PROCESSES.append(p)
    for _ in range(20):
        require(p.poll() is None, 'PORT_FORWARD_FAILED')
        try:
            with urllib.request.urlopen('http://127.0.0.1:' + str(local) + ('/status' if remote == 4444 else '/colibri/stats'), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError('PORT_FORWARD_TIMEOUT')


def stats():
    with urllib.request.urlopen('http://127.0.0.1:18080/colibri/stats', timeout=3) as response:
        raw = json.load(response)
    keys = ['conferences', 'participants', 'endpoints', 'local_active_endpoints', 'healthy', 'stress_level',
            'bit_rate_download', 'bit_rate_upload', 'packet_rate_download', 'packet_rate_upload',
            'total_bytes_received', 'total_bytes_sent', 'total_packets_received', 'total_packets_sent',
            'ice_succeeded', 'ice_failed']
    return {k: raw[k] for k in keys if k in raw}


def require_idle(sample):
    require(sample.get('conferences') == 0 and sample.get('participants') == 0 and
            sample.get('local_active_endpoints') == 0, 'ACTIVE_MEETING_REFUSED')


def exact_web(pods, name, uid):
    matches = [(n, p) for n, p in pods.items() if p['component'] == 'web']
    require(len(matches) == 1 and matches[0][0] == name and matches[0][1]['uid'] == uid and
            re.fullmatch(r'jitsi-jitsi-meet-web-[a-z0-9]+-[a-z0-9]+', name) is not None, 'APPROVED_WEB_CHANGED')


def experiment(name, uid, run_id):
    # Reuse validated action/selectors, never its historical pod name.
    import yaml
    manifest = yaml.safe_load((ROOT / 'tests/chaos/podchaos-web-once.yaml').read_text())
    manifest['metadata'] = {'name': 'm2-chaos-' + run_id, 'namespace': 'jitsi', 'labels': {'m2-experiment-run': run_id}}
    manifest['spec']['selector']['pods'] = {'jitsi': [name]}
    require(manifest['spec']['action'] == 'pod-kill' and manifest['spec']['mode'] == 'one', 'ONE_POD_ONLY')
    return manifest


def verify_load_render(documents, release):
    require(len(documents) == 3 and {d['kind'] for d in documents} == {'Deployment', 'Service', 'Job'}, 'UNEXPECTED_TEST_RESOURCE')
    by_kind = {d['kind']: d for d in documents}
    service = by_kind['Service']['spec']
    require(service.get('type') == 'ClusterIP' and not service.get('externalIPs') and
            [(p['port'], p['targetPort']) for p in service['ports']] == [(4444, 'webdriver')], 'GRID_MUST_STAY_PRIVATE')
    job = by_kind['Job']['spec']
    require(job.get('suspend') is True and job.get('activeDeadlineSeconds') == 240 and job.get('backoffLimit') == 0, 'UNBOUNDED_TEST_JOB')
    for kind, suffix, cpu, memory, image in [
        ('Deployment', '-selenium', '900m', '2Gi', 'ghcr.io/saminoua/jitsi-selenium@sha256:5b898424cffed5b99a0c8acbb558c0e3f3e4a2fbb0aac48bb54af60b445dcd86'),
        ('Job', '-malleus', '300m', '768Mi', 'ghcr.io/saminoua/jitsi-malleus@sha256:01de65fb72bf78ded0191caa6302916f04850b94bdb6d1d943b0ceae6ce87092')]:
        obj = by_kind[kind]; pod = obj['spec']['template']['spec']
        require(obj['metadata']['name'] == release + suffix, 'UNEXPECTED_TEST_NAME')
        require(pod.get('automountServiceAccountToken') is False and not pod.get('hostNetwork') and not pod.get('hostPID'), 'UNSAFE_TEST_POD')
        require(not any('hostPath' in v or 'persistentVolumeClaim' in v for v in pod.get('volumes', [])), 'TEST_STORAGE_REFUSED')
        require(len(pod['containers']) == 1, 'EXTRA_TEST_CONTAINER')
        c = pod['containers'][0]
        require(c['image'] == image and c['resources']['limits']['cpu'] == cpu and c['resources']['limits']['memory'] == memory, 'UNVALIDATED_IMAGE_OR_BUDGET')
        require(not any(p.get('hostPort') for p in c.get('ports', [])), 'TEST_HOST_PORT_REFUSED')
    env = {e['name']: e.get('value') for e in by_kind['Job']['spec']['template']['spec']['containers'][0]['env']}
    require(env.get('PARTICIPANTS') == '2' and env.get('DURATION') == '90', 'ONLY_VALIDATED_2X90_PROFILE')


def controller_permissions(name):
    # Audit every binding granting this controller destructive Pod permissions.
    found = False
    bindings = read('rolebindings --all-namespaces')['items'] + read('clusterrolebindings')['items']
    for binding in bindings:
        if not any((s.get('kind') == 'ServiceAccount' and s.get('namespace') == 'chaos-testing' and s.get('name') == 'chaos-controller-manager') or
                   (s.get('kind') == 'User' and s.get('name') == CONTROLLER) or
                   (s.get('kind') == 'Group' and s.get('name') in ['system:serviceaccounts:chaos-testing', 'system:serviceaccounts', 'system:authenticated'])
                   for s in binding.get('subjects', [])):
            continue
        ref = binding['roleRef']; namespace = binding['metadata'].get('namespace')
        role = read(('clusterrole ' if ref['kind'] == 'ClusterRole' else 'role ') + ref['name'], None if ref['kind'] == 'ClusterRole' else namespace)
        for rule in role.get('rules', []):
            production_scope = binding['kind'] == 'ClusterRoleBinding' or namespace == 'jitsi'
            sensitive = {'secrets', 'serviceaccounts', 'serviceaccounts/token', 'deployments', 'statefulsets', 'replicasets', 'daemonsets', 'roles', 'rolebindings', 'clusterroles', 'clusterrolebindings', '*'}
            if production_scope and sensitive.intersection(rule.get('resources', [])):
                require(not any(v in ['create', 'patch', 'update', 'delete', 'deletecollection', '*'] for v in rule.get('verbs', [])), 'CONTROLLER_PRODUCTION_MUTATION_REFUSED')
                if 'secrets' in rule.get('resources', []) or '*' in rule.get('resources', []):
                    require(not any(v in ['get', 'list', 'watch', '*'] for v in rule.get('verbs', [])), 'CONTROLLER_SECRET_READ_REFUSED')
            require(not any(r.startswith('pods/') and '*' in r for r in rule.get('resources', [])), 'CONTROLLER_WILDCARD_SUBRESOURCE_REFUSED')
            if any(r == '*' or r.startswith('pods') for r in rule.get('resources', [])) and (any(v in ['delete', 'deletecollection', 'create', 'patch', 'update', '*'] for v in rule.get('verbs', [])) or any(r in ['pods/exec', 'pods/attach', 'pods/eviction'] for r in rule.get('resources', []))):
                require(binding['kind'] == 'RoleBinding' and namespace == 'jitsi' and
                        rule.get('apiGroups') == [''] and rule.get('resources') == ['pods'] and
                        rule.get('verbs') == ['delete'] and rule.get('resourceNames') == [name], 'CONTROLLER_POD_RIGHTS_TOO_BROAD')
                found = True
    require(found, 'EXACT_CONTROLLER_DELETE_RIGHT_REQUIRED')


def injection_verified(status):
    records = status.get('experiment', {}).get('containerRecords', [])
    require(len(records) <= 1 and sum(r.get('injectedCount', 0) for r in records) <= 1, 'MULTIPLE_INJECTIONS_REFUSED')
    return (any(c.get('type') == 'AllInjected' and c.get('status') == 'True' for c in status.get('conditions', [])) and
            len(records) == 1 and records[0].get('phase') == 'Injected' and records[0].get('injectedCount') == 1)


def sanitize_log(log):
    return '\n'.join(re.findall(r'BUILD SUCCESS|Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+', log)) + '\n'


def folder():
    return Path(os.environ['RUNNER_TEMP']) / ('jitsi-experiment-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT'])


def cleanup():
    path = folder() / 'ownership.json'
    if not path.exists():
        return
    state = json.loads(path.read_text())
    expected = os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']
    require(state.get('run') == expected, 'CLEANUP_OWNER_MISMATCH')
    if state['mode'] == 'malleus':
        require(state['name'] == 'm2-load-' + expected and state['namespace'] == 'jitsi-load-test', 'CLEANUP_SCOPE_REFUSED')
        releases = json.loads(run(['helm', 'list', '-a', '-n', 'jitsi-load-test', '-o', 'json']))
        if any(r['name'] == state['name'] for r in releases):
            run(['helm', 'uninstall', state['name'], '-n', 'jitsi-load-test', '--wait', '--timeout', '90s'], timeout=120)
    else:
        require(state['name'] == 'm2-chaos-' + expected and state['namespace'] == 'jitsi', 'CLEANUP_SCOPE_REFUSED')
        raw = kubectl('-n', 'jitsi', 'get', 'podchaos', state['name'], '--ignore-not-found', '-o', 'json')
        if raw.strip():
            obj = json.loads(raw)
            require(obj['metadata'].get('labels', {}).get('m2-experiment-run') == expected, 'CLEANUP_OWNER_MISMATCH')
            kubectl('-n', 'jitsi', 'delete', 'podchaos', state['name'], '--wait=true', '--timeout=60s')
    path.unlink()


def access_allowed(verb, resource, namespace):
    resource, _, subresource = resource.partition('/')
    resource, _, group = resource.partition('.')
    question = f'{verb}:{resource}:{subresource or "-"}:{namespace}'
    review = {
        'apiVersion': 'authorization.k8s.io/v1',
        'kind': 'SelfSubjectAccessReview',
        'spec': {'resourceAttributes': {
            'namespace': namespace, 'verb': verb, 'group': group,
            'resource': resource, 'subresource': subresource,
        }},
    }
    path = '/apis/authorization.k8s.io/v1/selfsubjectaccessreviews'
    response = json.loads(kubectl('create', '--raw', path, '-f', '-', data=json.dumps(review)))
    status = response.get('status')
    require(isinstance(status, dict) and not status.get('evaluationError') and type(status.get('allowed')) is bool,
            'ACCESS_REVIEW_INCONCLUSIVE ' + question)
    return status['allowed']


def cleanup_permissions(mode):
    # Refuse to create anything if the identity cannot clean it up later.
    if mode == 'malleus':
        namespace = 'jitsi-load-test'
        checks = [(v, r) for r in ['configmaps', 'secrets', 'services', 'deployments.apps', 'jobs.batch']
                  for v in ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']]
        checks += [('get', 'pods'), ('list', 'pods'), ('get', 'pods/log'), ('create', 'pods/portforward'), ('list', 'replicasets.apps')]
    else:
        namespace = 'jitsi'
        checks = [(v, 'podchaos.chaos-mesh.org') for v in ['get', 'create', 'delete']]
    for verb, resource in checks:
        require(access_allowed(verb, resource, namespace),
                f'REQUIRED_EXECUTION_OR_CLEANUP_PERMISSION_MISSING {verb}:{resource}')


def execute(mode):
    guard(mode)
    require(run(['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)']).strip() == ACCOUNT, 'DEDICATED_IDENTITY_REQUIRED')
    credentials = json.loads(Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS']).read_text())
    require(credentials.get('type') == 'external_account' and 'private_key' not in credentials, 'KEYLESS_REQUIRED')
    identity = json.loads(kubectl('auth', 'whoami', '-o', 'json'))['status']['userInfo']['username']
    require(identity == ACCOUNT, 'KUBERNETES_IDENTITY_MISMATCH')
    # Experiment identity must not directly mutate any production Pod.
    for verb in ['delete', 'deletecollection', 'patch', 'update', 'create']:
        require(not access_allowed(verb, 'pods', 'jitsi'),
                f'PRODUCTION_POD_MUTATION_RIGHT_REFUSED {verb}:pods')
    for verb, resource in [('create', 'pods/exec'), ('get', 'pods/exec'), ('create', 'pods/eviction'), ('get', 'secrets')]:
        require(not access_allowed(verb, resource, 'jitsi'),
                f'SENSITIVE_PRODUCTION_RIGHT_REFUSED {verb}:{resource}')
    cleanup_permissions(mode)
    before = production(); capacity(projected=True); https()
    jvb = [n for n, p in before.items() if p['component'] == 'jvb']
    require(len(jvb) == 1, 'ONE_JVB_REQUIRED')
    forward('pod/' + jvb[0], 'jitsi', 18080, 8080)
    require_idle(stats())
    out = folder(); out.mkdir(mode=0o700, exist_ok=True)
    run_id = os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']
    summary = {'mode': mode, 'success': False, 'video_samples': 0, 'cleanup': False}
    try:
        if mode == 'malleus':
            require(read('namespace jitsi-load-test')['metadata']['name'] == 'jitsi-load-test', 'PRECREATED_TEST_NAMESPACE_REQUIRED')
            require(not read('pods', 'jitsi-load-test')['items'], 'TEST_NAMESPACE_NOT_EMPTY')
            releases = json.loads(run(['helm', 'list', '-a', '-n', 'jitsi-load-test', '-o', 'json']))
            require(not releases, 'EXISTING_TEST_RELEASE_REFUSED')
            name = 'm2-load-' + run_id
            import yaml
            rendered = run(['helm', 'template', name, 'charts/jitsi-load-test', '-n', 'jitsi-load-test',
                            '-f', 'tests/load/values-video-2x90.yaml', '-f', 'tests/load/values-video-2x90-low-cpu.yaml'])
            verify_load_render([d for d in yaml.safe_load_all(rendered) if d], name)
            (out / 'ownership.json').write_text(json.dumps({'run': run_id, 'mode': mode, 'name': name, 'namespace': 'jitsi-load-test'}))
            run(['helm', 'install', name, 'charts/jitsi-load-test', '-n', 'jitsi-load-test',
                 '-f', 'tests/load/values-video-2x90.yaml', '-f', 'tests/load/values-video-2x90-low-cpu.yaml',
                 '--set', 'malleus.suspend=true', '--wait', '--timeout', '180s'], timeout=210)
            forward('service/' + name + '-selenium', 'jitsi-load-test', 14444, 4444)
            spec = importlib.util.spec_from_file_location('light', ROOT / 'scripts/run-malleus-light.py')
            light = importlib.util.module_from_spec(spec); spec.loader.exec_module(light)
            light.GRID = 'http://127.0.0.1:14444'; light.VIDEO_MODE = True
            guard(mode); require_idle(stats()); stable(before, production())
            kubectl('-n', 'jitsi-load-test', 'patch', 'job', name + '-malleus', '--type=merge', '-p', '{"spec":{"suspend":false}}')
        else:
            name = 'm2-chaos-' + run_id
            approved = os.environ.get('APPROVED_WEB_NAME', ''); uid = os.environ.get('APPROVED_WEB_UID', '')
            exact_web(before, approved, uid)
            require(kubectl('get', 'crd', 'podchaos.chaos-mesh.org', '-o', 'name').strip(), 'PREINSTALLED_CHAOS_REQUIRED')
            controller = read('deployment chaos-controller-manager', 'chaos-testing')
            require(controller.get('status', {}).get('readyReplicas') == 1, 'CONTROLLER_NOT_READY')
            require(controller['spec']['template']['spec'].get('serviceAccountName') == 'chaos-controller-manager', 'UNEXPECTED_CONTROLLER_IDENTITY')
            pod_spec = controller['spec']['template']['spec']
            require(not pod_spec.get('hostNetwork') and not pod_spec.get('hostPID') and
                    not any('hostPath' in v for v in pod_spec.get('volumes', [])) and
                    len(pod_spec['containers']) == 1 and
                    not pod_spec['containers'][0].get('securityContext', {}).get('privileged'), 'UNSAFE_CONTROLLER')
            require(not read('daemonsets', 'chaos-testing')['items'], 'CHAOS_DAEMON_REFUSED')
            controller_permissions(approved)
            manifest = experiment(approved, uid, run_id)
            guard(mode); exact_web(production(), approved, uid); require_idle(stats())
            (out / 'ownership.json').write_text(json.dumps({'run': run_id, 'mode': mode, 'name': name, 'namespace': 'jitsi'}))
            kubectl('create', '-f', '-', data=json.dumps(manifest))
        completed = False
        injected_seen = False
        start = time.monotonic()
        with (out / 'metrics.jsonl').open('w') as output:
            while time.monotonic() - start < (240 if mode == 'malleus' else 180):
                sample = {'timestamp': datetime.now(timezone.utc).isoformat(), 'elapsed_s': round(time.monotonic() - start, 3), 'nodes': capacity(), 'jvb': stats()}
                sample['production_pods_metrics'] = pod_metrics('jitsi')
                if mode == 'malleus':
                    sample['test_pods_metrics'] = pod_metrics('jitsi-load-test')
                require(sample['jvb'].get('ice_failed', 0) == 0 and sample['jvb'].get('healthy') is True, 'JVB_UNHEALTHY')
                require(sample['jvb'].get('participants', 0) <= (2 if mode == 'malleus' else 0), 'UNEXPECTED_PARTICIPANTS')
                if mode == 'malleus':
                    stable(before, production())
                    sample['browsers'] = light.browser_stats()
                    if light.video_verified({'browsers': sample['browsers'], 'jvb-0': sample['jvb']}, 2):
                        summary['video_samples'] += 1
                    job = read('job ' + name + '-malleus', 'jitsi-load-test')
                    failed = any(c['type'] == 'Failed' and c['status'] == 'True' for c in job.get('status', {}).get('conditions', []))
                    require(not failed, 'TEST_JOB_FAILED')
                    complete = any(c['type'] == 'Complete' and c['status'] == 'True' for c in job.get('status', {}).get('conditions', []))
                else:
                    fault = read('podchaos ' + name, 'jitsi')
                    require(fault['metadata'].get('labels', {}).get('m2-experiment-run') == run_id, 'EXPERIMENT_OWNER_CHANGED')
                    injected_seen = injection_verified(fault.get('status', {})) or injected_seen
                    sample['injection_confirmed'] = injected_seen
                    summary['injection_confirmed'] = injected_seen
                    # Web may be temporarily absent; other components must stay ready and unchanged.
                    current = read('pods', 'jitsi')['items']
                    others = [p for p in current if p['metadata'].get('labels', {}).get('app.kubernetes.io/component') != 'web']
                    require(all(ready(p) for p in others), 'NON_WEB_NOT_READY')
                    snapshot = {p['metadata']['name']: {'uid': p['metadata']['uid'], 'component': p['metadata'].get('labels', {}).get('app.kubernetes.io/component'),
                                'restarts': sum(c['restartCount'] for c in p['status'].get('containerStatuses', []))} for p in others}
                    stable(before, snapshot, chaos=True)
                    complete = injected_seen and any(p['metadata'].get('labels', {}).get('app.kubernetes.io/component') == 'web' and p['metadata']['uid'] != uid and ready(p) for p in current)
                    if complete:
                        sample['https_status'] = https()
                output.write(json.dumps(sample) + '\n'); output.flush()
                if complete:
                    completed = True
                    break
                time.sleep(5)
        require(completed, 'RECOVERY_OR_JOB_TIMEOUT')
        if mode == 'malleus':
            log = kubectl('-n', 'jitsi-load-test', 'logs', 'job/' + name + '-malleus', '--tail=200')
            (out / 'logs-sanitized.txt').write_text(sanitize_log(log))
            require(summary['video_samples'] >= 3, 'VIDEO_EVIDENCE_INSUFFICIENT')
            summary['continuous_90s_video_validated'] = False
        https(); stable(before, production(), chaos=(mode == 'chaos'))
        summary['success'] = True
    finally:
        if mode == 'malleus' and (out / 'ownership.json').exists():
            try:
                log = kubectl('-n', 'jitsi-load-test', 'logs', 'job/' + name + '-malleus', '--tail=200')
                (out / 'logs-sanitized.txt').write_text(sanitize_log(log))
            except Exception:
                pass
        try:
            cleanup(); summary['cleanup'] = True
        except BaseException:
            summary['success'] = False
            raise
        finally:
            (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['malleus', 'chaos'])
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--cleanup', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(RuntimeError('CANCELLED')))
    try:
        if args.preflight:
            guard(args.mode)
        elif args.configure:
            spec = importlib.util.spec_from_file_location('diagnostic', ROOT / 'scripts/diagnose-cd.py')
            diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
            diagnostic.configure_gke(guard_fn=lambda: guard(args.mode), filename='jitsi-experiment-kubeconfig')
        elif args.cleanup:
            context(os.environ, args.mode); cleanup()
        else:
            execute(args.mode)
    except Exception as error:
        # No raw Kubernetes, logs, credentials or ICE candidates in public output.
        print('Controlled experiment failed: ' + (str(error) if type(error) is RuntimeError else type(error).__name__))
        raise SystemExit(1) from None
    finally:
        for p in PROCESSES:
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()


if __name__ == '__main__':
    main()
