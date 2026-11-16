#!/usr/bin/env bash
# Mutations UNIQUEMENT dans la section Helm. Ne pas lancer pendant la preparation.
set +x
set -euo pipefail
umask 077
# workflow_run : GITHUB_REF decrit le workflow CD, pas la branche de la CI.
# Le payload est reverifie en defense en profondeur, avant tout acces cloud.
python3 scripts/check-cd-event.py
[[ $(git rev-parse HEAD) == "$EXPECTED_SHA" ]]
check_main() {
  local current
  current=$(gh api repos/SaminouA/projet-jitsi-helm/git/ref/heads/main --jq '.object.sha')
  [[ "$current" == "$EXPECTED_SHA" && $(git rev-parse HEAD) == "$EXPECTED_SHA" ]] || { echo 'Commit main depasse : deploiement refuse.' >&2; exit 1; }
}
check_main
[[ $(kubectl config current-context) == gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster ]]
# Verifier l'identite Kubernetes effective, pas seulement le nom du contexte.
identity=$(kubectl auth whoami -o json | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"]["userInfo"]["username"])')
[[ "$identity" == github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com ]] || {
  echo 'Identite Kubernetes inattendue : deploiement refuse.' >&2; exit 1;
}
access_profile=${JITSI_ACCESS_PROFILE:?Profil CD explicite requis : localhost ou public-edge}
profile_values=()
case "$access_profile" in
  localhost) profile_values=(--set-string publicURL=http://localhost:8081) ;;
  public-edge)
    [[ ${JITSI_EDGE_CD_ENABLED:-false} == true ]] || {
      echo 'Profil public non active : bootstrap et migration a autoriser.' >&2; exit 1;
    }
    [[ $(kubectl auth can-i get persistentvolumeclaims/jitsi-edge-data -n jitsi 2>/dev/null) == yes ]] || {
      echo 'Lecture PVC requise pour la CD edge.' >&2; exit 1;
    }
    ;;
  *) echo 'Profil CD inconnu.' >&2; exit 1 ;;
esac
namespace=jitsi
release=jitsi
chart=./charts-officiels/jitsi-meet
# Aucun namespace, cluster, LB ou ressource supplementaire ne sera cree par cette CD.
for resource in configmaps secrets services serviceaccounts deployments.apps statefulsets.apps; do
  for verb in get list watch create update patch delete; do
    [[ $(kubectl auth can-i "$verb" "$resource" -n "$namespace" 2>/dev/null) == yes ]] || {
      echo "Permission RBAC manquante : $verb $resource dans $namespace" >&2; exit 1;
    }
  done
done
for resource in pods replicasets.apps; do
  for verb in get list watch; do
    [[ $(kubectl auth can-i "$verb" "$resource" -n "$namespace" 2>/dev/null) == yes ]] || {
      echo "Permission RBAC manquante pour Helm --wait : $verb $resource" >&2; exit 1;
    }
  done
done
CD_TMP_DIR=$(mktemp -d "$RUNNER_TEMP/jitsi-cd.XXXXXX")
export CD_TMP_DIR
# Nettoyage local et seconde protection dans l'etape always() du workflow.
printf 'CD_TMP_DIR=%s\n' "$CD_TMP_DIR" >> "$GITHUB_ENV"
trap 'rm -rf -- "$CD_TMP_DIR"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Ne pas afficher les erreurs brutes d'outils manipulant les valeurs sensibles.
quiet() {
  local label=$1; shift
  if ! "$@" >"$CD_TMP_DIR/command.out" 2>"$CD_TMP_DIR/command.err"; then
    echo "Echec : $label. Sorties sensibles non publiees ; aucun artefact sauvegarde." >&2
    exit 1
  fi
}
quiet 'lecture de la release existante' helm list -n "$namespace" --filter '^jitsi$' -o json
python3 - "$CD_TMP_DIR/command.out" <<'PY'
import json, sys
releases = json.load(open(sys.argv[1]))
if len(releases) != 1 or releases[0]['status'] != 'deployed':
    raise SystemExit('La CD initiale exige la release jitsi deja deployee ; bootstrap manuel distinct.')
