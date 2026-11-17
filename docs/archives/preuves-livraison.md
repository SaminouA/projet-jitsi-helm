# Index des preuves de livraison

Consolidation du 17 novembre 2026, sur la base technique
`23cb73d656015bbc71f16bb58abf308cb78d0fca`. Une réussite GitHub est qualifiée
selon son contenu : build, validation, plan et déploiement sont des preuves différentes.

| Preuve | Source | Ce qu'elle établit |
|---|---|---|
| CI finale main | [44167828378](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44167828378) | Validation Helm/Terraform/Python, pas de test média |
| CD après fusion | [44167893494](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44167893494) | Skipped : aucune nouvelle opération Helm |
| Plan Terraform readonly | [44116737677](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44116737677), [synthèse](../../tests/terraform/terraform-github-plan-final.json) | Plan sans changement sur son SHA ; aucun apply |
| Diagnostic runner Helm | [44053382824](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44053382824) | Identité Kubernetes et contrôles d'autorisation réussis |
| CD Helm contrôlée | [44057014445](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44057014445), [procédure et résultat](validation-cd-controlee.md) | Déploiement réel, révisions Jitsi 4 et edge 3 |
| Image Selenium corrigée | [44094388902](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44094388902), [résultat](../../tests/load/selenium-image-results.json) | Capture synthétique dans Chrome ; pas une conférence |
| Image Malleus | [44097184022](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44097184022), [résultat](../../tests/load/malleus-image-results.json) | Build et contrôle d'exécution ; pas une charge GKE |
| Référence/palier | [Synthèse recalculée](../../tests/load/preuve-repos-palier-2026-11-15.json) | Agrégats issus des collectes locales du 15 novembre |
| Vidéo GKE initiale | [Résultat expurgé](../../tests/load/k8s-video-results.json) | Arrêt de sécurité pour saturation, pas une réussite |
| Vidéo GKE low CPU | [Résultat expurgé](../../tests/load/k8s-video-low-cpu-results.json) | Test terminé, RTP reçu et décodé par deux clients |
| Chaos Web | [Résultat expurgé](../../tests/chaos/results-summary.json) | Une injection, remplacement du pod et récupération HTTPS |
| Intégration Terraform | [PR 7](https://github.com/SaminouA/projet-jitsi-helm/pull/7) | Workflow contrôlé intégré ; apply non exécuté |
| Intégration expériences | [PR 13](https://github.com/SaminouA/projet-jitsi-helm/pull/13) | Pipelines manuels intégrés ; pas de nouvelle expérience |
| Correction expressions Actions | [PR 14](https://github.com/SaminouA/projet-jitsi-helm/pull/14) | Initialisation KUBECONFIG corrigée ; reconnaissance GitHub |

Les runs invalides 44164624972 et 44164627481 ont échoué avant tout job : ils
ne constituent pas des tests Malleus/Chaos échoués sur le cluster. La correction
est validée syntaxiquement ; aucun lancement manuel n'est revendiqué.

Les JSON versionnés sont des synthèses expurgées, pas des traces exhaustives.
Les collectes brutes locales et les états Terraform sont volontairement exclus
de Git. Les témoignages fonctionnels de l'utilisatrice sont signalés comme tels
dans le [rapport](../rapport.md), sans capture inventée ni mesure reconstituée.
Le [journal conservé](rapport-avant-livraison-finale-2026-11-17.md)
permet de retrouver les commandes et incidents antérieurs ; ses statuts sont historiques.

## Contrôles de cette consolidation

Les liens locaux ont été vérifiés, y compris ceux de l'archive (161 références,
aucune cible absente). Les 19 URL de runs et les quatre PR distinctes citées
ont été interrogées en lecture seule via l'API GitHub : elles existent et leurs
statuts correspondent aux qualifications ci-dessus. Le lien d'historique de
branche a aussi été vérifié par résolution de sa référence GitHub.
Les autres liens externes de documentation ne sont pas certifiés disponibles
par le contrôleur local, qui ne vérifie que leur syntaxe.

Le contrôle documentaire du dépôt valide 24 documents de premier niveau,
111 liens locaux et la syntaxe de 57 blocs shell, sans exécuter ces procédures.
Le rapport initial est conservé intégralement dans l'archive, hors adaptation
des liens relatifs ; son SHA-256 d'origine est
`58e24b2ef45095da7f6300a3ebee67bd2c358ab7fa9f992843535a5fcd2988d0`.
Le contrôle des signatures de secrets n'a détecté aucune clé privée ni aucun
jeton dans les fichiers documentaires destinés à cette PR. Il ne remplace pas
les exclusions Git ni la revue humaine des données.


Les chiffres de contrôle ci-dessus décrivent la consolidation de la PR nº 15.
Après déplacement des documents, consulter la
[revue de réorganisation](reorganisation-documentaire.md) pour le
nouveau périmètre récursif, les correspondances de chemins et les validations locales.
