# Revue de réorganisation documentaire

Réorganisation documentaire uniquement, depuis main
`b3e4bce53449aa71d6b9ea281fc2a7bf1056e1f3`. Aucune expérience, mutation GCP,
modification de secret ou modification des déclenchements Actions.

## Choix des documents principaux

- `docs/rapport.md` est le rapport final unique ; les deux versions antérieures
  restent intégralement disponibles sous `docs/archives/`.
- `docs/presentation-finale.md` est le plan oral principal de 12 minutes.
  L'ancien `soutenance.md` est historique : ses révisions 3/2 et sa CD encore
  non validée ne doivent plus être annoncées comme l'état final.
- `docs/architecture.md` est remis en cohérence avec le rapport : révisions 4/3,
  CD réellement réussie puis désactivée, état distant et limites de bootstrap.
  L'ancienne version est conservée en archive avant cette mise à jour.

## Comparaison des rapports : sélection, pas concaténation

| Source historique | Information moins détaillée ou absente du rapport final | Traitement |
|---|---|---|
| Rapport du 15 novembre, préparation locale | Cache provider facultatif, options isolées, détails SSH restreint et commandes de diagnostic | Conservation en archive et renvoi par le rapport ; procédures historiques non présentées comme exécutées |
| Rapport du 15 novembre, statistiques JVB | Valeurs exactes des quatre compteurs cumulés constants | Réintroduites dans la section 8 avec leur date et la limite d'interprétation |
| Rapport du 15 novembre, palier 3 | Transitions 0/2/3 endpoints, relevé P2P/inactif et taux moyens de paquets | Réintroduits en section 9.1, sans inventer d'unité ou de volume transféré |
| Journal du 17 novembre, préparation IAM | Échec serviceusage.services.enable de l'identité VM et distinction gcloud/ADC | Résumé ajouté en section 4.1, sans déduire une politique IAM finale non conservée |
| Journal du 17 novembre, environnement | Liste des outils du poste et versions Windows/navigateurs non consignées | Précisées en section 4.1 ; aucune version inventée |
| Journal du 17 novembre, autres phases | Étapes SOPS/KMS, essais audio/vidéo, échecs GHCR, saturation, Chaos, GCS et CD | Résultats déjà couverts dans le rapport final ; détails et commandes conservés en archive |
| Les deux rapports | Statuts préparatoires devenus caducs : backend local, absence de CD ou essais encore attendus | Conservés comme histoire ; pas de réintroduction comme état final |

Les mesures non publiées sous forme de série identifiable restent qualifiées
comme comptes rendus historiques. Les résultats GitHub, les scénarios observés
et les validations statiques restent séparés. Les JSON n'ont été ni réécrits ni
recalculés pour cette réorganisation.

## Comparaison des supports oraux

Le support final couvre déjà les résultats plus récents (CD réussie, Malleus,
Chaos et état distant) et sert de référence. Les compléments utiles de l'ancien
support sont repris en fin du plan final : préparation pratique, consentement,
réseau filtré, portée d'un tunnel HTTPS et questions BOSH/PVC/rollback/TURN.
Les démonstrations réseau proposées ne sont pas décrites comme réalisées.
L'ancien minutage et les commandes complètes restent dans son archive.

## Fichiers déplacés avec git mv

