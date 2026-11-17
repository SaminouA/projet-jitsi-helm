# Documentation du projet Jitsi DevOps

Pour l'évaluation, commencer par le rapport, puis la présentation et la grille
de conformité. Les guides expliquent les manipulations ; les archives gardent
les états intermédiaires sans constituer une procédure actuelle à rejouer.

## Documents principaux

- [Rapport final unique](rapport.md)
- [Présentation orale principale](presentation-finale.md)
- [Architecture de référence](architecture.md)
- [Conformité et limites](livraison/conformite-finale.md)
- [Checklist de remise](livraison/checklist-remise.md)
- [Index des preuves et runs](preuves/preuves-livraison.md)

## Guides techniques

Ces documents restent datés de leur phase. Ils distinguent opérations réalisées
et préparations. Leurs commandes de mutation exigent une autorisation distincte.

| Guide | Sujet |
|---|---|
| [bootstrap-https-court.md](guides/bootstrap-https-court.md) | Bootstrap HTTPS historique : séquence et contrôles |
| [cd-diagnostic.md](guides/cd-diagnostic.md) | Diagnostic OIDC/GKE et authentification |
| [chaos-web-controle.md](guides/chaos-web-controle.md) | Expérience Chaos Web historique et garde-fous |
| [https-duckdns.md](guides/https-duckdns.md) | HTTPS, DNS DuckDNS et TLS |
| [jitsi-public-edge.md](guides/jitsi-public-edge.md) | Préparation du profil public Caddy |
| [malleus-selenium.md](guides/malleus-selenium.md) | Essais Malleus/Selenium natifs |
| [malleus-video-docker.md](guides/malleus-video-docker.md) | Vidéo synthétique et images Docker |
| [pipelines-experiences-controlees.md](guides/pipelines-experiences-controlees.md) | Pipelines manuels préparés, non exécutés |
| [selenium-helm-validation.md](guides/selenium-helm-validation.md) | Images Selenium et validation Helm |
| [terraform-cd-controlee.md](guides/terraform-cd-controlee.md) | Conception du pipeline Terraform contrôlé |
| [terraform-plan-apply-validation.md](guides/terraform-plan-apply-validation.md) | Plan exact et revue humaine avant apply |
| [test-video-helm-2x90.md](guides/test-video-helm-2x90.md) | Essais vidéo Kubernetes et profil CPU |

## Preuves et livraison

Les synthèses JSON expurgées sont regroupées dans `preuves/` et référencées
par l'[index des preuves](preuves/preuves-livraison.md). Les résultats Malleus
et Chaos restent dans leurs chemins sources sous `tests/load/` et `tests/chaos/`.
Les collectes brutes ignorées ne sont pas déplacées ou publiées.

La [validation CD historique](livraison/validation-cd-controlee.md) décrit
l'exécution réellement réussie. La [revue de réorganisation](livraison/reorganisation-documentaire.md)
explique la comparaison des documents et donne tous les déplacements.
Les nouveaux pipelines Malleus/Chaos et l'apply Terraform GitHub restent non exécutés.

## Historiques

Consulter l'[index des archives](archives/README.md) pour les deux rapports
antérieurs, l'ancien support oral et les audits datés. Aucune archive n'a été
supprimée. Un ancien échec ou une étape encore « prévue » décrit son époque,
pas nécessairement l'état final expliqué dans le rapport principal.
