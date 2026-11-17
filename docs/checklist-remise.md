# Checklist de remise

Consolidation locale du 16 novembre 2026. Une case distante cochée représente
une preuve antérieure identifiée dans le rapport, pas un nouveau contrôle.

## Réalisé ou documenté

- [x] Infrastructure Terraform et configuration Helm versionnées ; HTTPS public documenté.
- [x] Test audio/vidéo ordinateur/téléphone confirmé par l’utilisatrice, sans revendication de charge ou partage d’écran.
- [x] CI main antérieure réussie, CD ignorée ; dernier échec diagnostic conservé explicitement.
- [x] Correction locale exec ADC, tests de non-régression et nettoyage des fichiers privés préparés.
- [x] Architecture, responsabilités Terraform/hors Terraform, limites de disponibilité et coûts décrits.
- [x] Procédures de diagnostic, premier CD et rollback préparées, non exécutées.
- [x] Plan de soutenance 12 minutes, démonstration et solution de repli documentés.

## À vérifier avant le dépôt académique

- [ ] Renseigner auteur, établissement, encadrant et année universitaire dans le rapport.
- [ ] Vérifier les exigences de format, exporter le rapport et contrôler les diagrammes Mermaid dans le PDF.
- [ ] Préparer des captures expurgées des preuves existantes ; aucune capture vidéo n’est réputée réalisée.
- [ ] Répéter la soutenance avec chronomètre et tester le réseau autorisé avant le jour J.
- [ ] Ne joindre que les fichiers explicitement relus ; jamais une archive complète du répertoire de travail.
- [ ] Exclure états Terraform, kubeconfigs, credentials, sauvegardes Helm, clés privées et déchiffrements SOPS.
- [ ] Relever le SHA réellement publié après publication autorisée ; ne pas présenter le correctif local comme déjà dans main.

## Actions distantes soumises à accord distinct

- [ ] Publier le lot local relu dans une branche et une PR ; attendre les CI, puis autorisation de fusion.
- [ ] Après présence du diagnostic corrigé dans main, vérifier SHA et CD inactive ; autoriser un seul lancement manuel.
- [ ] Valider identité Kubernetes puis RBAC, PVC et SOPS/KMS sur le runner. Arrêter sur erreur sans élargir les droits.
- [ ] Adapter séparément l’authentification du workflow CD, faire relire et valider sa CI.
- [ ] Autoriser explicitement profil/variables et fenêtre de premier CD ; relever les révisions avant essai et convenir du rollback.
- [ ] Après essai, vérifier TLS, secrets sans affichage, pods, PVC, IP et médias ; désactiver le flag selon l’accord donné.

La CD reste non validée tant que ces étapes n’ont pas abouti. Voir le
[rapport](rapport.md), la [soutenance](soutenance.md), l’[architecture](architecture.md)
et la [procédure détaillée](validation-cd-controlee.md).