| Ancien chemin | Nouveau chemin |
|---|---|
| `docs/architecture.md` | `docs/archives/architecture-2026-11-16.md` |
| `docs/bootstrap-https-court.md` | `docs/guides/bootstrap-https-court.md` |
| `docs/cd-diagnostic.md` | `docs/guides/cd-diagnostic.md` |
| `docs/chaos-web-controle.md` | `docs/guides/chaos-web-controle.md` |
| `docs/checklist-remise.md` | `docs/livraison/checklist-remise.md` |
| `docs/conformite-finale.md` | `docs/livraison/conformite-finale.md` |
| `docs/https-duckdns.md` | `docs/guides/https-duckdns.md` |
| `docs/jitsi-public-edge.md` | `docs/guides/jitsi-public-edge.md` |
| `docs/malleus-selenium.md` | `docs/guides/malleus-selenium.md` |
| `docs/malleus-video-docker.md` | `docs/guides/malleus-video-docker.md` |
| `docs/pipelines-experiences-controlees.md` | `docs/guides/pipelines-experiences-controlees.md` |
| `docs/preuve-repos-palier-2026-11-15.json` | `docs/preuves/preuve-repos-palier-2026-11-15.json` |
| `docs/preuves-livraison.md` | `docs/preuves/preuves-livraison.md` |
| `docs/revue-integration-pr7-pr13.md` | `docs/archives/revue-integration-pr7-pr13.md` |
| `docs/selenium-helm-validation.md` | `docs/guides/selenium-helm-validation.md` |
| `docs/soutenance.md` | `docs/archives/soutenance-2026-11-16.md` |
| `docs/terraform-bootstrap-resultats.json` | `docs/preuves/terraform-bootstrap-resultats.json` |
| `docs/terraform-cd-controlee.md` | `docs/guides/terraform-cd-controlee.md` |
| `docs/terraform-droits-verifies.json` | `docs/preuves/terraform-droits-verifies.json` |
| `docs/terraform-github-environnement.json` | `docs/preuves/terraform-github-environnement.json` |
| `docs/terraform-github-plan-final.json` | `docs/preuves/terraform-github-plan-final.json` |
| `docs/terraform-github-plan-resultats.json` | `docs/preuves/terraform-github-plan-resultats.json` |
| `docs/terraform-migration-resultats.json` | `docs/preuves/terraform-migration-resultats.json` |
| `docs/terraform-oidc-correction-resultats.json` | `docs/preuves/terraform-oidc-correction-resultats.json` |
| `docs/terraform-plan-actualise.json` | `docs/preuves/terraform-plan-actualise.json` |
| `docs/terraform-plan-apply-validation.md` | `docs/guides/terraform-plan-apply-validation.md` |
| `docs/terraform-plan-preuve.json` | `docs/preuves/terraform-plan-preuve.json` |
| `docs/terraform-prerequis-audit.md` | `docs/archives/terraform-prerequis-audit.md` |
| `docs/terraform-second-failure-correction.json` | `docs/preuves/terraform-second-failure-correction.json` |
| `docs/test-video-helm-2x90.md` | `docs/guides/test-video-helm-2x90.md` |
| `docs/validation-cd-controlee.md` | `docs/livraison/validation-cd-controlee.md` |
| `docs/validation-remise.md` | `docs/archives/validation-remise-2026-11-16.md` |

Le nouveau document d'architecture est recréé à son chemin principal ; sa version
antérieure a d'abord été déplacée. Aucun rapport ni aucune preuve n'est supprimé.

## Références et préservation

Les liens Markdown sont recalculés relativement à leur nouveau document,
y compris dans les archives. Les chemins absolus au dépôt dans les documents
actifs suivent la même table. Le lien vers l'historique d'une branche supprimée
est remplacé par son SHA immuable `1676e23c2b7453bf616020dacacdebf9dc1e6cf3`.
Les anciens chemins contenus dans les transcriptions Git des archives sont
volontairement conservés : les réécrire falsifierait ces sorties historiques.
Ils ne sont pas des dépendances exécutables ; la table ci-dessus les résout.

Deux adaptations de scripts sont nécessaires et limitées à la structure :

- `scripts/check-terraform-oidc-subject.py` lit désormais la preuve de bootstrap
  dans `docs/preuves/`, sans changement de garde OIDC ou d'autorisation.
- `scripts/check-docs.py` parcourt récursivement les Markdown de `docs/` afin
  de conserver le contrôle des guides déplacés et d'inclure les archives.

Aucun workflow, profil Helm, fichier Terraform ou fichier de secret n'est modifié.
Les preuves restent sous leurs noms d'origine et leur contenu est comparé octet
pour octet avant/après. Les deux rapports archivés gardent leur texte historique,
hors adaptation des destinations de liens et notice de navigation explicite.

## Arborescence avant

