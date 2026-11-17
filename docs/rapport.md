# Déploiement et validation d'une plateforme de visioconférence Jitsi Meet sur Google Kubernetes Engine (GKE)

**Rapport de projet — Master 2 DevOps**
**Période documentée : octobre–novembre 2026 ; expérimentations et consolidation des 15–16 novembre 2026**

| Élément académique | Information |
|---|---|
| Auteur | À compléter avec le nom officiel attendu sur le rendu |
| Établissement et parcours | À compléter |
| Enseignant ou encadrant | À compléter |
| Année universitaire | À confirmer |
| Dépôt | [SaminouA/projet-jitsi-helm](https://github.com/SaminouA/projet-jitsi-helm) |

## Premier essai contrôlé de CD Helm réussi — 17 novembre 2026

Cette section actualise les états historiques « CD non validée » plus bas.
Le premier déploiement Helm automatisé contrôlé est désormais validé sur le
SHA main `ed49e2d6f829a926eeb7e9e534272a345f9ee7f5`. Il a été déclenché par
une unique relance de la CI push main existante, sans nouveau commit applicatif.
La CD permanente reste désactivée après l’essai. Cette réussite ne valide ni
Terraform apply automatisé, ni Malleus/Selenium Grid, ni Chaos Mesh.

### Autorisation, précontrôles et déroulement réellement exécuté

L’utilisatrice a autorisé un seul essai et son éventuel rollback. Avant activation :
SHA main attendu confirmé, contexte jitsi-cluster/europe-west1-b vérifié, cinq
pods prêts sans redémarrage, releases deployed, PVC Bound et IP inchangées.
Les statistiques internes Jicofo (port 8888 /stats) et JVB (port 8080
/colibri/stats) ont été interrogées deux fois : conférences=0 et participants=0
pour les deux composants ; JVB indiquait également zéro endpoint actif au premier
relevé. Aucun nom de salle ni identifiant de participant n’a été exporté.

Les révisions, UID des Services, UID/volume du PVC et IP ont été relevés dans un
fichier privé de métadonnées sous /tmp avant toute activation ; aucune sauvegarde
de valeurs Helm déchiffrées n’a été écrite. Les quatre variables de profil ont
été définies, puis GKE_CD_ENABLED=true en dernier :

| Variable | Valeur après l’essai |
|---|---|
| JITSI_ACCESS_PROFILE | public-edge |
| JITSI_PUBLIC_DOMAIN | jitsi-meet-m2.duckdns.org |
| JITSI_EDGE_ADDRESS_NAME | jitsi-edge-ip |
| JITSI_EDGE_CD_ENABLED | true — reste subordonnée au flag général |
| GKE_CD_ENABLED | **false**, désactivée et relue après l’essai |

Commande de relance exécutée une seule fois :

```bash
gh run rerun 44055927650 --repo SaminouA/projet-jitsi-helm
```

La [CI 44055927650, tentative 2](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44055927650/attempts/2)
a réussi ; son événement source reste push, branche main, SHA attendu.
Elle a déclenché le [CD 44057014445, tentative 1](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44057014445),
réussi lui aussi. OIDC, configuration exec ADC, préflights, déchiffrement SOPS,
vérifications et upgrades Helm ont réussi ; les nettoyages du répertoire privé,
du kubeconfig et des credentials de l’action OIDC sont marqués success.

Le CD a terminé le 17 novembre à 10:40:17, heure de Paris (09:40:17 UTC).
GKE_CD_ENABLED=false a été confirmé à 10:40:20, soit trois secondes après la
fin indiquée par GitHub. Aucun autre essai ou déploiement n’a été lancé.

### Révisions avant/après et vérifications indépendantes

| Élément | Avant | Après |
|---|---|---|
| Release Jitsi | Révision 3, deployed | **Révision 4, deployed** |
| Release Caddy jitsi-edge | Révision 2, deployed | **Révision 3, deployed** |
| Chart Jitsi / application | 3.10.0 / stable-11248 | Inchangés |
| Chart Caddy / application | 0.1.0 / 2.11.9 | Inchangés |
| Pods | 5 prêts, 0 redémarrage | Mêmes noms, 5 prêts, 0 redémarrage |
| PVC Caddy | 10 Gi, Bound, standard-rwo, RWO | Bound ; UID et volume inchangés |
| Services / IP | Web 34.78.71.58, JVB 34.62.165.81 | UID des Services et IP inchangés ; TCP 80/443 et UDP 10000 conservés |
| Événements Warning présents lors du contrôle final | Non utilisé comme mesure initiale | 0 |

Les mots de passe Jicofo/JVB actifs correspondent aux valeurs SOPS après
l’essai, comparaison en mémoire par booléens sans affichage ni fichier en clair.
Aucune rotation de secret n’est observée. Les logs ont été analysés au moyen
de messages fixes autorisés, sans reproduction des sorties brutes.

Le DNS résout vers l’IP Web attendue. La connexion TLS est validée par le magasin
de confiance système, avec vérification du nom, sans -k : certificat valide du
16 novembre 2026 à 18:30:15 UTC au 14 février 2027 à 18:30:14 UTC.

| Route HTTPS contrôlée après l’essai | Réponse |
|---|---|
| / | 200 |
| /config.js | 200 |
| /http-bind | 200 sur GET ; disponibilité HTTP, pas un test de session BOSH complète |
| /metrics, /colibri/stats, /debug, /healthz, /about/health | 404 |

La configuration servie conserve BOSH sur window.location.origin et ne contient
aucune référence à localhost:8081. Ces contrôles confirment la disponibilité
technique ; aucune nouvelle réunion audio/vidéo, aucun partage d’écran ni test
de charge n’a été exécuté après cet upgrade. Le test manuel utilisateur précédent
reste une preuve antérieure distincte.

### Résultat, retour arrière et limites

Aucune erreur ni dégradation n’a été observée ; le rollback autorisé n’a donc
pas été nécessaire et n’a pas été exécuté. Les cibles relevées avant cet essai
étaient Jitsi 3 et edge 2. Un rollback futur devrait faire l’objet d’un nouveau
contrôle de contexte et de révisions : ne pas réutiliser ces cibles aveuglément.
Le PVC, les IP et les secrets n’ont pas été supprimés ou remplacés.

La réussite prouve la chaîne CI push main → workflow_run → OIDC/exec ADC →
SOPS/préflights → deux upgrades Helm contrôlés. Elle ne prouve pas la création
automatisée de l’infrastructure, la haute disponibilité, la résilience ou une
capacité de charge. Aucun Terraform apply, changement IAM ni autre déploiement
n’a été effectué. Les deux upgrades restent non transactionnels ensemble.

Ce compte rendu est préparé localement sur la branche documentaire
`docs/first-controlled-helm-cd`, sans commit ni push et sans modification de main.

## Avancement du 17 novembre — diagnostic réussi, correction CD préparée

La PR nº 5 est fusionnée au SHA cbe2192bc2104b2f40b88633b24ae691eb854788.
Le [diagnostic 44053382824](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44053382824)
a réussi en une seule tentative : OIDC, exec ADC, plugin GKE, identité kubectl,
49 contrôles RBAC, PVC Bound, SOPS/KMS, comparaison des secrets/rendus et nettoyage.
La CI du merge a réussi et le job CD a été ignoré, sans aucune étape exécutée.
Ces faits remplacent les mentions d’un diagnostic encore bloqué dans les
sections historiques ci-dessous ; ils ne prouvent aucun déploiement CD.

La correction CD préparée ensuite réutilise les primitives exec ADC du diagnostic,
avec un adaptateur `scripts/configure-cd-gke.py`. Celui-ci valide l’événement
workflow_run via check-cd-event.py, exige une CI push main réussie, le dépôt
attendu, CD_ENABLE=true, le SHA actuel et un profil explicite. Il ne réutilise
pas le garde workflow_dispatch du diagnostic. Le kubeconfig CD est créé
exclusivement en 0600 sous RUNNER_TEMP, propagé au step suivant puis supprimé
par le nettoyage always ; les sorties sensibles restent capturées. Aucun droit
IAM/RBAC ou paramètre applicatif n’est changé.

Quand GKE_CD_ENABLED est absente ou false, la condition du job refuse le CD.
Un second contrôle dans le script refuse également tout flag autre que true
avant lecture cloud. Les gardes de CI préalable, main/SHA, SOPS/KMS, RBAC,
ressources existantes et comparaison des secrets/réseau restent présents.
Les validations locales de cette correction ont réussi : 64 tests unitaires
(58 précédents et 6 nouveaux tests CD avec outils distants simulés), contrôles
documentaires (11 documents, 26 liens locaux, 63 blocs shell) et diff --check.
Les URLs externes sont contrôlées syntaxiquement seulement. Le diagnostic
réussi cité plus haut précède cette nouvelle correction CD : aucune validation
runner de l’adaptateur workflow_run ni aucun upgrade ne sont revendiqués.

Cette préparation ne réalise aucun Helm upgrade, changement de variable ou
mutation GCP/GKE. **La CD n’est pas encore validée de bout en bout.**

La [procédure contrôlée](validation-cd-controlee.md) précise fusion/revue, contrôle
de dérive avant l’essai sans modification fonctionnelle, variables publiques,
révisions relevées immédiatement avant l’essai et rollback Jitsi puis edge si
concernés. Une mise à jour peut néanmoins redémarrer des pods ; prévoir une
fenêtre sans réunion. Aucun résultat de charge Malleus, résilience Chaos Mesh
ou Terraform apply automatisé n’est ajouté par cette correction Helm.

## État actuel pour la remise — consolidation locale du 16 novembre

Cette synthèse prévaut sur les descriptions historiques qui suivent. Aucune
nouvelle interrogation du cluster ou de GitHub, aucune mutation distante, aucun
commit ni push n’a été effectué pendant cette finalisation locale.

| Élément | Résultat et niveau de preuve |
|---|---|
| HTTPS public | Dernière validation : certificat de production, domaine `jitsi-meet-m2.duckdns.org`, Web `34.78.71.58` ; aucune nouvelle mesure distante ici |
| Jitsi / Caddy | Dernier état observé : Jitsi révision 3, edge révision 2, PVC indépendant 10 Gi Bound ; état actuel à recontrôler avant opération |
| Réunion publique | Test manuel confirmé par l’utilisatrice : salle `jitsitest`, ordinateur et téléphone simultanés, audio et vidéo dans les deux sens |
| Portée de cette réunion | Ni partage d’écran ni charge validés ; deux participants peuvent utiliser P2P, donc pas de preuve supplémentaire du trajet JVB |
| Main et CI | Dernier main confirmé `c3e8ead17a35e234c1789c6d80da2e89c87a77fe` ; CI réussie, job CD ignoré |
| Diagnostic réel | Run `43959531200` : plugin disponible, TCP API OK, `kubectl auth whoami` échoue avec `INDETERMINE` ; RBAC/PVC/SOPS runner non atteints |
| Correction locale | Kubeconfig dédié exec `gke-gcloud-auth-plugin` avec ADC OIDC ; aucun changement IAM/RBAC ; pas encore validé sur GitHub |
| CD | Intégrée, désactivée, non validée de bout en bout ; ancien `use_auth_provider: true` encore présent dans le workflow CD, adaptation séparée indispensable |

L’[architecture actuelle](architecture.md), la [procédure contrôlée](validation-cd-controlee.md),
la [soutenance](soutenance.md) et la [checklist de remise](checklist-remise.md)
regroupent les éléments opérationnels. Les sections chronologiques conservent
les manipulations et mesures antérieures : une ancienne mention de localhost,
de CD non implémentée ou de test restant ne décrit pas l’état final ci-dessus.

## Résumé

Ce projet étudie le déploiement reproductible d'une plateforme Jitsi Meet sur
Google Kubernetes Engine. L'infrastructure est décrite avec Terraform,
l'application est installée avec Helm et les configurations sont contrôlées
par GitHub Actions. La démarche couvre le provisionnement, la connectivité,
le diagnostic d'incidents et l'observation des ressources.

L'expérimentation a abouti à un cluster de deux nœuds et à quatre composants
Jitsi opérationnels. Les fonctions de réunion et de messagerie ont été testées
avec plusieurs sessions. Une conférence à trois participants a permis d'étayer
l'activité du pont média. Une référence au repos de deux minutes et un palier
progressif de cinq minutes ont ensuite été enregistrés. Les résultats montrent
une augmentation du CPU JVB pendant la conférence, sans redémarrage observé.
Ils ne permettent pas d'établir une capacité maximale ni une qualité de service
garantie. Ces mesures appartiennent à la phase du 15 novembre. Depuis, l’accès
HTTPS public et un essai manuel ordinateur/téléphone ont été confirmés par
l’utilisatrice. La CI fonctionne ; la CD est intégrée mais désactivée et non
validée de bout en bout. Le dernier diagnostic runner échoue sur l’identité
Kubernetes ; une correction exec ADC est préparée uniquement en local.

## Table des matières

1. Introduction, problématique et objectifs
2. Technologies et choix d'architecture
3. Méthodologie et préparation de l'environnement
4. Construction de l'infrastructure et déploiement
5. Validation fonctionnelle et résolution des incidents
6. Instrumentation et résultats de performance
7. Gestion de versions et validation continue
8. Analyse critique, limites et perspectives
9. Conclusion
10. Références
11. Annexes techniques et éléments de preuve

## 1. Introduction, problématique et objectifs

Une plateforme de visioconférence combine une application Web, des services
de signalisation et des flux audio/vidéo sensibles aux conditions réseau.
Son déploiement ne peut donc pas être évalué uniquement par l'affichage d'une
page ou par l'état « Running » de ses conteneurs. Il faut aussi vérifier la
cohérence des adresses annoncées, l'entrée dans les réunions et le transport
média, tout en maîtrisant les ressources et les coûts.

Dans ce projet de Master 2, j'ai retenu une démarche DevOps associant
infrastructure déclarative, packaging applicatif, versionnement et contrôles
automatisés. Le choix de GCP, GKE, Terraform, Helm et GitHub Actions constitue
le cadre technique du projet ; aucune étude comparative exhaustive avec
d'autres fournisseurs n'est revendiquée.

### 1.1. Problématique

**Comment déployer de manière reproductible une plateforme Jitsi Meet sur
un Kubernetes managé, puis démontrer son fonctionnement et observer son
comportement sous une charge limitée, sans confondre validation de
configuration, disponibilité technique et qualité de la communication ?**

### 1.2. Objectifs et critères de réussite

| Objectif | Critère retenu |
|---|---|
| Décrire l'infrastructure | Configuration Terraform versionnée et plan maîtrisé |
| Déployer l'application | Release Helm et composants Kubernetes prêts |
| Établir la connectivité | Accès Web, BOSH et adresse publique JVB cohérents |
| Valider les usages | Entrée en salle, audio/vidéo et messagerie observés |
| Observer les ressources | Mesures CPU/mémoire et statistiques média horodatées |
| Sécuriser les évolutions | Contrôles CI réussis et intégration par pull request |
| Maîtriser le périmètre | Secrets et résultats bruts exclus de Git, limites explicites |

Les manipulations réalisées, les observations instrumentées et les procédures
seulement proposées sont distinguées dans les sections suivantes. Les annexes
ne constituent pas, à elles seules, une preuve d'exécution de leurs commandes.

## 2. Technologies et choix d'architecture

### 2.1. GCP et Google Kubernetes Engine

Google Cloud Platform fournit les ressources de calcul, le réseau, les droits
IAM et les services nécessaires au cluster. GKE est le service Kubernetes
managé utilisé ici : il évite d'administrer soi-même les composants du plan de
contrôle tout en permettant de travailler avec les objets Kubernetes usuels.
Ce choix recentre l'étude sur l'infrastructure déclarative, le déploiement et
la validation d'une application distribuée. [Présentation de GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/kubernetes-engine-overview)

Le projet utilise `project-fcf2ef91-c005-4910-a10`, dans la zone
`europe-west1-b`. Le cluster zonal `jitsi-cluster` possède un pool de deux
nœuds `e2-standard-2`. Ce dimensionnement est un environnement pédagogique
limité, pas une architecture de haute disponibilité démontrée.

### 2.2. Docker, images et conteneurs

Une image regroupe l'application et ses dépendances ; un conteneur est une
instance d'exécution isolée issue de cette image. Docker fournit notamment
les outils de construction et de distribution de ces images, ce qui facilite
la réutilisation d'environnements applicatifs. [Documentation Docker](https://docs.docker.com/get-started/docker-overview/)

Le projet réutilise les images publiées de Jitsi, référencées par le chart
avec le tag `stable-11248`. Aucun Dockerfile propre au projet ni construction
d'image personnalisée n'a été établi. Docker était présent sur la VM de
travail ; les nœuds GKE observés exécutaient les conteneurs avec **containerd**.
La présence de Docker sur la VM ne signifie donc pas que Docker Engine est
le runtime du cluster.

### 2.3. Kubernetes

Kubernetes organise le placement des pods, leur cycle de vie et leur accès
réseau. Les contrôleurs maintiennent l'état attendu et les Services donnent
un point d'accès aux pods malgré leur renouvellement. Cette séparation est
utile pour une application composée de plusieurs services. [Concepts Kubernetes](https://kubernetes.io/docs/concepts/overview/)

Dans le namespace `jitsi`, Web, Jicofo et JVB sont gérés par des Deployments,
Prosody par un StatefulSet. Les sondes servent à déterminer l'état prêt des
conteneurs. Les ConfigMaps portent les paramètres applicatifs et les Secrets
les informations d'authentification internes. Aucun contenu de Secret n'est
reproduit dans ce rapport.

### 2.4. Terraform

Terraform décrit les ressources cloud en code et calcule les actions requises
pour rapprocher l'infrastructure de cet état déclaré. Le plan permet de
contrôler les changements avant leur application ; l'état conserve les liens
avec les ressources gérées. [Introduction à Terraform](https://developer.hashicorp.com/terraform/intro)

Le dépôt contient deux ressources : `google_container_cluster.jitsi` et
`google_container_node_pool.jitsi_nodes`. Le provider Google est verrouillé
en version `7.46.1`, dans la contrainte `~> 7.0`. Les contrôles ont utilisé
Terraform `1.16.6`, compatible avec le minimum `1.16.0` demandé. Aucun backend
distant n'est déclaré : l'état est local et exclu de Git. Terraform a été
choisi pour rendre la création du cluster lisible et reproductible, pas pour
piloter le déploiement Helm dans la version actuelle du projet.

### 2.5. Helm

Helm regroupe les manifests Kubernetes dans un chart paramétrable. Une
release identifie une installation et ses révisions ; les fichiers de valeurs
adaptent les modèles sans réécrire tous les objets. [Charts Helm](https://helm.sh/docs/topics/charts/)

Le chart réellement utilisé est `charts-officiels/jitsi-meet`, version
`3.10.0`, provenant de **jitsi-contrib/jitsi-helm**. Le nom du dossier ne
constitue pas une certification d'éditeur : il s'agit du chart communautaire
référencé dans `Chart.yaml`. Son réemploi permet de se concentrer sur la
configuration et la validation. Le dossier `jitsi/` est un ancien squelette
Helm Nginx, conservé mais non utilisé pour cette installation. La release et
le namespace retenus sont tous deux nommés `jitsi`.

### 2.6. Jitsi Meet et ses composants

Jitsi Meet est une plateforme de visioconférence reposant sur WebRTC. Ses
composants séparent l'interface, la signalisation, l'organisation des réunions
et le transport média. Cette architecture en fait un cas d'étude pertinent
pour un déploiement distribué. [Architecture Jitsi](https://jitsi.github.io/handbook/docs/architecture/)

| Composant | Rôle et utilisation dans le projet |
|---|---|
| Web | Sert l'interface et la configuration JavaScript ; relaie BOSH vers Prosody |
| Prosody | Assure la signalisation XMPP et les échanges de présence nécessaires aux réunions |
| Jicofo | Coordonne les conférences et l'utilisation des bridges |
| JVB | Reçoit et retransmet les flux média entre participants lorsqu'un bridge est utilisé |

Avec deux participants, Jitsi peut utiliser une connexion média P2P. À partir
d'un troisième participant, le fonctionnement habituel passe par JVB. La
présence d'un pod JVB prêt n'est donc pas une preuve que le média d'un appel
à deux a transité par ce pod.

### 2.7. Git, GitHub et GitHub Actions

Git conserve les versions et les branches du projet ; GitHub héberge le dépôt,
les pull requests et les contrôles associés. Le versionnement permet de relier
une configuration aux corrections et aux validations qui l'accompagnent.
[Documentation Git](https://git-scm.com/docs/git)

GitHub Actions exécute le workflow YAML de validation dans un environnement
séparé de la VM. Dans ce projet, son intérêt est de reproduire les contrôles
à chaque évolution sans dépendre uniquement des vérifications manuelles.
L'outil permet aussi des déploiements automatisés, mais cette possibilité
n'est pas mise en œuvre ici. [Présentation de GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions)

### 2.8. Architecture commentée

```text
Ordinateur Windows / navigateur
  http://localhost:8081
       |
       | transfert VS Code Remote SSH
       v
VM de travail : 127.0.0.1:8081
       |
       | kubectl port-forward TCP 8081:8000
       v
Service Web ClusterIP:8000 -> Web:8000
       | /http-bind
       v
Prosody:5280, HTTP interne et signalisation XMPP
       ^
       | connexions XMPP de Jicofo et JVB
       |
Navigateurs -- média UDP 10000 --> LoadBalancer public --> JVB:10000
```

Le trafic Web et la signalisation empruntent les tunnels TCP ; le média JVB
utilise un chemin UDP distinct. Le LoadBalancer attribue une IP publique qui
doit correspondre à celle annoncée aux clients par JVB. Lors du déploiement
observé, cette adresse était `34.62.165.81` ; il s'agit d'une donnée historique,
pas d'une adresse à recopier lors d'une recréation.

L'accès de démonstration ne nécessite pas de domaine public. Ce choix évite
l'achat d'un domaine et une terminaison TLS Web pendant l'expérimentation.
Il ne constitue pas une publication Internet adaptée à des utilisateurs non
encadrés. La portée de cette limitation est discutée en section 8.

> **Figure 1 à insérer :** schéma exportable de l'architecture, distinguant
> les tunnels Web/BOSH du chemin média UDP. Le schéma ci-dessus décrit les
> composants ; il ne remplace pas une preuve de trafic.

## 3. Méthodologie et préparation de l'environnement

### 3.1. Une validation par niveaux

J'ai organisé l'évaluation en quatre niveaux : configuration statique,
disponibilité des composants, fonctionnement utilisateur et observation de
la consommation. Cette progression évite de conclure trop tôt à la réussite
d'une réunion à partir du seul rendu Helm ou d'une réponse HTTP.

La démarche a consisté à examiner l'existant, corriger la configuration hors
cloud, recréer l'environnement pour une session de validation, puis observer
les scénarios fonctionnels et les ressources. Le premier cluster avait été
volontairement détruit pour réduire les coûts ; cet événement antérieur est
rapporté dans le suivi du projet, sans journal complet de destruction conservé
dans le dépôt.

### 3.2. Environnement de travail et versions

La préparation et les diagnostics ont été réalisés dans le dépôt
`~/projet-jitsi-helm` sur une VM GCP, depuis Windows avec VS Code Remote SSH.
Edge et Firefox ont servi aux sessions utilisateur. Les outils nécessaires
sont `gcloud`, le plugin d'authentification GKE, `kubectl`, Helm, Terraform,
Python 3 et PyYAML.

| Élément | Version ou paramètre vérifié |
|---|---|
| Helm utilisé par la CI et les validations | 3.22.1 |
| Terraform utilisé | 1.16.6 |
| Provider Google verrouillé | 7.46.1 |
| Chart Jitsi / application | 3.10.0 / stable-11248 |
| Python dans GitHub Actions | 3.12 |
| PyYAML déclaré | 6.0.3 |
| Kubernetes observé pendant les diagnostics | v1.36.4-gke.2377000 |

Les versions exactes du navigateur, du système Windows et de tous les clients
locaux n'ont pas été consignées. Elles restent à renseigner si les preuves
originales sont disponibles ; elles ne sont pas reconstituées a posteriori.

### 3.3. Authentification et contrôles préalables

Les vérifications précédant le déploiement ont confirmé l'absence de cluster
et un état Terraform local vide. Les contrôles `fmt -check`, `validate` et
`plan -lock=false -input=false -no-color -detailed-exitcode` ont réussi, avec
**deux créations, aucune modification et aucune suppression** prévues.

Un premier obstacle a concerné l'audit IAM : l'identité de la VM ne pouvait
pas activer Cloud Resource Manager, faute de `serviceusage.services.enable`.
Le passage au compte personnel dans `gcloud` a permis l'examen des droits,
mais n'a pas immédiatement changé l'identité de Terraform. En l'absence de
fichier ADC local et de variables de credentials, celui-ci utilisait le
compte de service de la VM via le serveur metadata.

Après authentification ADC du compte personnel, son identité a été confirmée
sans affichage de jeton. Les droits personnels nécessaires testés, dont
`iam.serviceAccounts.actAs`, étaient accordés. Le compte Compute par défaut
`198310729956-compute@developer.gserviceaccount.com` était le compte attendu
pour les nœuds : aucun autre compte n'est explicitement configuré dans le
node pool. L'audit a constaté l'absence de
`roles/container.defaultNodeServiceAccount`, directement et dans
l'organisation parente examinée. La commande d'attribution a été fournie,
mais son exécution et la politique IAM finale ne sont pas attestées dans les
preuves conservées ici. Le succès ultérieur du déploiement ne remplace pas
ce justificatif. Aucun contenu d'ADC n'est versionné.

Les quotas examinés laissaient une marge pour 4 vCPU E2 et deux disques de
30 Go : E2 à 0/24 vCPU, CPU globaux à 2/32, instances régionales à 1/24,
adresses régionales utilisées à 1/8 et quota SSD à 20/500 Go. Les API GKE,
Compute, IAM, Service Usage, Logging et Monitoring étaient activées. Le réseau
`default` et son sous-réseau `10.132.0.0/20` existaient. Ces relevés sont des
instantanés préalables et ne garantissent ni les quotas actuels ni la capacité
physique disponible dans la zone.

> **Figure 2 à insérer :** sortie expurgée du plan à deux créations et des
> deux nœuds Ready. Conserver la date de la preuve ; masquer les credentials.

## 4. Construction de l'infrastructure et déploiement

### 4.1. Infrastructure déclarée

`terraform/main.tf` crée un cluster zonal puis un pool séparé. Le pool par
défaut initial est supprimé (`remove_default_node_pool=true`) ; le pool final
comprend deux nœuds `e2-standard-2`, chacun avec un disque `pd-balanced` de
30 Go. La suppression du cluster est autorisée par
`deletion_protection=false`, choix adapté au cycle de démonstration et de
nettoyage. Les paramètres projet, région et zone sont codés en dur dans le
provider ; leur externalisation constitue une amélioration future.

Le cluster a été recréé avant les essais du 15 novembre. L'observation de
deux nœuds Ready confirme son état opérationnel. Le dépôt permet de reproduire
la procédure, mais ne contient pas la transcription intégrale du `terraform
apply` exécuté lors de cette recréation. Les étapes de provisionnement en
annexe sont donc présentées comme une procédure, sans leur attribuer un
journal d'exécution inexistant.

### 4.2. Préparation du chart et résolution BOSH

La configuration initiale associait `publicURL: "localhost:8081"`, sans
protocole, à un JVB accessible uniquement en ClusterIP. Ces éléments ont été
corrigés avant la nouvelle session cloud. Ils constituaient des incohérences
identifiées ; le journal conservé ne permet pas d'attribuer rétrospectivement
l'ancien échec de réunion à une cause unique.

`values-gke.yaml` définit désormais `publicURL: "http://localhost:8081"`.
La surcharge JavaScript suivante, montée par le mécanisme du chart, fixe
BOSH sur l'origine réellement utilisée par le navigateur :

```javascript
config.bosh = window.location.origin + '/http-bind';
```

Web relaie ensuite les requêtes vers Prosody sur HTTP 5280 à l'intérieur du
cluster. L'HTTP interne n'est pas une URL publique donnée au navigateur.
HTTPS interne à Web, redirection HTTP, Ingress, Gateway et WebSocket XMPP
restent désactivés. Les navigateurs autorisent normalement les périphériques
sur localhost comme contexte de confiance, avec consentement utilisateur ;
cette exception n'autorise pas une publication Web sur une IP publique HTTP.

### 4.3. Déploiement Helm en deux phases

La phase 1 a créé la release `jitsi` dans `jitsi` avec `values-gke.yaml`.
La révision 1 a été observée en statut `deployed`, avec les quatre pods prêts.
Le Service JVB était déjà un LoadBalancer UDP 10000, mais son adresse devait
encore être injectée dans la configuration annoncée.

L'IP réelle `34.62.165.81` a ensuite été lue depuis le Service. Le script
`scripts/jvb-values.py` a produit `values-gke.demo.yaml`, contenant uniquement
`jvb.publicIPs`. Ce fichier local est ignoré par Git. Après réussite des
contrôles sur les deux fichiers fusionnés, `helm upgrade` a appliqué la
phase 2 : **révision 2, statut deployed**. `JVB_ADVERTISE_IPS` et `JVB_PORT`
ont été vérifiés dans le pod et correspondaient à `34.62.165.81` et `10000`.

Un seul bridge est configuré : `replicaCount=1`, `portRangeSize=1`, port nommé
`rtp-udp-0`. `useNodeIP`, `hostPort`, `hostNetwork` et STUN sont désactivés
pour annoncer explicitement l'adresse du LoadBalancer. TURN n'est pas activé.
Le Service Web reste ClusterIP sur 8000 ; Prosody n'est pas exposé au public.

Les anciens pods JVB/Jicofo ont été vus en terminaison pendant la mise à jour,
puis les nouveaux pods sont devenus prêts. Quelques messages initiaux ont été
observés : absence de `sip-communicator.properties` dans JVB, difficultés XMPP
au démarrage et, plus tard, abandon SCTP signalé par un pair. Leur présence
n'a pas été assimilée à une panne permanente : les diagnostics ultérieurs
ont trouvé JVB sain, une connexion BOSH fonctionnelle et aucun nouvel échec
ICE dans les fenêtres examinées.

## 5. Validation fonctionnelle et résolution des incidents

### 5.1. Accès depuis Windows et incident Remote SSH

Le tunnel Kubernetes actif sur la VM était correctement configuré :

```sh
kubectl -n jitsi port-forward --address 127.0.0.1 \
  svc/jitsi-jitsi-meet-web 8081:8000
```

Le port distant 8081 était ensuite transféré vers le port local 8081 de
Windows dans VS Code. Le premier transfert acceptait les connexions TCP mais
ne transmettait aucune réponse HTTP. Les contrôles sur la VM ont trouvé le
processus en écoute, un endpoint Web prêt et une réponse HTTP 200 avec
`curl --noproxy '*' -v --max-time 10`. La page de salle, `config.js`, les
fichiers JavaScript et CSS étaient également accessibles. Aucune erreur Web
ou Prosody récente n'a été détectée dans la fenêtre de cinq minutes examinée.

La suppression du seul transfert VS Code puis sa recréation manuelle ont
rétabli l'accès Windows à `http://localhost:8081`. Aucun redémarrage de pod
ni changement de règle GCP n'a été nécessaire. Une tentative de tunnel SSH
direct a rencontré une demande de phrase secrète de clé ; aucune
réinitialisation de clé n'a été réalisée. La connexion Remote SSH déjà
ouverte a été privilégiée.

Ce diagnostic illustre la nécessité de séparer le chemin Windows–VM du
chemin VM–Kubernetes. Un HTTP 200 depuis la VM ne prouve pas que le navigateur
Windows atteint ce port. De même, une connexion TCP locale acceptée ne
prouve pas la réception de la réponse HTTP à travers tout le tunnel.

### 5.2. Résultats utilisateur

| Étape | Résultat observé | Portée |
|---|---|---|
| Un participant | Salle `demo` rejointe, aperçu caméra, microphone détecté, statut modérateur | Accès et périphériques locaux |
| Deux participants | `nadira` et `test` simultanés ; vidéo entre sessions validée, audio confirmé par l'utilisatrice | Deux sessions sur le même ordinateur Windows, Edge/Firefox |
| Messagerie | Chat collectif et messages privés fonctionnels ; deux utilisateurs affichés | Fonctions de réunion observées |
| Trois participants | `nadira`, `test`, `test3` simultanés | Observation dédiée du bridge, détaillée ci-dessous |

Une réponse HTTP 200, la présence de la surcharge dans le `config.js`
effectivement servi et l'ouverture d'une session BOSH ont confirmé le chemin
de signalisation via Web. Le contenu de la session n'a pas été divulgué.
La détection du microphone seule ne prouve pas la transmission du son ; la
validation audio à deux repose sur la confirmation de l'utilisatrice.
Les observations à trois ne documentent pas individuellement tous les flux
reçus. Aucun test entre deux réseaux distincts n'est attesté.

> **Figure 3 à insérer :** interface de la salle `demo`, caméra et liste des
> participants. Ajouter seulement une capture réellement disponible, avec
> accord des personnes et masquage des données personnelles si nécessaire.
>
> **Figure 4 à insérer :** chat collectif et message privé observés pendant
> le test à deux. Ne pas fabriquer ou reconstituer une preuve d'écran.

### 5.3. Validation de Jitsi Videobridge — conférence à trois participants

**Date : 15 novembre 2026.** Les participants « nadira », « test » et « test3 »
étaient connectés simultanément à la salle « demo » lors du diagnostic en
lecture seule. Deux lectures de l'API JVB `/colibri/stats` ont été réalisées à
15:56:39 et 15:56:55, heure de Paris, avec un intervalle mesuré de
**15,271 secondes**.

| Indicateur | Première mesure | Seconde mesure |
|---|---:|---:|
| `healthy` | `true` | `true` |
| `conferences` | 1 | 1 |
| `inactive_conferences` | 0 | 0 |
| `participants` | 3 | 3 |
| `endpoints` | 3 | 3 |
| `p2p_conferences` | 0 | 0 |
| `bit_rate_download` | 829 | 693 |
| `bit_rate_upload` | 892 | 722 |
| `packet_rate_download` | 269 | 245 |
| `packet_rate_upload` | 257 | 232 |

Les débits et taux de paquets sont conservés comme valeurs brutes de l'API,
sans conversion ni attribution d'unités non vérifiées. Les compteurs cumulés
suivants n'ont pas varié sur cet intervalle :

| Compteur | Valeur aux deux mesures | Variation |
|---|---:|---:|
| `total_bytes_received` | 143 354 | 0 |
| `total_bytes_sent` | 10 500 | 0 |
| `total_packets_received` | 1 813 | 0 |
| `total_packets_sent` | 214 | 0 |

Leur stabilité ne constitue pas une preuve d'augmentation du trafic pendant
les 15,271 secondes. Aucune explication de leur mode d'actualisation n'a été
établie par ce diagnostic. Ces deux lectures ponctuelles proviennent du
compte rendu du diagnostic ; leur sortie brute n'est pas identifiée dans un
fichier JSONL conservé, contrairement aux scénarios instrumentés de la section 6.

Les compteurs ICE indiquaient **5 succès et 0 échec** ; il s'agit des totaux
observés, pas nécessairement de cinq nouvelles connexions pendant l'intervalle.
Les logs récents JVB montraient `ICE connected` et une transition vers
`Completed`, sans erreur ICE détectée dans la fenêtre examinée.

L'activité média sur JVB est **fortement étayée** par la conférence active à
trois endpoints, l'absence de conférence comptabilisée en P2P et les débits
entrants et sortants non nuls. Les connexions ICE réussies soutiennent ce
constat de connectivité. Ces observations ne constituent toutefois pas une
validation individuelle de chaque flux audio et vidéo reçu par chacun des
participants ; elles ne doivent pas être confondues avec une mesure de qualité
ou de capacité.

### 5.4. Retour au repos et qualification des scénarios

Après fermeture des navigateurs, les compteurs n'ont pas immédiatement disparu.
Une première lecture indiquait encore une conférence et trois endpoints actifs.
La lecture suivante indiquait une conférence inactive, trois endpoints inactifs,
aucun endpoint local actif et des débits nuls. Les logs JVB montraient des
événements de déconnexion ; l'absence d'événements récents Jicofo ne permettait
pas à elle seule de conclure à une suppression déjà effectuée.

À 16:19:26, heure de Paris, conférences, participants, endpoints et conférences
inactives étaient revenus à zéro, avec des débits nuls. La vérification a été
arrêtée dès cette condition satisfaite, sans redémarrage de composant.

Le scénario nommé `reference-sans-participants` a été écarté comme référence :
malgré son nom, ses huit relevés sur 120,001 secondes comportaient encore une
conférence et trois endpoints. La validité d'un scénario doit ainsi être
établie à partir de ses mesures, pas de son nom de dossier. Une nouvelle
référence a été retenue après confirmation instrumentée du retour au repos.

## 6. Instrumentation et résultats de performance

### 6.1. Protocole de mesure

Le script `scripts/monitor-load.sh` effectue des lectures toutes les quinze
secondes. Il interroge l'API `metrics.k8s.io`, l'état des pods et l'endpoint
JVB `/colibri/stats`. Chaque exécution produit `metadata.json`,
`metrics.jsonl`, `errors.jsonl` et `summary.json` dans un dossier daté sous
`tests/results/`. Le script accepte un nom de scénario et une durée, conserve
les données à l'interruption et ne génère aucune charge. Un relevé ponctuel
et un test d'interruption avec réponses simulées ont vérifié sa collecte et
son arrêt propre. Les résultats bruts sont conservés localement, hors Git.

Metrics Server était accessible et `kubectl top` fonctionnait. Chaque nœud
présentait environ 1,93 CPU et 5,88 Gio allouables aux pods, pour une machine
nominale de 2 vCPU et 8 Go. Pendant les diagnostics, Web, Jicofo et JVB étaient
sur le nœud `…ddx2`, Prosody sur `…jjk0`. Le bridge unique ne dispose donc pas
automatiquement des quatre vCPU du cluster. Les limites mémoire de JVB et
Jicofo sont de 4 Gio chacune, Web de 1 Gio et Prosody de 2 Gio ; les limites
cumulées ne constituent pas une réservation physique et peuvent dépasser
la capacité d'un nœud. Cette situation nécessite une surveillance sous charge.

Aucun outil dédié k6, JMeter, Locust ou Jitsi Meet Torture n'a été trouvé dans
les emplacements examinés ; aucun scénario automatisé de charge média n'était
présent. La démarche retenue consiste à observer les sessions navigateur
existantes, sans créer une infrastructure de génération supplémentaire.
Un test HTTP répété ne représenterait pas une charge Jitsi audio/vidéo : il
solliciterait Web et les tunnels, sans nécessairement créer d'endpoints média.

### 6.2. Tests de performance — référence au repos

**Date : 15 novembre 2026.** Le scénario `reference-repos-confirme` a été
observé de 16:21:27 à 16:23:27, heure de Paris. Les données proviennent de
`tests/results/20261115T152127.518271Z_reference-repos-confirme/` et ont été collectées avec `scripts/monitor-load.sh`, sans générer
de charge.

La collecte s'est achevée normalement après **120,001 secondes**, sans
interruption : **8 relevés**, cadence configurée de 15 secondes et **zéro
erreur de collecte**. Les relevés vont du lancement à la seconde 105.0 ;
la durée totale inclut l'attente finale. Les fichiers JSONL sont lisibles et
le nombre de relevés correspond au bilan `summary.json`.

Sur tous les relevés, `conferences=0`, `participants=0` et `endpoints=0`.
JVB est resté `healthy=true`. Cette exécution constitue donc une référence
au repos valide pour la période observée, contrairement au scénario précédent
`reference-sans-participants`, qui comportait encore trois participants.

Les résultats CPU/mémoire figurent dans le tableau comparatif de la section 6.3.

Les valeurs CPU sont converties depuis les quantités Kubernetes :
1 mCPU = 1 000 000 nanocœurs et 1 CPU = 1 000 mCPU. Pour la mémoire,
1 Mio = 1 024 Kio = 1 048 576 octets. Les moyennes sont arithmétiques sur les
8 relevés, en sommant les conteneurs pour le pod JVB. Metrics Server peut
retourner une même observation à plusieurs lectures ; les nombres d'horodatages
source distincts sont : nœud …ddx2 : 4, nœud …jjk0 : 4, JVB : 4. Les minima et maxima sont ceux des
observations collectées, pas des pics instantanés garantis.

Les quatre pods Web, Prosody, Jicofo et JVB sont restés `Running` et `Ready`
sur tous les relevés, avec un compteur de redémarrages égal à zéro.
La disponibilité observée des pods ne remplace pas un test utilisateur ou
une mesure HTTP continue. Cette référence courte décrit la consommation au
repos ; elle ne permet pas de déduire une capacité maximale ni la performance
sous charge.

> **Figure 7 à insérer :** courbes CPU/mémoire construites à partir des JSONL
> effectivement conservés, avec unités, horodatages et identification du
> scénario. Une capture de `kubectl top` isolée ne remplace pas ces séries.

### 6.3. Tests de performance — palier à trois participants

**Date : 15 novembre 2026.** Le scénario `palier-3-participants` est comparé
à la dernière exécution de `reference-repos-confirme` du même jour. Sources :

- `tests/results/20261115T152127.518271Z_reference-repos-confirme/`
- `tests/results/20261115T152725.078684Z_palier-3-participants/`

Les bilans `summary.json` indiquent respectivement **120,001 secondes et
8 relevés** pour le repos, puis **300,001 secondes et 20 relevés** pour le
palier. Les deux collectes sont terminées sans interruption, avec zéro échec
de requête. Les fichiers `errors.jsonl` sont vides et aucun relevé ne contient
d'erreur de collecte. La cadence configurée est de 15 secondes. Pour le palier,
le premier et le dernier relevés sont séparés de 285 secondes ; la durée totale
inclut l'attente finale.

#### 6.3.1. Comparaison des ressources

| Ressource | Scénario | CPU min. (mCPU) | CPU moyen (mCPU) | CPU max. (mCPU) | Mémoire min. (Mio) | Mémoire moyenne (Mio) | Mémoire max. (Mio) |
|---|---|---:|---:|---:|---:|---:|---:|
| JVB | Repos | 6,299 | 8,632 | 11,070 | 303,578 | 303,580 | 303,582 |
| JVB | Palier 3 | 3,089 | 85,794 | 142,609 | 303,582 | 305,922 | 307,879 |
| Nœud `…ddx2` | Repos | 123,128 | 128,622 | 140,299 | 2220,863 | 2224,256 | 2227,859 |
| Nœud `…ddx2` | Palier 3 | 105,472 | 198,941 | 302,259 | 2223,504 | 2228,494 | 2232,629 |
| Nœud `…jjk0` | Repos | 118,544 | 128,161 | 138,823 | 2055,973 | 2058,711 | 2061,828 |
| Nœud `…jjk0` | Palier 3 | 113,430 | 129,523 | 162,221 | 2052,543 | 2057,631 | 2060,398 |

Conversions : 1 mCPU = 1 000 000 nanocœurs ; 1 Mio = 1 024 Kio.
Les moyennes arithmétiques portent sur tous les relevés de chaque scénario,
en sommant les conteneurs pour JVB. Les compteurs CPU/mémoire ont quatre
horodatages source distincts par ressource au repos et dix au palier : des
lectures successives réutilisent certaines observations Metrics Server.

#### 6.3.2. Conférence, média et stabilité

Le palier ne maintient pas trois participants pendant toute la collecte :
quatre relevés indiquent zéro conférence et zéro endpoint, un relevé indique
une conférence avec deux endpoints mais aucun endpoint local actif, puis
quinze relevés indiquent une conférence avec trois endpoints et trois
endpoints locaux actifs. Ces quinze observations vont de 16:28:40 à 16:32:10,
heure de Paris. Les moyennes ci-dessus incluent donc la montée en charge et
ne sont pas les moyennes d'un régime constant à trois participants.

| Statistique JVB | Repos : min. / moyenne / max. | Palier : min. / moyenne / max. |
|---|---:|---:|
| `conferences` | 0 / 0 / 0 | 0 / 0,8 / 1 |
| `participants` et `endpoints` | 0 / 0 / 0 | 0 / 2,35 / 3 |
| `local_active_endpoints` | 0 / 0 / 0 | 0 / 2,25 / 3 |
| `bit_rate_download` | 0 / 0 / 0 | 0 / 594,85 / 827 |
| `bit_rate_upload` | 0 / 0 / 0 | 0 / 724,3 / 1 029 |
| `packet_rate_download` | 0 / 0 / 0 | 0 / 207,9 / 315 |
| `packet_rate_upload` | 0 / 0 / 0 | 0 / 321,85 / 452 |

Les débits et taux de paquets conservent les valeurs brutes de l'API, sans
unités ajoutées. Une conférence inactive et une conférence P2P sont chacune
signalées sur un relevé transitoire ; aucun des quinze relevés à trois
endpoints actifs n'est comptabilisé en P2P ou comme conférence inactive.
JVB reste `healthy=true` sur tous les relevés.

`total_ice_failed`, `endpoints_ice_failed`, `relays_ice_failed` et
`dtls_failed_endpoints` restent à zéro. `total_ice_succeeded` passe de 5 à 8,
soit trois succès supplémentaires pendant le palier. Les compteurs cumulés
`total_bytes_received`, `total_bytes_sent`, `total_packets_received` et
`total_packets_sent` restent respectivement à 126 702 372, 133 997 464,
355 307 et 320 743 : aucune augmentation n'est observée sur cet intervalle.
Ils ne doivent pas être utilisés comme preuve d'un volume transféré pendant
le test ; les débits non nuls et les endpoints actifs étayent l'activité média.

Les pods Web, Prosody, Jicofo et JVB sont `Running` et `Ready` sur les 20
relevés du palier, comme sur les 8 relevés de repos. Leurs compteurs de
redémarrages restent à zéro. Ce constat porte sur les instants échantillonnés,
pas sur une disponibilité continue mesurée par un client. L'absence d'erreur
de collecte ou d'échec ICE ne constitue pas une analyse exhaustive des logs.

#### 6.3.3. Portée du résultat

Le CPU moyen JVB est plus élevé que lors du repos, tandis que sa mémoire
reste proche de la référence. Ce résultat décrit un petit palier observé ;
il ne détermine ni la capacité maximale du bridge, ni une limite de
participants supportés, ni une performance garantie.

Les durées des scénarios diffèrent, le palier inclut l'arrivée des participants
et les mesures Metrics Server ne sont pas toutes indépendantes. Aucun profil
constant de résolution, de cadence vidéo ou de nombre d'émetteurs n'est
consigné dans ces fichiers. Ils ne valident ni chaque flux reçu, ni les
échanges entre réseaux distincts, ni la latence ou la qualité audio/vidéo.
Les performances des postes générateurs et des tunnels ne sont pas mesurées.
Des paliers stabilisés, répétés et à des charges supérieures seront nécessaires
pour poursuivre l'évaluation.

## 7. Gestion de versions et validation continue

### 7.1. Organisation du dépôt et chronologie vérifiable

Les branches ont séparé la première CI, l'infrastructure GCP et la préparation
de la démonstration. Les principaux jalons sont liés aux commits suivants :

| Date Git | Commit | Contenu attesté dans le dépôt |
|---|---|---|
| 20 octobre 2026 | `8005957`, `92dca89` | Workflow Helm et hooks locaux |
| 21 octobre 2026 | `509f327`, `98e4213` | Initialisation Terraform et fichier de rapport |
| 12 novembre 2026 | `21427a0` | Configuration GKE et valeurs de déploiement |
| 13 novembre 2026 | `68c9fe3` | Contrôles Helm/Terraform et préparation réseau |
| 13 novembre 2026 | `8e820d3` | Démonstration sans domaine et procédure JVB en deux phases |
| 15 novembre 2026 | `fb4d118` | Résultats fonctionnels, instrumentation et analyses de performance |
| 15 novembre 2026 | `1676e23` | Nom du contrôle CI aligné sur la protection de main |

Ces dates sont celles de l'historique Git ; elles n'établissent pas à elles
seules l'heure d'une manipulation cloud. Les commits sont consultables dans
[l'historique GitHub](https://github.com/SaminouA/projet-jitsi-helm/commits/feature/jitsi-offline-readiness/).

L'analyse des branches a montré que `feature/ci-helm` était déjà incluse dans
`main`, et `feature/terraform-gcp` dans `feature/jitsi-offline-readiness`.
Une seule avance rapide locale suffisait à regrouper le travail, sans
supprimer les branches ni écraser de fichier. Les états Terraform locaux ont
été conservés.

### 7.2. Contenu et validation de la CI

Le workflow `.github/workflows/helm-ci.yml`, nommé « Validation Helm et
Terraform », se déclenche sur les pushes, les pull requests vers `main` et
manuellement. Il installe Helm 3.22.1, Terraform 1.16.6, Python 3.12 et les
dépendances déclarées, puis exécute `sh scripts/validate.sh`.

Ce contrôle partagé avec les hooks `pre-commit` et `pre-push` réalise :

1. Le lint strict et le rendu des profils `mes-valeurs.yaml` et `values-gke.yaml`.
2. Le contrôle du BOSH même origine, des noms Kubernetes et du chemin UDP JVB.
3. La vérification de format Terraform, puis son initialisation et sa validation
   dans une copie temporaire des seuls fichiers `.tf` et du lock provider,
   avec backend désactivé et lockfile en lecture seule.
4. Lorsque `GKE_VALUES_FILE` est fourni, le contrôle du rendu fusionné avec
   l'adresse publique annoncée par JVB. Cette variable n'est pas fournie par
   le workflow actuel : la phase 2 réelle a été validée localement.

La CI dispose seulement de `contents: read`, sans identifiant GCP. Elle ne
réalise ni plan authentifié ni déploiement. Les manifests rendus pouvant
contenir des Secrets XMPP générés, ils restent dans un répertoire temporaire
supprimé, sans publication comme artefacts. Les credentials, clés, états,
plans, surcharges locales et résultats bruts sont exclus de Git. La syntaxe
du script de surveillance a été vérifiée localement ; son contrôle explicite
n'a pas encore été ajouté au workflow.

### 7.3. Incident d'intégration et preuves GitHub

Le push direct de l'intégration locale vers `main` a été refusé par GitHub :
les règles imposaient une pull request et un contrôle nommé « Validation Helm ».
Le job initialement nommé `validation` ne produisait pas ce nom exact.
La correction a consisté uniquement à ajouter `name: Validation Helm` au job,
sans supprimer les vérifications ni modifier les protections.

La [pull request nº 2](https://github.com/SaminouA/projet-jitsi-helm/pull/2)
a été créée depuis `feature/jitsi-offline-readiness`. Les contrôles du push
et de la PR ont réussi. Lors de la vérification documentaire, GitHub indiquait
sa fusion le 15 novembre 2026 à 17:28:44, heure de Paris, dans le commit
`90c58e77d4ac20d1214d7eecaad5ab4faa33a040`. L'identité de l'auteur de la fusion
n'est pas déduite de cette observation.

| Preuve | Résultat |
|---|---|
| [CI du travail documenté, commit fb4d118](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43732627159) | Réussite |
| [CI après correction du contrôle requis](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43734740781) | Réussite |
| [CI de la PR nº 2](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43734772489) | Réussite |
| [CI de main après fusion](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43735687915) | Réussite |

Ces exécutions attestent la CI de ces versions du code. La présente refonte
documentaire n'est pas encore commitée et n'est donc pas couverte par une
nouvelle exécution distante.

> **Figure 5 à insérer :** PR nº 2 et contrôle « Validation Helm » réussi.
> **Figure 6 à insérer :** workflow réussi sur main avec le hash associé.

### 7.4. Périmètre de la livraison continue

**La CI est validée ; la CD n'est pas implémentée.** Le déploiement étudié a
été effectué par commandes, pas par un pipeline GitHub Actions de livraison.
Le niveau d'automatisation attendu pour le rendu reste à confirmer avec
l'enseignant. Une future CD demanderait une identité GCP dédiée, des droits
adaptés, une gestion durable et verrouillée de l'état Terraform, des
approbations et des vérifications après déploiement. Il serait inexact de
présenter ces éléments comme déjà réalisés.

### Sécurisation des secrets avec SOPS et Google Cloud KMS

**Travaux du 16 novembre 2026.** Après les validations fonctionnelles, la
sécurisation a porté sur les mots de passe XMPP de Jicofo et JVB. L'objectif
est de conserver une configuration versionnable sans enregistrer ces valeurs
en clair dans Git et sans remplacer involontairement les mots de passe du
déploiement existant. Les opérations cloud et les tests cryptographiques
ci-dessous sont ceux réalisés lors de cette étape, selon le compte rendu du
projet ; ils n'ont pas été relancés pour rédiger cette section.

SOPS est un outil de chiffrement de fichiers structurés : il peut protéger
les valeurs d'un YAML en conservant une structure exploitable. Google Cloud
KMS gère la clé qui protège la clé de données utilisée par SOPS ; l'accès aux
opérations cryptographiques dépend des autorisations Google Cloud. Cette
séparation permet de versionner les données chiffrées sans placer la clé KMS
dans le dépôt. Le chiffrement par enveloppe sépare la protection des données
de celle de leur clé. [Documentation SOPS](https://getsops.io/docs/),
[principe du chiffrement par enveloppe](https://docs.cloud.google.com/kms/docs/envelope-encryption).

#### 1. Identification des Secrets Kubernetes existants

Les Secrets associés à Jicofo et JVB ont été identifiés dans le namespace
`jitsi`. Avec les noms de release et les templates du projet, il s'agit de
`jitsi-jitsi-meet-jicofo-secret` et `jitsi-jitsi-meet-jvb-secret`.
Les champs concernés sont respectivement `JICOFO_AUTH_PASSWORD` et
`JVB_AUTH_PASSWORD`. Ils permettent aux composants de s'authentifier dans
l'environnement XMPP ; ce ne sont pas des mots de passe de participants.

Cette identification a permis de partir des valeurs déjà utilisées par les
composants plutôt que de créer des mots de passe indépendants. Un Secret
Kubernetes et l'encodage base64 de son champ `data` ne constituent pas, à eux
seuls, un fichier chiffré pouvant être publié. Aucune valeur de ces champs,
encodée ou déchiffrée, n'est reproduite ici.

#### 2. Analyse de la génération et de la conservation par Helm

Les fichiers `templates/jicofo/secret.yaml`, `templates/jvb/secret.yaml` et
`templates/_helpers.tpl` du chart ont été examinés. En l'absence de
`existingSecretName`, chaque template applique la priorité suivante :

1. Utiliser `jicofo.xmpp.password` ou `jvb.xmpp.password` si une valeur est fournie.
2. Sinon, reprendre la valeur du Secret existant grâce au helper
   `jitsi-meet.existingSecretValue`, qui utilise `lookup` et décode le champ.
3. À défaut, générer une chaîne aléatoire avec `randAlphaNum 10`.

Si `existingSecretName` est renseigné, le chart référence le Secret externe
au lieu de créer ce Secret. Lors d'un rendu local sans accès au cluster,
`lookup` ne récupère pas le Secret déjà installé : un rendu statique ne prouve
donc pas la conservation des mots de passe en production. Cette analyse
explique l'intérêt de chiffrer les valeurs existantes et de vérifier leur
égalité avant toute utilisation ultérieure dans un déploiement.

#### 3. Activation de l'API Google Cloud KMS

L'API `cloudkms.googleapis.com` a été activée dans le projet
`project-fcf2ef91-c005-4910-a10`. Elle donne accès aux fonctions de gestion
des clés et aux opérations cryptographiques nécessaires à SOPS. Cette étape
prépare le service de chiffrement ; elle n'active ni un mécanisme OIDC ni une
connexion automatique entre GitHub Actions et GCP.

#### 4. Création du key ring et de la clé

Le key ring `jitsi-sops-keyring` et la clé `jitsi-sops-key` ont été créés dans
la région `europe-west1`. Le key ring organise les clés dans une localisation ;
la clé sert ici à protéger la clé de données SOPS. La référence non secrète
présente dans les métadonnées du fichier est :

```text
projects/project-fcf2ef91-c005-4910-a10/locations/europe-west1/keyRings/jitsi-sops-keyring/cryptoKeys/jitsi-sops-key
```

La localisation KMS est régionale, contrairement à celle du cluster zonal
`europe-west1-b`. La présence de cette référence dans le fichier chiffré a été
vérifiée ; elle identifie la clé utilisée sans divulguer son contenu. La
rotation, la récupération en cas de perte d'accès et la politique IAM minimale
ne sont pas évaluées par le seul test de chiffrement.

#### 5. Installation de SOPS sur la VM

SOPS **3.11.0** a été installé sur la VM. La commande `sops --version` confirme
cette version ; les métadonnées du YAML chiffré indiquent également `3.11.0`.
L'installation locale permet les opérations cryptographiques depuis cet
environnement, sans supposer que SOPS est déjà disponible sur les runners
GitHub Actions.

#### 6. Validation du chiffrement et du déchiffrement

Un essai de chiffrement puis de déchiffrement avec SOPS et la clé KMS a été
réalisé avec succès. Il valide le fonctionnement de l'outil, la référence de
clé et l'accès cryptographique avec l'identité locale utilisée pendant le
test. Il ne démontre pas qu'une identité GitHub possède les mêmes droits.
Aucun contenu de test déchiffré ni jeton d'authentification n'est publié.

#### 7. Création du fichier de valeurs chiffré

Le fichier `values-secrets.sops.yaml` a été créé avec les valeurs sensibles
de `jicofo.xmpp.password` et `jvb.xmpp.password`. La lecture de sa structure,
sans déchiffrement, confirme que les deux champs sont stockés sous forme
`ENC[...]` et que les métadonnées SOPS référencent la clé KMS attendue.

La structure YAML facilite l'identification des paramètres, mais les valeurs
sensibles ne sont pas utilisables directement comme mots de passe tant
qu'elles restent chiffrées. Helm ne déchiffre pas nativement un fichier SOPS :
ce fichier ne doit pas être passé tel quel à un déploiement en supposant
qu'il sera automatiquement interprété. La préparation du fichier chiffré est
réalisée ; son intégration à une procédure de déploiement sécurisée reste
une étape distincte.

#### 8. Comparaison avec les Secrets du cluster

Les mots de passe issus du déchiffrement ont été comparés aux valeurs des
Secrets Kubernetes existants. La correspondance a été vérifiée pour Jicofo
et pour JVB, sans publier les valeurs. Le résultat confirme que le fichier
chiffré représente les identifiants du déploiement contrôlé et ne constitue
pas une rotation de mots de passe.

Cette égalité est une validation de cohérence des données. Elle ne remplace
pas un test de mise à jour Helm utilisant le mécanisme sécurisé, ni une
vérification de connexion XMPP après un tel déploiement. Aucun déchiffrement
supplémentaire n'a été effectué lors de la présente mise à jour documentaire.

#### 9. Exclusion du fichier temporaire en clair

Le fichier de travail `values-secrets.plain.yaml` est protégé contre un ajout
Git ordinaire par la règle `/values-secrets.plain.yaml` dans `.gitignore`.
L'application de cette règle et le suivi du seul fichier chiffré ont été
vérifiés. Le commit étudié ne contient pas le fichier en clair.

Cette exclusion ne chiffre pas le fichier local, ne restreint pas ses droits
d'accès et ne remplace pas son nettoyage. Elle n'empêcherait pas non plus un
ajout forcé. La suppression finale du temporaire n'est pas déduite de la seule
règle Git ; elle doit être vérifiée séparément, sans afficher son contenu.

#### 10. Traçabilité dans Git

La sauvegarde de cette étape correspond au commit
`0069f6585a2c0b6a2aaefffeb497b0003bf0c11c`, abrégé `0069f65`, créé le
16 novembre 2026 sur `feature/jitsi-offline-readiness`, avec le message :

```text
security: encrypt Jitsi Helm secrets with SOPS and GCP KMS
```

Le diff du commit porte sur deux fichiers : ajout de
`values-secrets.sops.yaml` et ajout de l'exclusion du temporaire dans
`.gitignore`. Il ne contient ni modification de template Helm ni nouvelle
étape de déploiement dans GitHub Actions. La présence d'un commit local ne
prouve pas, à elle seule, son push ou son intégration dans `main`.

#### 11. Contrôles statiques associés au commit

Le dépôt est configuré avec `core.hooksPath=.githooks`. Le hook
`pre-commit` appelle `scripts/validate.sh`, qui interrompt le commit si un
contrôle échoue. Les vérifications statiques prévues par ce script sont :

| Contrôle | Utilité et portée |
|---|---|
| `helm lint --strict` sur les deux profils existants | Vérifier la cohérence des valeurs et du chart |
| `helm template` sur ces profils | Vérifier le rendu des manifests sans déploiement |
| `scripts/check-render.py` | Contrôler les invariants Web/BOSH et UDP JVB |
| `terraform fmt -check` | Contrôler le format sans réécriture |
| Initialisation temporaire sans backend, puis `terraform validate` | Vérifier la configuration Terraform sans appliquer ni modifier l'état du projet |

Le commit a bien été créé. Les sorties détaillées du hook lors de ce commit
ne sont toutefois pas archivées dans Git : son existence et la configuration
actuelle du hook ne permettent pas d'attester séparément le résultat
historique de chaque commande, ni d'exclure un contournement du hook. Une
sortie de terminal expurgée reste à joindre pour documenter ces résultats
individuels. Aucun contrôle n'est relancé ici pour le présenter comme un
résultat historique.

Le script ne déchiffre pas `values-secrets.sops.yaml` et ne l'ajoute pas aux
fichiers de valeurs rendus par défaut. Les contrôles statiques ne constituent
donc pas une validation d'un déploiement utilisant les secrets SOPS. Les
validations cryptographiques et les comparaisons d'égalité réalisées
précédemment ont une portée distincte.

#### Bilan et étapes encore à réaliser

La préparation locale établit un fichier chiffré versionné, une référence KMS
identifiée et une correspondance vérifiée avec les deux Secrets existants.
Elle protège les données conservées dans Git ; elle ne configure pas le
chiffrement des Secrets Kubernetes au repos et ne supprime pas le besoin de
valeurs utilisables par les composants à l'exécution.

À l'issue de la seule étape SOPS, OIDC / Workload Identity Federation et
l'intégration GitHub Actions restaient à réaliser. La préparation décrite dans
la sous-section suivante actualise cet état : les politiques WIF/IAM sont
désormais vérifiées et le workflow est préparé localement. L'échange de jeton
depuis le runner, l'utilisation de SOPS dans GitHub Actions et les tests de
déploiement sécurisé restent non exécutés. La CI existante reste une CI de
validation ; la CD n'est pas encore validée en fonctionnement.

> **Preuves à joindre :** version SOPS, référence KMS, confirmations de succès
> du chiffrement/déchiffrement et des comparaisons, puis sortie des contrôles
> du commit. Les captures doivent exclure toute valeur en clair et tout jeton.

### Préparation de la CD sécurisée GitHub Actions — 16 novembre 2026

Cette étape prolonge la sécurisation SOPS/KMS. Le workflow de déploiement est
**préparé localement, sans commit, push ni exécution de CD**. La CI existante,
son nom « Validation Helm et Terraform » et son job « Validation Helm » sont
conservés sans modification. Les mentions antérieures de CD non implémentée
reflètent le stade précédent : une définition est maintenant préparée, mais
aucun déploiement automatisé réussi n'est encore revendiqué.

#### Identités et autorisations effectivement vérifiées

Le provider `github-provider` du pool `github-jitsi-pool` est `ACTIVE`, utilise
l'émetteur `https://token.actions.githubusercontent.com` et applique la condition :

```text
assertion.repository=='SaminouA/projet-jitsi-helm' && assertion.ref=='refs/heads/main'
```

Son chemin est
`projects/198310729956/locations/global/workloadIdentityPools/github-jitsi-pool/providers/github-provider`.
Le mapping fournit le sujet Google et les attributs dépôt, branche et ID du
dépôt. Cette condition limite les assertions acceptées au dépôt attendu sur
`main` ; elle ne dispense pas de contrôler le contexte déclencheur du workflow.

Les politiques lues confirment :

| Périmètre | Attribution observée | Utilité |
|---|---|---|
| Compte `github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com` | `roles/iam.workloadIdentityUser` au principalSet du dépôt dans le pool | Autoriser l'identité fédérée du dépôt à utiliser ce compte |
| Projet GCP | `roles/container.clusterViewer` pour le compte de déploiement | Lire les informations du cluster pour configurer l'accès Kubernetes |
| Clé `jitsi-sops-key` | `roles/cloudkms.cryptoKeyDecrypter` pour ce compte | Autoriser le déchiffrement de la clé de données SOPS |

Aucune clé privée JSON de compte de service n'est créée. L'action Google
utilisera une description temporaire de credentials fédérés pour ADC ; ce
fichier JSON est un descripteur WIF, pas une clé privée de compte de service.
L'action prévoit son nettoyage en fin de job. Le mécanisme OIDC complet depuis
un runner GitHub reste à tester : les politiques existantes ne constituent pas
une preuve d'échange de jeton réussi par le nouveau workflow.

Dans `jitsi`, le Role et le RoleBinding `github-jitsi-deployer` sont présents.
Le binding cible l'identité utilisateur Kubernetes correspondant au compte de
service Google. Les règles accordent `get`, `list`, `watch`, `create`, `update`,
`patch` et `delete` pour ConfigMaps, Secrets, Services, ServiceAccounts,
Deployments et StatefulSets. Les tests `create deployments.apps` et
`create secrets` sont confirmés positifs par `kubectl auth can-i --as=...`.
Il s'agit de vérifications d'autorisation, pas de créations de ressources.

Lors du premier diagnostic, les tests de lecture Pods/ReplicaSets retournaient
`no`, ce qui bloquait les contrôles de disponibilité Helm. Ce constat est
historique : la vérification suivante, détaillée ci-dessous, confirme désormais
les droits nécessaires. Le précontrôle conserve l'exigence `get/list/watch`
sur `pods` et `replicasets`, dans les groupes API respectifs `""` et `apps`.
Aucune règle IAM ou RBAC n'a été modifiée par les diagnostics ou les corrections
du pipeline présentés dans ce rapport.

#### Déclenchement et code de confiance

`.github/workflows/deploy-gke.yml` écoute uniquement la fin du workflow
« Validation Helm et Terraform » sur `main`. Le job vérifie explicitement
`conclusion=success`, l'événement source `push`, la branche `main`, le dépôt du
run et son dépôt d'origine. Un run de pull request, même vert ou issu du même
dépôt, ne doit pas déclencher ce déploiement. Aucun artefact de CI, cache issu
d'une PR ou code provenant d'une branche non validée n'est utilisé.

Le checkout porte sur le SHA exact contrôlé par la CI. Une lecture de la tête
de `main`, avant l'authentification puis juste avant Helm, refuse un commit
entre-temps dépassé. Les actions tierces sont épinglées par SHA. Le job a
uniquement `contents: read` et `id-token: write` ; la permission OIDC permet de
demander un jeton éphémère sans introduire de secret de connexion permanent.
Les protections de `main` restent nécessaires pour établir la confiance dans
le code fusionné. [Événement workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
[action Google d'authentification](https://github.com/google-github-actions/auth).

Une concurrence unique `deploy-jitsi-gke-main`, sans annulation du run actif,
sérialise les déploiements de ce workflow. GitHub peut remplacer un run encore
en attente par un plus récent ; la définition ne promet pas une livraison de
chaque commit intermédiaire. Une activation explicite via la variable de dépôt
`GKE_CD_ENABLED=true` est requise. Cette variable n'a pas été créée ou modifiée :
la préparation seule ne déclenche aucune mise à jour distante.

#### Périmètre Helm et précontrôles

Le workflow cible le cluster existant `jitsi-cluster`, la zone `europe-west1-b`,
la release et le namespace `jitsi`, et le chart local 3.10.0. Il n'exécute pas
Terraform, ne crée pas le namespace et ne modifie ni IAM ni KMS. Pour cette
première CD, la release doit déjà être `deployed` et le LoadBalancer JVB doit
posséder une IPv4 publique. Une installation initiale cloud reste une
procédure distincte malgré l'emploi de `helm upgrade --install`.

Le script `scripts/deploy-gke.sh` vérifie l'identité Kubernetes effective et
les permissions avant tout déchiffrement. Il récupère l'IP réelle du Service
JVB, produit une surcharge réseau temporaire et fusionne les trois fichiers :

1. `values-gke.yaml`, qui conserve Web privé et BOSH sur localhost ;
2. la surcharge générée `jvb.publicIPs`, sans IP codée en dur ;
3. les valeurs SOPS déchiffrées pour Jicofo/JVB.

Un lint et un rendu local précèdent l'application. `scripts/check-render.py`
vérifie les invariants Web/BOSH/JVB. `scripts/check-cd-render.py` refuse les
types hors périmètre, les objets absents, l'adoption d'une autre release, les
changements de ports/type de Service et les nouvelles annotations réseau.
L'inventaire du rendu avec mots de passe fictifs est comparé aux noms des
ressources déjà présentes ; aucun contenu de Secret n'est affiché.
Les mots de passe déchiffrés seront comparés en mémoire aux Secrets existants :
une différence bloque cette CD, qui ne doit pas réaliser une rotation implicite.
Une rotation intentionnelle nécessiterait une procédure et une autorisation
spécifiques.

Cette limitation évite de créer par inadvertance un autre Service LoadBalancer
ou des ressources cloud depuis Helm. Elle ne garantit pas qu'une mise à jour
soit sans effet : les pods peuvent être renouvelés et les charges peuvent
varier. Le workflow n'automatise ni mise à l'échelle, ni migration de chart,
ni retour arrière. En cas d'échec Helm, il signale l'échec sans lancer une
seconde mise à jour ou un rollback implicite.

#### Gestion du déchiffrement et fin de déploiement

Le runner installera SOPS 3.11.0 avec une empreinte SHA256 épinglée à partir
de la distribution officielle. Après authentification WIF, SOPS utilisera
les ADC fédérés pour demander à KMS le déchiffrement. Le fichier en clair
reste dans un répertoire créé avec `mktemp`, mode 700, sous `RUNNER_TEMP` ;
`umask 077` et `chmod 600` protègent les fichiers. Il n'est jamais écrit dans
le dépôt. Aucun `set -x`, affichage de valeurs, upload d'artefact ou trace brute
Helm/SOPS n'est prévu. Les sorties pouvant contenir des valeurs sensibles sont
capturées dans ce répertoire privé et ne sont pas publiées.

Un trap supprime le répertoire à la sortie du script, y compris sur échec ou
interruption traitable. Une étape `always()` apporte un second nettoyage.
Une suppression forcée du runner ne permet pas de garantir l'exécution d'un
trap ; l'utilisation d'un runner GitHub hébergé éphémère limite la persistance.
Le workflow exécute ensuite la mise à jour avec `--wait --timeout 10m`, sans
hooks, puis vérifie les workloads prêts et la correspondance de l'IP JVB.
Ces contrôles de disponibilité ne remplacent pas un test audio/vidéo depuis
un navigateur.

#### Vérifications locales et statut

La préparation inclut des tests synthétiques dans `tests/test_cd.py` : valeurs
cohérentes, refus de rotation sans fuite du mot de passe dans le message,
schéma sensible inattendu, nouvel objet, adoption d'une autre release,
changement de port, IP incohérente, workload non prêt et frontières de confiance
du workflow. Les neuf tests ont réussi localement. Ils n'obtiennent aucun jeton et ne
contactent aucun cluster. Le nouveau workflow les relancera avant son étape
d'authentification Google. La comparaison du rendu à valeurs fictives avec les
métadonnées du cluster a identifié 16 objets, tous déjà présents et gérés par
la release `jitsi`, sans type hors périmètre.
Les validations Helm/Terraform existantes sont exécutées séparément, avec la
validation Terraform isolée sans backend.

Aucun workflow n'a été poussé ou lancé pour cette étape. Restent nécessaires :
la revue du code, la confirmation RBAC décrite ci-dessous, l'intégration par PR avec
CI verte, puis l'activation explicite et un premier déploiement sécurisé
autorisé. La possibilité d'atteindre l'API GKE depuis un runner hébergé et le
cycle OIDC/KMS doivent être validés lors de cet essai. Les opérations cloud
et les lectures Kubernetes de la présente étape n'ont modifié aucune ressource.

### Corrections et nouvelle validation de la CD — 16 novembre 2026

La relecture des fichiers locaux a confirmé la séparation des arguments
`"$resource" -n`, `--install "$release"` et `echo 'Commit…'`, ainsi que la
commande `python3 -m unittest discover -s tests -p test_cd.py -v`.
Les concaténations signalées n'étaient plus présentes dans les versions
inspectées ; des tests de non-régression ont été ajoutés pour contrôler les
frontières des arguments. `bash -n` est nécessaire, mais ne suffit pas :
une concaténation de mots peut être syntaxiquement valide tout en modifiant
les arguments réellement transmis à une commande.

#### Contrôle du contexte workflow_run et du commit

Le script ne décide plus de la branche de la CI à partir de `GITHUB_REF`.
Pour `workflow_run`, cette variable décrit le contexte du workflow CD sur
la branche par défaut, et ne remplace pas `workflow_run.head_branch`.
Le nouveau helper `scripts/check-cd-event.py` lit le payload JSON de
`GITHUB_EVENT_PATH` et refuse toute exécution qui ne vérifie pas :

- l'événement GitHub `workflow_run`, une CD explicitement activée et le dépôt
  `SaminouA/projet-jitsi-helm` ;
- une CI « Validation Helm et Terraform » issue d'un `push`, terminée et réussie ;
- la branche source `main` et le même dépôt pour le run et son origine ;
- un SHA de 40 caractères hexadécimaux identique à `EXPECTED_SHA`.

Le workflow impose également `status=completed` et les mêmes contrôles de
succès, dépôt et branche avant de démarrer le job. Le checkout utilise le
SHA de la CI, sans récupérer d'artefact de PR. Le script compare le HEAD
checkouté et la tête distante de `main` à ce SHA, au début puis juste avant
Helm. Un commit dépassé ou différent est refusé. Cette vérification ne
verrouille pas la branche GitHub pendant la mise à jour : un nouveau commit
peut arriver ensuite, mais il ne change pas le code déjà checkouté. La
concurrence du workflow sérialise les déploiements ; chaque exécution reste
liée à son propre commit validé.

Les actions restent épinglées par SHA, sur un runner `ubuntu-latest` compatible
avec les runtimes des actions choisies. Les protections OIDC/WIF, les droits
GitHub limités, la vérification de l'identité Kubernetes, le checksum SOPS,
le répertoire temporaire privé et son double nettoyage sont conservés.
Aucun contenu déchiffré réel n'a été utilisé pour vérifier ces corrections.

#### Validation RBAC Pods/ReplicaSets

Les tests suivants ont été exécutés en lecture seule avec l'identité
`github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com`
via `kubectl auth can-i --as=...`, dans le namespace `jitsi` :

| Verbe | Ressource | Résultat |
|---|---|---|
| `get` | `pods` | `yes` |
| `list` | `pods` | `yes` |
| `get` | `replicasets.apps` | `yes` |
| `list` | `replicasets.apps` | `yes` |

Les vérifications `watch pods` et `watch replicasets.apps` retournent aussi
`yes`. Les droits `delete` sur `configmaps`, `secrets`, `services`,
`serviceaccounts`, `deployments.apps` et `statefulsets.apps` sont également
accordés. Le précontrôle demande désormais explicitement `delete`, en plus
de `get/list/watch/create/update/patch`, pour les ressources gérées par Helm.
Helm peut devoir supprimer des objets retirés d'une révision ; vérifier ces
droits évite une mise à jour partiellement appliquée par manque d'autorisation.
Les Pods et ReplicaSets sont seulement lus par ce contrôle ; le pipeline ne
leur demande pas directement de suppression. Aucun droit supplémentaire n'a
été attribué durant cette vérification.

Le blocage RBAC identifié précédemment n'est donc plus observé pour ces
lectures et suppressions. Ces tests d'autorisation ne sont ni un déploiement
ni une validation de la fédération depuis GitHub ; cette dernière reste à
vérifier dans une exécution réelle autorisée.

#### Résultats des contrôles locaux

Les **14 tests Python** réussissent. Ils couvrent les contrôles précédents
et les refus d'événements PR, de forks, de branches autres que main, de CI
non terminées ou échouées, de SHA incohérents et de CD désactivée. Un test
exécute les précontrôles Bash avec de faux outils locaux : l'absence simulée
de `delete` arrête le script avant tout appel à SOPS ou Helm. Aucun outil
cloud réel n'est utilisé par ce test.

La syntaxe Python, le YAML et tous les blocs Bash du workflow sont vérifiés.
Les validations existantes Helm/Terraform réussissent avec Terraform isolé
sans backend. Le rendu de phase 2, réalisé avec des mots de passe fictifs et
l'IP publique lue depuis le Service existant, contient **16 objets** ; les
invariants BOSH et JVB sont respectés. Aucun manifest sensible n'est affiché.
Le workflow CI initial et son job « Validation Helm » restent inchangés.

La portée de ces résultats reste une validation locale. Aucun déploiement,
commit ou push n'est effectué pour cette correction. Il reste à relire et
intégrer le code par PR, activer explicitement la CD après accord et vérifier
l'accès depuis le runner, l'échange OIDC/KMS puis une première mise à jour
sécurisée. Aucune exécution distante réussie de cette CD n'est revendiquée.

### Préparation Terraform initiale — état historique du 17 novembre 2026

Ce journal décrit la préparation initiale. Les statuts de backend, IAM et
déclenchement sont actualisés par la réconciliation et la revue finale ci-dessous.
Les procédures anciennes ne doivent pas être rejouées.

Les attendus pédagogiques précisent Terraform et Helm après push, secrets,
Malleus/Selenium Grid, Chaos Mesh et Cloud Monitoring. La CD Helm a réussi comme
détaillé plus bas ; **aucun apply Terraform automatisé n’est encore validé**.
Cette étape prépare uniquement une PR et ses contrôles. La branche documentaire
originale et ses modifications sont conservées dans leur worktree ; ce rapport
reprend aussi le compte rendu du premier CD, sans l’écraser.

#### Audit et plan réellement effectués

L’état Terraform local est au format 4, Terraform 1.16.6, serial 9 ; deux ressources
sont suivies : google_container_cluster.jitsi et google_container_node_pool.jitsi_nodes.
Il n’y a pas de backend distant configuré dans la base auditée. Aucun bucket
GCS du projet n’a été retourné par la liste. Le cluster jitsi-cluster est RUNNING,
zone europe-west1-b ; Logging et Monitoring Kubernetes sont configurés. Le label
observé avant modification est goog-terraform-provisioned=true. Le compte OIDC
Helm existant a container.clusterViewer au projet ; aucun compte Terraform dédié
n’a été trouvé. Le provider WIF existant est actif et restreint au dépôt/main.

Un worktree séparé prépare un label de preuve `devops-apply-proof=github-actions`
sur le cluster, avec prevent_destroy sur cluster et pool. Un plan a été calculé
avec les credentials opérateur existants, sur copie privée de la configuration
et de l’état, backend local isolé ; il lit GCP sans appliquer ni écrire dans
l’état original. Résultat : **cluster update, pool no-op**, changements limités
à resource_labels, terraform_labels et effective_labels ; aucune valeur inconnue
après apply, aucune création, suppression ou remplacement. Le garde strict a
accepté ce vrai plan. La [preuve expurgée](terraform-plan-preuve.json) ne contient
ni état, ni plan complet, ni credential. Ce plan local ne valide pas les futures
permissions du compte runner et doit être recalculé après migration.

#### Backend, identité et workflow proposés

Le [guide Terraform contrôlé](terraform-cd-controlee.md) détaille les commandes
préparées, coûts, conditions d’arrêt et preuves futures. Backend GCS proposé :
bucket dédié régional europe-west1, versioning, accès uniforme et prévention
d’accès public, préfixe jitsi/gke, workspace default, verrouillage GCS natif.
Le bucket doit préexister ; aucun bucket n’est géré par l’état qu’il héberge.
Le nom global reste à vérifier. Aucun bucket n’a été créé, aucun état migré.
La migration exigera un accord distinct, une copie privée conservant l’original,
la comparaison lineage/serial/adresses/IDs et l’interdiction de tout état vide.

Le compte proposé terraform-jitsi-deployer est séparé de Helm, sans clé statique,
RBAC Kubernetes ou déchiffrement KMS. Deux rôles personnalisés sont proposés :
lecture/mise à jour cluster et opérations au projet, accès objets/lock au seul
bucket. Le droit cluster update reste plus large qu’un label ; la restriction
par champ est assurée par le garde logiciel et la revue, pas par IAM. Un nouveau
provider OIDC est proposé avec dépôt/main/workflow_ref Terraform et attribut
pipeline dédié pour son binding SA. Aucun rôle, binding, provider ou SA n’a été
créé ou modifié pendant cette préparation.

Le workflow terraform-gke.yml attend une CI push main réussie, TF_CD_ENABLED=true,
TF_APPROVED_SHA égal au SHA CI et à la tête main, et Helm désactivé. Il partage
la sérialisation Helm/diagnostic et utilise l’environnement terraform-controlled,
**dont les protections humaines devront être configurées et vérifiées avant
activation**. Il prépare fmt/init/validate, vérifie bucket/lineage/serial et les
deux ressources, calcule un plan privé, refuse tout changement hors label,
puis prévoit apply du seul binaire contrôlé, sous verrou. Le code d’apply n’a
pas été exécuté contre GCP. Après un futur apply autorisé, il vérifiera label,
cluster RUNNING, serial et plan final sans changement, puis supprimera les
fichiers privés. Aucun état/plan n’est téléversé comme artefact ou affiché.

#### Validations locales de cette préparation

78 tests unitaires ont réussi : les 64 précédents et 14 nouveaux tests Terraform.
Les outils externes de ces tests sont simulés, y compris le scénario d’apply ;
il ne constitue aucune preuve d’application réelle. Helm public/localhost et
Terraform fmt/init backend=false/validate ont réussi sur copies isolées. Les
contrôles documentaires couvrent 12 documents, 28 liens locaux et 66 blocs shell
sans erreur ; les URLs externes sont contrôlées syntaxiquement seulement.
Le vrai plan privé de lecture a également été accepté par le validateur strict.

#### Limites et autorisations restantes

Avant le premier apply : autoriser séparément bucket et coûts, identité/rôles/WIF,
migration préservant l’état, protections GitHub, fusion, variables et fenêtre de
l’unique essai. Le flag Terraform restera absent/false jusque-là ; Helm reste
false. L’opérateur devra désactiver TF_CD_ENABLED après l’essai, même en échec ;
le token workflow n’a volontairement aucun droit de modification des variables.
Un échec n’autorise pas une relance, un destroy, un déverrouillage forcé ou une
restauration aveugle du state. Le retrait du label demanderait une nouvelle revue
et un plan autorisé, car le garde de premier essai refuse les changements généraux.

GCS ajoute stockage/versioning et opérations facturables, sur un état actuel
d’environ 24 Ko ; pas de nouveau calcul GKE ou LB pour le label. Aucun budget
mensuel n’est chiffré sans tarification/consommation confirmées et aucune ressource
payante n’est créée dans cette préparation. Les essais Malleus/Chaos et les
preuves Cloud Monitoring corrélées restent distincts et non réalisés ici.


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

#### Correction de la revue finale : approbation du plan exact

La première préparation ci-dessus approuvait le job avant génération du plan.
Elle ne satisfaisait donc pas une revue humaine du plan exact. Elle est remplacée
par la chaîne manuelle suivante : génération du plan privé, publication de sa
projection exhaustive des seuls changements autorisés et de son SHA-256,
attente d'un job distinct sous terraform-apply-review, puis apply du même binaire.
L'environnement de revue est distinct de celui de génération et n'a aucun droit
OIDC. Son absence ou une protection insuffisante bloque dès le précontrôle.

Le plan et l'état de référence sont transférés uniquement chiffrés, avec
AES-256-CBC/PBKDF2 et HMAC-SHA256 encrypt-then-MAC à clés indépendantes. Un secret
GitHub dédié TF_PLAN_TRANSPORT_KEY, à provisionner après accord, est requis ;
aucune clé réelle n'a été créée ou révélée. Les secrets Jitsi SOPS/KMS restent
inchangés. L'artefact est limité au même run/attempt et conservé un jour.
L'apply vérifie HMAC, SHA du plan, SHA du commit, run/attempt, revue et état
courant avant toute mutation. Il ne régénère pas le plan avant application.
Un rerun partiel, une dérive d'état, un artefact altéré ou une revue absente
imposent une nouvelle préparation et une nouvelle approbation.

Le résumé public contient l'ajout du label de preuve, ses champs exacts et le
pool no-op ; les attributs inchangés et les secrets ne sont pas publiés.
Le garde refuse désormais un label de preuve déjà présent, même avec une autre
valeur : aucun avant secret ou arbitraire n'est nécessaire dans cette revue.
Les tests locaux portent sur cette chaîne et le transport, pas sur un apply réel.
Aucun nouveau plan cloud n'a été lancé pendant cette revue finale, la configuration
Terraform et les preuves du dernier plan étant inchangées.


## 8. Analyse critique, limites et perspectives

### 8.1. Ce que les résultats démontrent

Le projet relie une configuration versionnée à un déploiement opérationnel
et à des observations de fonctionnement. La résolution du problème BOSH,
l'annonce explicite de l'IP JVB et le diagnostic du tunnel VS Code montrent
que l'état des pods et l'accès utilisateur doivent être analysés séparément.
Le cas de la fausse référence au repos illustre aussi l'importance de valider
les conditions expérimentales avant de calculer des moyennes.

Le CPU moyen JVB passe de 8,632 mCPU au repos à 85,794 mCPU sur l'ensemble du
palier progressif ; la mémoire moyenne passe de 303,580 à 305,922 Mio. Cette
augmentation est compatible avec l'activité de conférence observée. Elle
n'isole pas un effet causal de chaque participant : la montée en charge, les
fenêtres Metrics Server et les autres tâches des nœuds influencent les
mesures. Aucune extrapolation linéaire à des dizaines de participants n'est
justifiée.

### 8.2. Limites techniques et expérimentales

| Limite | Conséquence pour l'interprétation |
|---|---|
| Deux nœuds zonaux et un seul JVB | Haute disponibilité et montée en charge non démontrées |
| Accès Web par tunnels locaux | Dépendance aux postes et à Remote SSH ; pas un accès public autonome |
| Authentification Jitsi désactivée | Configuration réservée à une démonstration encadrée |
| TURN désactivé | Les réseaux bloquant l'UDP peuvent empêcher les médias |
| Tests à deux sur un même ordinateur | Pas de validation entre réseaux distincts |
| Trois endpoints observés, flux non contrôlés individuellement | Pas de preuve de qualité pour chaque destinataire |
| Mesures courtes, échantillonnées et parfois répétées | Pics et variations rapides potentiellement non observés |
| Pas de profil média constant documenté | Comparaison de capacité limitée |
| État Terraform local et paramètres codés en dur | Collaboration et réutilisation encore perfectibles |
| Phase 2 non testée automatiquement en CI | Contrôle réseau réel encore dépendant de la session locale |

L'accès au loopback de la VM peut être partagé par d'autres utilisateurs de
cette machine. Le serveur doit donc rester un environnement de confiance.
Une solution publique de production nécessiterait une conception dédiée de
l'accès, de TLS, de l'authentification et des secrets.

### 8.3. Coûts et gestion du cycle de vie

Les postes de coût sont les deux VM, les disques, le LoadBalancer UDP, les
adresses éventuellement facturées et le trafic sortant. L'absence de domaine
ou de LoadBalancer Web réduit certains besoins, mais ne rend pas GKE gratuit.
Une première destruction volontaire a limité la durée de vie du cluster ;
la preuve d'un nettoyage final après les essais du 15 novembre n'est pas
établie ici. La procédure de retrait est conservée en annexe D.

Aucune facture détaillée ni dépense totale vérifiée n'est disponible. Le
rapport ne transforme donc pas des tarifs indicatifs en coût effectivement
payé. Une synthèse de facturation datée, séparant les ressources préexistantes,
serait nécessaire pour un bilan économique chiffré.

### 8.4. Perspectives

Les suites prioritaires sont la confirmation des attentes pédagogiques sur
la CD, la validation sur plusieurs postes et réseaux, puis des paliers
stabilisés et répétés. Un générateur WebRTC tel que Jitsi Meet Torture/Malleus
pourrait automatiser les participants, sous réserve de contrôler aussi les
ressources des générateurs. Aucune installation ni utilisation de cet outil
n'est revendiquée dans ce travail.

Sur le plan opérationnel, les améliorations concernent l'état Terraform
distant, la séparation des identités de déploiement et des nœuds, les droits
minimaux, l'authentification applicative, TURN pour les réseaux restrictifs et
une collecte historique durable. Les propriétés de mise à l'échelle de JVB
nécessiteraient une étude spécifique ; elles ne découlent pas du seul nombre
de nœuds GKE.

## 9. Conclusion

Ce projet a permis de déployer Jitsi Meet sur un cluster GKE décrit avec
Terraform, de paramétrer ses composants avec Helm et de valider les
configurations par une CI GitHub Actions. La démonstration a établi l'accès
utilisateur, plusieurs fonctions de réunion et une activité média fortement
étayée sur JVB lors d'une conférence à trois participants.

La démarche de diagnostic a été aussi importante que le déploiement : il a
fallu distinguer signalisation et média, accès distant et accès Kubernetes,
configuration prête et trafic réellement observé. Les mesures au repos et
sur un premier palier apportent des résultats reproductibles à l'échelle de
l'expérience, sans constituer un dimensionnement de production.

Le résultat est une plateforme pédagogique fonctionnelle et documentée,
accompagnée d'une CI éprouvée. La validation publique ordinateur/téléphone est désormais confirmée par
l’utilisatrice. Des essais de charge plus complets et la validation effective
de la CD restent des perspectives explicites,
à traiter selon les exigences de l'enseignement et les contraintes de coût.

## 10. Références

Les références techniques ci-dessous ont été consultées pour la rédaction ;
le 15 novembre 2026 ; les versions utilisées expérimentalement restent celles du dépôt, même si
les documentations en ligne évoluent.

- [Google Cloud — Présentation de GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/kubernetes-engine-overview)
- [Docker — Présentation de la plateforme](https://docs.docker.com/get-started/docker-overview/)
- [Kubernetes — Concepts généraux](https://kubernetes.io/docs/concepts/overview/)
- [HashiCorp — Introduction à Terraform](https://developer.hashicorp.com/terraform/intro)
- [Helm — Charts](https://helm.sh/docs/topics/charts/)
- [Jitsi — Architecture](https://jitsi.github.io/handbook/docs/architecture/)
- [Git — Documentation](https://git-scm.com/docs/git)
- [GitHub — Comprendre GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions)

La version antérieure est conservée intégralement dans
`docs/archives/rapport-avant-refonte-2026-11-15.md` ; elle constitue une archive
historique et ne remplace pas la synthèse présente.

Les fichiers du dépôt, les liens de CI de la section 7 et les dossiers de
mesures cités en section 6 constituent les sources propres au projet. Les
résultats bruts ne sont pas publiés dans Git ; ils doivent être conservés
séparément et rendus disponibles à l'évaluation sous une forme expurgée si
l'établissement le demande.

## 11. Annexes techniques et éléments de preuve

### Annexe A — Paramètres et commandes de préparation

Les blocs suivants servent à la reproductibilité. Les commandes de diagnostic
et de validation ont été utilisées pendant le projet ; les séquences de
création et de nettoyage sont des procédures conservées, sans garantie que
chaque ligne ait été exécutée exactement sous cette forme. Copier un bloc de
procédure ne constitue pas une nouvelle exécution dans le cadre du rapport.

```sh
export GCP_PROJECT=project-fcf2ef91-c005-4910-a10
export GKE_ZONE=europe-west1-b
export GKE_CLUSTER=jitsi-cluster
export JITSI_NAMESPACE=jitsi
export JITSI_RELEASE=jitsi
export JVB_SERVICE="${JITSI_RELEASE}-jitsi-meet-jvb"
export WEB_SERVICE="${JITSI_RELEASE}-jitsi-meet-web"
```

Les ressources générées sont les Services `jitsi-jitsi-meet-web`,
`jitsi-jitsi-meet-jvb`, `jitsi-jitsi-meet-prosody`, les Deployments
`jitsi-jitsi-meet-web`, `jitsi-jitsi-meet-jicofo`, `jitsi-jitsi-meet-jvb-0`
et le StatefulSet `jitsi-jitsi-meet-prosody`. Ces noms ont été contrôlés dans
le rendu et les ressources observées. Les anciennes commandes avec la release
`mon-jitsi` ne correspondent pas à cette installation.

Installation des dépendances de validation et contrôles locaux :

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
sh scripts/validate.sh
TF_OFFLINE_PLUGIN_DIR="$PWD/terraform/.terraform/providers" sh scripts/validate.sh
```

La seconde variante réutilise le provider installé localement. Les deux
commandes sont des alternatives pour la même validation. Le script neutralise
`TF_DATA_DIR`, `TF_WORKSPACE` et les injections `TF_CLI_ARGS` des commandes
utilisées. Il ne copie pas l'état Terraform et désactive le backend dans son
répertoire temporaire.

Vérifications préalables et d'identité, sans publication de credentials :

```sh
gcloud auth list --filter=status:ACTIVE --format='value(account)'
terraform fmt -check -recursive terraform
terraform -chdir=terraform validate -no-color
terraform -chdir=terraform state list
terraform -chdir=terraform plan -lock=false -input=false -no-color -detailed-exitcode
```

Le code retour 2 du dernier plan indique des changements proposés, pas une
erreur. Les lectures IAM et d'identité ADC ont été effectuées sans afficher
les jetons. Une attribution IAM ne doit pas être déduite de la seule présence
d'une commande suggérée.

### Annexe B — Procédure de provisionnement et déploiement en deux phases

**Procédure susceptible de créer des ressources facturables.** Retrouver
l'état Terraform existant avant toute réutilisation. Ne pas fabriquer un
nouvel état pour contourner une incohérence et ne pas supprimer cet état.
La création du cluster est attestée par ses observations opérationnelles,
mais son journal intégral de provisionnement n'est pas annexé.

```sh
gcloud auth login
gcloud auth application-default login
gcloud config set project "$GCP_PROJECT"
terraform -chdir=terraform init -lockfile=readonly
terraform -chdir=terraform plan -out=tfplan
terraform -chdir=terraform apply tfplan
gcloud container clusters get-credentials "$GKE_CLUSTER" \
  --zone "$GKE_ZONE" --project "$GCP_PROJECT"
kubectl config current-context
kubectl get nodes
```

Les identités `gcloud` et ADC doivent être contrôlées séparément. Les plans
peuvent contenir des informations sensibles et restent hors Git.

La phase 1 est attestée par la release déployée en révision 1 :

```sh
helm upgrade --install "$JITSI_RELEASE" ./charts-officiels/jitsi-meet \
  --namespace "$JITSI_NAMESPACE" --create-namespace \
  -f values-gke.yaml --wait --timeout 10m
kubectl -n "$JITSI_NAMESPACE" get pods,svc
kubectl -n "$JITSI_NAMESPACE" get svc "$JVB_SERVICE" --watch
```

Après attribution de l'IP, arrêter la surveillance avec Ctrl+C puis générer
la surcharge. Si l'adresse manque ou si une validation échoue, ne pas
poursuivre. Un délai Helm expiré doit être diagnostiqué avant toute nouvelle
installation.

```sh
export JVB_PUBLIC_IP="$(kubectl -n "$JITSI_NAMESPACE" get svc "$JVB_SERVICE" \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
test -n "$JVB_PUBLIC_IP" || { echo 'IP LB encore indisponible'; false; }
python3 scripts/jvb-values.py --jvb-ip "$JVB_PUBLIC_IP" > values-gke.demo.yaml
GKE_VALUES_FILE=values-gke.demo.yaml sh scripts/validate.sh
```

La phase 2 et le contrôle des variables ont été réalisés avec succès :

```sh
helm upgrade "$JITSI_RELEASE" ./charts-officiels/jitsi-meet \
  --namespace "$JITSI_NAMESPACE" \
  -f values-gke.yaml -f values-gke.demo.yaml --wait --timeout 10m
kubectl -n "$JITSI_NAMESPACE" rollout status \
  "deployment/${JITSI_RELEASE}-jitsi-meet-jvb-0" --timeout=180s
kubectl -n "$JITSI_NAMESPACE" get svc "$JVB_SERVICE" \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}{"\n"}{.spec.ports}{"\n"}'
kubectl -n "$JITSI_NAMESPACE" exec "deployment/${JITSI_RELEASE}-jitsi-meet-jvb-0" \
  -- printenv JVB_ADVERTISE_IPS JVB_PORT
```

Le Service doit conserver son identité lors de la mise à jour. Si le
LoadBalancer est recréé avec une autre IP, régénérer la surcharge et contrôler
à nouveau l'annonce. Le générateur refuse une IP vide, privée ou invalide.
Ne pas exposer Prosody ni ouvrir indistinctement les ports des nœuds.
Les commandes suivantes constituent des diagnostics complémentaires :

```sh
kubectl -n "$JITSI_NAMESPACE" describe svc "$JVB_SERVICE"
gcloud compute firewall-rules list --project "$GCP_PROJECT"
```

### Annexe C — Accès, diagnostics et collecte

Sur la VM, conserver le port-forward TCP au premier plan :

```sh
kubectl -n "$JITSI_NAMESPACE" port-forward --address 127.0.0.1 \
  "svc/$WEB_SERVICE" 8081:8000
ss -ltnp 'sport = :8081'
ps -eo pid,args | rg '[k]ubectl.*port-forward'
curl --noproxy '*' -v --max-time 10 http://127.0.0.1:8081/ -o /dev/null
```

Dans VS Code Remote SSH, transférer le port distant 8081 vers le port local
8081, en accès privé. Vérifier la colonne d'adresse locale : si le port est
occupé, VS Code peut en choisir un autre. Ouvrir ensuite
`http://localhost:8081/demo`. Un transfert temporaire local vers 18081 a
également été proposé comme diagnostic de conflit, sans attestation de son
utilisation. Ne pas écouter sur `0.0.0.0` ni publier le tunnel.

Diagnostics Windows proposés ; leur transcription complète n'est pas
conservée, contrairement aux réponses HTTP constatées sur la VM :

```powershell
Test-NetConnection 127.0.0.1 -Port 8081
curl.exe --noproxy "*" -I --max-time 10 http://127.0.0.1:8081/
Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

Dans les outils développeur du navigateur, `window.isSecureContext` et
`navigator.mediaDevices` permettent de diagnostiquer l'accès aux périphériques.
Ces vérifications ont été proposées ; leurs sorties individuelles n'ont pas
été archivées. La commande suivante est la forme reproductible du contrôle
BOSH réalisé ; sa réponse peut contenir un identifiant de session à masquer :

```sh
curl --fail http://localhost:8081/ -o /dev/null
curl --fail http://localhost:8081/config.js | rg 'bosh|http-bind'
curl -i -H 'Content-Type: text/xml' --data \
  '<body rid="1" xmlns="http://jabber.org/protocol/httpbind" to="meet.jitsi" wait="5" hold="1" ver="1.6"/>' \
  http://localhost:8081/http-bind
```

Une réponse XML BOSH avec session, sans terminaison d'erreur, a été observée.
Elle vérifie la signalisation jusqu'à Prosody, pas une réunion audio/vidéo
complète. Une page HTML ou une erreur 404/502 orienterait vers un problème
de routage. Les fichiers CSS et JavaScript servis par Web ont aussi répondu
HTTP 200 pendant le diagnostic.

Commandes de lecture des logs et statistiques utilisées pendant les
vérifications ; ne pas publier de logs bruts contenant des identifiants :

```sh
kubectl -n jitsi get pods -o wide
kubectl -n jitsi get svc
kubectl -n jitsi get endpointslices \
  -l kubernetes.io/service-name=jitsi-jitsi-meet-jvb
kubectl -n jitsi logs deployment/jitsi-jitsi-meet-web --tail=100
kubectl -n jitsi logs statefulset/jitsi-jitsi-meet-prosody --tail=100
kubectl -n jitsi logs deployment/jitsi-jitsi-meet-jicofo --since=10m --timestamps=true
kubectl -n jitsi logs deployment/jitsi-jitsi-meet-jvb-0 --since=10m --timestamps=true
kubectl -n jitsi exec deployment/jitsi-jitsi-meet-jvb-0 -- \
  curl --max-time 10 -fsS http://127.0.0.1:8080/about/health
kubectl -n jitsi exec deployment/jitsi-jitsi-meet-jvb-0 -- \
  curl --max-time 10 -fsS http://127.0.0.1:8080/colibri/stats
kubectl top nodes
kubectl -n jitsi top pods --containers
kubectl get apiservice v1beta1.metrics.k8s.io
```

`helm test "$JITSI_RELEASE" -n "$JITSI_NAMESPACE" --logs` est un contrôle
HTTP Web interne proposé dans le guide initial ; son exécution n'est pas
attestée dans les résultats conservés. Ce test crée un pod temporaire et ne
constitue ni une simple lecture ni une validation média. Un `nc -u` ne
suffirait pas non plus à prouver l'ouverture du chemin WebRTC.

Paramétrages de collecte correspondant aux scénarios analysés ; les bilans
JSON attestent leurs durées et noms, pas une transcription littérale de
chaque commande de lancement :

```sh
./scripts/monitor-load.sh --scenario reference-repos-confirme --duration 120
./scripts/monitor-load.sh --scenario palier-3-participants --duration 300
```

Ctrl+C arrête la surveillance et conserve les mesures. Le script possède
également `--once` pour un relevé unique. Les quantités CPU/mémoire restent
brutes dans les JSONL ; la conversion et les moyennes du rapport sont calculées
à partir de ces fichiers, sans attribuer d'unités non vérifiées aux débits JVB.

### Annexe D — Nettoyage envisagé après la démonstration

**Procédure non attestée comme exécutée à la clôture de ce rapport.** Elle
est destructive et doit être décidée séparément. Fermer les tunnels avec
Ctrl+C, puis désinstaller la release avant de supprimer le cluster afin de
laisser le contrôleur GKE retirer le LoadBalancer. Vérifier le propriétaire
des ressources résiduelles avant toute suppression.

```sh
helm uninstall "$JITSI_RELEASE" --namespace "$JITSI_NAMESPACE" --wait --timeout 10m
kubectl -n "$JITSI_NAMESPACE" get svc,pvc
gcloud compute forwarding-rules list --project "$GCP_PROJECT"
gcloud compute addresses list --project "$GCP_PROJECT"
terraform -chdir=terraform plan -destroy -out=tfplan-destroy
terraform -chdir=terraform apply tfplan-destroy
gcloud container clusters list --project "$GCP_PROJECT"
gcloud compute forwarding-rules list --project "$GCP_PROJECT"
gcloud compute addresses list --project "$GCP_PROJECT"
gcloud compute disks list --project "$GCP_PROJECT"
rm -f terraform/tfplan terraform/tfplan-destroy values-gke.demo.yaml
```

Ne jamais supprimer l'état Terraform ; le conserver pour tracer les ressources.
Ne pas supprimer les ressources préexistantes du projet. Le contrôle final
doit porter notamment sur les IP réservées, disques et LoadBalancers encore
facturables. La commande `rm` ci-dessus ne concerne que des plans et une
surcharge générée, pas l'état.

### Annexe E — Accès distant de participants : variante non expérimentée

Une méthode a été préparée pour des utilisateurs possédant chacun un compte
SSH limité au tunnel Web, sans kubeconfig ni droits GCP. Son provisionnement
et ses restrictions effectives n'ont pas été validés. L'extrait suivant est
un modèle de configuration, pas la configuration SSH appliquée :

```text
Match Group jitsi-demo
    AuthenticationMethods publickey
    PasswordAuthentication no
    AllowTcpForwarding local
    PermitOpen 127.0.0.1:8081
    AllowAgentForwarding no
    X11Forwarding no
    PermitTTY no
    MaxSessions 0
```

Il faudrait créer les comptes et clés autorisés, vérifier la configuration
avec `sshd -t` et les paramètres effectifs avec `sshd -T -C` en fournissant
les paramètres de connexion appropriés. `MaxSessions 0` interdit les sessions
tout en laissant les transferts autorisés possibles. Après définition des
vrais compte et serveur, la commande de tunnel proposée est :

```sh
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8081:127.0.0.1:8081 "$SSH_DEMO_USER@$SSH_DEMO_HOST"
```

L'empreinte du serveur doit être vérifiée, sans désactiver
`StrictHostKeyChecking`. Ne pas cumuler ce tunnel et celui de VS Code sur
le même port local. La salle `demo-master2`, utilisée dans des commandes
préparatoires, ne doit pas être confondue avec la salle `demo` des tests
fonctionnels rapportés. L'alternative publique HTTPS avec domaine reste
également non retenue : `scripts/gke-values.py` la prépare, tandis que
`mes-valeurs.yaml` utilise un domaine fictif pour les contrôles Helm.

### Annexe F — Traçabilité et éléments à compléter pour le rendu

| Élément | État de la preuve ou complément attendu |
|---|---|
| Infrastructure et déploiement | Observations deux nœuds Ready, release 2 et pods prêts ; joindre captures authentiques |
| Réunion utilisateur | Résultats rapportés et confirmés ; joindre captures avec consentement |
| Signalisation et bridge | Réponses HTTP/BOSH et statistiques observées ; conserver sorties expurgées |
| Performance | JSONL locaux et tableaux vérifiés ; archiver les sources hors Git pour l'évaluation |
| IAM final des nœuds | Attribution finale du rôle minimal non confirmée dans les éléments conservés |
| Provisionnement initial et nettoyage final | Journaux complets non disponibles ; ne pas présenter toutes les procédures comme exécutées |
| CI et intégration | Liens GitHub vérifiés, PR nº 2 fusionnée et CI main réussie |
| CD attendue | Exigence à confirmer avec l'enseignant ; non implémentée |
| Page de garde et références | Compléter les informations administratives et le format bibliographique demandé |
| Assistance et contributions | Vérifier les règles de l'établissement sur leur déclaration |

La rédaction n'attribue pas d'essais, d'installations ou de mesures non
réalisés. Une assistance à la préparation technique, à l'analyse et à la
rédaction a été utilisée au cours du projet. Si l'établissement impose une
déclaration d'usage d'outils d'intelligence artificielle ou d'autres
contributions, elle devra être renseignée selon ses consignes, sans supprimer
cette information ni inventer une répartition de travail non documentée.

## Préparation d'un accès public HTTPS avec Caddy — 16 novembre 2026

Après la validation de la démonstration via localhost, une évolution a été
préparée sur la branche `feature/jitsi-public-edge` pour permettre un accès HTTPS
avec un futur sous-domaine DuckDNS. Cette étape porte uniquement sur les fichiers
et les contrôles locaux : aucun DNS, certificat public, LoadBalancer, disque ou
déploiement supplémentaire n'a été créé. Elle ne remplace pas les résultats
fonctionnels précédemment rapportés et ne constitue pas un test public réussi.

Le chart complémentaire `charts/jitsi-edge` prépare un proxy Caddy 2.11.9,
un Service LoadBalancer L4 TCP 80/443 et une ConfigMap. TLS sera terminé par
Caddy, puis les requêtes transmises au Service Web privé sur le port 8000.
Le profil `values-jitsi-public.yaml`, distinct de localhost, conserve BOSH sur
l'origine du navigateur. Le LoadBalancer JVB UDP 10000 et son annonce d'IP restent
indépendants. Aucun WebSocket Colibri n'est annoncé sans route correspondante.

Un PVC indépendant de 10 Gi est décrit dans `deploy/jitsi-edge-storage.yaml`
pour conserver les certificats et clés ACME sous `/data`. Une seule réplique
Caddy et une stratégie Recreate ont été retenues pour le volume RWO. Ce choix
limite la disponibilité pendant les mises à jour et implique une politique de
sauvegarde et de nettoyage explicite. Le conteneur est préparé sans root, sans
token Kubernetes et avec système racine en lecture seule. Ses sondes internes
ne sont pas exposées par le Service ; elles ne prouvent pas la validité TLS.

Les fixtures utilisent exclusivement `jitsi.invalid`. Le générateur des valeurs
réelles refuse les domaines réservés et n'écrase pas les fichiers locaux.
Les tests ont validé les rendus Helm, le Caddyfile avec le binaire Caddy, les
invariants d'exposition réseau et 25 tests Python. Les validations Helm et
Terraform existantes ont également réussi, sans accès au backend Terraform.
Aucun secret SOPS n'a été déchiffré pour ces contrôles. Ces résultats statiques
ne prouvent ni l'émission ACME, ni la propagation DNS, ni un relais média externe.

La CI conserve son contrôle `Validation Helm` et ajoute ces vérifications.
La CD publique reste une préparation désactivée par défaut : les contrôles
OIDC, dépôt, branche, succès CI, SHA et nettoyage SOPS/KMS sont conservés.
Le mode public exige un bootstrap autorisé préalable, des objets Helm existants,
un PVC Bound et un droit de lecture du PVC qui reste à confirmer. Il ne crée
pas implicitement cette nouvelle infrastructure et n'autorise pas une migration
DNS automatique. La mise à jour des deux releases n'est pas transactionnelle.

Avant toute mise en service restent nécessaires : le choix du domaine réel,
l'accord sur les coûts disque/IP/LB, le bootstrap, les contrôles ACME staging
puis production, la politique d'accès des utilisateurs, les tests BOSH et une
réunion externe mesurée sur JVB. Le dimensionnement et les commandes de contrôle
sont consignés dans [la préparation technique](jitsi-public-edge.md). Les coûts
supplémentaires dépendent notamment du groupe de règles réseau déjà facturé au
projet, du disque et du trafic ; aucun total mensuel n'a été mesuré.

*Preuves à joindre après réalisation : DNS réel, certificat reconnu, état du
Service edge et du PVC, réunion externe et exécution CI/CD. Ces captures ne sont
pas disponibles à cette étape.*


## Contrôle de remise — 16 novembre 2026 (heure de Paris)

Cette section actualise les états historiques précédents. Le dépôt était propre
sur `feature/jitsi-public-edge`. L'ordre chronologique est `ab53548`
(documentation), `84a19b7` (CD), puis `f3a5aef` (HTTPS). La branche a été poussée
vers `SaminouA/projet-jitsi-helm`, sans fusion ni activation CD.

### Résultats effectivement observés

| Contrôle | Résultat | Portée |
|---|---|---|
| CI GitHub du SHA `f3a5aef65ffcc8edbc640a7a276f7008fe89b723` | Succès, run `43929749540` | Validation statique, aucun déploiement |
| Helm/Terraform via hook pre-push | Succès | Deux profils Jitsi, backend Terraform désactivé sur copie temporaire |
| Tests Python | 25/25 réussis | Garde-fous CD et edge |
| Caddy | Lint/rendu edge et `caddy validate` réussis | Aucun serveur ni certificat lancé |
| GKE | Deux nœuds Ready | Observation ponctuelle |
| Jitsi | Web, Prosody, Jicofo, JVB : quatre pods Ready, zéro redémarrage | Observation ponctuelle |
| Helm | `jitsi`, révision 2, `deployed`, chart 3.10.0, application stable-11248 | Release existante préservée |
| Réseau interne | Services et EndpointSlices Web/Prosody/JVB présents | Ne prouve pas le transport média externe |
| Événements | Aucun Warning retourné dans `jitsi` | Seulement la rétention actuelle des événements |
| HTTP via port-forward sur loopback | `/`, `/config.js`, `/http-bind` : HTTP 200 | Disponibilité des routes, pas de session XMPP ni de réunion validée |
| Collecte ponctuelle | Un relevé, zéro erreur de collecte | Aucun générateur de charge |

La collecte locale est conservée dans
`tests/results/20261116T183203.174107Z_remise-observation/`, exclue de Git.
JVB indiquait `healthy=true`, un client MUC connecté, zéro conférence et zéro
participant. Les compteurs cumulés historiques ne sont pas attribués à cet essai.
Les usages CPU observés des nœuds étaient environ 0,100 et 0,107 cœur ; ces
mesures ponctuelles ne démontrent aucune capacité sous charge.
Aucune nouvelle réunion ni charge média n'a été exécutée.

### Premier déploiement OIDC : conditions et limites

Les lectures GCP confirment un provider WIF ACTIVE, une condition limitée au dépôt
et à `refs/heads/main`, `roles/iam.workloadIdentityUser` sur le compte de service,
`roles/container.clusterViewer` sur le projet et
`roles/cloudkms.cryptoKeyDecrypter` sur la clé SOPS. Le RoleBinding cible le compte
attendu ; le Role inclut les lectures Pods/ReplicaSets et les opérations Helm.
Aucune politique IAM/RBAC n'a été modifiée. Aucun secret n'a été déchiffré.

La liste des variables de dépôt GitHub est vide : `GKE_CD_ENABLED` n'est pas
activée au niveau dépôt et n'a pas été créée. Les éventuelles variables héritées
d'organisation ne sont pas attestées par cette seule commande. L'API de protection
de `main` renvoie HTTP 404 « Branch not protected » : il ne faut donc pas affirmer
qu'une revue ou un statut obligatoire est actuellement imposé par cette protection.
Le contrôle complémentaire des règles effectives (`rules/branches/main`) confirme
toutefois un ruleset : passage par PR, statut `Validation Helm` requis, refus des
suppressions et des pushes non fast-forward. Le nombre minimal d’approbations
est zéro : aucune approbation humaine obligatoire n’est attestée. Le HTTP 404
concerne donc la protection classique, pas l’absence de règles effectives.

Avant le premier essai réel : revoir la PR et la CI du SHA final, faire approuver
la fusion puis, séparément, l'activation CD ; recontrôler les autorisations
effectives complètes et l'accès réseau du runner. L'essai devra confirmer l'échange
OIDC, KMS, les comparaisons de secrets sans divulgation, la conservation de l'IP JVB
et la disponibilité après Helm. Rien de cela n'est présenté comme déjà exécuté.

### HTTPS : blocages concrets

Aucune release `jitsi-edge` ni aucun PVC n'apparaît dans le namespace. La classe
`standard-rwo` existe, avec `WaitForFirstConsumer` et politique `Delete`.
La liste des adresses réservées du projet est vide. Aucun domaine réel n'a été
fourni ou vérifié. Le test d'autorisation impersonné
`get persistentvolumeclaims` du compte CD retourne `no` : blocage pour la CD
publique, sans conséquence sur le profil localhost.

Il reste à autoriser le budget, choisir le domaine, confirmer les quotas et les
coûts, approuver le stockage ACME et sa sauvegarde, puis autoriser le bootstrap
IP/PVC/LB/Caddy et la migration Jitsi. La CD préparée ne fait pas ce bootstrap.
Aucune ressource payante, règle DNS ou certificat n'a été créé par cette étape.
Les tarifs ne sont pas réévalués dans ce contrôle ; aucun coût mensuel validé
n'est annoncé. Voir `docs/jitsi-public-edge.md` pour l'ordre des opérations.

### Préparation de la soutenance et validations restantes

Le support de prise de parole est dans `docs/soutenance.md` et le protocole
borné dans `docs/validation-remise.md`. Ces livrables séparent l'infrastructure
observée, les tests statiques et les essais encore nécessaires. Les résultats
fonctionnels du 15 novembre restent des résultats historiques, distincts du
contrôle actuel. Le README a été corrigé : le cluster est actif aujourd'hui.


## Préparation du domaine DuckDNS réel — 16 novembre 2026

L'utilisateur a déclaré réservé `jitsi-meet-m2.duckdns.org`, sans autoriser de
création payante. Le dépôt était propre sur `feature/jitsi-public-edge` à
`c591ad4`, identique au distant. Deux surcharges ont été préparées localement :
`deploy/jitsi-edge-duckdns.yaml` pour Caddy en ACME staging et
`deploy/jitsi-duckdns.yaml` pour l'URL Jitsi. `jitsi-edge-ip` est un nom de
réservation proposé ; aucune adresse n'a été créée. Les profils génériques et
les workflows n'ont pas été modifiés.

Le contrôle cluster confirme quatre pods Ready sans redémarrage, la release
`jitsi` révision 2 déployée, les services/EndpointSlices et aucun Warning
actuellement retourné. Aucun PVC ni release edge n'existe. Le DNS local et Google
public répondent A `37.67.80.37` ; Google retourne NOERROR sans réponse AAAA.
Cette IP n'est pas un Caddy du cluster. Aucun contact HTTP/TLS vers elle, aucune
modification DNS et aucune utilisation de jeton DuckDNS n'ont eu lieu.

Les quotas régionaux consultés donnent notamment adresses statiques 0/8,
adresses en usage 3/8, stockage SSD (incluant pd-balanced) 80/500 GiB,
règles external network LB 1/50 et backends external network LB 0/50.
Les deux nœuds disposent chacun de 1930m CPU et 6170232Ki allouables, avec 727m
CPU demandé par nœud ; les 100m/128Mi de Caddy paraissent planifiables sans ajout
de nœud. Cela n'est pas une validation de capacité sous charge ; les limites
mémoire existantes sont surengagées. Aucun ResourceQuota/LimitRange dans `jitsi`.

Le stockage `standard-rwo` est en réalité **pd-balanced zonal**, provisionné par
CSI activé, RWO/WaitForFirstConsumer/Delete. Le PVC de 10Gi et le fsGroup 1000
sont préparés ; montage, écriture et persistance réels restent non testés.
Un PVC Pending avant le premier consommateur serait normal. Le retour arrière
préparé conserve le PVC et ses données ACME ; sa suppression n'est pas autorisée.

Les tests d'autorisation opérateur Kubernetes create PVC/Deployment/Service/
ConfigMap, patch Deployment et delete Service répondent yes. Le test IAM GCP
confirme les permissions interrogées pour adresses, disques et création réseau,
sans valider toutes les actions futures du contrôleur GKE. Le compte CD n'a
toujours pas get PVC. Aucune politique IAM/RBAC n'a été changée.

La revue des tarifs publics identifie disque, traitement LB, transferts et IP
réservée inutilisée. Une IP attachée à une règle n'a pas de charge IPv4 distincte.
Le groupe de règles régionales pourrait rester celui du JVB existant ; aucun
supplément forfaitaire de 18,25 USD/mois n'est affirmé. Le tarif exact pd-balanced
europe-west1 et le budget global restent à confirmer, sans coût créé ici. La facturation du projet est activée (`billingEnabled=true`),
sans consultation de montant contractuel ou de facture.
Les hypothèses, formules et sources consultées sont dans
[le mode opératoire DuckDNS](https-duckdns.md).

Validations locales réellement réussies : lint/rendu du chart edge avec domaine
réel, invariants d'exposition, `caddy validate` staging et production, rendu Jitsi
public, 25 tests Python et `scripts/validate.sh` pour les profils existants et
Terraform sans backend. Aucun SOPS déchiffré. Les nouvelles modifications n'ont
pas été poussées et aucune nouvelle CI distante n'est revendiquée.

Les commandes exactes sont préparées dans `docs/https-duckdns.md`, avec accords
séparés pour bootstrap staging, production ACME, migration Jitsi et nettoyage.
La migration manuelle proposée réutilise les valeurs effectives de la release
pour préserver secrets/IP JVB ; le rollback capture sa révision avant migration.
Le profil localhost reste déployé tant qu'aucune migration n'a lieu. Après
migration publique, le port-forward seul ne suffira pas à rétablir localhost.
La future CD devra sélectionner explicitement public-edge ; une CD localhost
pourrait sinon remettre l'ancienne URL. Aucun flag GitHub n'a été modifié.
Aucun certificat, déploiement Caddy, réunion publique ni charge n'est validé.


### Derniers contrôles avant bootstrap et procédure courte

Le contrôle en lecture seule du 16 novembre confirme les quotas précédents,
quatre pods Ready sans redémarrage, la release révision 2 et aucun Warning
retourné. `kubectl top nodes` donne 97m/103m CPU et 2308Mi/2115Mi mémoire.
Aucune adresse réservée ni PVC n'existe. Le manifeste de stockage demande bien
10Gi de pd-balanced via standard-rwo. Les tests confirment 48/48 autorisations
opérateur Helm et 4/4 permissions IAM de réservation IPv4 interrogées ; get PVC
reste refusé au compte CD. Aucun droit modifié.

Lint/rendus edge, invariants, `caddy validate` staging et production et rendu
Jitsi public avec le domaine réel sont de nouveau réussis. Aucune émission de
certificat ni validation média n'en est déduite. DNS Google reste A 37.67.80.37,
sans réponse AAAA. La PR nº 3 est toujours ouverte, deux checks verts sur c591ad4 ;
ces CI ne couvrent pas les nouveaux fichiers locaux non poussés.

La procédure courte est dans `docs/bootstrap-https-court.md`. Ses blocs Bash
passent le contrôle syntaxique sans exécution. Elle sépare réservation/PVC/edge,
DNS, staging, production ACME, migration Jitsi et rollback, avec points d'arrêt
soumis à accord. La disponibilité d'une IPv4 précise et le coût réel du compte
ne sont pas garantis par les quotas/tarifs publics. Aucun nouveau coût créé,
aucune fusion, aucun changement IAM/RBAC ou activation CD.


### Bootstrap staging autorisé : précontrôles réussis, arrêt sur erreur

Le 16 novembre 2026, l'utilisateur a explicitement autorisé les étapes 1 et 2
(IP régionale, PVC 10Gi, Caddy staging), avec arrêt à la première erreur.
Les précontrôles confirment quatre pods Ready, absence de ressources edge et
réservation homonyme, domaine attendu et ACME staging. Le lint strict passe.
La révision Jitsi 2 a été enregistrée exclusivement dans le fichier local ignoré
`deploy/local/jitsi-before-public.revision`, sans extraction de secret.

La tentative `gcloud compute addresses create` a échoué :
`IP Version is not supported for regional addresses.` La commande préparée
utilisait à tort `--ip-version=IPV4`. L'aide locale précise que cette option est
réservée aux adresses globales et que le défaut est IPV4. Les deux guides ont
été corrigés sans relancer la commande.

Les opérations de création ont été arrêtées immédiatement. Une nouvelle lecture
confirme aucune adresse réservée, aucun PVC, aucune release Caddy, et Jitsi
inchangé (révision 2, quatre pods Ready, zéro redémarrage). Aucune IP Web n'est
donc disponible. Aucun changement DNS, IAM/RBAC, ACME production, migration Jitsi,
merge ou activation CD. Les modifications Git préexistantes sont conservées.


### Reprise autorisée : bootstrap Caddy staging réussi — 16 novembre 2026

Après nouvel accord explicite de l'utilisateur, la commande régionale corrigée
(sans `--ip-version`) a réussi. Les précontrôles ont retrouvé Jitsi en révision 2,
quatre pods Ready et aucune ressource edge existante. La capture de révision
locale existante a été conservée sans écrasement.

1. Réservation `jitsi-edge-ip`, région `europe-west1`, EXTERNAL/PREMIUM :
   **34.78.71.58**. État RESERVED juste après création, puis IN_USE après
   attribution au LoadBalancer.
2. Création du PVC `jitsi-edge-data`, 10Gi, `standard-rwo`. Pending initial avec
   événement normal WaitForFirstConsumer, puis Bound après installation Caddy.
   Le disque `pvc-4e3f507f-f61b-46e1-9639-8bfece68b3b9` est READY,
   pd-balanced, 10 GiB, dans `europe-west1-b`.
3. `helm install jitsi-edge ... -f deploy/jitsi-edge-duckdns.yaml --wait
   --timeout 10m` a réussi : release `jitsi-edge` révision 1, statut deployed,
   chart 0.1.0, Caddy 2.11.9 avec digest épinglé. Le pod
   `jitsi-edge-7d57f56b9c-k4hg2` est Running, 1/1 Ready, zéro redémarrage.
4. Le Service `jitsi-edge` est LoadBalancer, IP externe 34.78.71.58,
   TCP 80/443 vers 8080/8443. L'EndpointSlice pointe vers 10.56.1.12.
   La règle GCP `a6fe9a20c97314fed8dbd53cb70e98b6` est régionale, TCP,
   ports discrets 80/443, Premium. L'événement SyncLoadBalancerSuccessful
   confirme la convergence Kubernetes. Les deux nœuds existants restent Ready.

Les connexions TCP externes vers 34.78.71.58:80 et :443 ont réussi depuis le
poste d'exécution. Une requête HTTP avec résolution ponctuelle `curl --resolve`
(sans modification DNS) retourne 308 et
`Location: https://jitsi-meet-m2.duckdns.org/`, sans port interne dans l'URL.
Le test `test -w /data` dans le conteneur confirme l'accessibilité en écriture
du volume, sans écrire de fichier ni lire de clé ACME. Cela ne valide pas encore
la conservation des certificats après redémarrage.

La ConfigMap active utilise exclusivement l'ACME **staging** Let's Encrypt.
Aucun certificat de production demandé par cette procédure ; aucun certificat
staging ou accès HTTPS avec validation TLS n'est présenté comme validé. Caddy
peut tenter automatiquement l'émission staging ; le DNS n'a pas été modifié
et ces tentatives ne sont pas qualifiées ici.

Contrôle final : Jitsi reste deployed en révision 2, ses quatre pods Ready sans
redémarrage, et son LB UDP garde l'IP 34.62.165.81. Aucun événement Warning
n'est retourné dans le namespace. Aucun changement Jitsi, DuckDNS, IAM/RBAC,
activation CD, merge ou déchiffrement de secret. Les ressources créées sont
celles du bootstrap autorisé ; aucune facture réelle ni coût contractuel n'a été
vérifié. IP/LB/disque sont désormais à considérer dans le suivi des coûts.
Les modifications Git préexistantes sont préservées ; seule cette section de
rapport est ajoutée pendant la reprise.

Étapes suivantes en attente : autorisation de modification DNS vers 34.78.71.58,
validation ACME staging, accord séparé ACME production, puis migration Jitsi et
tests fonctionnels. Aucune de ces étapes n'a été exécutée.


### DNS et certificat ACME staging validés — 16 novembre 2026

Après modification DuckDNS effectuée par l'utilisateur, les lectures du résolveur
local, de Google DNS et de Cloudflare DNS renvoient toutes A **34.78.71.58** pour
`jitsi-meet-m2.duckdns.org`. Google et Cloudflare répondent NOERROR sans réponse
AAAA. Aucun DNS n'a été modifié par l'agent.

Caddy est Running, 1/1 Ready, zéro redémarrage, release `jitsi-edge` révision 1
`deployed`. Le PVC reste Bound à 10Gi et le Service expose TCP 80/443 sur
34.78.71.58. La ConfigMap utilise toujours exclusivement le serveur ACME staging.
Les quatre pods Jitsi et la release révision 2 restent inchangés ; aucun Warning
n'est actuellement retourné dans le namespace.

Les journaux filtrés montrent six échecs de challenge entre 20 h 18 min 49 s et
20 h 22 min 39 s (heure de Paris), HTTP-01 et TLS-ALPN-01. Leurs problèmes ACME
sont de type connection et mentionnent l'ancienne IP 37.67.80.37. Ces erreurs
historiques correspondent aux tentatives précédant la convergence DNS ; elles
ne sont pas masquées. Un challenge HTTP-01 ultérieur a abouti, et le message
`certificate obtained successfully` est daté de **20 h 24 min 45 s, Paris**.

Le certificat réellement présenté sur le port 443 contient :

- sujet et SAN : `jitsi-meet-m2.duckdns.org` ;
- émetteur : `Let's Encrypt / (STAGING) Artificial Amaranth YE1` ;
- validité publiée : 16 novembre 2026 18:26:12 UTC au 19 janvier 2027 18:26:11 UTC ;
- empreinte SHA256 :
  `81:3F:F5:DB:CB:CC:4D:42:68:DB:5D:CD:6A:8D:91:E1:22:4C:B3:CB:7B:99:F9:DC:07:9E:32:3E:98:38:EC:AA`.

La requête HTTP publique renvoie **308** avec
`Location: https://jitsi-meet-m2.duckdns.org/`, sans port interne. Avec le magasin
de confiance système, curl HTTPS échoue avec le code 60, « unable to get local
issuer certificate » : résultat attendu pour staging, qui n'est pas une autorité
reconnue par les clients habituels.

Pour qualifier le staging sans désactiver la vérification TLS, les racines
staging publiques ont été téléchargées depuis les liens de la documentation
[officielle Let's Encrypt](https://letsencrypt.org/docs/staging-environment/)
dans un répertoire temporaire. Un contexte TLS réservé au test et OpenSSL avec
`-CAfile`, `-verify_hostname` et `-verify_return_error` valident la chaîne et le
nom DNS. Ce magasin isolé a ensuite été supprimé ; aucune racine n'a été ajoutée
au système et aucun `curl -k` n'a été utilisé.

Avec cette confiance staging temporaire, HTTPS renvoie **200** sur `/`,
`/config.js` et `/http-bind`, et **404** sur `/colibri/stats`, `/metrics` et
`/healthz`. Ces contrôles valident routage et protections testées, pas une session
BOSH/XMPP ni une réunion audio/vidéo. Le profil Jitsi reste localhost et n'a pas
encore été migré ; la qualité d'une réunion publique n'est pas revendiquée.

#### Passage en production : procédure préparée, non exécutée

Le staging est validé pour émission, chaîne TLS de test, domaine et HTTP/HTTPS.
Après accord explicite, recontrôler DNS, état de la release et PVC ; conserver
les ports 80/443 joignables pour ACME et le renouvellement, puis exécuter :

```bash
helm upgrade jitsi-edge charts/jitsi-edge -n jitsi \
  -f deploy/jitsi-edge-duckdns.yaml --set acmeEnvironment=production \
  --wait --timeout 10m --no-hooks --hide-notes
```

Le fichier local reste par défaut staging : la surcharge production doit être
explicite pour éviter qu'une réapplication ultérieure ne rétablisse staging.
Après émission, vérifier sans racine de test et sans contournement TLS :

```bash
curl --head --max-time 15 https://jitsi-meet-m2.duckdns.org/
timeout 15 openssl s_client -connect jitsi-meet-m2.duckdns.org:443 \
  -servername jitsi-meet-m2.duckdns.org \
  -verify_hostname jitsi-meet-m2.duckdns.org -verify_return_error </dev/null
```

Vérifier aussi l'émetteur de production, les dates, les 404 des routes privées,
les pods et les événements. `helm --wait` seul ne prouve pas l'émission TLS.
En cas de problème, arrêter et diagnostiquer ; le retour à la révision edge 1
est préparé par `helm rollback jitsi-edge 1 -n jitsi --wait --timeout 10m
--no-hooks`, après accord et contrôle de l'historique. Ce retour rétablit un
certificat staging non reconnu et conserve le PVC. La migration Jitsi vers
l'URL publique et toute activation CD restent des actions distinctes à autoriser.

Aucune commande de bascule production ou rollback ci-dessus n'a été exécutée.
Aucun changement Jitsi, DuckDNS, secret, permissions, CD ou autre ressource ; seul
le rapport a été complété pendant cette vérification. Aucun renouvellement ni
test de persistance après redémarrage n'est encore validé.


### Bascule Caddy ACME production autorisée — 16 novembre 2026

L'utilisateur a explicitement autorisé uniquement la mise à jour de `jitsi-edge`
vers ACME production, avec conservation des valeurs et du stockage. Les
précontrôles confirment DNS local/Google/Cloudflare A 34.78.71.58, aucune réponse
AAAA publique, cinq pods Ready et le PVC d'origine Bound à 10Gi. La release
Jitsi est toujours en révision 2, edge initialement en révision 1 staging.

Commande réellement exécutée avec succès :

```bash
helm upgrade jitsi-edge charts/jitsi-edge -n jitsi --reuse-values \
  --set acmeEnvironment=production --wait --timeout 10m --no-hooks --hide-notes
```

La release edge est maintenant **révision 2, deployed**. Une comparaison en
mémoire des valeurs des révisions 1 et 2 confirme que seul `acmeEnvironment`
a changé, de staging à production. Aucun contenu sensible de valeurs n'a été
publié. Le nouveau pod `jitsi-edge-6b74c6cf6-t4t4k` est 1/1 Ready, sans
redémarrage. Le PVC `jitsi-edge-data` reste Bound sur le même volume
`pvc-4e3f507f-f61b-46e1-9639-8bfece68b3b9`, 10Gi. L'IP Web reste 34.78.71.58.

**Erreur observée et évolution automatique :** à 20 h 28 min 41 s (Paris),
le challenge HTTP-01 a échoué avec un problème ACME connection : timeout lors
de la connexion à 34.78.71.58. Le message suggère un problème de pare-feu, mais
cette cause n'est pas établie par ce seul événement. Aucune nouvelle mutation,
relance manuelle ou modification réseau n'a été effectuée après cette erreur.
Caddy a ensuite finalisé automatiquement l'autorisation à 20 h 28 min 45 s et
journalisé `certificate obtained successfully` à **20 h 28 min 47 s**. Les
vérifications suivantes sont uniquement des constats en lecture seule de cet
état finalement convergé ; le timeout transitoire n'est pas masqué.

Le certificat effectivement présenté et vérifié contient :

- sujet et SAN : `jitsi-meet-m2.duckdns.org` ;
- émetteur : `Let's Encrypt`, intermédiaire **YE1**, sans mention STAGING ;
- validité : **16 novembre 2026 18:30:15 UTC au 14 février 2027 18:30:14 UTC** ;
- empreinte SHA256 :
  `33:AE:FB:29:C6:25:25:BC:22:72:E2:09:07:29:05:D2:92:0C:1B:F9:43:50:20:89:6D:8E:7B:B4:58:18:1A:93`.

La connexion Python avec `ssl.create_default_context()` valide la confiance
système et le nom DNS, en TLS 1.3. OpenSSL avec `-verify_hostname` et
`-verify_return_error`, sans CAfile staging, confirme
**Verify return code: 0 (ok)**. Aucun `-k`, contexte TLS non vérifié ou ajout
d'autorité de test n'a été utilisé.

| Route HTTPS | Résultat avec confiance système normale |
|---|---|
| `/` | 200 |
| `/config.js` | 200 |
| `/http-bind` | 200 |
| `/colibri` et `/colibri/stats` | 404 |
| `/colibri-ws` | 404 |
| `/metrics` | 404 |
| `/debug` | 404 |
| `/healthz` | 404 |
| `/about/health` | 404 |

Le contrôle de ressources après émission confirme Jitsi deployed révision 2,
quatre pods Jitsi Ready sans redémarrage, LB UDP JVB toujours 34.62.165.81,
et aucun événement Warning actuellement retourné. Seule la release edge a été
mise à jour. Aucun changement DuckDNS, valeurs Jitsi, secret, permissions,
pipeline CI/CD, activation CD ou suppression de PVC. Les modifications Git
préexistantes sont conservées ; seul le rapport a été complété.

L'entrée HTTPS est désormais reconnue par la confiance système. Les HTTP 200
ne valident ni une session XMPP ni une réunion publique ; la configuration
Jitsi reste localhost en attente d'une migration distincte autorisée. Aucun
renouvellement automatique futur ou test de reprise après panne n'est encore
qualifié. Le fichier de valeurs DuckDNS local demeure staging : une future
réapplication devra conserver explicitement production pour éviter un retour
involontaire au certificat de test.


### Migration Jitsi vers l'URL publique autorisée — 16 novembre 2026

L'utilisateur a autorisé la migration de Jitsi vers
`https://jitsi-meet-m2.duckdns.org`, en préservant les paramètres, secrets, Caddy,
DuckDNS et le pipeline. Avant modification, la release Jitsi était deployed en
révision 2 avec PUBLIC_URL localhost ; Caddy production restait en révision 2.

#### Sauvegarde et modification minimale

Une sauvegarde locale exclusive a été créée sous
`deploy/local/backups/jitsi-revision-2-before-public-20261116/` : répertoire
0700, fichiers 0600, chemin exclu de Git et confirmé par `git check-ignore`.
Elle contient les valeurs utilisateur et calculées, le manifeste de révision 2,
la copie précédente de `values-gke.yaml` et des empreintes d'intégrité privées.
Les valeurs/manifeste peuvent contenir des secrets : ils n'ont pas été affichés
ni ajoutés à Git. Commandes de sauvegarde, avec sorties dirigées vers ces
fichiers privés :

```bash
helm get values jitsi -n jitsi --revision 2 -o yaml
helm get values jitsi -n jitsi --revision 2 --all -o yaml
helm get manifest jitsi -n jitsi --revision 2
```

Dans `values-gke.yaml`, seule la ligne `publicURL` a été changée de
`http://localhost:8081` à `https://jitsi-meet-m2.duckdns.org`. Le lint strict du
chart avec ce fichier a réussi. Une surcharge privée ne contenant que cette
clé a été générée depuis la même URL. Le fichier complet n'a pas été appliqué
pour éviter de remplacer les valeurs effectives spécifiques au cluster :

```bash
helm upgrade jitsi charts-officiels/jitsi-meet -n jitsi --reuse-values \
  -f deploy/local/backups/jitsi-revision-2-before-public-20261116/public-url-only.yaml \
  --wait --timeout 10m --no-hooks --hide-notes
```

Résultat : **Jitsi révision 3, deployed**. La comparaison en mémoire des valeurs
révisions 2/3 confirme que seule `publicURL` a changé. Les empreintes du contenu
des Secrets applicatifs sont identiques ; aucune rotation ni modification de
leur contenu n'est observée et aucun secret SOPS n'a été déchiffré.

#### Rechargement des composants et difficultés

Le chart n'inclut pas la ConfigMap commune contenant PUBLIC_URL dans les
checksums qui déclenchent un rollout. Les pods devaient donc être rechargés pour
prendre la nouvelle variable d'environnement. Des redémarrages contrôlés ont
été réalisés successivement, avec attente de disponibilité après chacun :

```bash
for resource in statefulset/jitsi-jitsi-meet-prosody deployment/jitsi-jitsi-meet-jicofo deployment/jitsi-jitsi-meet-jvb-0 deployment/jitsi-jitsi-meet-web; do
  kubectl -n jitsi rollout restart "$resource"
  kubectl -n jitsi rollout status "$resource" --timeout=180s
done
```

Les quatre rollouts ont réussi. Des événements Warning de sondes readiness
« connection refused » ont été observés pendant l'arrêt/démarrage de Prosody,
Jicofo et JVB. Ils sont documentés comme transitoires : au contrôle final,
les quatre nouveaux pods sont Running, 1/1 Ready, zéro redémarrage. Les quatre
processus exposent désormais la PUBLIC_URL publique attendue. Le pod Caddy
n'a pas été redémarré par cette migration.

#### HTTPS et cohérence des URL vérifiées

Avec la confiance TLS système normale, sans désactivation de vérification :

| Route | Résultat | Contrôle du contenu |
|---|---|---|
| `/` | 200 | Absence de `localhost:8081` |
| `/config.js` | 200 | Absence de `localhost:8081`, URL publique HTTPS correcte |
| `/interface_config.js` | 200 | Absence de `localhost:8081` |
| `/http-bind` | 200 | Absence de `localhost:8081` |

La configuration publique générée référence
`https://jitsi-meet-m2.duckdns.org/` et conserve
`config.bosh = window.location.origin + '/http-bind';`, donc la même origine
HTTPS. Le contrôle `scripts/check-render.py --edge --ready` du manifeste réel
Helm révision 3 réussit. Ces vérifications ne simulent pas l'exécution complète
dans un navigateur et ne prouvent pas une session XMPP ni un transport média.

#### JVB : exposition confirmée, média externe non validé

Le Service JVB conserve son UID, sa spec et l'IP **34.62.165.81**, UDP **10000**.
Le JVB annonce cette même IP ; un EndpointSlice pointe vers son nouveau pod
10.56.1.15 sur UDP10000. L'écoute noyau sur le port 10000 du pod est confirmée.
La règle de forwarding GCP reste UDP 10000-10000 en europe-west1 ; ses deux
backends sont HEALTHY. Le pare-feu UDP10000 est actif, source 0.0.0.0/0.
Les statistiques JVB indiquent healthy=true, un client MUC connecté, zéro
conférence et zéro participant lors du relevé.

Une unique requête STUN Binding sans authentification a été envoyée au port
public ; elle n'a reçu aucune réponse dans les cinq secondes. Ce résultat est
**non concluant**, sans preuve de panne ni preuve d'accessibilité média de bout
en bout. Aucun autre générateur de trafic n'a été lancé. Une réunion externe
avec négociation ICE reste nécessaire pour valider réellement UDP/audio/vidéo.
Aucun test audio/vidéo n'est déclaré réussi.

#### Conservation, retour arrière et limite CI

Les UID et specs du Service edge, du Service JVB et du PVC Caddy sont inchangés.
Caddy reste révision 2 production ; aucune modification DNS, secrets, droits,
CI/CD ni nouvelle infrastructure. Les modifications Git existantes sont
préservées. Seuls `values-gke.yaml` et cette section de rapport ont été modifiés
pendant la migration, en plus de la sauvegarde privée ignorée.

Un script privé `rollback-prepared.sh`, vérifié avec `bash -n` mais **non
exécuté**, prépare `helm rollback jitsi 2 -n jitsi --wait --timeout 10m --no-hooks`,
puis les rechargements progressifs nécessaires de PUBLIC_URL. Il faut relire
l'historique et confirmer le contexte avant une éventuelle exécution ; la copie
`values-gke-before.yaml` permet de restaurer la seule ligne locale après revue.
Aucun rollback n'a été engagé sur la seule absence de réponse STUN non authentifiée.

Point à traiter avant un prochain push : le contrôle historique
`scripts/check-render.py` sans `--edge` impose explicitement localhost et
`scripts/validate.sh` l'appelle ainsi pour `values-gke.yaml`. Le changement
publicURL demandé rend cette hypothèse obsolète. Le lint et le contrôle public
explicite réussissent, mais la CI complète n'est pas annoncée verte pour ces
modifications ; les checks distants antérieurs ne les couvrent pas. Le pipeline
et ses scripts n'ont pas été modifiés conformément à la consigne : une adaptation
cohérente des validations des profils doit être autorisée séparément.


### Visioconférence publique : test manuel confirmé par l'utilisatrice

**Résultats communiqués par l'utilisatrice le 16 novembre 2026**, après la
migration Jitsi en révision 3. L'agent n'a pas participé à la réunion et ne
présente pas ces observations comme des mesures automatisées.

| Élément | Résultat manuel confirmé par l'utilisatrice |
|---|---|
| Salle | `jitsitest` |
| URL | `https://jitsi-meet-m2.duckdns.org/jitsitest` |
| Participants | Deux connexions simultanées, un ordinateur et un téléphone |
| Vidéo | Visible dans les deux sens |
| Audio | Fonctionnel dans les deux sens |
| Accès | HTTPS public fonctionnel |

Ce test valide le scénario utilisateur audio/vidéo à deux participants décrit
ci-dessus. Le transport P2P ou via JVB n'a pas été instrumenté pendant cet essai :
il ne permet donc pas, à lui seul, d'attribuer les médias au JVB ou de lever
la réserve sur son trajet UDP externe. Aucune durée, statistique réseau ou
configuration de navigateur non fournie n'est inventée. Aucun résultat de partage
d'écran, de charge ou de capacité n'est revendiqué pour ce test.

La soutenance est actualisée avec l'accès public HTTPS, Jitsi révision 3 et
Caddy production, et distingue cette confirmation manuelle des validations
techniques précédentes. Les mentions antérieures « réunion non testée »
décrivaient l'état avant ce retour utilisatrice.


### Validation CI des profils local et HTTPS public adaptée

À la demande de l'utilisatrice, le validateur qui imposait encore
`http://localhost:8081` a été adapté, sans changement des workflows GitHub ni des
garde-fous de déploiement. `scripts/check-render.py` expose désormais un mode
explicite `--auto-profile` utilisé par `scripts/validate.sh` : il accepte soit
l'origine locale exacte, soit une origine HTTPS DNS du profil edge. Les modes
stricts existants restent disponibles : défaut localhost, `--edge` et `--public`
pour l'ancien profil Ingress GCE, avec options mutuellement exclusives.

Les origines HTTP publiques, IP comme hôte HTTPS, localhost HTTPS, ports publics
explicites, identifiants dans l'URL, chemins de salle, requêtes/fragments et noms
DNS malformés sont refusés. Les contrôles du Service Web ClusterIP, de BOSH même
origine, de l'absence d'Ingress en mode edge/local et du JVB UDP10000 restent en
place. `--ready` exige toujours une IP JVB publique annoncée. La validation
locale ajoute un rendu explicitement surchargé localhost, même lorsque
`values-gke.yaml` contient désormais l'URL publique ; le profil local reste donc
vérifié sans modifier le profil déployé.

Six tests de régression ont été ajoutés dans `tests/test_render_profiles.py` :
acceptation des deux profils, maintien des modes stricts, rejet d'origines non
conformes, maintien des invariants BOSH/Web privé, contrôle d'IP JVB et refus
d'options de profils contradictoires. Une première exécution a révélé deux
erreurs dans la fixture de test sur des ConfigMaps avec `data: null` ; le test a
été corrigé pour les ignorer comme le validateur, puis toute la suite a été
relancée avec succès.

Résultats locaux réellement obtenus :

| Commande / contrôle | Résultat |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | **31 tests réussis** |
| `sh scripts/validate.sh` | Lint/rendus Jitsi du profil courant public et régression localhost réussis ; Terraform fmt/init sans backend/validate réussis |
| `CADDY_BIN=/tmp/jitsi-remise-caddy/caddy python3 scripts/validate-edge.py` | Lint/rendu edge, profil public et validation réelle du Caddyfile réussis |
| `sh -n scripts/validate.sh` et `bash -n scripts/deploy-gke.sh` | Syntaxe valide |
| `git diff --check` | Aucune erreur |

Terraform a été initialisé sur une copie temporaire sans backend ni accès à
l'état du projet. Ces tests ne déploient rien et n'ont pas utilisé les sauvegardes
privées ou déchiffré SOPS. Aucun test de charge, partage d'écran ou nouvelle
réunion n'a été exécuté par l'agent. La validation manuelle à deux participants
reste celle confirmée par l'utilisatrice, distincte des contrôles statiques.
Toutes les modifications antérieures sont préservées. **Aucun commit ni push**
n'a été effectué ; aucune nouvelle CI distante n'est donc revendiquée.


### Préparation de publication GitHub, sans commit ni push

Branche contrôlée : `feature/jitsi-public-edge`, HEAD `c591ad4`, index vide.
Les modifications existantes ont été conservées. Le lot proposé comporte 12
fichiers : README, valeurs GKE, deux surcharges DuckDNS, deux scripts de
validation, un fichier de régression et cinq documents. La liste explicite et
le message de commit proposés sont préparés localement sous `/tmp`, sans ajout
à l'index et sans exécution de commit/push/merge.

L'audit automatisé des 177 fichiers suivis ou candidats n'a détecté aucun motif
de clé privée, jeton GitHub/Google ou jeton DuckDNS affecté. La comparaison en
mémoire aux contenus longs des secrets applicatifs actuels, en clair et base64,
n'a trouvé aucune correspondance dans ces fichiers. Il s'agit d'un contrôle de
motifs et de correspondances connues, pas d'une garantie exhaustive. Les mots
de passe du fichier `values-secrets.sops.yaml` sont toujours ENC[AES256_GCM] ;
ce fichier est inchangé. Aucun déchiffrement SOPS effectué.

Les exclusions Git sont confirmées pour `deploy/local/` (dont toutes les
sauvegardes Helm), les états/plans Terraform, valeurs locales de démonstration,
valeurs de secrets en clair, rendus locaux et mesures `tests/results/`. Aucun
chemin de sauvegarde, clé privée, état ou kubeconfig n'est déjà suivi dans le
périmètre inspecté. Ces fichiers ne font pas partie du lot proposé.

L'audit a corrigé deux écarts de publication : le README décrit maintenant
l'accès public et les révisions actuelles ; la surcharge spécifique au domaine
Caddy est désormais `acmeEnvironment: production`, correspondant au live.
Le défaut du chart générique reste staging ; les deux guides de bootstrap
imposent explicitement `--set acmeEnvironment=staging` pour un nouveau bootstrap.
La surcharge Jitsi DuckDNS inclut l'IP JVB actuelle 34.62.165.81 pour reproduire
le réseau réel sans modifier le profil générique. Des encadrés distinguent les
constats historiques des ressources déjà créées ; aucun bootstrap ne doit être
rejoué sur l'environnement existant.

Comparaison effectuée en lecture seule : le rendu edge candidat est identique
au manifeste Helm edge révision 2 ; le rendu Jitsi candidat est identique au
manifeste Helm Jitsi révision 3 hors hooks. Pour cette comparaison, les secrets
existants ont été lus en mémoire puis utilisés dans des fichiers temporaires
privés, supprimés ensuite, sans publication. Les contrôles de cohérence réseau,
secrets et disponibilité de `check-cd-render.py --after` réussissent. Cinq pods
Ready, PVC Bound 10Gi, IP Web 34.78.71.58 et JVB 34.62.165.81 ont été observés.
Aucune ressource cluster n'a été modifiée par cet audit.

Nouvelle validation du lot final : **31 tests Python réussis**,
`scripts/validate.sh` réussi (Helm courant public, rendu localhost explicite,
Terraform sur copie temporaire sans backend), validation edge fixtures et
Caddyfile de production réel réussie, `git diff --check` sans erreur.
Les blocs Bash des guides sont vérifiés syntaxiquement, sans exécution.

Risques à conserver visibles : IPs spécifiques à revalider après recréation ;
CD toujours désactivée avec premier échange OIDC non validé et droit get PVC du
compte CD manquant ; son mode localhost strict ne convient pas au profil source
public et doit être revu avant activation. Les résultats manuels à deux ne
qualifient pas le trajet JVB ni une charge/partage d'écran. Le renouvellement
futur et la reprise après panne ne sont pas qualifiés. Les CI distantes vertes
précédentes concernent c591ad4 et ne couvrent pas encore ce lot local.
Aucun commit, push, merge, changement de permissions ou activation CD effectué.


### Corrections CD et diagnostic OIDC/KMS préparés localement

**16 novembre 2026 — préparation uniquement, après audit en lecture seule.**
L'utilisateur autorise les modifications locales, mais interdit toute activation
API, attribution IAM/RBAC, modification de variable GitHub, lancement de workflow,
commit ou push. Ces interdictions ont été respectées. L'état déployé HTTPS n'a
pas été modifié pendant cette étape.

#### Changements proposés, non appliqués au cloud

- `.github/workflows/deploy-gke.yml` exige désormais `JITSI_ACCESS_PROFILE`
  explicitement, sans fallback silencieux. Avant OIDC, le mode public exige le
  flag edge, le domaine `jitsi-meet-m2.duckdns.org` et `jitsi-edge-ip`.
  Le déclenchement workflow_run de CI push main réussie, SHA exact/tête de main,
  dépôt d'origine, opt-in `GKE_CD_ENABLED`, permissions et concurrence restent
  conservés. Aucune variable n'a été définie ni activée.
- `scripts/deploy-gke.sh` conserve la sélection explicite et prépare une vraie
  surcharge `publicURL=http://localhost:8081` pour le mode local, malgré la base
  publique. Le mode public conserve ses valeurs HTTPS et contrôles existants.
  Le test de droit PVC cible le nom `persistentvolumeclaims/jitsi-edge-data`.
- `deploy/cd-pvc-reader.yaml` propose un Role/RoleBinding additionnel dans
  `jitsi`, seulement `get` sur le PVC nommé `jitsi-edge-data`, pour le compte
  CD. Il ne remplace aucun Role existant, ne crée pas de PVC et n'accorde ni
  list/watch global, create/delete PVC, ni administration RBAC. **Non appliqué.**
- `scripts/check-gcp-apis.py` inventorie les six APIs requises en lecture seule
  sous identité opérateur, sans possibilité d'activation. Le diagnostic runner
  ne requiert pas un droit Service Usage supplémentaire pour cet inventaire.

La proposition de variables et les commandes d'administration futures,
explicitement non exécutées, sont documentées dans `docs/cd-diagnostic.md`.
`GKE_CD_ENABLED` et `JITSI_EDGE_CD_ENABLED` restent absentes/désactivées pendant
le diagnostic. Leur future activation est une décision séparée.

#### Workflow de diagnostic sans déploiement

`.github/workflows/diagnose-gke.yml` est un nouveau workflow manuel préparé,
indépendant de la CD. Il exige une confirmation booléenne, le dépôt exact,
la branche main, le SHA checkout égal à la tête actuelle de main. Le garde
`scripts/diagnose-cd.py --guard-only` s'exécute avant l'authentification Google ;
le SHA est recontrôlé à la fin. Les actions sont épinglées et SOPS est vérifié
par SHA256. Le verrou de concurrence est partagé avec la CD pour éviter une
observation pendant une autre exécution automatisée du déploiement.

Après OIDC et configuration du kubeconfig local au runner, le diagnostic prévu
vérifie l'identité GKE, les URL/configurations publiques existantes, les releases,
49 autorisations (requêtes `can-i`, sans exécuter les verbes CRUD), le PVC Bound,
SOPS/KMS, les rendus et la correspondance des secrets/IP/disponibilités.
Le droit minimal PVC proposé correspond exactement au nom interrogé.

Le déchiffrement futur est limité à un dossier RUNNER_TEMP privé 0700 avec
fichiers 0600, sans sortie brute d'outil, debug, artefact ou cache sensible.
Nettoyage Python à la sortie et à l'erreur, traitement SIGTERM et nettoyage
always() de secours sont préparés ; l'action auth nettoie ses credentials WIF.
Aucun helm upgrade/install/rollback/uninstall, aucune écriture de ressource
applicative ou opération de bootstrap n'est prévue. Les fichiers temporaires,
kubeconfig et credentials sont locaux au runner. Les opérations KMS/runner
peuvent avoir un coût d'opération/temps, sans création d'infrastructure.

#### Résultats réellement obtenus ici

| Contrôle | Résultat | Portée |
|---|---|---|
| `python3 scripts/check-gcp-apis.py` | Sortie 1 attendue : **STS et Resource Manager manquantes** ; IAM/IAMCredentials/GKE/KMS actives | Lecture réelle de l'inventaire, aucune activation |
| Suite `unittest` locale | **42 tests réussis**, dont 11 nouveaux | Données synthétiques/mocks pour le diagnostic ; aucun appel runner/OIDC/KMS réel |
| `sh scripts/validate.sh` | Réussi | Helm public et localhost ; Terraform fmt/init/validate sur copie temporaire sans backend |
| `scripts/validate-edge.py` avec CADDY_BIN | Réussi | Lint/rendu edge et validation Caddyfile ; aucun serveur lancé |
| Syntaxe | YAML du workflow lu, blocs run validés avec bash -n ; Python compilé ; Bash de déploiement valide | Aucun déclenchement GitHub ; actionlint non disponible |
| `git diff --check` et scan de motifs sensibles | Réussis | Aucune clé privée/jeton détecté dans les nouveaux fichiers contrôlés |

Les tests couvrent contexte/fork/branche/SHA/confirmation refusés, droit PVC
nommé, commandes de mutation refusées, erreurs sensibles masquées, scénario
synthétique de réussite et nettoyage après échec SOPS. Les messages de réussite
simulée ne sont pas présentés comme un résultat réel d'authentification.
Aucun SOPS n'a été réellement déchiffré pendant cette préparation.

#### Toujours prévu, non réalisé

Publication et intégration du nouveau workflow sur main, activation approuvée
des APIs manquantes, application approuvée du seul droit PVC, sélection des
variables sans activer la CD, puis lancement manuel autorisé du diagnostic.
L'échange OIDC, l'accès GKE depuis GitHub et le déchiffrement KMS sous l'identité
CD restent **non testés sur runner**. Les workflows GitHub n'ont pas été lancés.
Aucun commit/push/merge effectué pour ces corrections locales.

Risques : le compte CD garde ses droits applicatifs existants ; le caractère
sans déploiement repose donc aussi sur le code relu, pas sur une identité
entièrement read-only. Le durcissement WIF par ID immuable/workflow exact et
l'approbation humaine/environnement GitHub restent à discuter. Les upgrades
CD ne sont pas transactionnels ; une future migration PUBLIC_URL nécessitera
son rechargement contrôlé. Le diagnostic ne valide ni renouvellement TLS,
reprise après panne ou conférence. Aucun succès du diagnostic ne devra être
interprété comme une autorisation implicite d'activer la CD.


### Activation limitée des APIs nécessaires au diagnostic CD — 16 novembre 2026

L'utilisateur a autorisé uniquement l'activation de `sts.googleapis.com` et
`cloudresourcemanager.googleapis.com` dans
`project-fcf2ef91-c005-4910-a10`, sous réserve de précontrôles. Les modifications
locales préparées précédemment ont été conservées ; aucune autre configuration
ou permission n'a été modifiée.

#### Précontrôles réellement effectués avant modification

- `gcloud config get-value project` correspond exactement au projet attendu ;
  une seule identité authentifiée est active. Aucun changement de projet ou
  d'identité n'a été effectué.
- Les lectures directes Service Usage indiquent **DISABLED** pour les deux APIs.
- `testIamPermissions` confirme pour l'identité courante les permissions
  `serviceusage.services.get`, `serviceusage.services.list` et
  **`serviceusage.services.enable`**. Aucun rôle nouveau attribué.
- La documentation officielle Google sur
  [WIF et les pipelines de déploiement](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
  inclut les APIs IAM, Resource Manager, IAMCredentials et STS parmi les
  prérequis. STS sert à l'échange du jeton fédéré ; ces deux services manquaient
  au jeu de prérequis retenu. Cela ne constituait pas une preuve d'échange OIDC.

#### Commande autorisée et résultat

```bash
gcloud services enable sts.googleapis.com cloudresourcemanager.googleapis.com \
  --project=project-fcf2ef91-c005-4910-a10
```

La commande a terminé avec succès. Les inventaires complets des services actifs,
lus avant et après, donnent exactement deux ajouts :

| API | Avant | Après, confirmé par Service Usage |
|---|---|---|
| `sts.googleapis.com` | DISABLED | **ENABLED** |
| `cloudresourcemanager.googleapis.com` | DISABLED | **ENABLED** |

Aucun autre service activé et aucun service désactivé selon cette comparaison.
Le projet actif est resté identique.

#### Contrôle après activation

`python3 -B scripts/check-gcp-apis.py` termine avec le **code 0** et confirme
les six APIs actives : IAM, IAMCredentials, STS, Resource Manager, GKE et KMS.
La sortie précise : « Prerequis API presents ; aucun echange OIDC teste ici. »
Les mentions antérieures d'APIs manquantes décrivent donc l'état avant cette
activation autorisée, désormais levé.

Aucune modification IAM/RBAC, variable GitHub, ressource Kubernetes, secret,
configuration Jitsi/Caddy ou autre service. Aucun déploiement ni workflow lancé,
aucun commit, push ou merge. Seule cette section a été ajoutée au rapport pendant
l'opération, sans écraser les changements précédents. Aucun jeton n'a été affiché.

Le diagnostic OIDC/GKE/SOPS sur runner reste **préparé, non exécuté** ; la lecture
minimale du PVC et l'intégration du workflow demeurent des étapes séparées
nécessitant leur propre accord. Aucune activation CD n'est déduite de ce succès.


### Droit de lecture minimal du PVC Caddy appliqué après validation

**16 novembre 2026.** L'utilisateur a autorisé uniquement l'application de
`deploy/cd-pvc-reader.yaml` après contrôle du contexte, du sujet et validation
sans persistance. Aucune autre permission ou ressource n'était autorisée.

Le contexte courant est
`gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster` ; son serveur
correspond à l'endpoint du cluster GKE `jitsi-cluster`, état RUNNING,
`europe-west1-b`, projet attendu. Le namespace `jitsi` est Active.

**Précision d'identité :** la CD utilise le compte de service Google
`github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com`
via OIDC/GKE, représenté dans Kubernetes par un sujet **kind: User**, comme dans
le RoleBinding CD préexistant et le contrôle d'identité du script. Ce n'est pas
un Kubernetes ServiceAccount de forme `system:serviceaccount:namespace:nom`.
Le nouveau binding cible exactement cette identité existante, sans substitution.

Le manifeste a été contrôlé structurellement : exactement deux objets nouveaux,
Role et RoleBinding `github-jitsi-caddy-pvc-reader`, dans `jitsi`. Le Role
contient une seule règle :

```yaml
apiGroups: [""]
resources: [persistentvolumeclaims]
resourceNames: [jitsi-edge-data]
verbs: [get]
```

Aucun Role/RoleBinding homonyme n'existait avant intervention. Les tests initiaux
par impersonation retournaient no pour get du PVC nommé, create, update, patch
et delete. Le contrôle préparatoire a été réalisé avant toute application :

```bash
kubectl apply --dry-run=server -f deploy/cd-pvc-reader.yaml
kubectl diff -f deploy/cd-pvc-reader.yaml
```

La validation serveur réussit sans persistance ; le diff affiché ne contient que
les deux ajouts attendus (code 1 de kubectl diff, signifiant différence et non
échec). L'empreinte du manifeste et le contexte ont été revérifiés immédiatement
avant l'application autorisée :

```bash
kubectl apply -f deploy/cd-pvc-reader.yaml
```

Résultat : Role et RoleBinding **created**, puis relecture des règles et du
sujet conformes. Aucune commande n'a ciblé le PVC en écriture.

#### Résultats effectifs après application

Les contrôles `kubectl auth can-i ... --as=COMPTE_CD -n jitsi` donnent :

| Opération | Résultat |
|---|---|
| get `persistentvolumeclaims/jitsi-edge-data` | **yes** |
| get `persistentvolumeclaims/autre-pvc` | no |
| list / watch `persistentvolumeclaims` | no |
| create `persistentvolumeclaims` | no |
| update / patch / delete `persistentvolumeclaims/jitsi-edge-data` | no |
| create / update / patch / delete `persistentvolumeclaims` sans nom | no |
| deletecollection `persistentvolumeclaims` | no |

Une véritable lecture `kubectl get pvc jitsi-edge-data` avec impersonation du
compte CD réussit : Bound, 10Gi. La comparaison avant/après confirme UID, spec
et statut du PVC identiques. Les UID des cinq pods sont inchangés et tous sont
Ready. Les releases Helm sont identiques à la capture initiale (Jitsi révision 3,
Caddy révision 2). Les règles et bindings préexistants du namespace sont
inchangés ; seuls les deux objets approuvés ont été ajoutés.

Ces résultats prouvent la permission effective de lecture nommée et les refus
d'écriture interrogés, sans tentative de création/modification/suppression de
PVC. Ils ne constituent pas un test du workflow OIDC depuis GitHub. Le diagnostic
runner reste préparé, non lancé, et la CD reste désactivée.

Aucun changement du PVC, pods, releases, variables GitHub, secrets ou droits IAM.
Aucun autre droit RBAC modifié, aucun commit/push/merge ou workflow déclenché.
Les modifications locales antérieures sont préservées ; seule cette section a
été ajoutée au rapport pendant l'intervention.


### Publication du diagnostic CD préparée, sans opération Git distante

**16 novembre 2026.** L'utilisateur demande la préparation de publication, sans
commit, push, merge, workflow ou modification cloud. La branche active reste
`feature/jitsi-public-edge`, HEAD `ff74090`, index vide. Le lot local contient
11 fichiers : les deux workflows CD/diagnostic, `scripts/deploy-gke.sh`,
`scripts/diagnose-cd.py`, `scripts/check-gcp-apis.py`, le manifeste PVC reader,
les trois tests CD/edge/diagnostic et les documents rapport/diagnostic.
Une liste explicite et un message de commit sont préparés localement sous
`/tmp/jitsi-diagnostic-publication-{files,message}.txt`, sans indexation.

#### Audit du lot et du périmètre sans déploiement

Les fichiers modifiés et non suivis ont été inspectés. Le scan des motifs de
clés privées, jetons GitHub/Google/DuckDNS et credentials Google, ainsi que la
comparaison aux secrets applicatifs connus en clair et base64, ne détectent
aucun secret dans le lot. Les sauvegardes Helm sous `deploy/local/`, états/plans
Terraform, valeurs en clair, rendus et résultats locaux restent ignorés et
exclus du lot. Ces contrôles ne constituent pas une garantie exhaustive contre
toute forme de secret inconnue ; aucun contenu sensible n'a été affiché.

Le workflow diagnostic a uniquement workflow_dispatch, confirmation par défaut
false, dépôt/branche main stricts et garde de SHA avant OIDC et en fin de test.
Il n'a aucun déclencheur push, PR, schedule ou workflow_run. Un dispatch reste
une action explicite d'un utilisateur/API GitHub autorisé, pas une conséquence
du push ou du merge. Permissions globales vides ; seuls contents:read et
id-token:write au job. Pas de permission d'écriture du dépôt ou de gestion des
workflows. Actions épinglées, absence de commande de déploiement et contrôles
appelés en lecture seule confirmés ; les opérations CRUD RBAC sont seulement
interrogées avec can-i. Le contexte local de diagnostic reste public-edge.

Le Role PVC déjà appliqué a seulement son commentaire de provenance actualisé,
sans changement de règle. Le guide distingue maintenant les APIs/PVC déjà
validés de l'intégration GitHub encore à faire. Aucune réapplication du manifeste
ou activation de service ne fait partie de cette publication.

#### Prérequis de lancement revérifiés en lecture seule

- Les six APIs sont actives ; `scripts/check-gcp-apis.py` réussit.
- get du PVC nommé répond yes par impersonation ; aucune permission modifiée.
- Provider WIF ACTIVE, émetteur GitHub, condition dépôt attendu et refs/heads/main.
  Clé primaire KMS ENABLED. Le succès réel OIDC/KMS depuis GitHub reste non testé.
- GitHub Actions est activé et les actions utilisées sont autorisées. Le défaut
  du GITHUB_TOKEN est read ; le job déclare précisément les permissions utiles.
- **Aucun secret GitHub ajouté ou variable de dépôt n'est nécessaire au
  diagnostic.** GH_TOKEN est le jeton automatique github.token ; OIDC remplace
  une clé JSON permanente. Les valeurs SOPS chiffrées sont déjà dans le dépôt.
  Aucun PAT personnel, token DuckDNS ou mot de passe en clair ne doit être créé.
- Les variables du dépôt sont toujours vides. Les propositions public-edge
  documentées concernent la future CD ; elles ne bloquent pas le diagnostic.
  GKE_CD_ENABLED doit rester absente/false pendant toute cette validation.
- La branche par défaut est main. Le workflow diagnostic y est **absent (404)** ;
  seule la CI y est actuellement enregistrée. La PR nº 3 est ouverte en
  brouillon, head ff74090. Aucune disponibilité manuelle depuis la seule branche
  feature n'est supposée.

#### Validations locales relancées

La suite complète termine avec **42 tests réussis**. `scripts/validate.sh`
réussit (Helm public et localhost ; Terraform sans backend sur copie temporaire),
ainsi que `validate-edge.py` avec Caddy, syntaxe Bash, lecture YAML et
`git diff --check`. Tous les blocs run du workflow ont été contrôlés avec
bash -n, sans exécution ; les commandes futures du guide sont vérifiées
syntaxiquement, sans lancement. Les tests OIDC/KMS sont simulés : aucun nouveau
déchiffrement réel, jeton OIDC GitHub ou runner n'est utilisé pour ces tests.

#### Actions restantes pour une exécution réelle

1. Obtenir l'accord commit/push des 11 fichiers, puis publier sur la branche et
   attendre les CI du nouveau SHA. Aucun commit n'a encore été créé ici.
2. Revoir la PR nº 3 complète, qui contient aussi les dépendances HTTPS/CD
   précédentes : copier seulement le YAML diagnostic sur main ne suffirait pas.
   Obtenir un accord distinct de fusion, avec GKE_CD_ENABLED toujours désactivée.
3. Après fusion autorisée, attendre une CI verte du **push main**, relever le
   SHA final et confirmer que le nouveau workflow et ses dépendances sont
   présents sur main et enregistrés dans Actions.
4. Obtenir un accord de lancement manuel, par un opérateur disposant du droit
   d'exécuter Actions. Sélectionner main et confirm_read_only=true. La commande
   préparée dans le guide est `gh workflow run diagnose-gke.yml --repo
   SaminouA/projet-jitsi-helm --ref main -f confirm_read_only=true` ; **non lancée**.
5. Vérifier l'ID de run, l'événement workflow_dispatch, la branche main et le SHA
   attendu ; attendre la conclusion et relire identité, RBAC, PVC, KMS, rendus et
   nettoyage. Garder main stable pendant le test. Aucun succès ne doit activer
   implicitement la CD ou autoriser un déploiement.

Les fichiers locaux existants sont préservés. Seuls les commentaires de
provenance et la documentation ont été actualisés pendant cette préparation ;
aucun service/droit/variable ou ressource applicative modifié. Aucun commit,
push, merge ou lancement GitHub Actions effectué. Le compte CD conserve ses
permissions applicatives : la sûreté du diagnostic repose aussi sur le code
relu et le nettoyage des données temporairement déchiffrées. Ce risque reste
visible dans le guide avant autorisation d'exécution.


### Fusion autorisée de la PR nº 3 et vérification de la CD ignorée

**16 novembre 2026.** L'utilisateur a autorisé la sortie du mode Draft et la
fusion de la PR nº 3, après recontrôle immédiat du SHA/cible, des checks requis
et de la désactivation CD. Avant l'opération : PR ouverte vers main, tête exacte
`11d9784c95ffe01fdce328c979f19a897b797463`, deux checks obligatoires Validation
Helm réussis, GKE_CD_ENABLED absente. Aucun conflit signalé.

Opérations réellement effectuées via GitHub, sans contournement administrateur :

```bash
gh pr ready 3
gh pr checks 3 --required
gh pr merge 3 --merge --match-head-commit 11d9784c95ffe01fdce328c979f19a897b797463
```

La cible, le SHA et le flag CD ont aussi été recontrôlés entre la sortie du
brouillon et la fusion. Les protections ont été respectées ; aucune option
admin, auto-merge ou suppression de branche n'a été utilisée.

GitHub confirme la PR merged le **16 novembre 2026 à 20:54:59 UTC**, soit
**21:54:59 à Paris**. Le SHA final de main est
**`3d9a37c1bec4e98de70750aa211099bded524cbe`**. La branche distante
`feature/jitsi-public-edge` existe toujours et pointe sur
`11d9784c95ffe01fdce328c979f19a897b797463`.

#### Résultats réels après fusion

| Vérification | Résultat |
|---|---|
| CI Validation Helm et Terraform | **success**, événement push, branche main, SHA final exact |
| Run CI | [43954679027](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43954679027) |
| Workflow Deploy Jitsi to GKE | completed, conclusion **skipped**, événement workflow_run |
| Run CD | [43954755012](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43954755012) |
| Job Deploy Jitsi (trusted main) | **skipped**, liste d'étapes vide |
| Variable GKE_CD_ENABLED | Toujours absente/inactive au dernier contrôle |
| Workflow diagnostic | Présent/enregistré et active sur main, **non lancé** |

Le job CD n'a exécuté aucune étape : ni authentification Google, configuration
GKE, déchiffrement SOPS ou commande Helm de déploiement par ce workflow.
La création automatique de son exécution workflow_run n'est pas une activation
CD ; le garde d'opt-in a empêché le job. Aucun lancement manuel Actions, changement
de variable ou opération GCP/Kubernetes n'a été effectué par l'agent.

#### Rapport local et étapes encore prévues

Cette section est ajoutée **uniquement au fichier local de la branche feature**,
après vérification de la branche courante. Aucun nouveau commit/push n'est
réalisé pour ces notes et main n'est pas modifiée après sa fusion autorisée.
Le rapport publié dans main s'arrête donc à l'état documenté par le commit
fusionné ; les faits post-fusion consignés ici restent locaux.

La prochaine étape possible est le diagnostic manuel sur main avec confirmation
confirm_read_only=true, **uniquement après un nouvel accord explicite**. Les
APIs et le droit PVC ont été validés auparavant, mais l'échange OIDC, GKE et le
déchiffrement KMS depuis le runner restent non testés tant que ce diagnostic
n'est pas exécuté. La réussite de la CI ne constitue pas leur validation et
n'autorise aucune activation CD implicite.


### Premier diagnostic manuel OIDC/GKE/SOPS : échec au contrôle d'identité GKE

**16 novembre 2026.** L'utilisateur autorise un seul lancement du workflow
`.github/workflows/diagnose-gke.yml` sur main, confirm_read_only=true, sans
modification applicative ou activation CD. Les précontrôles ont confirmé main
sur `3d9a37c1bec4e98de70750aa211099bded524cbe`, GKE_CD_ENABLED absente et le
workflow diagnostic exact (ID 420594675), actif et limité à workflow_dispatch.
Son contenu distant a été comparé au contenu relu, et aucun autre workflow
n'a été ciblé. Aucune exécution diagnostic n'existait avant le dispatch.

Un seul dispatch a été envoyé :

```bash
gh workflow run 420594675 --repo SaminouA/projet-jitsi-helm \
  --ref main -f confirm_read_only=true
```

Exécution [43955701042](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43955701042),
créée le 16 novembre à **21:01:02 UTC (22:01:02 Paris)**,
événement workflow_dispatch, branche main, SHA attendu, **run_attempt=1**.
Le contrôle final de la liste confirme exactement **une exécution**, sans relance.
La conclusion est **failure**, job diagnose (133609551874), code de sortie 1.

#### Étapes réellement réalisées et limites

| Vérification / étape | Résultat observé |
|---|---|
| Checkout, Python et dépendances | success |
| Garde de confiance avant OIDC | success |
| Helm et installation SOPS avec checksum | success ; installer SOPS ne valide pas son déchiffrement |
| Action Authentification OIDC vers Google Cloud | **success** |
| Installation/configuration gcloud et plugin GKE | success |
| Action get-gke-credentials, cluster existant | **success**, accès aux informations GCP du cluster et kubeconfig runner préparé |
| Garde répété au début du script et nom du contexte | Franchis avant le contrôle suivant ; pas de preuve suffisante d'accès Kubernetes |
| Identité effective Kubernetes via kubectl auth whoami | **Échec**, message fixe `Echec diagnostic : identite GKE ; details non publies.` |
| Comparaison du nom utilisateur Kubernetes | Non réalisée : la commande whoami n'a pas réussi |
| 49 contrôles RBAC dans le runner | **Non réalisés**, arrêt avant cette étape |
| Lecture/vérification du PVC par le runner | **Non réalisée** |
| Déchiffrement SOPS/KMS et comparaison des secrets | **Non réalisés** |
| Lint/rendus applicatifs et contrôles de disponibilité du diagnostic | **Non réalisés** |
| Nettoyage always() de secours | success |
| Nettoyage post-action auth des credentials fédérés | success |

L'étape de récupération des credentials GKE a réussi, mais cela ne prouve pas
l'accès effectif à l'API Kubernetes depuis le runner. Le résultat permet de
constater la réussite de la configuration OIDC et de l'accès aux informations
Google Cloud utilisées par l'action ; l'identité Kubernetes effective reste
non confirmée. Aucun succès SOPS/KMS n'est revendiqué sur la seule installation
du binaire ou le succès de l'authentification Google.

#### Analyse sans divulgation et sans nouvelle exécution

Les logs ont été capturés uniquement pour extraction en mémoire de messages
fixes et des états d'étapes. Aucun log brut, jeton, secret ou valeur déchiffrée
n'a été publié. L'erreur native de whoami avait été volontairement masquée par
le script ; son détail n'est donc pas disponible dans les logs GitHub. La cause
précise (réseau, authentification/plugin ou autorisation Kubernetes) n'est **pas
établie** à ce stade. Les avertissements Node.js 20/runner Ubuntu sont des
avertissements de plateforme ; aucune causalité avec cette erreur n'est prouvée.

Un contrôle complémentaire local, seulement en lecture et par impersonation,
a été effectué : create SelfSubjectReview est autorisé et `kubectl auth whoami`
réussit avec l'identité attendue. Cela ne reproduit pas l'authentification
fédérée depuis le runner et ne remplace pas le diagnostic échoué. Ce résultat
ne justifie aucune extension RBAC à l'aveugle ; aucun droit n'a été modifié.

Le script s'est arrêté avant de créer son répertoire de déchiffrement et avant
SOPS : aucune valeur SOPS en clair n'a été générée par cette exécution.
Les étapes de nettoyage des credentials ont terminé avec succès. Aucun Helm
upgrade/install/rollback/uninstall, changement de PVC/pod, attribution de droit,
variable GitHub ou autre ressource n'a été effectué. Aucun workflow deploy-gke
n'a été lancé manuellement et aucun second diagnostic n'a été demandé.
Main reste au SHA attendu ; la liste des variables du dépôt reste vide.

#### Prochaine action nécessaire, non exécutée

Préparer après accord une instrumentation minimale et expurgée du seul contrôle
whoami : présence/version du plugin, distinction timeout réseau / échec de
credentials / réponse 401 ou 403, sans publier stderr brut ou token. Revoir cette
correction, l'intégrer sur main avec CI, puis obtenir une nouvelle autorisation
pour une tentative distincte sur le nouveau SHA attendu. Ne pas modifier IAM/RBAC
sans cause établie et ne pas activer la CD avant le succès complet du diagnostic.

Cette section est ajoutée uniquement au rapport **local sur la branche feature**,
en conservant les notes post-fusion existantes. Aucun commit, push, merge ou
modification de main n'a été réalisé pour ces notes. Les vérifications runner
non atteintes restent explicitement prévues, pas validées.


### Instrumentation expurgée du contrôle whoami — correction locale uniquement

**16 novembre 2026.** L'utilisateur demande une correction minimale pour analyser
l'échec du run GitHub `43955701042`, sans relance, publication ou changement
IAM/RBAC/cloud. Les notes locales post-fusion et du premier diagnostic sont
conservées. Aucun contenu existant n'a été supprimé du rapport.

#### Échec réel et hypothèse, non confondus avec les tests locaux

Le run réel reste en échec sur la commande `kubectl auth whoami`, après les
étapes OIDC et get-gke-credentials réussies. Les contrôles runner RBAC/PVC et
SOPS/KMS n'ont pas été atteints. La cause native n'a pas été enregistrée car
le script masquait tout stderr. Le contrôle local précédent par impersonation
réussissait pour whoami et SelfSubjectReview, sans reproduire l'authentification
ni le réseau GitHub.

L'hypothèse de travail est donc un problème dans le chemin spécifique au runner
vers Kubernetes (réseau/TLS ou exécution du plugin/credentials), plutôt qu'un
manque déjà démontré du droit PVC. Cela reste une **hypothèse**, sans classement
prouvé entre ces causes et sans preuve suffisante pour modifier IAM/RBAC.
Les avertissements de versions Node/Ubuntu ne sont pas retenus comme cause sans
preuve. Le workflow et ses actions ont été examinés ; aucun changement YAML ou
permission GitHub n'est nécessaire pour instrumenter le script existant.

#### Correction proposée dans scripts/diagnose-cd.py

1. Vérifier la présence du binaire `gke-gcloud-auth-plugin` et son invocation
   `--version`, sortie capturée. Ce contrôle ne demande pas directement de token.
2. Lire en mémoire le seul champ serveur du contexte minifié, sans exporter ou
   afficher le kubeconfig, son certificat ou ses credentials. Refuser une URL
   endpoint anormale (HTTP, identifiants, chemin ou requête).
3. Tester une connexion TCP vers cet endpoint sans credential, avec timeout
   de connexion 5 secondes. N'afficher ni hostname ni adresse de l'endpoint.
4. Exécuter whoami avec `--request-timeout=15s` et limite processus 30 secondes.
   Classer les stdout/stderr capturés uniquement en catégories fixes. Aucun
   extrait natif ne doit apparaître dans le message d'erreur.
5. Vérifier la structure de la réponse et l'identité attendue, sans afficher
   l'identité reçue. Arrêter avant les autres lectures applicatives et SOPS
   si la vérification échoue.

Les catégories couvrent plugin absent/défaillant/timeout, credentials refusés,
authentification 401, refus d'autorisation 403, DNS, timeout réseau, TLS,
connexion refusée et autre erreur de transport. Une erreur non reconnue reste
INDETERMINE ; un timeout global whoami est DELAI_INDETERMINE et n'est pas
attribué automatiquement au réseau. Un 403 exige une analyse ultérieure et
n'est pas une autorisation d'ajouter un rôle (RBAC/IAM à distinguer).

TCP OK ne prouve pas TLS/auth/RBAC. Un échec TCP direct peut aussi être non
concluant avec un proxy : whoami est tout de même exécuté une fois et reste le
contrôle autoritatif. Le fonctionnement effectif du plugin et la fraîcheur des
credentials sont testés par whoami, pas par le seul succès de --version.
Aucune nouvelle commande de mutation n'a été ajoutée. Les deux seules nouvelles
commandes autorisées sont plugin --version et lecture locale du champ serveur.
Les déclencheurs manuels/main/SHA, permissions GitHub, opt-in CD, nettoyage SOPS
et interdictions Helm restent inchangés.

#### Tests et validations réellement réalisés

Neuf tests de régression supplémentaires ont été ajoutés à
`tests/test_diagnostic.py`, avec sous-cas synthétiques pour les catégories :
plugin absent/défaillant/timeout, erreurs réseau, erreurs d'authentification et
403, masquage de sentinelles de secrets, réponse invalide, identité inattendue,
TCP non concluant et arrêt avant RBAC/déchiffrement. Aucun plugin réel, accès
réseau au cluster, jeton GitHub ou déchiffrement réel n'est utilisé par ces tests.
Les simulations complètes préexistantes ont été adaptées aux probes simulés.

| Contrôle local | Résultat |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_*.py' -v` | **51 tests réussis** (42 existants + 9 nouveaux) |
| `sh scripts/validate.sh` | Réussi : Helm public/local et Terraform sans backend sur copie temporaire |
| Validation edge avec CADDY_BIN | Réussie : lint/rendu et Caddyfile |
| Syntaxe Python, YAML, blocs Bash et script de déploiement | Valide, sans exécution distante |
| `git diff --check` | Aucune erreur |

Fichiers concernés : `scripts/diagnose-cd.py`, `tests/test_diagnostic.py`,
`docs/cd-diagnostic.md` et ce rapport. Le workflow lui-même reste inchangé.
Les sorties des probes ne publient que catégories/statuts fixes, jamais token,
credential, endpoint, kubeconfig, identité reçue ou valeur déchiffrée.

#### Toujours non réalisé

La correction est **locale, non committée et non poussée**, sur la branche
feature ; elle n'est pas dans main et n'a pas été exécutée sur GitHub. Aucun
second run n'a été lancé et aucun succès runner n'est revendiqué. La prochaine
étape sera une revue puis publication/intégration après accord, suivie d'une
nouvelle autorisation de diagnostic sur le SHA main contenant cette correction.
Aucune permission IAM/RBAC, ressource GCP/Kubernetes, variable GitHub ou release
Helm n'a été modifiée pendant cette préparation. Aucune opération de déploiement
n'a été effectuée.


### Diagnostic instrumenté exécuté une seule fois : erreur INDETERMINE

**16 novembre 2026.** L'utilisateur autorise une seule exécution du diagnostic
manuel sur main au SHA `c3e8ead17a35e234c1789c6d80da2e89c87a77fe`, sans changement
de droit, variable ou ressource. Les précontrôles ont confirmé ce SHA, le flag
GKE_CD_ENABLED absent/inactif, et le workflow exact ID 420594675, actif, manuel,
avec les mêmes script et YAML que la correction relue. Aucun deploy-gke n'est
ciblé. Une ancienne exécution existait sur l'ancien SHA ; aucune sur le nouveau.

Un seul dispatch a été effectué avec main et confirm_read_only=true :

```bash
gh workflow run 420594675 --repo SaminouA/projet-jitsi-helm \
  --ref main -f confirm_read_only=true
```

Run [43959531200](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43959531200),
créé à **21:23:03 UTC (22:23:03 Paris)**, événement workflow_dispatch,
branche main et SHA attendu, **run_attempt=1**, conclusion **failure**.
Le job diagnose (133622904392) termine avec code 1. L'inventaire après exécution
confirme une seule tentative sur ce SHA ; aucune relance automatique ou manuelle.

#### Résultats effectifs du runner

| Étape | Résultat réel |
|---|---|
| Garde dépôt/main/SHA/confirmation | success |
| Installation Helm/SOPS et vérification checksum | success ; pas une preuve de déchiffrement |
| Authentification OIDC et configuration gcloud | success |
| get-gke-credentials, informations GCP du cluster | success |
| Présence et invocation --version du plugin | **Diagnostic plugin : DISPONIBLE** |
| Connexion TCP à l'endpoint API | **Diagnostic reseau TCP : OK** |
| kubectl auth whoami | **Diagnostic identite GKE : INDETERMINE** ; échec |
| Comparaison de l'identité effective | Non réalisée, pas de réponse whoami valide |
| Contrôles runner RBAC (49 autorisations) | **Non réalisés** |
| Contrôle runner du PVC | **Non réalisé** |
| Déchiffrement SOPS/KMS et comparaison des secrets | **Non réalisés** |
| Rendus et contrôles applicatifs ultérieurs | **Non réalisés** |
| Nettoyage always() et post-action credentials | **success** |

Le plugin n'est pas absent et la connectivité TCP depuis ce runner est établie.
Cela ne prouve pas TLS, authentification ou autorisation Kubernetes. whoami
reste en échec ; aucun succès RBAC/PVC/SOPS/KMS runner n'est déduit des succès
locaux antérieurs. Le répertoire SOPS n'est pas créé avant ce contrôle : aucune
valeur SOPS déchiffrée n'a été produite par le script dans cette exécution.
Les journaux ont été capturés seulement pour extraction de catégories fixes et
états d'étapes ; aucun token, credential, kubeconfig ou log brut n'a été affiché.

#### Piste principale identifiée par lecture des sources, non confirmée par le stderr du run

Une investigation supplémentaire strictement en lecture a examiné les sources
[officielles de l'action get-gke-credentials au commit épinglé](https://github.com/google-github-actions/get-gke-credentials/blob/3da1e46a907576cefaa90c484278bb5b259dd395/src/client.ts#L399).
La branche useAuthProvider=true y génère le mécanisme kubeconfig legacy
`auth-provider: {name: gcp}`, plutôt qu'une entrée exec du plugin. Le workflow
courant fournit précisément `use_auth_provider: true`.

La [documentation Google de dépannage kubectl](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/kubectl)
indique l'erreur « no Auth Provider found for name gcp » pour les clients basés
sur client-go 1.26 et ultérieurs. Installer le binaire ne suffit pas si le
kubeconfig sélectionne encore l'ancien mécanisme.

Un contrôle synthétique local confirme que le texte public documenté de cette
erreur est classé INDETERMINE par le classificateur actuel. Cela est cohérent
avec la catégorie reçue et constitue une piste concrète de compatibilité,
**pas une preuve que ce texte exact a été produit par ce run** : le stderr
natif était expurgé, et la version exacte de kubectl n'a pas été qualifiée dans
cette analyse. Aucun kubeconfig du runner n'a été exporté ou lu par l'agent.
Les permissions RBAC ne doivent pas être élargies sans autre preuve.

#### Prochaine action proposée, non exécutée

Préparer après accord la correction de la configuration d'authentification
locale au runner : soit le mode jeton court fourni par l'action issue d'OIDC
(use_auth_provider=false), soit une vraie entrée exec moderne du plugin,
avec tests et nettoyage du kubeconfig temporaire. Ajouter un contrôle expurgé
du mécanisme choisi et une catégorie dédiée à l'ancien auth-provider, sans
publier le contenu du kubeconfig ou le token. Le workflow CD utilise le même
paramètre et devra être examiné séparément avant toute activation.

Aucun de ces changements n'a été effectué ici. Leur publication/intégration et
un nouvel essai demandent un accord distinct ; aucune tentative supplémentaire
n'est faite pour contourner l'échec. Main reste sur c3e8ead et le flag CD est
inactif. Aucune permission, variable, ressource GCP/Kubernetes ou release Helm
n'a été modifiée. Aucun déploiement Jitsi ou workflow CD déclenché par l'agent.

Cette section est ajoutée uniquement au rapport local de la branche de
correction, sans commit ni push. Le code et le workflow ne sont pas modifiés
pendant cette exécution ; les limites d'identification de la cause restent
explicitement distinguées des faits observés et du test synthétique local.


### Correction locale de l'authentification GKE : exec ADC via OIDC

**16 novembre 2026.** À la demande de l'utilisateur, une correction minimale
est préparée uniquement dans le workflow de diagnostic et son script, sans
changer IAM/RBAC, CD ou ressources. Le dernier run réel reste
[43959531200](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43959531200)
en échec : plugin disponible, TCP OK, whoami INDETERMINE ; RBAC/PVC/SOPS non
atteints. La correction suivante n'a pas été exécutée sur GitHub.

#### Vérification de la piste et choix

Une nouvelle lecture des sources officielles confirme qu'au commit épinglé
3da1e46a907576cefaa90c484278bb5b259dd395, get-gke-credentials génère
`auth-provider: {name: gcp}` quand useAuthProvider=true, et non une entrée exec.
Le workflow diagnostic passait précisément use_auth_provider=true. Cette
construction est un fait vérifié par le code de l'action ; son implication
comme cause exacte du stderr masqué reste une hypothèse.

La méthode retenue est la génération officielle gcloud d'un kubeconfig exec
avec Application Default Credentials fédérés. La documentation
[get-credentials](https://docs.cloud.google.com/sdk/gcloud/reference/container/clusters/get-credentials)
prévoit la propriété container/use_application_default_credentials=true.
Le code SDK installé, lu sans obtenir de credentials, confirme l'entrée exec
v1beta1 et l'argument --use_application_default_credentials.

#### Changements préparés, non exécutés sur des ressources

- `.github/workflows/diagnose-gke.yml` conserve l'action auth OIDC épinglée,
  les restrictions dispatch/main/SHA, contents:read et id-token:write.
  Seule l'étape de génération de kubeconfig par get-gke-credentials est remplacée
  par un appel au script `--configure-gke`. Setup-gcloud installe toujours
  kubectl et le plugin.
- Le mode exec du plugin et la propriété ADC sont explicitement sélectionnés
  via les variables d'environnement du runner, pas des variables GitHub de
  dépôt. KUBECONFIG utilise runner.temp au niveau de l'étape appropriée, puis
  son chemin seul est propagé par GITHUB_ENV.
- `scripts/diagnose-cd.py --configure-gke` revalide main/SHA et exécute seulement
  la lecture GCP suivante pour générer un fichier local privé :

```bash
gcloud container clusters get-credentials jitsi-cluster \
  --project=project-fcf2ef91-c005-4910-a10 --zone=europe-west1-b --quiet
```

Cette commande est **préparée, pas exécutée ici**. Elle est l'unique opération
gcloud ajoutée à la whitelist ; commande de création/suppression ou arguments
supplémentaires tels que --log-http restent refusés.

Le kubeconfig dédié est créé exclusivement en 0600 dans RUNNER_TEMP ; un fichier
préexistant ne peut pas être remplacé. En cas d'échec, le fichier partiel est
supprimé. Le nettoyage always() supprime aussi le fichier après le diagnostic,
et le post de l'action auth nettoie ses credentials fédérés. Aucun kubeconfig
opérateur n'est utilisé ou modifié ; aucune clé statique n'est introduite.

Avant whoami, quatre champs ciblés sont lus en mémoire : absence du provider
legacy, exec vers gke-gcloud-auth-plugin, API exec v1/v1beta1 et argument ADC
attendu. Aucun kubeconfig complet, token ou credential n'est affiché. Le seul
statut positif ajouté est EXEC_ADC. Une erreur legacy connue obtient désormais
AUTH_PROVIDER_LEGACY plutôt que INDETERMINE. La présence/format du plugin ne
remplace pas la future validation effective whoami.

#### Tests réellement effectués localement

Sept nouveaux tests vérifient le mode exec ADC, le refus de l'ancien provider,
la lecture sélective sans --raw, les permissions 0600, le refus d'un fichier
existant ou extérieur au répertoire prévu, le nettoyage sur échec, le workflow
OIDC inchangé et la whitelist gcloud. Les fixtures anciennes ont été adaptées
aux contrôles supplémentaires ; aucune opération de génération GKE réelle ou
requête de token n'est utilisée par les tests.

| Validation | Résultat |
|---|---|
| Suite Python | **58 tests réussis** (51 précédents + 7 nouveaux), relancée après ajustement du contexte runner.temp |
| Validation Helm public/local et Terraform sans backend | Réussie |
| Validation edge/Caddyfile | Réussie |
| Syntaxe Python, YAML et blocs Bash | Valide |
| git diff --check et scan des motifs de secrets | Sans erreur / aucun motif sensible détecté |

Les cinq fichiers modifiés sont le workflow diagnostic, le script diagnostic,
les tests, le guide `docs/cd-diagnostic.md` et ce rapport. Les notes locales du
run précédent sont conservées. Le workflow de déploiement CD et le manifeste
RBAC n'ont pas été modifiés.

#### Étapes GitHub encore prévues

Après revue et autorisations distinctes : publier sur branche de correction,
attendre CI, intégrer sur main avec GKE_CD_ENABLED inactive, attendre CI main et
CD skipped, puis relever le **nouveau SHA** et autoriser un seul diagnostic
manuel avec confirm_read_only=true. Contrôler alors EXEC_ADC, whoami CONFIRMEE,
RBAC 49, PVC Bound, déchiffrement et comparaison SOPS/KMS, puis nettoyages.
En cas d'échec, aucune relance ou attribution de droit automatique.

Aucun commit, push, merge ou workflow déclenché pendant cette préparation.
Aucune permission, variable de dépôt, ressource GCP/Kubernetes ou release Helm
modifiée ; aucun secret déchiffré réellement. Le workflow CD garde son paramètre
legacy et nécessite une revue séparée avant toute activation. Le succès local
ne démontre pas encore le succès de la correction sur runner GitHub.

## Consolidation pédagogique et contrôles locaux de remise — 16 novembre 2026

### Technologies : utilité, intégration et travail effectué

| Technologie | Utilité et intégration dans ce projet | Manipulation / limite documentée |
|---|---|---|
| GCP | Héberge calcul, réseau, stockage, GKE et KMS dans le projet pédagogique | API et quotas contrôlés lors des étapes autorisées antérieures ; aucune nouvelle vérification distante pendant cette consolidation |
| Terraform | Décrit le cluster GKE et son pool de nœuds dans `terraform/main.tf` | Deux nœuds e2-standard-2, zone europe-west1-b, disques de nœud 30 Go pd-balanced ; init isolé sans backend, fmt et validate réalisés localement |
| État Terraform | Relie les adresses déclaratives aux ressources existantes | État local exclu de Git ; absence de backend distant partagé. Ne pas assimiler validation statique et absence de dérive ; aucun plan/apply réalisé ici |
| GKE / Kubernetes | GKE gère le plan de contrôle ; Kubernetes orchestre les composants et expose les Services | Pods, Services, endpoints et événements ont été contrôlés pendant les étapes précédentes ; disponibilité non réinterrogée ici |
| Conteneurs | Images distinctes pour Web, Prosody, Jicofo, JVB et Caddy | Images et chart déterminent le comportement ; les tests de rendu ne prouvent pas que toutes les images démarrent sur un autre cluster |
| Helm | Assemble les objets Kubernetes et conserve les révisions des releases | Chart applicatif `charts-officiels/jitsi-meet`, complément `charts/jitsi-edge` ; profils public et localhost validés séparément |
| Jitsi | Web sert l’interface ; Prosody assure XMPP/BOSH, Jicofo coordonne les conférences, JVB relaie les médias lorsque sélectionné | Migration antérieure de publicURL vers HTTPS ; essai public manuel à deux confirmé par l’utilisatrice ; route média non instrumentée |
| Caddy / ACME | Termine TLS, renouvelle le certificat et relaie vers les composants privés | Staging puis production ont été validés antérieurement ; profil du domaine en production, défaut générique staging ; ports publics TCP 80/443, sonde interne 8082 |
| Stockage persistant | Conserve données ACME et identité du serveur lors des mises à jour Caddy | PVC indépendant `jitsi-edge-data`, 10 Gi, RWO, standard-rwo observé pd-balanced ; ne pas supprimer pour résoudre un incident |
| DNS / réseau | DuckDNS associe le nom public à l’IP Web fixe ; le LB média reste distinct | Web 34.78.71.58, média 34.62.165.81 UDP 10000 ; pas de modification DNS pendant cette finalisation |
| Git / GitHub Actions CI | Revue par PR et contrôles reproductibles avant intégration | Dernières CI main réussies selon preuves antérieures ; validations locales répétées ci-dessous, sans nouvel appel Actions |
| OIDC / WIF | Échange une identité GitHub temporaire contre l’identité Google CD sans clé statique | Restriction dépôt et refs/heads/main auditée précédemment ; action auth réussie, mais cela ne démontre pas l’authentification Kubernetes |
| Plugin GKE / ADC | Le plugin exec fournit au client Kubernetes des credentials issus de l’identité fédérée | Correctif local : get-credentials ciblé, fichier runner privé exclusif, ADC et métadonnées exec vérifiées sans afficher le kubeconfig |
| IAM / RBAC | IAM autorise lecture du cluster et déchiffrement KMS ; RBAC borne les opérations Kubernetes | Aucun droit modifié ici. Le diagnostic interroge les droits de déploiement sans les exercer ; rôle PVC séparé limité à get sur son nom |
| SOPS / Cloud KMS | SOPS chiffre les valeurs et KMS protège la clé de données | Fichier versionné chiffré ; diagnostic prévoit déchiffrement privé temporaire puis comparaison sans affichage. Étape runner non atteinte lors des deux échecs réels |
| CD | Enchaîner une CI push main approuvée et des préflights avant Helm | Workflow intégré mais flag désactivé ; identité runner et premier déploiement non validés de bout en bout ; aucun essai déclenché ici |

L’architecture et la propriété des ressources figurent dans [architecture.md](architecture.md).
Terraform ne gère pas l’ensemble du projet : WIF/IAM, IP Web et PVC ont des
procédures distinctes. `deletion_protection=false` est un risque de destruction
à traiter dans une évolution autorisée, sans modifier l’infrastructure pendant
la remise. Deux nœuds dans une zone ne constituent pas une preuve de haute
 disponibilité, de reprise après sinistre ou de mise à l’échelle automatique.

### Incident d’authentification et sécurité du correctif

Le run [43959531200](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43959531200)
a confirmé plugin disponible et connexion TCP API, puis échoué sur whoami
avec INDETERMINE. Cela ne tranche pas entre TLS, credentials et autorisations.
La source de l’action get-gke-credentials épinglée montre que
`use_auth_provider=true` génère l’ancien auth-provider gcp ; le client Kubernetes
moderne exige le mécanisme exec. Il s’agit d’une hypothèse étayée par le code,
pas d’une récupération de l’erreur brute du runner.

La correction retire cette action du diagnostic seulement et prépare un
kubeconfig exec ADC privé. Les sorties des outils sont capturées ; les erreurs
publiées sont des catégories fixes. Le fichier est créé exclusivement en 0600,
le chemin est transmis au step suivant, puis nettoyé même en échec. Le guard
continue d’exiger dispatch confirmé, dépôt attendu, main et SHA courant.
Aucune permission GitHub, IAM ou RBAC n’est étendue. Aucun secret n’est déchiffré
pendant les validations de cette consolidation.

Le workflow de déploiement conserve encore l’ancien mode ; il doit être corrigé
séparément après le diagnostic, en tenant compte de son événement workflow_run.
Copier directement la commande diagnostique protégée pour workflow_dispatch
ferait échouer son garde. Les deux mises à jour Helm ne sont pas atomiques
ensemble ; une ConfigMap PUBLIC_URL ne déclenche pas nécessairement les rollouts
Jitsi. Ces limites sont prises en compte dans la procédure et le rollback.

### Validations réellement exécutées pendant cette finalisation

| Contrôle local | Résultat | Portée |
|---|---|---|
| `python3 -B -m unittest discover -s tests -p 'test_*.py'` | 58 tests réussis | Régressions et cas d’authentification simulés, aucune preuve runner supplémentaire |
| `sh scripts/validate.sh` | Réussi | Helm lint strict, rendus publics/localhost, Terraform fmt/init isolé backend=false/validate ; aucun plan ni apply |
| `CADDY_BIN=/tmp/jitsi-remise-caddy/caddy python3 scripts/validate-edge.py` | Réussi | Chart edge, ports/persistance/protections et Caddyfile validés ; aucun serveur démarré |
| `python3 -B scripts/check-docs.py` | Réussi | Liens relatifs et syntaxe des blocs shell ; aucune commande documentaire exécutée, URLs externes contrôlées syntaxiquement seulement |
| `git diff --check` | Réussi | Absence d’erreur d’espacement dans le diff ; ne constitue pas un audit de secrets |

Le validateur documentaire est exécuté de nouveau après les dernières écritures.
Les liens Actions sont des références de preuves antérieures, sans nouvelle
consultation des runs pendant cette session. Actionlint n’est pas installé ;
la réussite locale du parse YAML et des tests ne remplace pas les futures CI.
Les coûts ne sont pas recalculés depuis une facture : nœuds, disques, deux LB,
IPv4, gestion GKE et trafic sont les postes à surveiller. Aucun nouveau coût
cloud n’est engagé ; un montant mensuel actualisé nécessite tarification,
consommation et éventuels crédits réellement observés.

### Remise, soutenance et étapes soumises à accord

La [checklist](checklist-remise.md) sépare livrables disponibles, informations
académiques encore à renseigner et actions distantes restantes. La
[soutenance](soutenance.md) propose 12 minutes, une démonstration en lecture,
les questions techniques et des solutions autorisées si DuckDNS est bloqué.
Aucune capture ou répétition chronométrée n’est présentée comme déjà réalisée.

La [procédure contrôlée](validation-cd-controlee.md) prépare publication du
correctif, CI/revue/fusion, un seul diagnostic manuel autorisé, adaptation CD,
puis premier essai contrôlé et retour arrière aux révisions relevées juste avant.
Le rollback conserve PVC et données ACME ; il ne restaure pas leur contenu.
Aucun commit, push, PR, merge, dispatch, activation CD ou changement de ressources
n’a été effectué pendant cette finalisation locale.

Contrôle final du lot local : 11 fichiers modifiés ou nouveaux, sans mise en
index. Le scan heuristique (clés privées, formats courants de jetons et noms
sensibles) ne relève aucune alerte ; toutes les feuilles applicatives du fichier
SOPS restent chiffrées et les principales exclusions Git sont effectives.
Ce scan ne constitue pas une garantie exhaustive d’absence de secret. Les
syntaxes Python, shell et YAML des workflows ont été contrôlées. Le contrôle
documentaire final couvre 11 documents, 25 liens locaux et 63 blocs shell sans
erreur ; les 35 URLs externes sont vérifiées syntaxiquement, pas par HTTP.
Le brouillon de message/PR et la liste exacte du lot sont préparés dans
`/tmp/jitsi-remise-pr.md` et `/tmp/jitsi-remise-files.txt`, hors index Git ;
ils ne représentent ni commit ni PR publiés.
