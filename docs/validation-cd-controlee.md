# Prochain diagnostic et premier déploiement CD contrôlé

**Procédure préparée, aucune commande de mutation exécutée pendant la remise.**
Les blocs d'activation, relance et rollback ne doivent être utilisés qu'après
accord distinct couvrant l'opération. Ce document n'autorise aucun lancement.

## Situation et conditions d'arrêt

Dernier main confirmé : cbe2192bc2104b2f40b88633b24ae691eb854788.
Le [diagnostic 44053382824](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44053382824)
a réussi le 17 novembre : OIDC, exec ADC, identité kubectl, 49 autorisations,
PVC Bound et SOPS/KMS validés, nettoyages réussis, une seule tentative.
La présente correction aligne localement l’authentification CD sur les mêmes
primitives, avec un garde propre à workflow_run. **La CD reste désactivée et
aucun déploiement automatisé n’est encore validé.** L’état doit être revérifié
lors de la future session ; ce document n’est pas un relevé temps réel.

Arrêter si SHA inattendu, CI non verte, flag CD déjà actif avant accord,
ressource/release absente, secret différent, IP/ports modifiés, pod indisponible,
ou erreur d'authentification. Ne pas élargir les droits pour contourner une erreur
non identifiée. Ne pas relancer automatiquement une opération échouée.

## A. Historique du diagnostic, déjà réussi avant cette correction CD

1. Relire le lot local exact, l'audit secrets et les tests. Après accord seulement,
   créer une branche depuis le main courant en conservant les modifications,
   committer/pousser et ouvrir une PR. La préparation du message/description est
   locale ; aucune PR n'est créée par cette finalisation.
2. Attendre les CI du SHA de PR. Recontrôler GKE_CD_ENABLED absente/false avant une
   fusion distinctement autorisée. La correction ne touche pas les droits IAM/RBAC.
3. Attendre CI push main, relever le nouveau SHA et confirmer CD skipped. Le
   workflow doit être présent dans la branche par défaut, avec ses dépendances.
4. Avant le dispatch autorisé, vérifier en lecture :

```bash
set -euo pipefail
REPO=SaminouA/projet-jitsi-helm
gh api "repos/$REPO/git/ref/heads/main" --jq '.object.sha'
gh api "repos/$REPO/actions/variables" --jq '[.variables[] | select(.name == "GKE_CD_ENABLED")]'
python3 scripts/check-gcp-apis.py
kubectl auth can-i get persistentvolumeclaims/jitsi-edge-data -n jitsi \
  --as=github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com
```

Comparer humainement le SHA à celui approuvé. Ne pas modifier l'API, les droits
ou une variable depuis ce précontrôle. Puis, **après accord de lancement** :

```bash
gh workflow run diagnose-gke.yml --repo SaminouA/projet-jitsi-helm \
  --ref main -f confirm_read_only=true
```

Identifier l'ID exact du nouveau run, head_sha et run_attempt=1 ; ne pas réutiliser
un ancien résultat vert. Attendre avec `gh run watch RUN_ID --exit-status`.
Garder main stable pendant le test : le garde final refuse un SHA dépassé.

Attendus : EXEC_ADC à la configuration puis au contrôle, plugin DISPONIBLE,
identité CONFIRMEE, 49 autorisations, PVC Bound, SOPS/KMS et comparaison des
secrets/rendus réussis, tous les nettoyages réussis. Ne jamais copier les logs
bruts, un kubeconfig, un jeton ou les valeurs déchiffrées dans le rapport.
Une réussite du diagnostic n'est pas une autorisation de déployer.

## B. Premier essai CD après fusion autorisée de la correction

1. Relire la PR CD et ses CI, confirmer le flag absent/false, puis fusionner
   seulement après accord. Attendre la CI du nouveau main et le job CD skipped.
2. Vérifier sur ce SHA que deploy-gke.yml appelle configure-cd-gke.py, sans
   use_auth_provider, et que le profil public est explicite. Un nouveau diagnostic
   sur ce SHA peut être autorisé séparément pour actualiser les préflights ;
   il n’est jamais lancé automatiquement par cette procédure.
3. Pour l’essai sans modification fonctionnelle, conserver chart/images/valeurs,
   IP, ports et secrets. Vérifier les révisions et l’absence de dérive applicative.
   Le diagnostic vérifie notamment secrets, réseau et disponibilité, mais ne
   garantit pas une égalité exhaustive des configurations Helm. Si les rendus
   privés et les valeurs live divergent fonctionnellement, arrêter : ne pas
   exécuter Helm sous prétexte que le dernier diagnostic a réussi.
4. Faire autoriser explicitement la configuration des variables, un unique essai
   et son rollback. Ne pas activer le flag tant que ces conditions restent ouvertes.

La section A conserve la procédure historique ; **ne pas rejouer le diagnostic
ou republier son correctif automatiquement**. Pour cette PR, seule la fusion
future puis la procédure ci-dessous restent à considérer.

Préalables complémentaires :

- Faire valider cette adaptation CD par revue/CI puis fusion autorisée.
  configure-cd-gke.py applique check-cd-event.py, vérifie le checkout et main,
  puis réutilise configure_gke avec un nom de fichier CD distinct. Le garde
  workflow_dispatch du diagnostic reste inchangé ; il n’est pas contourné.
- Vérifier le mode public explicite, domaine/réservation attendus, guardrails
  SOPS/secrets/réseau, PVC existant, chart et images inchangés, et diagnostic
  valide pour le SHA/correction concerné.
- Prévoir une fenêtre sans réunion ; une mise à jour même sans changement
  fonctionnel peut provoquer une interruption. Les deux upgrades Helm ne sont
  pas transactionnels ; --wait ne prouve ni certificat ni audio/vidéo.
