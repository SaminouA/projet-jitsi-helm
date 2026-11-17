> Document historique conservé. Pour l’état consolidé du 17 novembre 2026,
> consulter le [rapport final](../rapport.md), les [preuves](preuves-livraison.md)
> et le [plan oral final](presentation-finale.md). Les statuts antérieurs ci-dessous
> ne décrivent pas nécessairement la version livrée.

# Revue finale d'intégration des PR nº 7 et nº 13 — 17 novembre 2026

Aucune PR n'est fusionnée. Aucun apply, test de charge ou chaos n'a été lancé.
Les nouvelles preuves concernent le code, les fixtures, le transport chiffré
et la compatibilité Git. Les preuves GCP/expérimentales antérieures ne sont pas
présentées comme des exécutions des nouveaux workflows.

## Avis

| PR | Fusion de préparation inactive | Activation / exécution |
|---|---|---|
| [7 — Terraform](https://github.com/SaminouA/projet-jitsi-helm/pull/7) | GO technique après CI verte et accord de fusion | NO-GO tant que revue protégée, secret de transport et accords ne sont pas validés |
| [13 — expériences](https://github.com/SaminouA/projet-jitsi-helm/pull/13) | GO technique après CI verte et accord de fusion | NO-GO tant que prérequis OIDC/RBAC/bootstrap et tests réels autorisés ne sont pas validés |

Ordre recommandé : PR 7 puis PR 13, en gardant TF_CD_ENABLED et GKE_CD_ENABLED
à false et EXPERIMENTS_ENABLED absent/false. Après la première fusion, relire
la base et les checks de la seconde ; ne pas supposer un état distant inchangé.
Les deux workflows modifiants ajoutés sont manuels : la fusion ne les lance pas.
Le workflow Helm existant reste lui aussi soumis à son flag désactivé.

## Correction Terraform déterminante

L'ancien job était approuvé avant de générer son plan. Cette approbation ne
valait pas revue du plan exact. La correction impose :

1. Un précontrôle main/SHA/CI/flags et des deux environnements protégés.
2. prepare-plan sous l'identité OIDC/GCS existante, sans instruction d'apply.
3. Publication du résumé exhaustif des seuls changements permis, du SHA-256
   du binaire et d'un artefact chiffré/authentifié conservé un jour.
4. review-plan, sans OIDC ni accès aux secrets, dans l'environnement DISTINCT
   terraform-apply-review, après préparation. Le digest est affiché dans son nom
   et le résumé est lié depuis l'environnement.
5. apply dépend des deux jobs et télécharge l'ID d'artefact immuable de ce run.
   HMAC, binaire, commit, run/attempt, digest revu et état distant sont vérifiés.
   Le même binaire est appliqué ; aucun recalcul ne précède l'apply.

Le garde refuse aussi tout label de preuve déjà présent : les trois champs de
labels ne peuvent recevoir que l'ajout prévu, pool no-op, aucune autre mutation.
Les before/after privés inchangés ne sont pas publiés dans la projection.
Une dérive d'état, un nouveau commit, une autre tentative, une altération, une
clé absente ou une revue absente bloquent l'apply. La décision humaine est
matérialisée par le job protégé ; le workflow ne prouve pas que la personne a
réellement lu et compris le résumé.

Les jobs OIDC restent liés à terraform-controlled : le provider GCP peut garder
son sujet immutable et son chemin de workflow existants, sans élargissement IAM.
Le gate de revue distinct ne demande aucun token OIDC. Il reste à créer avec
reviewer obligatoire, main uniquement et bypass administrateur interdit.
TF_PLAN_TRANSPORT_KEY, secret privé de 64 octets aléatoires encodés en 128 hex,
reste à provisionner dans terraform-controlled ; aucune vraie clé n'a été
créée ou affichée. Ce secret de transport ne constitue pas une clé JSON GCP.
L'environnement de revue et ce secret étaient absents au dernier contrôle.

Transport : OpenSSL AES-256-CBC/PBKDF2 puis HMAC-SHA256 à clé indépendante,
vérifié avant déchiffrement. Seuls le paquet chiffré et son manifeste public
sont téléversés ; jamais le plan/state en clair. Les secrets SOPS/KMS Jitsi
restent inchangés. Le test réel du transport d'un binaire Terraform entre deux
runners, puis son approbation, reste à effectuer après autorisation. Les tests
actuels utilisent des binaires/états synthétiques.

Le mode readonly historique reste strictement zéro changement. Avec le label
de preuve encore à ajouter, il peut refuser le changement attendu sans appliquer.
Le job prepare-plan constitue le circuit de préparation label-only. Ne pas
confondre refus du diagnostic zéro-change et échec d'un apply non exécuté.

## Malleus et Chaos : déclenchement et nettoyage

Les deux workflows imposent workflow_dispatch, main exact, CI push réussie,
flag et confirmation explicites, reviewer dans experiments-controlled, identité
séparée proposée et concurrence partagée avec Terraform/Helm. Les contrôles
CPU/RAM, pressions, réunions et pods de production précèdent la création.
Les droits nécessaires **au nettoyage** sont désormais vérifiés en amont :
un delete manquant refuse la création, sans modification automatique du RBAC.

Malleus conserve deux participants/90 s configurées, les digests validés,
les limites low CPU, un Grid ClusterIP, une release unique et un Job suspendu
jusqu'aux derniers contrôles. Chaos exige nom et UID Web approuvés, suppression
nominative via le contrôleur, absence de droits Pods plus larges, preuve d'une
seule injection et récupération d'un nouveau Web Ready/HTTPS 200. Les autres
composants ne sont jamais des cibles. Aucun scheduler ni daemon Chaos n'est créé.

finally et always ne nettoient que les objets possédés par le run. Le Job est
borné et possède un TTL ; une perte complète du runner peut néanmoins laisser
Selenium. Une suppression manuelle ciblée pourra alors être nécessaire, après
contrôle/accord. Les artefacts d'expérience sont filtrés et conservés trois jours,
sans token, état, kubeconfig, ID Selenium, candidat ICE ou logs bruts.

Les comptes/providers dédiés, l'environnement d'expérience, le namespace de test
et le contrôleur minimal ne sont pas provisionnés ici. Leur absence et le refus
RBAC du compte Helm ont déjà été constatés. Aucun élargissement de ses droits.

## Tableau de conformité des exigences techniques connues

| Critère | État établi | Validation ou preuve manquante |
|---|---|---|
| Infrastructure GKE Terraform, cluster/pool existants | Validée historiquement ; prevent_destroy et garde strict préparés | Apply automatisé réel non exécuté |
| CI Helm/Terraform après push/PR | CI verte sur les corrections de code ; hooks maintenus | Checks du dernier commit documentaire à suivre sur les PR |
| Plan sans destruction/remplacement | Dernier plan réel : 1 update label, 0 create/delete/replace ; pas de nouveau plan cloud pendant cette revue | Nouveau plan du workflow corrigé à produire après accord |
| Revue du plan exact avant apply | DAG distinct, artefact authentifié, SHA et état liés, tests négatifs réussis | Environnement de revue, secret de transport, revue humaine réelle et exécution autorisée |
| Terraform automatiquement déclenché après push | Non couvert : déclenchement manuel actuel, CI push préalable exigée | Confirmer l'acceptabilité pédagogique du manuel, sinon prévoir un déclenchement de préparation après CI sans retirer la revue |
| OIDC/GCS sans clé JSON | Configuration Terraform historique conservée ; aucune modification IAM | Nouveau parcours plan/revue/apply non exécuté |
| Secrets Jitsi SOPS/KMS et état privé | Inchangés ; pas de plaintext/state/plan ajouté à Git | Transport réel et gestion/rotation de sa nouvelle clé à valider |
| Déploiement Helm et accès Jitsi HTTPS | Validations historiques conservées | Aucun nouveau déploiement dans cette revue |
| Charge Malleus/Selenium | Résultats manuels historiques et digests conservés ; workflow préparé | Nouveau pipeline réel, ses droits et son nettoyage à valider ; pas de preuve de capacité maximale ni 90 s vidéo continue |
| Résilience Chaos Mesh | Pod-kill Web historique validé ; nouveaux gardes testés | Bootstrap minimal, RBAC nominatif courant, nouveau pipeline autorisé, récupération/nettoyage réels |
| Mesures et Cloud Monitoring | Métriques kubectl/JVB et Monitoring GKE décrits dans les preuves historiques | Captures/graphes Cloud Monitoring corrélés aux scénarios non validés par cette revue |
| Compatibilité des PR et préservation du rapport | Fusion virtuelle sans conflit et suite combinée réussie | Recontrôler après évolution de main ; fusion humaine encore requise |

Ce tableau reprend les attendus techniques déjà décrits dans le projet. Il ne
certifie pas un barème supplémentaire qui n'aurait pas été communiqué.

## Vérifications nouvelles et traçabilité

- 28 tests Terraform ciblés : garde, refus des états modifiés, revue absente,
  mauvais SHA/run/attempt/clé, altérations de manifeste/ciphertext/MAC et roundtrip.
- 15 tests d'expérience ciblés après ajout du contrôle des droits de nettoyage.
- 138 tests sur un snapshot de fusion virtuelle des DEUX branches, sans fusion
  ni déplacement de main ; 20 documents, 90 liens et 87 blocs shell sans erreur.
- Le code des scénarios physiques n'a pas été rejoué. Les tests font appel aux
  fixtures, outils simulés, rendus Helm locaux et OpenSSL sur données synthétiques.
- Les validations locales inchangées n'ont pas été répétées manuellement ; les
  hooks et CI existants ont continué leurs contrôles habituels, sans backend.

Base main de comparaison : `a5053689f79cb89e8706cc34b0112509b97e7fb5`.

Têtes de code testées : Terraform `73c7b6f8163796a83de485df776f9a1c818f61cb`, expériences `cab41a859624543f6d25b8f0b5f467aa8057c1af`.

Arbre de fusion virtuelle testé : `977b986bb053be0a5028c52973253674329ccfdd`. Les ajouts documentaires suivants ne modifient pas ce code.

## Périmètres exacts par rapport à main

### PR 7 — 12 fichiers

```text
A	deploy/terraform/gke-role.yaml
A	deploy/terraform/state-role.yaml
A	docs/terraform-cd-controlee.md
A	docs/terraform-plan-apply-validation.md
A	docs/terraform-plan-preuve.json
A	scripts/check-terraform-plan.py
A	scripts/terraform-controlled.py
A	scripts/terraform-plan-bundle.py
A	tests/test_terraform_controlled.py
M	.github/workflows/terraform-gke.yml
M	docs/rapport.md
M	terraform/main.tf
```

### PR 13 — 57 fichiers

```text
A	.github/workflows/chaos-controlled.yml
A	.github/workflows/malleus-controlled.yml
A	deploy/terraform/gke-label-role-read-fix.yaml
A	deploy/terraform/oidc-subject-correction.json
A	docs/chaos-web-controle.md
A	docs/malleus-selenium.md
A	docs/malleus-video-docker.md
A	docs/pipelines-experiences-controlees.md
A	docs/revue-integration-pr7-pr13.md
A	docs/selenium-helm-validation.md
A	docs/terraform-bootstrap-resultats.json
A	docs/terraform-droits-verifies.json
A	docs/terraform-github-environnement.json
A	docs/terraform-github-plan-final.json
A	docs/terraform-github-plan-resultats.json
A	docs/terraform-migration-resultats.json
A	docs/terraform-oidc-correction-resultats.json
A	docs/terraform-plan-actualise.json
A	docs/terraform-plan-apply-validation.md
A	docs/terraform-prerequis-audit.md
A	docs/terraform-second-failure-correction.json
A	docs/test-video-helm-2x90.md
A	scripts/chaos-web-postrender.py
A	scripts/check-terraform-oidc-subject.py
A	scripts/controlled-experiment.py
A	scripts/observe-chaos-web.py
A	scripts/observe-malleus-video.py
A	scripts/run-malleus-light.py
A	scripts/summarize-malleus-light.py
A	scripts/summarize-malleus-video.py
A	tests/chaos/plan.json
A	tests/chaos/podchaos-web-once.yaml
A	tests/chaos/results-summary.json
A	tests/chaos/values-controller-only.yaml
A	tests/load/cpu-reduction-plan.json
A	tests/load/docker/build-results.json
A	tests/load/docker/job-malleus.yaml
A	tests/load/k8s-video-low-cpu-results.json
A	tests/load/k8s-video-results.json
A	tests/load/malleus-image-results.json
A	tests/load/results-summary.json
A	tests/load/selenium-grid.toml
A	tests/load/selenium-image-results.json
A	tests/load/values-video-2x90-low-cpu.yaml
A	tests/load/values-video-2x90.yaml
A	tests/load/video-final-checks.json
A	tests/load/video-results-summary.json
A	tests/test_chaos_web_safety.py
A	tests/test_controlled_experiments.py
A	tests/test_load_safety.py
A	tests/test_load_video.py
A	tests/test_terraform_oidc_subject.py
M	charts/jitsi-load-test/templates/selenium.yaml
M	charts/jitsi-load-test/values.yaml
M	docs/rapport.md
M	tests/test_load_helm.py
M	tests/test_terraform_readonly.py
```