PY
kubectl -n "$namespace" get service jitsi-jitsi-meet-jvb -o json > "$CD_TMP_DIR/service.json"
python3 - "$CD_TMP_DIR/service.json" > "$CD_TMP_DIR/ip" <<'PY'
import json, ipaddress, sys
service = json.load(open(sys.argv[1]))
assert service['spec']['type'] == 'LoadBalancer', 'LoadBalancer JVB existant requis'
ip = service.get('status', {}).get('loadBalancer', {}).get('ingress', [{}])[0].get('ip', '')
address = ipaddress.IPv4Address(ip)
assert address.is_global and not address.is_multicast, 'IPv4 publique attribuee requise'
print(ip)
PY
python3 scripts/jvb-values.py --jvb-ip "$(cat "$CD_TMP_DIR/ip")" > "$CD_TMP_DIR/network.yaml"
edge_check=()
if [[ "$access_profile" == public-edge ]]; then
  # Generateur rejette les domaines de test ; fichiers dans le repertoire prive.
  (
    cd "$CD_TMP_DIR"
    python3 "$GITHUB_WORKSPACE/scripts/public-values.py" \
      --domain "${JITSI_PUBLIC_DOMAIN:?Domaine reel manquant}" \
      --address-name "${JITSI_EDGE_ADDRESS_NAME:?Reservation existante manquante}" --acme production
  )
  edge_values="$CD_TMP_DIR/deploy/local/edge.yaml"
  profile_values=(-f values-jitsi-public.yaml -f "$CD_TMP_DIR/deploy/local/jitsi.yaml")
  edge_check=(--edge)
  quiet 'lint edge' helm lint --strict charts/jitsi-edge -n jitsi -f "$edge_values"
  if ! helm template jitsi-edge charts/jitsi-edge -n jitsi -f "$edge_values" \
      > "$CD_TMP_DIR/edge-render.yaml" 2> "$CD_TMP_DIR/command.err"; then
    echo 'Rendu edge refuse.' >&2; exit 1
  fi
  python3 scripts/check-edge-live.py "$CD_TMP_DIR/edge-render.yaml" "$JITSI_PUBLIC_DOMAIN"
fi
# Aucun dechiffrement sur la VM pendant la preparation. Ce code est pour le runner.
quiet 'dechiffrement SOPS/KMS' sops --decrypt --output "$CD_TMP_DIR/secrets.yaml" values-secrets.sops.yaml
chmod 600 "$CD_TMP_DIR/secrets.yaml"
quiet 'lint Helm avec les valeurs fusionnees' helm lint --strict "$chart" \
  -f values-gke.yaml "${profile_values[@]}" -f "$CD_TMP_DIR/network.yaml" -f "$CD_TMP_DIR/secrets.yaml"
if ! helm template "$release" "$chart" -n "$namespace" --skip-tests \
  -f values-gke.yaml "${profile_values[@]}" -f "$CD_TMP_DIR/network.yaml" -f "$CD_TMP_DIR/secrets.yaml" \
  > "$CD_TMP_DIR/render.yaml" 2> "$CD_TMP_DIR/command.err"; then
  echo 'Rendu Helm refuse ; details sensibles non publies.' >&2; exit 1
fi
quiet 'invariants Web/BOSH et JVB' python3 scripts/check-render.py "$CD_TMP_DIR/render.yaml" --ready "${edge_check[@]}"
# Refuse les ressources ajoutees, les changements d'exposition et la rotation implicite.
python3 scripts/check-cd-render.py "$CD_TMP_DIR/render.yaml" "$CD_TMP_DIR/secrets.yaml"
check_main
if [[ "$access_profile" == public-edge ]]; then
  # Le preflight exige les objets existants : aucune installation edge implicite.
  quiet 'mise a jour edge existant' helm upgrade jitsi-edge charts/jitsi-edge -n jitsi \
    -f "$edge_values" --wait --timeout 5m --no-hooks --hide-notes
  quiet 'verification edge finale' python3 scripts/check-edge-live.py \
    "$CD_TMP_DIR/edge-render.yaml" "$JITSI_PUBLIC_DOMAIN" --after
fi
check_main
# Pas de --create-namespace, --force, --debug, --dry-run ou affichage de manifests.
quiet 'mise a jour Helm' helm upgrade --install "$release" "$chart" --namespace "$namespace" \
  -f values-gke.yaml "${profile_values[@]}" -f "$CD_TMP_DIR/network.yaml" -f "$CD_TMP_DIR/secrets.yaml" \
  --wait --timeout 10m --no-hooks --hide-notes
quiet 'verification finale des valeurs et de la disponibilite' \
  python3 scripts/check-cd-render.py "$CD_TMP_DIR/render.yaml" "$CD_TMP_DIR/secrets.yaml" --after
printf '%s\n' 'Deploiement Helm termine ; disponibilite et IP verifiees. Audio/video a tester separement.'