- Confirmer le rôle opérateur de retour arrière et la présence des historiques
  Helm. Ne pas modifier les données ACME ou les mots de passe.

Capturer seulement les révisions/métadonnées non sensibles immédiatement avant
l'essai. Pas d'export en clair des valeurs ou manifests Helm :

```bash
set -euo pipefail
umask 077
EXPECTED_CONTEXT=gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster
[[ "$(kubectl config current-context)" == "$EXPECTED_CONTEXT" ]]
BACKUP_DIR=$(mktemp -d /tmp/jitsi-cd-revisions.XXXXXX)
helm list -n jitsi -o json > "$BACKUP_DIR/releases.json"
python3 - "$BACKUP_DIR" <<'PY'
import json, pathlib, sys
folder = pathlib.Path(sys.argv[1])
rows = json.loads((folder / 'releases.json').read_text())
for name in ['jitsi', 'jitsi-edge']:
    selected = [r for r in rows if r['name'] == name and r['status'] == 'deployed']
    assert len(selected) == 1
    (folder / (name + '.revision')).write_text(str(selected[0]['revision']) + '\n')
PY
helm history jitsi -n jitsi
helm history jitsi-edge -n jitsi
kubectl -n jitsi get pods,svc,pvc,endpointslices
```

Conserver BACKUP_DIR dans la même session ou noter son chemin privé. Les révisions
ne contiennent pas de secret ; les révisions Helm stockées dans le cluster
restent nécessaires au rollback. Ne pas supposer que les révisions historiques
2/1 conviennent : elles pourraient rétablir localhost ou ACME staging.

Après autorisation d'activation couvrant aussi le retour arrière, préparer les
variables explicites, puis seulement le flag général en dernier. **À ne pas
exécuter pendant la finalisation locale :**

```bash
gh variable set JITSI_ACCESS_PROFILE --repo SaminouA/projet-jitsi-helm --body public-edge
gh variable set JITSI_PUBLIC_DOMAIN --repo SaminouA/projet-jitsi-helm --body jitsi-meet-m2.duckdns.org
gh variable set JITSI_EDGE_ADDRESS_NAME --repo SaminouA/projet-jitsi-helm --body jitsi-edge-ip
gh variable set JITSI_EDGE_CD_ENABLED --repo SaminouA/projet-jitsi-helm --body true
gh variable set GKE_CD_ENABLED --repo SaminouA/projet-jitsi-helm --body true
```

L'activation de la variable ne déclenche rien à elle seule. Pour un essai contrôlé,
identifier la CI **event=push, head_branch=main, head_sha=tête actuelle** approuvée,
puis, après accord, relancer cette CI précise :

```bash
gh run rerun "$CI_MAIN_RUN_ID" --repo SaminouA/projet-jitsi-helm
```

Un workflow_dispatch de la CI ne convient pas : la CD exige que l'événement
source de CI soit push. Observer la nouvelle tentative et le workflow_run CD
correspondant au même SHA. Aucune relance automatique en cas d'échec.

Après le premier essai, désactiver le flag selon le périmètre convenu avec
l'utilisatrice ; ne pas laisser une activation permanente implicite :

```bash
gh variable set GKE_CD_ENABLED --repo SaminouA/projet-jitsi-helm --body false
```

Vérifier les deux releases, PVC/IP inchangés, secrets comparés sans affichage,
HTTPS normal sans -k sur /, /config.js, /http-bind et 404 des routes privées.
Une réunion manuelle consentie doit encore vérifier les médias après ce nouvel
essai ; ne pas réutiliser le succès utilisateur antérieur comme résultat futur.

## C. Retour arrière contrôlé, non exécuté

Arrêter la progression et désactiver GKE_CD_ENABLED après accord de retour
arrière. Déterminer quelles releases ont réellement été mises à jour. Les
restaurer dans l'ordre inverse : Jitsi puis edge, seulement si concernées.

```bash
set -euo pipefail
EXPECTED_CONTEXT=gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster
[[ "$(kubectl config current-context)" == "$EXPECTED_CONTEXT" ]]
JITSI_BEFORE=$(cat "$BACKUP_DIR/jitsi.revision")
EDGE_BEFORE=$(cat "$BACKUP_DIR/jitsi-edge.revision")
[[ "$JITSI_BEFORE" =~ ^[0-9]+$ && "$EDGE_BEFORE" =~ ^[0-9]+$ ]]
helm history jitsi -n jitsi
helm history jitsi-edge -n jitsi
# Uniquement apres revue de l'historique et accord :
helm rollback jitsi "$JITSI_BEFORE" -n jitsi --wait --timeout 10m --no-hooks
helm rollback jitsi-edge "$EDGE_BEFORE" -n jitsi --wait --timeout 10m --no-hooks
kubectl -n jitsi get pods,svc,pvc,endpointslices
```

Si PUBLIC_URL a changé, la ConfigMap commune ne déclenche pas à elle seule les
rollouts. Après accord, recharger progressivement les composants puis vérifier
l'URL réellement servie :

```bash
for resource in statefulset/jitsi-jitsi-meet-prosody deployment/jitsi-jitsi-meet-jicofo deployment/jitsi-jitsi-meet-jvb-0 deployment/jitsi-jitsi-meet-web; do
  kubectl -n jitsi rollout restart "$resource"
  kubectl -n jitsi rollout status "$resource" --timeout=180s
done
```

Le rollback Helm conserve le PVC mais ne restaure pas les données ACME. Ne pas
supprimer PVC/disque, namespace, IP ou LB ; aucun terraform destroy. Vérifier
TLS de production, IP JVB, disponibilité et médias séparément. Un rollback crée
une nouvelle révision : documenter la révision obtenue, pas seulement sa cible.
