#!/usr/bin/env python3
"""Private plan transport: AES-256-CBC/PBKDF2, then HMAC-SHA256 (separate key).
No Terraform or cloud operation. Raw plans/states never leave the encrypted payload.
"""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def require(ok):
    if not ok:
        raise SystemExit('Reviewed plan bundle refused; private details suppressed.')


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def identity(env):
    result = {k: env.get(k, '') for k in ['GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT']}
    require(re.fullmatch(r'[a-f0-9]{40}', result['GITHUB_SHA']) is not None)
    require(all(re.fullmatch(r'[0-9]+', result[k]) for k in ['GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT']))
    return result


def key_material(key):
    require(re.fullmatch(r'[a-fA-F0-9]{128}', key or '') is not None)
    raw = bytes.fromhex(key)
    return raw[:32], raw[32:]


def crypt(data, key, decrypt=False):
    with tempfile.TemporaryDirectory(prefix='tf-plan-crypto.') as tmp:
        path = Path(tmp) / 'pass'
        path.write_text(key.hex() + '\n'); path.chmod(0o600)
        args = ['openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-iter', '200000', '-pass', 'file:' + str(path)]
        if decrypt:
            args.append('-d')
        result = subprocess.run(args, input=data, capture_output=True, timeout=30)
        require(result.returncode == 0)
        return result.stdout


def seal(plan, state, changes, key, env, destination):
    enc, mac = key_material(key)
    review = dict(identity(env), plan_sha256=hashlib.sha256(plan).hexdigest(),
                  state_sha256=hashlib.sha256(canonical(state)).hexdigest(), changes=changes,
                  format='jitsi-reviewed-plan-v1')
    payload = canonical({'binary_plan': base64.b64encode(plan).decode(), 'state_before': state, 'review': review})
    encrypted = crypt(payload, enc)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    (destination / 'bundle.enc').write_bytes(encrypted)
    (destination / 'review.json').write_bytes(canonical(review))
    (destination / 'bundle.hmac').write_text(hmac.new(mac, canonical(review) + b'\n' + encrypted, hashlib.sha256).hexdigest())
    for path in destination.iterdir():
        path.chmod(0o600)
    return review


def unseal(directory, key, env, expected_digest):
    require({p.name for p in directory.iterdir()} == {'bundle.enc', 'review.json', 'bundle.hmac'})
    require(all(p.is_file() and not p.is_symlink() for p in directory.iterdir()))
    enc, mac = key_material(key)
    encrypted = (directory / 'bundle.enc').read_bytes()
    review = json.loads((directory / 'review.json').read_text())
    actual = hmac.new(mac, canonical(review) + b'\n' + encrypted, hashlib.sha256).hexdigest()
    require(hmac.compare_digest(actual, (directory / 'bundle.hmac').read_text()))
    require(review.get('format') == 'jitsi-reviewed-plan-v1')
    require(all(review.get(k) == v for k, v in identity(env).items()))
    require(re.fullmatch(r'[a-f0-9]{64}', expected_digest or '') is not None)
    require(review.get('plan_sha256') == expected_digest == env.get('TF_REVIEWED_PLAN_SHA256'))
    payload = json.loads(crypt(encrypted, enc, decrypt=True))
    require(payload['review'] == review)
    plan = base64.b64decode(payload['binary_plan'], validate=True)
    state = payload['state_before']
    require(hashlib.sha256(plan).hexdigest() == expected_digest)
    require(hashlib.sha256(canonical(state)).hexdigest() == review['state_sha256'])
    return plan, state, review
