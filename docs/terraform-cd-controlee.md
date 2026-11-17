# Premier apply Terraform contrôlé — préparation, pas une exécution

**Actualisation :** les sections initiales ci-dessous décrivent la préparation
historique. Le bucket, le compte et le backend existent désormais : ne pas
rejouer leur bootstrap ou migration. La procédure courante figure à la fin
et dans [la validation plan/apply](terraform-plan-apply-validation.md).

Le 17 novembre 2026, seul un plan local en lecture a été produit sur une copie
privée de l’état : une mise à jour du label GCP du cluster, pool inchangé,
aucune création/suppression/remplacement. Aucun apply, bootstrap IAM/GCS ou
migration d’état n’est autorisé par ce document. Ne pas exécuter les blocs
administratifs sans validation distincte. La CD Helm reste désactivée.

## Architecture et choix

- Backend GCS natif : verrouillage par objet `.tflock`, pas de base de verrou
  supplémentaire. Bucket dédié préexistant, régional europe-west1, versioning,
  accès uniforme et prévention d’accès public. Aucun verrou de rétention bucket
  qui empêcherait de supprimer le lock ; ne jamais forcer un unlock sans enquête.
- Nom proposé, disponibilité mondiale **non vérifiée** :
  `project-fcf2ef91-c005-4910-a10-tfstate`, préfixe `jitsi/gke`, workspace default.
  Le backend correspondra à `jitsi/gke/default.tfstate`. Pas de création du bucket
  dans le même état qu’il héberge : bootstrap administratif séparé.
- État local audité : Terraform 1.16.6, format 4, serial 9, deux ressources
  `google_container_cluster.jitsi` et `google_container_node_pool.jitsi_nodes`.
  Ne pas repartir d’un état vide, importer à nouveau ou utiliser le vieux tfplan.
- Compte proposé `terraform-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com` :
  aucune clé JSON, aucun accès Kubernetes RBAC ni KMS/SOPS nécessaire pour ce label.
  Le compte Helm existant reste séparé et n’est pas élargi.
- Nouveau provider WIF `github-terraform-provider` dans le pool existant, limité
  au dépôt, main et au fichier workflow Terraform. Son attribut pipeline dédié
  permet de borner le binding SA ; le provider CD existant ne possède pas cet
  attribut, donc son principalSet repository n’est pas réutilisé pour Terraform.
- La permission `container.clusters.update` est plus large qu’un seul label :
  IAM ne fournit pas ici un droit par champ. Les gardes de plan et la revue de
  main limitent son utilisation ; ne pas présenter cette protection logicielle
  comme une restriction IAM par champ ou une identité administratrice globale.

