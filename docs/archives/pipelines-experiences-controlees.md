# Pipelines manuels Malleus et Chaos Mesh — préparation du 17 novembre 2026

## État réel

Les workflows `malleus-controlled.yml` et `chaos-controlled.yml` sont préparés,
mais **aucun des deux n'a été exécuté**. Les résultats historiques restent dans
les documents Malleus et Chaos déjà publiés ; ils ne prouvent pas l'exécution de
ces nouveaux pipelines. Aucun test de charge, injection, bootstrap ou changement
IAM n'a été effectué pendant cette préparation.

Les deux manifestes publics GHCR ont été relus anonymement : HTTP 200, digest
exact conforme aux profils existants. Selenium :
`sha256:5b898424cffed5b99a0c8acbb558c0e3f3e4a2fbb0aac48bb54af60b445dcd86` ;
Malleus : `sha256:01de65fb72bf78ded0191caa6302916f04850b94bdb6d1d943b0ceae6ce87092`.
Il ne s'agit ni d'un nouveau build, ni d'une analyse de vulnérabilités des images.

## Garde commun

Les workflows sont uniquement `workflow_dispatch`, limités au dépôt et à main.
Le flag `EXPERIMENTS_ENABLED=true`, la confirmation manuelle et une CI push main
réussie sur le SHA courant sont indispensables. Un premier job sans OIDC
vérifie le SHA et les protections GitHub ; le job d'expérience attend ensuite
l'approbation de l'environnement `experiments-controlled`. Aucun approbateur
n'est appelé automatiquement, aucune PR ni aucun artefact PR n'est exécuté.

Le groupe de concurrence `deploy-jitsi-gke-main` est partagé avec Helm et
Terraform pour sérialiser les mutations. Il ne bloque pas une intervention
manuelle externe : le script recontrôle les réunions et l'identité des pods.
Le job est limité à 12 minutes, les observations à 240 s pour Malleus et 180 s
pour Chaos. Les appels de commande ont aussi des délais bornés.

L'identité prévue est **nouvelle et non provisionnée** :
`github-jitsi-experiments@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com`,
via le fournisseur proposé `github-experiments-provider`. Aucun compte Helm ou
Terraform n'est élargi. L'authentification utilise des identifiants externes,
sans clé JSON privée, et le même mécanisme exec ADC GKE déjà validé dans le
projet. Le kubeconfig est temporaire privé et supprimé en fin de job.

Les précontrôles exigent cinq pods de production prêts, deux nœuds Ready sans
pression, métriques accessibles et aucune conférence ni participant JVB. Le
budget d'entrée conservateur est CPU <20 % et mémoire <55 % sur chaque nœud ;
l'arrêt est déclenché à CPU ou mémoire >=80 %. Cette règle laisse une marge,
mais ne calcule pas les réservations exactes du scheduler et n'est pas un test
de capacité maximal. La pression disque est surveillée ; la capacité disque
libre réelle n'est pas déduite de l'allocatable.

## Malleus : profil existant à deux participants et 90 secondes

Le chart `charts/jitsi-load-test` et les deux profils `values-video-2x90.yaml`
et `values-video-2x90-low-cpu.yaml` sont réutilisés. Le rendu fusionné est vérifié
avant toute installation : seulement Deployment, Service ClusterIP et Job,
images exactes, aucun PVC/hostPath/hostNetwork/token Kubernetes ou port hôte,
Job initialement suspendu et délai maximal 240 s. Les limites restent 900m CPU /
2 Gi pour Selenium et 300m / 768 Mi pour Malleus. L'anti-affinité Selenium/JVB
est conservée.

Le namespace `jitsi-load-test` doit être précréé, vide et autorisé séparément.
La release porte un nom unique par run/attempt, jamais `jitsi` ou `jitsi-edge`.
Après préparation du Grid, une seconde vérification de main, de l'absence de
réunion et des pods précède la levée de suspension du seul Job créé.

Les fonctions existantes `browser_stats` et `video_verified` sont réutilisées
sur un port-forward Grid loopback privé. Les mesures comprennent CPU/mémoire
nœuds et pods, états et redémarrages des pods de production, compteurs JVB et
indices vidéo clients. La réussite exige un Job Complete et au moins trois
échantillons vidéo positifs. **Elle ne prouve pas 90 secondes de vidéo continue**,
ni un test audio (les expéditeurs audio du profil historique sont désactivés).
La comparaison des erreurs ICE est conservatrice : un compteur historique
non nul peut provoquer un refus, même sans nouvelle erreur pendant le run.

## Chaos Mesh : uniquement un pod Web explicitement approuvé

Le workflow n'installe ni CRD, ni contrôleur, ni rôle cluster. Il exige le
contrôleur minimal déjà installé après autorisation, sans daemon, accès hôte
ou conteneur privilégié. Ces composants étaient absents lors de l'audit, après
le nettoyage historique. Leur bootstrap éventuel n'est pas autorisé ici.

