# Trame de soutenance — Jitsi sur GKE

Support préparé le 16 novembre 2026. Prévoir environ dix minutes, puis démonstration
si les conditions réseau et les participants le permettent.

| Diapositive | Message à présenter | Preuve / limite |
|---|---|---|
| 1. Problématique | Rendre une plateforme de visioconférence reproductible et contrôlable | Démonstration académique, pas de SLA |
| 2. Architecture actuelle | Navigateur HTTPS → LB TCP 80/443 → Caddy → Web → BOSH/Prosody ; Jicofo orchestre ; JVB exposé séparément sur UDP 10000 | HTTPS production vérifié ; réunion à deux confirmée manuellement, trajet JVB/P2P non instrumenté |
| 3. Terraform et GKE | Déclaration réseau/cluster/nœuds ; état à préserver ; deux nœuds Ready | `terraform/main.tf`, validation sans backend ; aucun apply durant la remise |
| 4. Helm | Chart Jitsi officiel versionné, valeurs GKE, installation en deux phases pour l'IP JVB | Release jitsi révision 3, chart 3.10.0 ; ancien dossier jitsi distinct |
| 5. Secrets SOPS/KMS | Valeurs chiffrées dans Git ; déchiffrement temporaire privé et nettoyage | IAM KMS relu ; pas de secret affiché ni de rotation |
| 6. GitHub Actions | CI Helm/Terraform et tests Python ; PR vers main | Deux CI vertes sur c591ad4 ; adaptations suivantes testées localement, pas encore poussées ; ruleset PR et Validation Helm requis |
| 7. OIDC et CD | Jeton GitHub → WIF limité au dépôt/main → compte de déploiement → GKE/KMS | Configuration IAM présente ; premier échange runner non validé, CD désactivée |
| 8. HTTPS déployé | Domaine DuckDNS → 34.78.71.58 → Caddy ; certificat Let’s Encrypt production et PVC 10Gi | Caddy révision 2, chaîne TLS et routes vérifiées ; renouvellement futur non testé |
| 9. Tests et résultats | Tests statiques, HTTPS et réunion jitsitest à deux : ordinateur/téléphone, audio/vidéo bidirectionnels | Réunion manuelle confirmée par l’utilisatrice ; aucun test de partage d’écran ni de charge revendiqué pour cet essai |
| 10. Coûts et limites | GKE/nœuds, LB JVB existants ; HTTPS ajoute disque, réseau/IP/LB selon tarification | Bootstrap IP/LB/PVC autorisé et réalisé ; aucun total mensuel réel vérifié |
| 11. Suite | Revue/CI, autorisations distinctes merge/CD, premier OIDC, instrumentation JVB à trois participants | Ne pas confondre préparation, déploiement et validation utilisateur |

Pour la démonstration, montrer la PR et ses checks, `helm list -n jitsi`,
`kubectl -n jitsi get pods,svc,endpointslices`, puis l’accès public `https://jitsi-meet-m2.duckdns.org`.
Ne jamais afficher `helm get values`, les Secrets, l'état Terraform ou des jetons.
Les preuves de collecte restent locales sous `tests/results/` ; préparer seulement
un extrait de compteurs agrégés si nécessaire, sans données de session.

Questions probables : pourquoi trois participants (distinguer JVB/P2P) ? Pourquoi
SOPS et KMS (chiffrement versionnable et autorisation centralisée) ? Pourquoi OIDC
(éviter une clé privée permanente) ? Pourquoi Caddy (TLS automatique, mais stockage
et coût réseau supplémentaires) ? Que démontre la CI (cohérence statique), et que
reste-t-il à démontrer (runner OIDC, transport JVB instrumenté à trois participants et renouvellement TLS) ?


## Test manuel confirmé par l'utilisatrice

Résultats communiqués le 16 novembre 2026 : salle **jitsitest**, accessible à
`https://jitsi-meet-m2.duckdns.org/jitsitest`. Deux participants se sont connectés
simultanément depuis un ordinateur et un téléphone. L'utilisatrice confirme
l'audio fonctionnel et la vidéo visible dans les deux sens, ainsi que l'accès
HTTPS public fonctionnel. L'agent n'a pas observé directement cette réunion.

À expliquer au jury : c'est une validation fonctionnelle manuelle de ce scénario
à deux participants. Elle n'identifie pas le trajet média P2P/JVB et ne constitue
pas un test de capacité. Aucun test de partage d'écran ni de charge n'est
revendiqué pour cet essai. Les résultats historiques du 15 novembre restent
séparés ; aucune mesure supplémentaire n'est déduite du retour utilisatrice.


## Validation locale avant publication

Le validateur accepte le profil localhost et le profil HTTPS edge, avec maintien
des contrôles BOSH/Web privé/JVB. Le 16 novembre 2026, les **31 tests Python**,
les lint/rendus Helm (dont une régression explicite localhost), la validation du
Caddyfile et Terraform sans backend réussissent localement. Les workflows de
CD restent inchangés. Ces changements ne sont ni committés ni poussés à ce stade :
aucune nouvelle CI distante n'est présentée comme exécutée.
