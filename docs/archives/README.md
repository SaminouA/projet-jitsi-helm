# Archives du projet

Le seul document principal est le [rapport final](../rapport.md).
La présentation, les procédures et les bilans ci-dessous sont conservés comme
supports historiques ou complémentaires. Ils ne constituent pas des instructions
à exécuter sans vérifier leur date, les ressources présentes et l'autorisation.
Les statuts successifs restent dans leur contexte ; aucun résultat n'est effacé.

## Rapports et supports

- [Rapport avant refonte du 15 novembre](rapport-avant-refonte-2026-11-15.md)
- [Journal avant consolidation du 17 novembre](rapport-avant-livraison-finale-2026-11-17.md)
- [Présentation finale archivée](presentation-finale.md)
- [Ancien support de soutenance](soutenance-2026-11-16.md)
- [Architecture de référence archivée](architecture-reference-2026-11-17.md)
- [Ancienne architecture du 16 novembre](architecture-2026-11-16.md)

## Autres documents conservés

- [bootstrap-https-court.md](bootstrap-https-court.md)
- [cd-diagnostic.md](cd-diagnostic.md)
- [chaos-web-controle.md](chaos-web-controle.md)
- [checklist-remise.md](checklist-remise.md)
- [conformite-finale.md](conformite-finale.md)
- [https-duckdns.md](https-duckdns.md)
- [index-avant-simplification.md](index-avant-simplification.md)
- [jitsi-public-edge.md](jitsi-public-edge.md)
- [malleus-selenium.md](malleus-selenium.md)
- [malleus-video-docker.md](malleus-video-docker.md)
- [pipelines-experiences-controlees.md](pipelines-experiences-controlees.md)
- [preuves-livraison.md](preuves-livraison.md)
- [readme-avant-simplification.md](readme-avant-simplification.md)
- [reorganisation-documentaire.md](reorganisation-documentaire.md)
- [revue-integration-pr7-pr13.md](revue-integration-pr7-pr13.md)
- [selenium-helm-validation.md](selenium-helm-validation.md)
- [sommaire-avant-simplification.md](sommaire-avant-simplification.md)
- [terraform-cd-controlee.md](terraform-cd-controlee.md)
- [terraform-plan-apply-validation.md](terraform-plan-apply-validation.md)
- [terraform-prerequis-audit.md](terraform-prerequis-audit.md)
- [test-video-helm-2x90.md](test-video-helm-2x90.md)
- [validation-cd-controlee.md](validation-cd-controlee.md)
- [validation-remise-2026-11-16.md](validation-remise-2026-11-16.md)

## Résultats techniques

Les JSON sont conservés sans modification dans `tests/terraform/`, `tests/load/`
et `tests/chaos/` à la racine du dépôt. Le script de vérification OIDC lit
`tests/terraform/terraform-bootstrap-resultats.json` ; son chemin a été adapté
et validé. Les collectes brutes ignorées n'ont pas été déplacées ou publiées.

La première proposition d'organisation de la PR nº 16 reste dans
[reorganisation-documentaire.md](reorganisation-documentaire.md), avec ses arbres
et chemins de l'époque. La présente simplification la remplace : aucun dossier
`guides/`, `preuves/` ou `livraison/` ne reste à la racine de `docs/`.
Les anciens chemins cités dans les transcriptions ou les tableaux historiques
ne sont pas des dépendances exécutables. Les liens de navigation ont été actualisés.
