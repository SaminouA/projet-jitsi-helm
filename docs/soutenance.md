# Trame de soutenance — Jitsi sur GKE

Support préparé le 16 novembre 2026. Prévoir environ dix minutes, puis démonstration
si les conditions réseau et les participants le permettent.

| Diapositive | Message à présenter | Preuve / limite |
|---|---|---|
| 1. Problématique | Rendre une plateforme de visioconférence reproductible et contrôlable | Démonstration académique, pas de SLA |
| 2. Architecture actuelle | Navigateur → port-forward → Web → BOSH/Prosody ; Jicofo orchestre ; JVB reçoit les médias sur UDP 10000 public | Quatre pods Ready observés ; pas de HTTPS public déployé |
| 3. Terraform et GKE | Déclaration réseau/cluster/nœuds ; état à préserver ; deux nœuds Ready | `terraform/main.tf`, validation sans backend ; aucun apply durant la remise |
| 4. Helm | Chart Jitsi officiel versionné, valeurs GKE, installation en deux phases pour l'IP JVB | Release jitsi révision 2, chart 3.10.0 ; ancien dossier jitsi distinct |
| 5. Secrets SOPS/KMS | Valeurs chiffrées dans Git ; déchiffrement temporaire privé et nettoyage | IAM KMS relu ; pas de secret affiché ni de rotation |
| 6. GitHub Actions | CI Helm/Terraform et tests Python ; PR vers main | CI verte sur f3a5aef ; protection de branche non constatée |
| 7. OIDC et CD | Jeton GitHub → WIF limité au dépôt/main → compte de déploiement → GKE/KMS | Configuration IAM présente ; premier échange runner non validé, CD désactivée |
| 8. HTTPS préparé | Internet → LB TCP 80/443 → Caddy → Web ; JVB UDP séparé ; ACME persistant | Chart/Caddyfile validés localement ; domaine, budget, droits PVC et bootstrap manquants |
| 9. Tests et résultats | 25 tests Python, HTTP 200 sur trois routes, collecte JVB saine au repos | Aucun nouveau résultat de réunion/charge ; résultats du 15 novembre identifiés comme historiques |
| 10. Coûts et limites | GKE/nœuds, LB JVB existants ; HTTPS ajoute disque, réseau/IP/LB selon tarification | Aucun total mensuel vérifié ; pas de création payante autorisée |
| 11. Suite | Revue/CI, autorisations distinctes merge/CD, premier OIDC, puis HTTPS et réunion bornée | Ne pas confondre préparation, déploiement et validation utilisateur |

Pour la démonstration, montrer la PR et ses checks, `helm list -n jitsi`,
`kubectl -n jitsi get pods,svc,endpointslices`, puis le Web par tunnel local.
Ne jamais afficher `helm get values`, les Secrets, l'état Terraform ou des jetons.
Les preuves de collecte restent locales sous `tests/results/` ; préparer seulement
un extrait de compteurs agrégés si nécessaire, sans données de session.

Questions probables : pourquoi trois participants (distinguer JVB/P2P) ? Pourquoi
SOPS et KMS (chiffrement versionnable et autorisation centralisée) ? Pourquoi OIDC
(éviter une clé privée permanente) ? Pourquoi Caddy (TLS automatique, mais stockage
et coût réseau supplémentaires) ? Que démontre la CI (cohérence statique), et que
reste-t-il à démontrer (runner OIDC, TLS externe, média et charge bornée) ?
