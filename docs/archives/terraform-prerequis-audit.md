# Terraform CD : audit réel et actions restantes

PR [nº 7](https://github.com/SaminouA/projet-jitsi-helm/pull/7), tête
fe9edd1e3ab0ba81803b00c91f55bea27ce776da : OPEN, MERGEABLE/CLEAN,
deux CI Validation Helm réussies. Aucun merge ni push effectué pendant cet audit.

## Vérifications réalisées

Projet actif project-fcf2ef91-c005-4910-a10, cluster jitsi-cluster RUNNING.
APIs activées : storage, iam, iamcredentials, sts, cloudresourcemanager, container.
État local original 23629 octets, serial 9, deux ressources attendues ; empreinte
inchangée. Plan frais sur une copie privée, provider 7.46.1 déjà en cache,
Terraform init/validate/plan réussis, garde exact accepté :
[preuve expurgée](../preuves/terraform-plan-actualise.json). Un update du label
`devops-apply-proof=github-actions` seulement ; autres labels conservés, pool
no-op, zéro create/delete/replace. Aucun apply ou transfert d’état.

Les cinq commits épinglés des actions du workflow existent. Garde workflow :
CI push main réussie, SHA explicitement approuvé et toujours tête de main,
flag Terraform true et flag Helm différent de true, OIDC dédié, concurrence
partagée, plan binaire strict appliqué sans recalcul, contrôle lineage/serial,
plan final sans changement attendu, pas d’artefact state/plan. Quatorze tests
ciblés réussis et terraform fmt -check réussi.

## Blocages constatés

| Prérequis | État réel |
| --- | --- |
| Bucket project-fcf2ef91-c005-4910-a10-tfstate | absent, describe HTTP 404 ; liste buckets projet vide |
| Versioning, accès uniforme, prévention publique et lock GCS | non configurés, bucket absent |
| terraform-jitsi-deployer | absent de la liste des comptes du projet |
| Rôles personnalisés Terraform GKE/state | aucun rôle correspondant trouvé |
| Provider github-terraform-provider | absent ; seul github-provider CD existe |
| WIF du compte Terraform | impossible tant que le compte/provider n’existent pas |
| State distant autoritaire | absent ; state original toujours local, non migré |
| Environnement terraform-controlled | absent ; liste environnements GitHub vide |
| Variables TF_STATE_BUCKET / TF_STATE_LINEAGE / TF_APPROVED_SHA / TF_CD_ENABLED | absentes |
| Droits opérateur de bootstrap | testIamPermissions HTTP 429, non concluants |

Le provider existant limite repository et refs/heads/main, mais n’expose pas
l’attribut pipeline Terraform attendu. Ne pas le modifier pour réutiliser les
droits CD. Le compte Helm ne reçoit pas de nouveaux droits. Aucune permission
Terraform existante n’est prétendue validée puisque le compte n’existe pas.
Le HTTP 429 ne prouve ni présence ni absence des permissions opérateur.

## Actions requises, NON exécutées

1. Après accord de bootstrap, recontrôler les droits opérateur une fois le quota
   API disponible. Puis créer le bucket dédié privé/versionné, le compte sans
   clé, les deux rôles minimaux et le provider WIF exact préparés par la PR.
   Commandes complètes dans le worktree de la PR :
   `/tmp/jitsi-terraform-controlled/docs/terraform-cd-controlee.md`, section 1.
   Les créations et bindings IAM nécessitent validation explicite ; aucune
   commande ci-dessous n’est un accord d’exécution.

```bash
# Depuis le worktree de la PR, uniquement après accord et contrôle d’identité.
PROJECT=project-fcf2ef91-c005-4910-a10
TF_BUCKET=project-fcf2ef91-c005-4910-a10-tfstate
gcloud storage buckets create "gs://$TF_BUCKET" --project="$PROJECT" --location=europe-west1 --default-storage-class=STANDARD --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update "gs://$TF_BUCKET" --versioning
gcloud iam service-accounts create terraform-jitsi-deployer --project="$PROJECT"
gcloud iam roles create jitsiTerraformLabelUpdater --project="$PROJECT" --file=deploy/terraform/gke-role.yaml
gcloud iam roles create jitsiTerraformStateAccess --project="$PROJECT" --file=deploy/terraform/state-role.yaml
# Ensuite : bindings projet/bucket et provider WIF, exactement selon section 1.
```

2. Faire vérifier le bucket (projet, europe-west1, versioning, accès uniforme,
   prévention publique, aucun accès allUsers/allAuthenticatedUsers). Pas de
   rétention verrouillée empêchant la suppression du fichier de lock.
   GCS nécessite un bucket préexistant et fournit le verrouillage ; le nom
   backend dans Git seul ne migre pas l’état.
3. Après accord DISTINCT de migration, copie privée de l’état, backend vide au
   préfixe jitsi/gke, init -migrate-state interactif depuis la copie ; jamais de
   force-copy/state push/import/recréation de l’état. Comparer lineage, serial,
   deux IDs et ressources puis replanifier. L’original reste conservé.
4. Créer/protéger l’environnement GitHub terraform-controlled : main uniquement,
   reviewer effectif, pas d’auto-approbation selon la politique convenue. Vérifier
   sa disponibilité et la présence d’un reviewer capable d’approuver avant de
   prétendre le contrôle actif. Ne pas supprimer cette protection pour gagner
   du temps ; convenir explicitement d’une alternative si elle est impossible.
5. Après accord de merge, intégrer la PR. Après accord d’apply, renseigner les
   variables backend/lineage/SHA approuvé, activer TF_CD_ENABLED en dernier,
   GKE_CD_ENABLED restant false ; relancer une CI push main du SHA approuvé.
   Surveiller le workflow Terraform et remettre TF_CD_ENABLED=false à la fin,
   succès ou échec. Aucun apply ne peut être autorisé par le présent document.

Coût : stockage GCS, versions et opérations facturables ; volume actuel environ
24 Ko, aucun nouveau nœud/disque/LB GKE requis. Aucun devis ferme ni gratuité
promis. [Tarification officielle](https://cloud.google.com/storage/pricing),
[backend GCS](https://developer.hashicorp.com/terraform/language/backend/gcs).
Aucune ressource créée, migration, mutation IAM, variable GitHub ou apply pendant
l’audit. Verdict : **NO-GO apply**, malgré le plan local sûr.

## Mise à jour : contrôle des droits projet désormais réussi

Le test ciblé suivant a confirmé les permissions projet de création du bucket,
SA, rôles et provider WIF, ainsi que les bindings IAM. Un binding Owner direct
sans condition est constaté. Le HTTP 429 précédent reste un échec de quota,
pas un refus IAM. Les droits sur le bucket inexistant ne sont pas testés :
contrôler sa politique immédiatement après création autorisée, avant migration.
Voir [les droits vérifiés](../preuves/terraform-droits-verifies.json). GO conditionnel
bootstrap progressif, NO-GO apply tant que les autres prérequis restent absents.

## Mise à jour : bootstrap réellement terminé

Après accord distinct, bucket privé/versionné, identité sans clé, deux rôles
minimaux et provider WIF dédié ont été créés et vérifiés. Voir
[les résultats réels](../preuves/terraform-bootstrap-resultats.json). Les droits opérateur
sur le bucket existent désormais et ont été testés, avec un marqueur non secret
écrit/relu/supprimé. Le state reste local et le pipeline désactivé. Les blocages
encore ouverts sont migration autorisée, protections GitHub et validation
runner avant apply. L’ancien état « bucket absent » décrit l’audit antérieur.

## Mise à jour : state désormais migré et contrôlé

La migration a été explicitement autorisée puis effectuée par init -migrate-state
interactif sur copie privée. Backend GCS/workspace default vérifiés, mêmes deux
ressources et mêmes IDs/attributs, serial 10 et lineage conservé. Validate et
plan de contrôle exit 0, sans changement. Voir
[les résultats](../preuves/terraform-migration-resultats.json). Les fichiers locaux serial 9
sont conservés comme sauvegardes non autoritaires ; ne plus appliquer en local.
Il reste les protections GitHub, la validation runner et l’accord distinct
pour apply. Aucun pipeline activé et aucun apply réalisé.
