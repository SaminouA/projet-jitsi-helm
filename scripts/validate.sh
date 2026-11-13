#!/bin/sh
# Validation locale partagee entre hooks et CI. Jamais de plan/apply/destroy.
set -eu
# Neutraliser les options pouvant rediriger les donnees ou injecter des arguments.
unset TF_DATA_DIR TF_WORKSPACE TF_CLI_ARGS TF_CLI_ARGS_init TF_CLI_ARGS_validate TF_CLI_ARGS_fmt
cd "$(git rev-parse --show-toplevel)"
for tool in helm terraform python3; do
    command -v "$tool" >/dev/null || { echo "Outil manquant : $tool" >&2; exit 1; }
done
python3 -c 'import yaml' || { echo 'Installer scripts/requirements.txt' >&2; exit 1; }
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM
for values in mes-valeurs.yaml values-gke.yaml; do
    helm lint --strict ./charts-officiels/jitsi-meet -f "$values"
    helm template mon-jitsi ./charts-officiels/jitsi-meet -f "$values" > "$tmp_dir/render.yaml"
    if [ "$values" = values-gke.yaml ]; then
        python3 scripts/check-render.py "$tmp_dir/render.yaml"
    fi
done
if [ -n "${GKE_VALUES_FILE:-}" ]; then
    helm lint --strict ./charts-officiels/jitsi-meet -f values-gke.yaml -f "$GKE_VALUES_FILE"
    helm template mon-jitsi ./charts-officiels/jitsi-meet -f values-gke.yaml -f "$GKE_VALUES_FILE" > "$tmp_dir/public.yaml"
    python3 scripts/check-render.py "$tmp_dir/public.yaml" --public
fi
# Copie isolee : aucun acces au backend, a .terraform ou aux etats du projet.
terraform fmt -check -recursive terraform
mkdir "$tmp_dir/terraform"
cp terraform/*.tf terraform/.terraform.lock.hcl "$tmp_dir/terraform/"
# Cache provider facultatif pour travailler sans reseau.
if [ -n "${TF_OFFLINE_PLUGIN_DIR:-}" ]; then
    terraform -chdir="$tmp_dir/terraform" init -backend=false -input=false -lockfile=readonly -plugin-dir="$TF_OFFLINE_PLUGIN_DIR"
else
    terraform -chdir="$tmp_dir/terraform" init -backend=false -input=false -lockfile=readonly
fi
terraform -chdir="$tmp_dir/terraform" validate
printf '%s\n' 'Controles statiques reussis. Aucune validation fonctionnelle de visioconference.'
