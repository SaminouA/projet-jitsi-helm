# Terraform contrôlé : état de préparation


### Réconciliation de la PR Terraform nº 7 — 17 novembre 2026

La branche de la PR a intégré la base main actuelle ; le conflit add/add sur
`terraform-gke.yml` a été résolu en conservant le diagnostic readonly et en
ajoutant un mode manuel `operation=apply-label`. Aucun apply ni fusion dans main
n'a été exécuté. Le mode readonly reste celui par défaut, avec sa confirmation
explicite et son invariant de plan sans changement. Avant la preuve de label,
ce diagnostic pourra refuser le changement attendu : ce refus ne vaut pas apply.

Le fournisseur OIDC existant impose le dépôt, ses identifiants immuables, main,
le chemin exact de ce workflow et le sujet de l'environnement terraform-controlled.
Ce chemin est conservé pour ne pas modifier IAM. Le mode apply exige le flag
Terraform, le flag Helm désactivé, le SHA main explicitement saisi, une CI push
réussie sur ce SHA et une seconde vérification avant application. Le job de
précontrôle n'a pas de droit OIDC. Le job apply attend l'approbation humaine de
l'environnement puis utilise des identifiants externes sans clé JSON.
Le contrôle GitHub impose un reviewer configuré, interdit le bypass administrateur
et n'autorise que main. L'auto-approbation par l'utilisatrice déclenchante reste
permise par le paramètre existant ; il ne s'agit pas d'une séparation à deux personnes.

Le 17 novembre, les lectures IAM ont confirmé les rôles dédiés cluster et bucket,
la permission compute.instanceGroupManagers.list, le binding WIF, le versioning,
l'accès uniforme et la prévention publique du bucket europe-west1. Le garde
recontrôle ces protections, le workspace, le lineage privé et les deux ressources.
Un plan frais a été exécuté avec les ADC de l'opératrice, sur une copie privée
avec le backend GCS (ce n'est pas un essai d'apply avec le compte du runner) : **une mise
à jour du seul label devops-apply-proof, zéro création, destruction ou remplacement,
node pool inchangé**. L'état distant était identique avant et après. Le plan privé
a été supprimé et aucune valeur sensible n'a été publiée.

L'approbation de l'environnement intervient avant le job plan/apply. Elle ne
constitue pas une approbation interactive du plan binaire intermédiaire : le
contenu de celui-ci est contraint par le garde label-only testé, conservé sur le
même runner et appliqué sans recalcul. Aucun artefact state/plan n'est transféré.
Le fichier du plan est privé, son empreinte et l'état complet sont recontrôlés.
Les flags restent false. Pour une future exécution autorisée, il faudra activer
explicitement TF_CD_ENABLED au niveau dépôt **et environnement**, saisir le SHA
main approuvé, puis approuver humainement le job. Aucune de ces opérations n'a
été faite dans cette préparation.

PR : https://github.com/SaminouA/projet-jitsi-helm/pull/7
