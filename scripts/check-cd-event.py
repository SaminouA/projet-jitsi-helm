#!/usr/bin/env python3
"""Valide le payload workflow_run ; ne depend pas de GITHUB_REF (branche CD)."""
import json
import os
from pathlib import Path
import re
import sys

REPOSITORY = 'SaminouA/projet-jitsi-helm'
CI_NAME = 'Validation Helm et Terraform'


def verify_event(payload, environment):
    run = payload.get('workflow_run') or {}
    expected = environment.get('EXPECTED_SHA', '')
    conditions = [
        environment.get('GITHUB_ACTIONS') == 'true',
        environment.get('GITHUB_EVENT_NAME') == 'workflow_run',
        environment.get('GITHUB_REPOSITORY') == REPOSITORY,
        environment.get('CD_ENABLE') == 'true',
        (payload.get('repository') or {}).get('full_name') == REPOSITORY,
        (run.get('repository') or {}).get('full_name') == REPOSITORY,
        (run.get('head_repository') or {}).get('full_name') == REPOSITORY,
        run.get('name') == CI_NAME,
        run.get('event') == 'push',
        run.get('status') == 'completed',
        run.get('conclusion') == 'success',
        run.get('head_branch') == 'main',
        re.fullmatch(r'[0-9a-f]{40}', expected) is not None,
        run.get('head_sha') == expected,
    ]
    if not all(conditions):
        raise SystemExit('Evenement CD refuse : CI main de confiance et SHA valide requis.')
    return expected


if __name__ == '__main__':
    try:
        payload = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        verify_event(payload, os.environ)
    except (KeyError, OSError, ValueError, TypeError, AttributeError):
        raise SystemExit('Evenement CD absent ou illisible : deploiement refuse.') from None
    print('Evenement workflow_run main et SHA valide : OK.')
