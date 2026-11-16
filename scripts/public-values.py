#!/usr/bin/env python3
"""Genere des valeurs locales depuis des identifiants reels, sans appel cloud."""
import argparse
import ipaddress
from pathlib import Path
import re
import yaml


def valid_domain(domain):
    if len(domain) > 253 or len(domain.split('.')) < 2:
        return False
    if any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', x) for x in domain.split('.')):
        return False
    if domain.endswith(('.invalid', '.test', '.example', '.localhost')):
        return False
    try:
        ipaddress.ip_address(domain)
        return False
    except ValueError:
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--address-name', required=True, help='Reservation IPv4 regionale EXISTANTE')
    parser.add_argument('--acme', choices=['staging', 'production'], default='staging')
    args = parser.parse_args()
    if not valid_domain(args.domain):
        parser.error('Nom DNS reel en minuscules requis ; les domaines de test sont refuses.')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,61}[a-z0-9]', args.address_name):
        parser.error('Nom de reservation GCP invalide.')
    directory = Path('deploy/local')
    directory.mkdir(parents=True, exist_ok=True)
    # Refus d'ecrasement de valeurs locales existantes.
    for name in ['jitsi.yaml', 'edge.yaml']:
        if (directory / name).exists():
            parser.error('Des valeurs locales existent deja ; revue manuelle requise.')
    (directory / 'jitsi.yaml').write_text(yaml.safe_dump({'publicURL': 'https://' + args.domain}))
    (directory / 'edge.yaml').write_text(yaml.safe_dump({'publicDomain': args.domain,
        'acmeEnvironment': args.acme, 'service': {'addressName': args.address_name}}))
    print('Valeurs creees dans deploy/local/ ; aucune ressource creee. Non deployees.')
