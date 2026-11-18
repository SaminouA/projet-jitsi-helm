# Déploiement, automatisation, sécurisation et supervision de Jitsi Meet sur Google Cloud Platform

## 1. Objectifs

Déployer un service Jitsi Meet accessible en HTTPS sur GKE, puis rendre sa
configuration reproductible et ses changements contrôlables depuis GitHub.
Le projet devait aussi démontrer une charge vidéo synthétique, la reconstruction
du pod Web après une panne injectée et l'observation de la plateforme.

Les neuf critères de la grille sont documentés en section 5. Les résultats
principaux sont le déploiement Helm réussi, un Plan et un Apply Terraform
protégés, les deux pipelines d'expérimentation réussis et la collecte JVB
vérifiée dans Managed Prometheus.

## 2. Architecture et choix techniques

```mermaid
flowchart LR
    N[Navigateurs] -->|HTTPS 443| L[LoadBalancer Web]
    L --> C[Caddy]
    C --> W[Service Web privé]
    W -->|BOSH| P[Prosody]
    J[Jicofo] --> P
    V[JVB] --> P
    N -.->|Média UDP 10000| U[LoadBalancer JVB]
    U --> V
    C --> D[PVC ACME]
    V -->|Métriques internes| M[Managed Prometheus]
    M --> G[Grafana local]
```

Le cluster GKE comporte deux nœuds. Caddy termine TLS et conserve les données
ACME sur un volume persistant. Prosody assure la signalisation, Jicofo
coordonne les conférences et JVB relaie les médias lorsqu'il est utilisé.
Le namespace `jitsi-load-test` accueille les ressources temporaires de charge.

| Technologie | Rôle et raison du choix |
|---|---|
| Terraform et GCS | Déclarer le cluster et son pool, centraliser l'état et vérifier les changements avant application. |
| Kubernetes et Helm | Déployer Jitsi et Caddy de façon reproductible et isoler le cycle de vie de la charge. |
| Caddy et DuckDNS | Fournir un point d'accès HTTPS avec renouvellement ACME et un nom de démonstration stable. |
| GitHub Actions et OIDC | Automatiser les contrôles avec des identifiants temporaires et des approbations pour les opérations sensibles. |
| SOPS et Cloud KMS | Versionner les mots de passe XMPP chiffrés et les déchiffrer lors du déploiement autorisé. |
| Selenium, Malleus et Chaos Mesh | Générer des participants, observer la vidéo et injecter une faute ciblée. |
| Cloud Monitoring, Managed Prometheus et Grafana | Réutiliser la collecte GKE et visualiser l'infrastructure, la disponibilité des pods et l'activité JVB. |

## 3. Étapes de réalisation

1. **Provisionnement.** Définition du cluster et du pool dans Terraform, puis
   migration de l'état vers GCS. La CI valide les configurations.
2. **Déploiement.** Validation du profil local, puis mise en service de Jitsi
   derrière Caddy. Le pipeline Helm protégé utilise OIDC et SOPS/KMS.
3. **Expérimentations.** Validation manuelle approuvée du scénario Chaos Web avec
   le manifeste PodChaos, puis exécution de Malleus. Chaque workflow
   publie les observations et nettoie ses ressources temporaires.
4. **Validation Terraform.** La preuve d'Apply a ajouté uniquement le label
   GKE `devops-apply-proof=github-actions`. Le plan exact a été contrôlé par
   empreinte et approuvé. Aucun nœud ou cluster n'a été créé, détruit ou
   remplacé. Après l'Apply, les deux nœuds étaient prêts, les cinq pods Jitsi
   avaient les mêmes UID et aucun redémarrage, et HTTPS répondait 200.
   `TF_CD_ENABLED` est désactivé au dépôt et dans l'environnement protégé.
   Le Plan nº 8 confirme zéro changement et un état GCS inchangé.
5. **Supervision.** Un PodMonitoring cible les métriques internes JVB sur 8080.
   Grafana interroge Managed Prometheus en PromQL. Le [guide de supervision](../monitoring/README.md) décrit la collecte et la source de données.

## 4. Résultats, difficultés et limites

| Sujet | Résultat et limite |
|---|---|
| Malleus | Le run nº 8 configure deux participants et 90 s. Le Job termine en 2 min 58 s, démarrage et fin compris. Trois relevés sur 49,1 s montrent deux endpoints actifs et des échanges vidéo dans les deux sens. La continuité vidéo sur 90 s n'a pas été mesurée. Les cinq pods Jitsi restent stables. Le chart de charge est nettoyé. |
| Chaos Mesh | Une suppression ciblée du Web. Le nouveau pod possède un UID différent et revient Ready, tandis que les quatre autres gardent leurs UID. Le PodChaos est nettoyé. Aucune réunion active n'a été soumise à cette faute. |
| Monitoring | Deux collecteurs Managed Prometheus prêts, scrape et santé JVB à 1. Les 19 requêtes des 14 panneaux ont renvoyé des séries. Grafana OSS est actif sur la VM pour les captures. Le débit JVB représente le RTP/RTCP agrégé. La preuve vidéo seule vient des navigateurs Malleus. |
| Réseau de charge | Namespace dédié et Selenium en ClusterIP sans IP externe. Aucun filtrage inter-namespace par NetworkPolicy n'a été démontré. La grille ne stipule pas ce filtrage. |