```text
docs/architecture.md
docs/archives/rapport-avant-livraison-finale-2026-11-17.md
docs/archives/rapport-avant-refonte-2026-11-15.md
docs/bootstrap-https-court.md
docs/cd-diagnostic.md
docs/chaos-web-controle.md
docs/checklist-remise.md
docs/conformite-finale.md
docs/https-duckdns.md
docs/jitsi-public-edge.md
docs/malleus-selenium.md
docs/malleus-video-docker.md
docs/pipelines-experiences-controlees.md
docs/presentation-finale.md
docs/preuve-repos-palier-2026-11-15.json
docs/preuves-livraison.md
docs/rapport.md
docs/revue-integration-pr7-pr13.md
docs/selenium-helm-validation.md
docs/soutenance.md
docs/terraform-bootstrap-resultats.json
docs/terraform-cd-controlee.md
docs/terraform-droits-verifies.json
docs/terraform-github-environnement.json
docs/terraform-github-plan-final.json
docs/terraform-github-plan-resultats.json
docs/terraform-migration-resultats.json
docs/terraform-oidc-correction-resultats.json
docs/terraform-plan-actualise.json
docs/terraform-plan-apply-validation.md
docs/terraform-plan-preuve.json
docs/terraform-prerequis-audit.md
docs/terraform-second-failure-correction.json
docs/test-video-helm-2x90.md
docs/validation-cd-controlee.md
docs/validation-remise.md
```

## Arborescence après

```text
docs/README.md
docs/architecture.md
docs/archives/README.md
docs/archives/architecture-2026-11-16.md
docs/archives/rapport-avant-livraison-finale-2026-11-17.md
docs/archives/rapport-avant-refonte-2026-11-15.md
docs/archives/revue-integration-pr7-pr13.md
docs/archives/soutenance-2026-11-16.md
docs/archives/terraform-prerequis-audit.md
docs/archives/validation-remise-2026-11-16.md
docs/guides/bootstrap-https-court.md
docs/guides/cd-diagnostic.md
docs/guides/chaos-web-controle.md
docs/guides/https-duckdns.md
docs/guides/jitsi-public-edge.md
docs/guides/malleus-selenium.md
docs/guides/malleus-video-docker.md
docs/guides/pipelines-experiences-controlees.md
docs/guides/selenium-helm-validation.md
docs/guides/terraform-cd-controlee.md
docs/guides/terraform-plan-apply-validation.md
docs/guides/test-video-helm-2x90.md
docs/livraison/checklist-remise.md
docs/livraison/conformite-finale.md
docs/livraison/reorganisation-documentaire.md
docs/livraison/validation-cd-controlee.md
docs/presentation-finale.md
docs/preuves/preuve-repos-palier-2026-11-15.json
docs/preuves/preuves-livraison.md
docs/preuves/terraform-bootstrap-resultats.json
docs/preuves/terraform-droits-verifies.json
docs/preuves/terraform-github-environnement.json
docs/preuves/terraform-github-plan-final.json
docs/preuves/terraform-github-plan-resultats.json
docs/preuves/terraform-migration-resultats.json
docs/preuves/terraform-oidc-correction-resultats.json
docs/preuves/terraform-plan-actualise.json
docs/preuves/terraform-plan-preuve.json
docs/preuves/terraform-second-failure-correction.json
docs/rapport.md
```


## Validations locales de la réorganisation

- 36 fichiers d'origine retrouvés ; 32 déplacements par git mv et aucune preuve supprimée.
- 11 JSON identiques octet pour octet ; texte historique conservé hors navigation.
- 30 documents Markdown contrôlés, 210 liens locaux et 103 blocs shell : zéro erreur.
- Recherche des anciens chemins actifs : zéro référence manquée ; citations
  historiques et table de correspondance explicitement exclues de cette catégorie.
- Actionlint sur tous les workflows : réussite ; définitions Actions inchangées.
- 138 tests Python réussis, sans expérience ni contact GCP dans les tests.
- Helm lint/rendu Jitsi et edge, Caddyfile, terraform fmt/validate avec backend
  désactivé dans une copie isolée : réussite. Aucun serveur Caddy lancé.
- git diff --check : aucune erreur.

Ces contrôles ne sont pas des réunions ni des expériences Malleus/Chaos.
Les anciens liens de fichiers sur une révision Git précise restent historiques ;
les chemins de la version courante sont ceux de cette table. La CI de la nouvelle
PR doit être vérifiée séparément après publication ; aucune fusion automatique.
