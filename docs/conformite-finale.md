# Conformité finale — 17 novembre 2026

Le barème officiel du professeur n'est pas présent dans le dépôt. Ce tableau
rapproche les exigences techniques communiquées pendant le projet des preuves
conservées ; il ne remplace pas une grille officielle signée.

| Critère | État | Preuve | Limite ou travail restant |
|---|---|---|---|
| Infrastructure GCP/GKE déclarative | Validé historiquement | `terraform/main.tf`, migration GCS, plan readonly GitHub | Aucun apply GitHub ; prochain plan peut inclure le label de preuve |
| Backend distant et identité sans clé | Validé pour readonly | `terraform-migration-resultats.json`, `terraform-github-plan-final.json` | Droits apply plus larges ; revue du plan indispensable |
| Terraform plan/apply contrôlé | Préparé, partiel | PR 7, `terraform-gke.yml`, tests de garde | Environnement de revue et secret de transport manquants ; apply jamais exécuté |
| Conteneurisation et Helm | Validé | Chart Jitsi 3.10.0, charts edge/test, Dockerfiles Malleus/Selenium | Pas de reconstruction des images Jitsi amont |
| HTTPS public et réseau | Validé historiquement | Guide HTTPS, profils DuckDNS, observations du rapport | Deux LB facturables ; pas de HA ni de TURN validé |
| Secrets SOPS/KMS | Validé | Fichier chiffré, correspondance locale, CD Helm réussie | Rotation et restauration complète non testées |
| CI GitHub Actions | Validé | Run 44167828378 ; job obligatoire Validation Helm | Ne prouve pas le succès des pipelines manuels |
| CD Helm OIDC | Validé historiquement | Run 44057014445 ; révisions 4 et 3 | Flag désactivé, pas de nouvelle exécution pour la remise |
| Réunion fonctionnelle | Validé dans les scénarios observés | Tests manuels à deux puis trois ; diagnostic JVB | Pas de validation exhaustive de tous les réseaux et flux |
| Mesure de référence et palier 3 | Validé, portée limitée | [Synthèse recalculée](preuve-repos-palier-2026-11-15.json) | 120/300 secondes, répétitions Metrics Server, pas de capacité maximale |
| Charge vidéo Malleus/Selenium GKE | Validé historiquement à deux | `tests/load/k8s-video-low-cpu-results.json` | Fenêtre stricte 56,35 s ; pas 90 s continues ni HD garantie |
| Pipeline Malleus dédié | Préparé, non exécuté | PR 13/14, `malleus-controlled.yml` | Identité/environnement dédiés à finaliser ; aucune exécution réelle |
| Résilience Chaos Mesh Web | Validé historiquement | `tests/chaos/results-summary.json` | Une injection ; HTTPS indisponible temporairement ; aucune réunion active |
| Pipeline Chaos dédié | Préparé, non exécuté | PR 13/14, `chaos-controlled.yml` | Même réserve d'identité/environnement ; aucune nouvelle expérience |
| Observabilité | Partielle | Collecteur, métriques, JVB, logs, JSON expurgés | Pas de tableaux de bord corrélés ni de seuil de capacité démontré |
| Documentation et reproductibilité | Préparé pour revue | Rapport, guides, sources, index et plan oral | Identité académique, captures réelles, export et relecture finale |

Les liens exécutables, SHA et statuts sont regroupés dans l'[index des preuves](preuves-livraison.md).
Le [rapport](rapport.md) explique les résultats et les limites de chaque essai.

La livraison documentaire est recommandée en l'état avec ces réserves visibles.
Si le professeur exige un apply automatisé réellement exécuté ou les pipelines
expérimentaux exécutés depuis GitHub, ces critères restent incomplets. Leur
validation demande une autorisation distincte et ne doit pas être simulée.
