#!/usr/bin/env python3
"""Inventaire APIs en lecture seule, a lancer par un operateur autorise."""
import json
import subprocess

PROJECT = 'project-fcf2ef91-c005-4910-a10'
REQUIRED = {'iam.googleapis.com', 'iamcredentials.googleapis.com', 'sts.googleapis.com',
            'cloudresourcemanager.googleapis.com', 'container.googleapis.com', 'cloudkms.googleapis.com'}


def missing_apis(enabled):
    return sorted(REQUIRED - set(enabled))


def main():
    p = subprocess.run(['gcloud', 'services', 'list', '--enabled', '--project=' + PROJECT,
                        '--format=json(config.name)'], capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise SystemExit('Inventaire APIs impossible : droits operateur Service Usage a verifier.')
    try:
        enabled = [row['config']['name'] for row in json.loads(p.stdout)]
    except (ValueError, KeyError, TypeError):
        raise SystemExit('Inventaire APIs illisible.') from None
    missing = missing_apis(enabled)
    for name in sorted(REQUIRED):
        print(name + ': ' + ('MANQUANTE' if name in missing else 'active'))
    if missing:
        raise SystemExit('Prerequis incomplets ; aucune API activee par ce controle.')
    print('Prerequis API presents ; aucun echange OIDC teste ici.')


if __name__ == '__main__':
    main()