Références primaires : [backend GCS et verrouillage](https://developer.hashicorp.com/terraform/language/backend/gcs),
[labels GKE](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/creating-managing-labels).
Le verrou GCS protège l’état ; la concurrence GitHub commune à Helm/diagnostic/
Terraform évite les exécutions simultanées de ces workflows, sans empêcher un
opérateur extérieur de modifier les ressources. Geler les changements manuels
pendant la fenêtre d’application.

## 1. Bootstrap administratif proposé — accord requis, non effectué

À valider d’abord : nom de bucket disponible, coût, localisation, identité
opérateur autorisée à créer bucket/SA/rôles/provider et bindings. Les fichiers
`deploy/terraform/gke-role.yaml` et `state-role.yaml` sont des propositions,
aucun rôle n’a été créé. Les permissions minimales proposées devront être
confirmées lors du premier plan runner ; ne pas ajouter de rôle Owner/Editor.

```bash
set -euo pipefail
PROJECT=project-fcf2ef91-c005-4910-a10
TF_BUCKET=project-fcf2ef91-c005-4910-a10-tfstate
TF_SA=terraform-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com
# Uniquement apres autorisation explicite de ces creations et de leur cout :
gcloud storage buckets create "gs://$TF_BUCKET" --project="$PROJECT" \
  --location=europe-west1 --default-storage-class=STANDARD \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update "gs://$TF_BUCKET" --versioning
gcloud iam service-accounts create terraform-jitsi-deployer --project="$PROJECT"
gcloud iam roles create jitsiTerraformLabelUpdater --project="$PROJECT" --file=deploy/terraform/gke-role.yaml
gcloud iam roles create jitsiTerraformStateAccess --project="$PROJECT" --file=deploy/terraform/state-role.yaml
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$TF_SA" --role="projects/$PROJECT/roles/jitsiTerraformLabelUpdater"
gcloud storage buckets add-iam-policy-binding "gs://$TF_BUCKET" \
  --member="serviceAccount:$TF_SA" --role="projects/$PROJECT/roles/jitsiTerraformStateAccess"
gcloud iam workload-identity-pools providers create-oidc github-terraform-provider \
  --project="$PROJECT" --location=global --workload-identity-pool=github-jitsi-pool \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.pipeline='terraform-gke'" \
  --attribute-condition="assertion.repository=='SaminouA/projet-jitsi-helm' && assertion.ref=='refs/heads/main' && assertion.workflow_ref=='SaminouA/projet-jitsi-helm/.github/workflows/terraform-gke.yml@refs/heads/main'"
gcloud iam service-accounts add-iam-policy-binding "$TF_SA" --project="$PROJECT" \
  --role=roles/iam.workloadIdentityUser \
  --member='principalSet://iam.googleapis.com/projects/198310729956/locations/global/workloadIdentityPools/github-jitsi-pool/attribute.pipeline/terraform-gke'
```

Le rôle GKE est accordé au projet ; le rôle stockage est accordé **au seul
bucket**. Les états/versions peuvent contenir des données sensibles. Versioning
et soft-delete éventuel consomment du stockage ; définir ensuite une conservation
raisonnée après accord, pas un effacement automatique improvisé.

Coûts supplémentaires prévus : stockage de l’état (actuellement environ 24 Ko),
versions, requêtes/locks GCS et éventuel soft-delete. Aucun nouveau nœud, disque
GKE ou LB n’est prévu pour le label. Aucun montant facturé n’est observé ni
plafond garanti ; vérifier les tarifs et crédits avant création. Aucun coût
cloud de provisioning n’a été engagé pendant la préparation.

## 2. Migration — validation distincte obligatoire, non effectuée

1. Arrêter tout plan/apply concurrent. Vérifier le projet, les deux IDs GCP,
   l’absence de backend distant autoritaire existant, l’état local original,
   son lineage/serial et ses deux ressources. Conserver son empreinte privée.
2. Créer une copie privée (0700, état 0600) de la configuration et de l’état
   existant, hors Git ; conserver l’original sur la machine. Prévoir une sauvegarde
   chiffrée selon la politique convenue. Ne pas mettre l’état dans un artefact GitHub.
3. Vérifier le bucket vide à ce préfixe, versioning/accès privé et autorisations.
   Seulement après accord de migration, depuis la copie, utiliser la commande
   interactive ci-dessous. Lire le récapitulatif et confirmer seulement le transfert
   prévu ; pas de -force-copy, yes automatique, state push ou import.

```bash
# MIGRATION_DIR doit designer la copie privee deja preparee et verifiee.
terraform -chdir="$MIGRATION_DIR" init -migrate-state -input=true -lockfile=readonly \
  -backend-config=bucket=project-fcf2ef91-c005-4910-a10-tfstate \
  -backend-config=prefix=jitsi/gke
```

4. Capturer `terraform state pull` uniquement en mémoire ou dans la copie privée
   pour comparer lineage, serial, adresses et IDs à l’original, sans les imprimer.
   Recontrôler les deux objets réels et un plan sans apply. Le seul changement
   admissible pour l’essai est le label ; le pool doit rester no-op.
5. GCS devient alors l’autorité ; conserver l’ancien état comme sauvegarde et ne
   plus appliquer depuis son backend local. Ne pas effacer l’original ni modifier
   son contenu pour rendre artificiellement le contrôle vert.

Ajouter backend.tf dans Git ne migre rien. Les validations statiques continuent
avec init backend=false sur copie jetable. Un runner sans état distant attendu
est refusé avant plan/apply : le workflow ne bootstrappe ni n’importe l’état.

## 3. Revue, activation et unique apply après CI push main — non effectués

- Faire relire/fusionner la PR après CI et accord distinct, flag TF absent/false.
  Confirmer GKE_CD_ENABLED=false : aucun enchaînement Helm n’est activé ici.
- Configurer l’environnement GitHub `terraform-controlled` : reviewer obligatoire,
  pas d’auto-approbation, branche main uniquement, pas de bypass administratif.
  **Vérifier réellement ces protections et leur disponibilité selon le plan GitHub.**
  Le nom d’environnement seul ne crée pas de protection ; si ces règles ne sont
  pas disponibles, arrêter et convenir d’un contrôle équivalent avant activation.
- Vérifier OIDC dédié et droits proposés, bucket/migration validés. Le premier plan
  du runner peut révéler un droit manquant ; arrêter pour analyse, sans escalade
  automatique ni relance non autorisée.
- Renseigner après accord les variables suivantes :

| Variable | Valeur / contrôle |
|---|---|
| TF_STATE_BUCKET | project-fcf2ef91-c005-4910-a10-tfstate |
| TF_STATE_LINEAGE | lineage exact de l’état préservé puis migré, pas une valeur inventée |
| TF_APPROVED_SHA | SHA complet du main fusionné approuvé pour cet unique essai |
| TF_CD_ENABLED | true en dernier, après autorisation d’application |
| GKE_CD_ENABLED | false pendant l’essai Terraform |

- Déclencher une CI **push main** sur le SHA approuvé, ou relancer une seule CI
  existante dont event=push, head_branch=main et head_sha=tête approuvée. Une CI
  workflow_dispatch n’est pas acceptée. Ne pas créer un commit vide par défaut.
- Approuver l’environnement seulement après revue de la PR, du plan local
  expurgé, du SHA et des prérequis. Le plan runner reste privé : sa revue est
  effectuée par le garde automatique exact (pas par une lecture humaine d’un
  artefact). Ce compromis est explicite ; pour un futur déploiement général,
  prévoir un circuit plan/approbation/apply adapté et sécurisé.

Le script prépare une copie runner privée, fmt/init/validate, contrôle backend,
workspace default, lineage/serial et ressources, puis calcule un plan sauvegardé.
Le garde exige exactement un update de label sur le cluster et un no-op du pool,
préserve tous les autres labels et champs, rejette create/delete/replace,
ressources supplémentaires, valeurs inconnues et sorties modifiées. Le plan
binaire contrôlé est le seul appliqué, sous lock, après nouvelle vérification
main/SHA/serial. Aucun -target, -replace, -destroy ou -lock=false.

Preuves attendues après accord, **non acquises à ce jour** :

- Run CI push main et workflow Terraform sur le SHA approuvé ; OIDC dédié réussi.
- Résumé expurgé `1 update de label, 0 create, 0 delete, 0 replace`.
- Apply réussi ; label `devops-apply-proof=github-actions` réellement visible sur
  jitsi-cluster RUNNING ; serial supérieur et même lineage dans GCS.
- Plan final sans changement, nœuds/pods/IP/PVC et HTTPS inchangés contrôlés
  indépendamment. L’apply ne démontre pas de nouvelle réunion audio/vidéo.
- Nettoyages réussis et TF_CD_ENABLED=false immédiatement après essai, réussite
  ou échec. Le flag ne se désactive pas lui-même dans le workflow (token GitHub
  volontairement sans permission d’écriture des variables) : l’opérateur doit
  surveiller et le désactiver. L’état label-only empêche un second apply identique
  de produire une nouvelle preuve, mais ce n’est pas un substitut au flag.

## 4. Échec et retour arrière

Ne pas relancer automatiquement. Une erreur avant apply ne nécessite pas de
mutation GKE. Si apply échoue, garder la version GCS et les sorties sensibles
privées, désactiver TF_CD_ENABLED, examiner l’état/ressources et proposer un
nouveau plan. Ne jamais restaurer aveuglément une ancienne version du state :
cela ne restaure pas les ressources et peut créer une divergence dangereuse.

Si seul le label a été ajouté, son retrait nécessite une nouvelle PR et un plan
update sans remplacement autorisé ; le garde de ce premier essai doit être adapté
par revue, car il refuse délibérément le retrait. Aucun rollback Terraform général,
destroy, force-unlock, migration inverse ou changement IAM automatique. En cas
d’impact Jitsi inattendu, arrêter et suivre le diagnostic applicatif ; ne pas
modifier le PVC ou les secrets pour contourner l’incident.


## 5. Procédure courante après réconciliation — NON exécutée

Le déclenchement automatique workflow_run initial n'est plus utilisé pour apply.
Le workflow `terraform-gke.yml` conserve le mode manuel readonly et ajoute le
choix explicite `operation=apply-label`. Une CI **push main** réussie sur le SHA
courant reste une preuve préalable obligatoire ; elle ne lance pas l'apply.
La variable historique TF_APPROVED_SHA est remplacée par l'entrée manuelle
`approved_sha`, vérifiée contre main, le checkout et GITHUB_SHA.

Après autorisations distinctes de fusion et d'apply seulement :

1. Confirmer le backend existant et les résultats du plan strict actualisé ; ne
   pas recréer le bucket, remigrer l'état ou changer son lineage.
2. Laisser GKE_CD_ENABLED=false et activer TF_CD_ENABLED explicitement au niveau
   dépôt et environnement. Les variables bucket/lineage restent privées dans
   l'environnement ; le précontrôle sans OIDC n'en dépend pas.
3. Déclencher le mode apply-label sur main et saisir son SHA complet approuvé.
4. Examiner le job de précontrôle, puis approuver humainement le job apply de
   l'environnement terraform-controlled. Aucun agent n'envoie cette approbation.
5. Examiner les résultats et remettre les deux flags Terraform à false, même
   en cas d'échec, sans relance automatique.

L'environnement actuel interdit le bypass administrateur et impose main et un
reviewer humain. Il permet toutefois à l'opératrice déclenchante d'approuver
son propre run : cette configuration, héritée du diagnostic readonly, ne
constitue pas une séparation des tâches à deux personnes. Le job recontrôle
les protections avant application. L'approbation précède le job plan/apply,
pas un transfert de plan binaire entre deux runners. Aucun artefact privé
n'est exposé. Le workflow général multi-ressources reste hors périmètre.


## 6. Correction finale obligatoire : revue après génération du plan

La section 5 décrit l'étape préparatoire antérieure. Elle est remplacée pour
l'activation par la chaîne prepare-plan → review-plan → apply documentée dans
[la validation actuelle](terraform-plan-apply-validation.md). L'approbation de
terraform-controlled avant plan ne suffit pas. Une seconde approbation distincte
sur terraform-apply-review, après publication du résumé lié au plan exact, est
obligatoire. L'artefact binaire est chiffré et authentifié ; son empreinte est
recontrôlée et aucun nouveau plan n'est calculé avant apply. Un secret privé de
transport et ce nouvel environnement protégé restent à provisionner après accord.
Ne pas activer les flags avant vérification de ces prérequis. Aucun apply réel
n'a été exécuté ; les procédures de bootstrap historiques ne sont pas à rejouer.