| Difficulté | Solution vérifiée |
|---|---|
| Passage de localhost à HTTPS | Profil public explicite, terminaison TLS Caddy et stockage ACME persistant. |
| Erreur d'autorisation du runner Chaos | Interrogation de SelfSubjectAccessReview avec l'identité effective. Les refus motivés et les erreurs d'évaluation sont traités distinctement. |
| Droits trop larges du contrôleur Chaos | Retrait du droit `pods/exec` inutile. La suppression reste limitée au seul nom du Web approuvé. |
| Première exécution Malleus interrompue | Retrait de la dépendance aux métriques des pods fraîchement créés. Le suivi du Job, la capacité des nœuds et la preuve vidéo ont été conservés. |
| Plan Terraform refusé en mode lecture seule | Ce mode exige un plan sans action. Le label a été appliqué via le mode protégé prévu pour ce changement, puis la convergence a été vérifiée séparément. |

Les tests couvrent les scénarios observés. La capacité maximale, la haute
disponibilité, TURN et la continuité d'une conférence pendant Chaos restent à
évaluer. Les relevés avant et après attestent l'état des composants à ces
instants. Les résultats vidéo sont échantillonnés et les débits ne constituent
pas une garantie de service.

## 5. Grille d'évaluation

| Nº | Critère | Résultat et preuve |
|---:|---|---|
| 1 | Chart Helm Jitsi | Validé. [Chart](../charts-officiels/jitsi-meet/Chart.yaml). |
| 2 | Chart Helm jitsi-meet-torture | Validé sous le nom [jitsi-load-test](../charts/jitsi-load-test/Chart.yaml). Il fournit Deployment et Service Selenium ainsi que le Job Malleus. |
| 3 | Code Terraform | Validé. [Cluster et pool](../terraform/main.tf), état distant GCS. |
| 4 | Secrets gérés par SOPS ou OpenBao | SOPS/KMS. [Valeurs chiffrées](../values-secrets.sops.yaml) et utilisation validée par le run Helm. Le contrôle ciblé ne couvre pas exhaustivement l'historique Git. |
| 5 | Dépôt organisé et documenté | [README](../README.md), [index documentaire](README.md), rapport et preuves. |
| 6 | Déploiement Helm ou ArgoCD passant | Voie Helm validée avec SOPS/KMS et OIDC. [Run 44057014445](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44057014445). |
| 7 | Provisionnement infra passant | [Plan et Apply nº 7](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44292386368) réussis. [Convergence nº 8](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44293963177) à zéro changement. |
| 8 | Pipeline Malleus dédié et passant | [Run nº 8](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44284381205) réussi. |
| 9 | Pipeline Chaos Mesh dédié et passant | [Run 44282191029](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44282191029) réussi. |

## 6. Conclusion et perspectives

Le projet a livré Jitsi sur GKE avec HTTPS, déploiement contrôlé et secrets
chiffrés. Les pipelines validés attestent la convergence Terraform, une charge
vidéo à deux participants et la reconstruction du Web après suppression.
Le monitoring fournit des mesures réelles pour étudier ces scénarios.

Le **bonus proposé par le professeur** reste une perspective **non réalisée**.
Il consisterait à déployer une architecture multicloud actif/passif, à gérer
le DNS Cloudflare avec Terraform et à sélectionner le fournisseur actif via
une variable du pipeline. Il resterait à tester le basculement et la reprise.

## 7. Preuves de validation

Les résultats expurgés ci-dessous sont versionnés dans ce rapport. Ils restent
consultables lorsque les artefacts temporaires de GitHub Actions expirent.
Les liens vers les runs attestent l'exécution. Les synthèses historiques
versionnées documentent des essais antérieurs distincts.

| Validation | Résultat conservé | Référence |
|---|---|---|
| Helm | Workflow réussi. Jitsi et Caddy déployés, avec déchiffrement SOPS/KMS et authentification OIDC. | [Run Helm](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44057014445) |
| Terraform Apply | Une modification sur place du cluster, ajout de `devops-apply-proof=github-actions`. Pool inchangé. Zéro création, destruction ou remplacement. Le plan exact a été approuvé. | [Run nº 7](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44292386368) |
| Terraform Convergence | Zéro création, modification, destruction ou remplacement. État distant GCS inchangé. | [Run nº 8](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44293963177) |
| Malleus | Job réussi et nettoyé. Deux participants et trois échantillons vidéo validés. | [Run nº 8](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44284381205) · [Synthèse historique](../tests/load/k8s-video-low-cpu-results.json) |
| Chaos Mesh | Une injection confirmée, remplacement du Web par un nouvel UID, retour à l'état Ready et nettoyage. | [Run Chaos](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44282191029) · [YAML](../tests/chaos/podchaos-web-once.yaml) · [Synthèse historique](../tests/chaos/results-summary.json) |
| Monitoring | Deux collecteurs prêts, collecte et santé JVB à 1. Les 19 requêtes des 14 panneaux ont renvoyé des séries. | [Configuration de la supervision](../monitoring/README.md) |

### Capture Grafana

![Quatre panneaux Grafana montrant le CPU et la mémoire des nœuds GKE et des pods Jitsi](images/grafana-cpu-memoire.png)

**Figure 1 — CPU et mémoire des deux nœuds GKE et des pods Jitsi, le 18 novembre 2026 sur une fenêtre de 30 minutes.** Le CPU du Jitsi Videobridge monte à environ 0,20 cœur et celui de l’un des nœuds atteint environ 0,43 cœur sur la même période. La mémoire des deux nœuds varie peu, autour de 2,3 et 3 Gio. Ces observations décrivent la fenêtre affichée.

Les ressources GCP maintenues pour la démonstration peuvent générer des coûts.
Elles comprennent le cluster et ses deux nœuds, la VM de travail, les disques
dont le PVC ACME, les load balancers et adresses publiques, GCS, KMS, le trafic,
les logs et l'ingestion Managed Prometheus. Aucun montant de facture n'a été vérifié.
