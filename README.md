# Jitsi Meet sur GKE — Master 2 DevOps

Déploiement d'une plateforme de visioconférence sur Google Cloud Platform avec
Terraform, Kubernetes et Helm. Caddy fournit HTTPS ; SOPS et Google Cloud KMS
protègent les secrets versionnés. GitHub Actions assure les validations et la
livraison contrôlée.

- **[Lire le rapport final](docs/rapport.md)** : architecture, démarche, résultats et limites.
- [Consulter les archives](docs/archives/README.md) : procédures datées, historiques et supports intermédiaires.

## Architecture

```text
Navigateur -- HTTPS --> LoadBalancer TCP 80/443 --> Caddy --> Web privé
                                                             |
                                                      BOSH /http-bind
                                                             |
                                                          Prosody
                                                        /         \
                                                    Jicofo        JVB
Navigateur -- média UDP 10000 --> LoadBalancer JVB -----------------+
```

Le cluster comporte deux nœuds `e2-standard-2`. Caddy conserve ses données ACME
sur un PVC de 10Gi. Le chart Jitsi communautaire est conservé en version 3.10.0.
Un appel à deux peut utiliser P2P ; le schéma montre le chemin via JVB.

Adresse de démonstration : https://jitsi-meet-m2.duckdns.org.
Les dernières observations documentées datent du 17 novembre 2026 : Jitsi
révision 4, Caddy révision 3. Ce README ne garantit pas le maintien du cluster
après la remise.

## Organisation du dépôt

```text
.github/workflows/             CI et pipelines contrôlés
terraform/                     Cluster, node pool et backend GCS
charts-officiels/jitsi-meet/    Chart applicatif Jitsi
charts/jitsi-edge/              Proxy HTTPS Caddy
charts/jitsi-load-test/         Selenium Grid et Job Malleus
values-gke.yaml                Configuration applicative
values-secrets.sops.yaml       Secrets chiffrés SOPS/KMS
deploy/                        Profils HTTPS et stockage
scripts/                       Validations et opérations contrôlées
tests/load/                    Résultats et profils Malleus/Selenium
tests/chaos/                   Résultats et expérience Web
tests/terraform/               Preuves Terraform, dont une entrée de script
docs/rapport.md                Rapport final unique
docs/archives/                 Documents historiques et intermédiaires
```

Le dossier historique `jitsi/` n'est pas le chart déployé. Les résultats bruts
locaux sous `tests/results/`, les states Terraform et les secrets déchiffrés
restent exclus de Git.

## Vérifications locales

Avec les outils et dépendances du projet installés :

```sh
sh scripts/validate.sh
python3 -m unittest discover -s tests -v
python3 scripts/check-docs.py
```

La validation Terraform utilise une copie isolée sans backend. Ces commandes
ne déploient pas l'infrastructure et ne prouvent pas une visioconférence.

## Résultats et limites

| Élément | État réellement établi |
|---|---|
| CI | Helm, Terraform et 138 tests Python validés sur la base technique livrée |
| CD Helm OIDC/SOPS | Une exécution contrôlée réussie ; flag désormais désactivé |
| Terraform GitHub | Plan readonly réussi ; apply non exécuté, garde limité à un label |
| Malleus/Selenium | Essais historiques, dont vidéo GKE à deux participants |
| Chaos Mesh | Une injection historique ciblant Web, récupération HTTPS mesurée |
| Nouveaux pipelines Malleus/Chaos | Préparés et validés statiquement ; jamais exécutés |

Les preuves détaillées et les liens de runs sont dans le rapport ; les JSON
versionnés restent sous `tests/`. Aucun résultat de haute disponibilité ou de
capacité maximale n'est revendiqué.

Les flags de déploiement restent désactivés. Toute création cloud, activation,
expérience ou fermeture exige une autorisation distincte. Ne jamais publier de
state, de clé JSON, de sauvegarde Helm ou de secret déchiffré. GKE, les VM,
disques, LoadBalancers, snapshots, stockage, trafic et KMS peuvent générer des
frais ; une désinstallation Helm ne supprime pas toutes ces ressources.
