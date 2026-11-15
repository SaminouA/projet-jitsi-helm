#!/bin/sh
# Collecte uniquement : lectures Kubernetes et GET local des statistiques JVB.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 - "$script_dir/.." "$@" <<'PY'
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

root = Path(sys.argv[1]).resolve()
parser = argparse.ArgumentParser(description="Collecte Jitsi en lecture seule, toutes les 15 secondes.")
parser.add_argument("--scenario", required=True, help="Nom descriptif, sans chemin")
parser.add_argument("--duration", type=int, default=300, help="Duree en secondes (defaut : 300)")
parser.add_argument("--namespace", default="jitsi")
parser.add_argument("--context", help="Contexte Kubernetes ; defaut : contexte actuel, ensuite fixe")
parser.add_argument("--once", action="store_true", help="Un seul releve, pour verifier la collecte")
a = parser.parse_args(sys.argv[2:])
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", a.scenario):
    parser.error("Scenario : 1 a 80 caracteres alphanumeriques, point, tiret ou underscore")
if a.duration <= 0:
    parser.error("La duree doit etre strictement positive")
if not shutil.which("kubectl"):
    parser.error("kubectl absent du PATH")
if not a.context:
    try:
        a.context = subprocess.check_output(
            ["kubectl", "config", "current-context"], text=True, stderr=subprocess.DEVNULL,
            timeout=10).strip()
    except (subprocess.SubprocessError, OSError):
        parser.error("Impossible de lire le contexte Kubernetes")
if not a.context:
    parser.error("Contexte Kubernetes vide")

stop = threading.Event()
def interrupted(signum, frame):
    stop.set()
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, interrupted)

def utc():
    return datetime.now(timezone.utc).isoformat()

# Dossier distinct a chaque execution ; aucun ecrasement de mesures existantes.
folder = root / "tests" / "results" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + a.scenario)
folder.mkdir(parents=True, mode=0o700)
os.chmod(folder, 0o700)
def open_private(name):
    return os.fdopen(os.open(folder / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", buffering=1)
def write(handle, obj):
    handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
    handle.flush()

base = ["kubectl", "--context", a.context, "--namespace", a.namespace, "--request-timeout=8s"]
def query(name, args):
    timestamp = utc()
    try:
        p = subprocess.run(base + args, text=True, capture_output=True, timeout=12,
                           start_new_session=True)
        if p.returncode:
            return name, timestamp, None, {"kind": "command_failed", "returncode": p.returncode}
        return name, timestamp, json.loads(p.stdout), None
    except subprocess.TimeoutExpired:
        return name, timestamp, None, {"kind": "timeout"}
    except (ValueError, OSError):
        return name, timestamp, None, {"kind": "invalid_json_or_command_unavailable"}

commands = {
    "nodes": ["get", "--raw", "/apis/metrics.k8s.io/v1beta1/nodes"],
    "pods_metrics": ["get", "--raw", "/apis/metrics.k8s.io/v1beta1/namespaces/" + a.namespace + "/pods"],
    "pods_status": ["get", "pods", "-o", "json"],
    "jvb": ["exec", "deployment/jitsi-jitsi-meet-jvb-0", "--", "curl", "--max-time", "8", "-fsS",
            "http://127.0.0.1:8080/colibri/stats"],
}

def filtered(name, data):
    if name in ("nodes", "pods_metrics"):
        return [{"name": item["metadata"]["name"], "timestamp": item.get("timestamp"),
                 "window": item.get("window"),
                 **({"usage": item.get("usage", {})} if name == "nodes" else
                    {"containers": [{"name": c["name"], "usage": c.get("usage", {})}
                                    for c in item.get("containers", [])]})}
                for item in data.get("items", [])]
    if name == "pods_status":
        return [{"name": p["metadata"]["name"], "node": p.get("spec", {}).get("nodeName"),
                 "phase": p.get("status", {}).get("phase"),
                 "ready": any(c.get("type") == "Ready" and c.get("status") == "True"
                              for c in p.get("status", {}).get("conditions", [])),
                 "containers": [{"name": c["name"], "ready": c.get("ready"),
                                 "restarts": c.get("restartCount", 0),
                                 "state": next(iter(c.get("state", {})), "unknown"),
                                 "last_termination_reason": c.get("lastState", {}).get("terminated", {}).get("reason")}
                                for c in p.get("status", {}).get("containerStatuses", [])]}
                for p in data.get("items", [])]
    # Seulement les compteurs numeriques/booleens, sans identifiants de session.
    return {k: v for k, v in data.items() if isinstance(v, (int, float, bool))}

metadata = {"scenario": a.scenario, "context": a.context, "namespace": a.namespace,
            "started_at": utc(), "duration_seconds": a.duration, "interval_seconds": 15,
            "once": a.once, "units": {"cpu_memory": "quantites Kubernetes brutes (ex. n, Ki)",
            "jvb": "valeurs brutes de /colibri/stats ; aucune unite deduite"},
            "scope": "mesures d'observation ; aucun generateur de charge"}
with open_private("metadata.json") as f:
    f.write(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
print("Collecte :", folder, flush=True)
print("Contexte :", a.context, "| Ctrl+C pour arreter et conserver les mesures.", flush=True)
start = time.monotonic()
next_tick = start
samples = 0
failures = 0
exit_code = 0
try:
    with open_private("metrics.jsonl") as metrics, open_private("errors.jsonl") as errors:
        with ThreadPoolExecutor(max_workers=4) as pool:
            while not stop.is_set() and time.monotonic() - start < a.duration:
                sampled_at = utc()
                record = {"timestamp": sampled_at, "elapsed_seconds": round(time.monotonic() - start, 3),
                          "scenario": a.scenario, "data": {}, "observed_at": {}, "errors": {}}
                futures = [pool.submit(query, name, args) for name, args in commands.items()]
                for future in futures:
                    name, observed, data, error = future.result()
                    record["observed_at"][name] = observed
                    if error is None:
                        try:
                            record["data"][name] = filtered(name, data)
                        except (TypeError, KeyError, AttributeError):
                            error = {"kind": "unexpected_response_shape"}
                    if error is not None:
                        failures += 1
                        record["errors"][name] = error
                        write(errors, {"timestamp": observed, "source": name, **error})
                record["finished_at"] = utc()
                write(metrics, record)
                samples += 1
                print("Releve", samples, "| erreurs :", len(record["errors"]), flush=True)
                if a.once:
                    break
                next_tick += 15
                # Ne pas accumuler de requetes si le cluster repond lentement.
                while next_tick < time.monotonic():
                    next_tick += 15
                stop.wait(max(0, min(next_tick, start + a.duration) - time.monotonic()))
except Exception as exc:
    # Ne jamais afficher une reponse brute ou un stderr potentiellement sensible.
    print("Collecte interrompue par erreur :", type(exc).__name__, file=sys.stderr)
    exit_code = 1
finally:
    with open_private("summary.json") as f:
        f.write(json.dumps({"ended_at": utc(), "samples": samples, "query_failures": failures,
                            "interrupted": stop.is_set(), "elapsed_seconds": round(time.monotonic() - start, 3)}, indent=2) + "\n")
    print("Mesures conservees dans", folder, flush=True)
if failures:
    print("Des sources ont echoue : consulter errors.jsonl.", file=sys.stderr)
sys.exit(exit_code or (2 if failures else 0))
PY
