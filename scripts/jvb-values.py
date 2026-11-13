#!/usr/bin/env python3
"""Genere une surcharge locale pour JVB a partir de l'IPv4 reelle du Service."""
import argparse
import ipaddress
import sys
import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--jvb-ip", required=True)
args = parser.parse_args()
try:
    ip = ipaddress.IPv4Address(args.jvb_ip)
except ValueError:
    parser.error("IPv4 invalide")
if not ip.is_global or ip.is_multicast:
    parser.error("Une IPv4 publique unicast du LoadBalancer est requise")
yaml.safe_dump({"jvb": {"publicIPs": [str(ip)]}}, sys.stdout, sort_keys=False)
