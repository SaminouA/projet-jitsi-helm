# Documentation du projet Jitsi DevOps

Pour l'évaluation, commencer par le rapport, puis la présentation et la grille
de conformité. Les guides expliquent les manipulations ; les archives gardent
les états intermédiaires sans constituer une procédure actuelle à rejouer.

## Documents principaux

- [Rapport final unique](../rapport.md)
- [Présentation orale principale](presentation-finale.md)
- [Architecture de référence](architecture-reference-2026-11-17.md)
- [Conformité et limites](conformite-finale.md)
- [Checklist de remise](checklist-remise.md)
- [Index des preuves et runs](preuves-livraison.md)

## Guides techniques

Ces documents restent datés de leur phase. Ils distinguent opérations réalisées
et préparations. Leurs commandes de mutation exigent une autorisation distincte.

| Guide | Sujet |
|---|---|
| [bootstrap-https-court.md](bootstrap-https-court.md) | Bootstrap HTTPS historique : séquence et contrôles |
| [cd-diagnostic.md](cd-diagnostic.md) | Diagnostic OIDC/GKE et authentification |
| [chaos-web-controle.md](chaos-web-controle.md) | Expérience Chaos Web historique et garde-fous |
| [https-duckdns.md](https-duckdns.md) | HTTPS, DNS DuckDNS et TLS |
| [jitsi-public-edge.md](jitsi-public-edge.md) | Préparation du profil public Caddy |
| [malleus-selenium.md](malleus-selenium.md) | Essais Malleus/Selenium natifs |
| [malleus-video-docker.md](malleus-video-docker.md) | Vidéo synthétique et images Docker |
| [pipelines-experiences-controlees.md](pipelines-experiences-controlees.md) | Pipelines manuels préparés, non exécutés |
| [selenium-helm-validation.md](selenium-helm-validation.md) | Images Selenium et validation Helm |
| [terraform-cd-controlee.md](terraform-cd-controlee.md) | Conception du pipeline Terraform contrôlé |
| [terraform-plan-apply-validation.md](terraform-plan-apply-validation.md) | Plan exact et revue humaine avant apply |
| [test-video-helm-2x90.md](test-video-helm-2x90.md) | Essais vidéo Kubernetes et profil CPU |

## Preuves et livraison

Les synthèses JSON expurgées sont regroupées dans `preuves/` et référencées
par l'[index des preuves](preuves-livraison.md). Les résultats Malleus
et Chaos restent dans leurs chemins sources sous `tests/load/` et `tests/chaos/`.
Les collectes brutes ignorées ne sont pas déplacées ou publiées.

La [validation CD historique](validation-cd-controlee.md) décrit
l'exécution réellement réussie. La [revue de réorganisation](reorganisation-documentaire.md)
explique la comparaison des documents et donne tous les déplacements.
Les nouveaux pipelines Malleus/Chaos et l'apply Terraform GitHub restent non exécutés.

## Historiques

Consulter l'[index des archives](index-avant-simplification.md) pour les deux rapports
antérieurs, l'ancien support oral et les audits datés. Aucune archive n'a été
supprimée. Un ancien échec ou une étape encore « prévue » décrit son époque,
pas nécessairement l'état final expliqué dans le rapport principal.
