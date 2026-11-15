#!/usr/bin/env python3
"""Produit uniquement du YAML sur stdout ; aucune operation cloud."""
import argparse
import ipaddress
import re
import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--domain", required=True, help="Domaine DNS reel dont vous avez le controle")
parser.add_argument("--tls-secret", required=True, help="Secret TLS reel dans le namespace Jitsi")
parser.add_argument("--jvb-ip", required=True, help="IPv4 publique du LoadBalancer UDP JVB")
a = parser.parse_args()
labels = a.domain.split(".")
if (len(labels) < 2 or len(a.domain) > 253 or a.domain != a.domain.lower()
        or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x) for x in labels)
        or a.domain.endswith((".invalid", ".example", ".test", ".localhost"))):
    parser.error("Fournir un nom DNS reel, sans protocole, chemin ou port")
try:
    ipaddress.ip_address(a.domain)
except ValueError:
    pass
else:
    parser.error("Un nom DNS est requis, pas une adresse IP")
if (len(a.tls_secret) > 253 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x)
                                  for x in a.tls_secret.split("."))):
    parser.error("Nom de Secret Kubernetes invalide")
try:
    ip = ipaddress.IPv4Address(a.jvb_ip)
except ValueError:
    parser.error("IPv4 JVB invalide")
if not ip.is_global or ip.is_multicast:
    parser.error("Une IPv4 publique unicast est requise")
yaml.safe_dump({
    "publicURL": "https://" + a.domain,
    "web": {"service": {"type": "NodePort"}, "ingress": {
        "enabled": True,
        "annotations": {"kubernetes.io/ingress.class": "gce"},
        "hosts": [{"host": a.domain, "paths": ["/"]}],
        "tls": [{"hosts": [a.domain], "secretName": a.tls_secret}],
    }},
    "jvb": {"publicIPs": [str(ip)]},
}, stream=__import__("sys").stdout, sort_keys=False)
