#!/usr/bin/env python3
"""Verifie les invariants reseau du profil GKE rendu, pas son fonctionnement."""
import ipaddress
import sys
from urllib.parse import urlparse
import yaml

def require(condition, message):
    if not condition:
        raise SystemExit(message)

docs = [d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
common = next(d["data"] for d in docs if d["kind"] == "ConfigMap" and "PUBLIC_URL" in (d.get("data") or {}))
web = next(d["data"] for d in docs if d["kind"] == "ConfigMap" and "XMPP_BOSH_URL_BASE" in (d.get("data") or {}))
public = len(sys.argv) > 2 and sys.argv[2] == "--public"
ready = len(sys.argv) > 2 and sys.argv[2] == "--ready"
if public:
    url = urlparse(common["PUBLIC_URL"])
    require(url.scheme == "https" and url.hostname and url.netloc == url.hostname and url.path in ("", "/") and not url.query and not url.fragment, "URL publique HTTPS avec DNS requise")
    ingress = next((d for d in docs if d["kind"] == "Ingress"), None)
    require(ingress is not None, "Ingress manquant")
    require(ingress["metadata"].get("annotations", {}).get("kubernetes.io/ingress.class") == "gce", "Ingress GCE attendu")
    require(any(r["host"] == url.hostname for r in ingress["spec"]["rules"]), "DNS Ingress / URL differents")
    require(any(url.hostname in t["hosts"] and t.get("secretName") for t in ingress["spec"].get("tls", [])), "Reference TLS manquante")
    bridge = next(d for d in docs if d["kind"] == "Deployment" and d["metadata"].get("labels", {}).get("app.kubernetes.io/component") == "jvb")
    env = bridge["spec"]["template"]["spec"]["containers"][0]["env"]
    advertised = next((e.get("value", "") for e in env if e["name"] == "JVB_ADVERTISE_IPS"), "")
    require(bool(advertised), "IP publique annoncee par JVB manquante")
    for value in advertised.split(","):
        ip = ipaddress.IPv4Address(value)
        require(ip.is_global and not ip.is_multicast, "IP JVB publique unicast requise")
else:
    require(common["PUBLIC_URL"] == "http://localhost:8081", "URL locale incoherente")
require(common["ENABLE_XMPP_WEBSOCKET"] == "false", "Profil attendu : BOSH")
require(web["DISABLE_HTTPS"] == "1", "HTTP interne Web attendu")
require(web["XMPP_BOSH_URL_BASE"].startswith("http://") and web["XMPP_BOSH_URL_BASE"].endswith(":5280"), "Proxy BOSH interne incoherent")
conffiles = next(d["data"] for d in docs if d["kind"] == "ConfigMap" and "custom-config.js" in (d.get("data") or {}))
require("config.bosh = window.location.origin + '/http-bind';" in conffiles["custom-config.js"], "BOSH doit suivre l'origine du navigateur")
web_deploy = next(d for d in docs if d["kind"] == "Deployment" and d["metadata"]["name"].endswith("-web"))
require(any(m.get("mountPath") == "/config/custom-config.js" and m.get("subPath") == "custom-config.js"
            for m in web_deploy["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]), "Surcharge BOSH non montee")
bridge_config = next(d["data"] for d in docs if d["kind"] == "ConfigMap" and d["metadata"]["name"].endswith("-jvb"))
require(bridge_config.get("JVB_DISABLE_STUN") == "true", "STUN doit etre desactive avec une IP LB explicite")
# Contrat des commandes du guide : release jitsi, namespace jitsi.
expected = {
    ("Service", "jitsi-jitsi-meet-web"),
    ("Service", "jitsi-jitsi-meet-jvb"),
    ("Service", "jitsi-jitsi-meet-prosody"),
    ("Deployment", "jitsi-jitsi-meet-web"),
    ("Deployment", "jitsi-jitsi-meet-jicofo"),
    ("Deployment", "jitsi-jitsi-meet-jvb-0"),
    ("StatefulSet", "jitsi-jitsi-meet-prosody"),
}
actual = {(d["kind"], d["metadata"]["name"]) for d in docs}
require(expected <= actual, "Noms des ressources incompatibles avec les commandes du guide")
services = [d for d in docs if d["kind"] == "Service"]
jvb = next(d for d in services if d["metadata"]["name"].endswith("-jvb"))
require(jvb["spec"]["type"] == "LoadBalancer", "Exposition JVB publique manquante")
require(any(p["protocol"] == "UDP" and p["port"] == 10000 for p in jvb["spec"]["ports"]), "UDP 10000 manquant")
bridges = [d for d in docs if d["kind"] == "Deployment" and d["metadata"].get("labels", {}).get("app.kubernetes.io/component") == "jvb"]
require(len(bridges) == 1 and bridges[0]["spec"]["replicas"] == 1, "Un seul bridge attendu")
pod = bridges[0]["spec"]["template"]
require(all(pod["metadata"]["labels"].get(k) == v for k, v in jvb["spec"]["selector"].items()), "Selecteur Service JVB incoherent")
container = pod["spec"]["containers"][0]
if ready:
    advertised = next((e.get("value", "") for e in container["env"] if e["name"] == "JVB_ADVERTISE_IPS"), "")
    require(bool(advertised), "Phase 2 : IP publique annoncee manquante")
    for value in advertised.split(","):
        ip = ipaddress.IPv4Address(value)
        require(ip.is_global and not ip.is_multicast, "IP JVB publique unicast requise")
require(any(p["name"] == "rtp-udp-0" and p["containerPort"] == 10000 and p["protocol"] == "UDP" for p in container["ports"]), "Port UDP du pod incoherent")
require(any(p.get("targetPort") == "rtp-udp-0" for p in jvb["spec"]["ports"]), "targetPort JVB incoherent")
require(any(e["name"] == "JVB_PORT" and e.get("value") == "10000" for e in container["env"]), "JVB_PORT incoherent")
web_service = next(d for d in services if d["metadata"]["name"].endswith("-web"))
require(web_service["spec"]["type"] == ("NodePort" if public else "ClusterIP"), "Type Service Web incoherent avec le profil")
if not public:
    require(not any(d["kind"] in ("Ingress", "Gateway", "HTTPRoute") for d in docs), "Web doit rester prive sans Ingress/Gateway")
print("Invariants du rendu GKE : OK ; aucun test reseau, DNS ou certificat")