L'opératrice fournit nom **et UID actuels** du pod Web au dispatch. Le sélecteur
validé de `tests/chaos/podchaos-web-once.yaml` est réutilisé avec ce nom courant,
jamais le nom historique. Le mode reste `one`, l'action `pod-kill`, le namespace
`jitsi` et le composant `web`. Le script vérifie le couple nom/UID immédiatement
avant création, sans pouvoir verrouiller atomiquement un objet Kubernetes.

Les bindings et règles du contrôleur sont relus, y compris ceux hérités de ses
groupes. Toute permission destructive Pods plus large que `delete` du seul nom
Web approuvé dans `jitsi` est refusée, y compris exec, eviction et wildcard.
Le rôle nominatif doit donc être revérifié et éventuellement ajusté manuellement
après autorisation si le pod Web a changé. L'identité GitHub ne peut pas supprimer
ni modifier directement les pods de production, ni lire leurs Secrets.

Les UID et redémarrages des autres composants sont comparés pendant le test.
La preuve d’injection exige AllInjected=True et un seul record Injected avec
injectedCount=1, selon le format des preuves historiques conservées. Le simple
remplacement du pod ne suffit pas. La récupération exige ensuite un nouveau
pod Web Ready et HTTPS 200 avec validation TLS
normale. Il ne s'agit pas d'un test de continuité d'une conférence, ni de haute
disponibilité. JVB, Jicofo, Prosody, Caddy et le contrôleur ne sont jamais des
cibles autorisées.

## Collecte et nettoyage

Le runner conserve des relevés horodatés dans un dossier privé sous RUNNER_TEMP.
Seuls `summary.json`, `metrics.jsonl` et `logs-sanitized.txt` sont publiables en
artefacts pendant trois jours. Les logs Maven sont filtrés par liste blanche
(compteurs de tests et BUILD SUCCESS), jamais publiés bruts. Ni identifiant de
session Selenium, candidat ICE, state, kubeconfig, secret ni token n'est exporté.
Les données de production ne sont pas téléchargées sous forme de Secrets.

Le nettoyage est appelé dans `finally`, puis dans une étape GitHub `always()` :
uniquement la release de test possédée par le run ou son objet PodChaos étiqueté.
Le namespace de test et le contrôleur préexistants restent à leur propriétaire ;
aucune suppression générale, finalizer forcé, suppression de namespace ou CRD.
Un échec de nettoyage est signalé, sans promettre une récupération réussie.
Une perte complète du runner peut empêcher ces deux nettoyages : le Job dispose
d'un délai maximal et d'un TTL, mais le Deployment Selenium peut subsister.
Il faut alors vérifier et supprimer explicitement la seule release identifiée,
après autorisation. Le nettoyage n'est donc pas une garantie absolue face à la
perte du runner.

## Prérequis bloquants et autorisations requises

- Environnement `experiments-controlled` à créer avec reviewer obligatoire,
  bypass administrateur interdit et politique main uniquement. Aucune création
  GitHub ou approbation n'a été faite dans cette étape.
- Fournisseur WIF et compte dédié à créer après accord : dépôt et identifiants
  immuables, ref main, chemins exacts des deux workflows et sujet immutable lié
  à cet environnement. Aucun élargissement du provider Terraform existant.
- IAM minimal de lecture du cluster pour le compte dédié ; binding WIF sans clé.
- RBAC de lecture métriques/nœuds et production ; accès port-forward au seul pod
  JVB approuvé (pas exec), droits Helm limités au namespace de test précréé.
  Le compte Helm existant a répondu **no** à create deployments dans ce namespace.
- Pour Chaos : contrôleur/CRD minimaux, droit de lecture des bindings/rôles pour
  le précontrôle, création/suppression du seul PodChaos de test et rôle nominatif
  de suppression du seul Web pour le contrôleur. Le droit create PodChaos n'est
  pas à lui seul une restriction de sélecteur : le garde du runner et le RBAC
  nominatif du contrôleur constituent deux barrières distinctes.
- Un dispatch réel est une nouvelle opération modifiant Kubernetes et générant
  de la charge : il demande un accord explicite. Aucun dispatch n'a été lancé.

Les validations locales couvrent 15 tests dédiés (fixtures, simulations et
rendus Helm), ajoutés aux tests existants. Elles ne valident pas les nouveaux
échanges OIDC, le RBAC futur ou une exécution des workflows sur GKE.

La permission GitHub `actions: read` permet la lecture des protections :
[environnements](https://docs.github.com/en/rest/deployments/environments#get-an-environment)
et [politiques de branche](https://docs.github.com/en/rest/deployments/branch-policies#list-deployment-branch-policies).
Aucun droit GitHub d’administration ou d’approbation n’est attribué au workflow.

Revue finale : les autorisations d’exécution **et de suppression nécessaires au
nettoyage** sont désormais contrôlées avant toute création. Un droit delete
manquant bloque le test en amont, sans élargissement automatique du RBAC.
