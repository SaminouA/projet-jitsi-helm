# Préparation du diagnostic OIDC/GKE/SOPS — sans déploiement

État : modifications locales proposées, aucun workflow lancé, commit ou push.
Les six APIs et le droit get du PVC ont été appliqués lors d'étapes antérieures
autorisées et revérifiés en lecture seule. Cette préparation de publication ne
modifie aucun service, droit ou variable. Le diagnostic est séparé de la CD
et ne nécessite pas d'activer `GKE_CD_ENABLED`.

## Contenu à publier

- `deploy/cd-pvc-reader.yaml` : trace du Role et RoleBinding déjà appliqués, limités au
  namespace `jitsi`, verbe `get`, ressource PVC nommée `jitsi-edge-data`, compte
  `github-jitsi-deployer`. Aucun create/delete PVC, list/watch global ou droit
  administrateur. Le contrôle CD `can-i` cible désormais ce nom, pour être
  compatible avec `resourceNames`. Le bootstrap reste réservé à l'opérateur.
- La CD exige un profil explicite, sans fallback implicite localhost. Avant OIDC,
  le profil public exige le domaine/réservation attendus et le flag edge.
- Le profil local applique `--set-string publicURL=http://localhost:8081` même si
  la base est publique ; le profil public conserve son chemin de fusion actuel.
  Aucun flag d'activation n'est changé par le code ou la préparation.

## Prérequis API : opérateur, lecture seule

```sh
python3 scripts/check-gcp-apis.py
```

Le script liste les APIs activées et retourne un échec si un prérequis manque ;
il ne les active jamais. Les six APIs sont maintenant actives : IAM,
IAMCredentials, STS, Resource Manager, GKE et KMS. Ne pas rejouer une activation
pour publier ce workflow. Leur activation ne prouve pas l'échange OIDC runner.

Ne pas attribuer au compte CD un rôle d'activation de services pour ce diagnostic.
L'inventaire Service Usage nécessite des droits opérateur ; le runner teste les
APIs par leurs opérations réelles OIDC, GKE et KMS et n'obtient pas de droit
supplémentaire Service Usage uniquement pour lister les services. La présence
des APIs ne prouve pas le succès de l'échange de jeton depuis GitHub.

## GitHub : besoins du diagnostic et future CD

**Aucune variable de dépôt ou secret GitHub supplémentaire n'est nécessaire au
diagnostic.** `GH_TOKEN` reçoit automatiquement `github.token` avec contents:read ;
id-token:write autorise l'obtention du jeton OIDC. Le provider WIF et le compte
Google sont des identifiants non secrets du workflow. Le fichier SOPS chiffré
est déjà versionné et sa clé est accessible via IAM/KMS. Ne pas ajouter de clé
JSON de compte Google, de jeton DuckDNS, de PAT personnel ou de secret en clair.

Le tableau suivant concerne seulement une **future activation CD** et ne doit
pas retarder ou activer le diagnostic :

| Variable de dépôt proposée | Valeur | Moment |
|---|---|---|
| `JITSI_ACCESS_PROFILE` | `public-edge` | Après accord de préparation |
| `JITSI_PUBLIC_DOMAIN` | `jitsi-meet-m2.duckdns.org` | Après accord de préparation |
| `JITSI_EDGE_ADDRESS_NAME` | `jitsi-edge-ip` | Après accord de préparation |
| `JITSI_EDGE_CD_ENABLED` | `false` | Rester désactivée pendant le diagnostic |
| `GKE_CD_ENABLED` | `false` ou absente | Rester désactivée pendant le diagnostic |

L'activation des deux flags est une décision ultérieure distincte. Le diagnostic
fixe lui-même le profil public dans son environnement relu, sans écrire de
variable GitHub ; il vérifie les fichiers et les ConfigMaps live attendus.
Le rôle PVC minimal est déjà appliqué. Sa lecture par impersonation a été
revérifiée : yes pour le seul PVC nommé ; les écritures restent interdites.
Ne pas réappliquer le manifeste lors de la publication. Contrôle lecture seule :

```sh
kubectl auth can-i get persistentvolumeclaims/jitsi-edge-data -n jitsi \
  --as=github-jitsi-deployer@project-fcf2ef91-c005-4910-a10.iam.gserviceaccount.com
```

## Workflow de diagnostic proposé

`.github/workflows/diagnose-gke.yml` : déclenchement uniquement manuel
`workflow_dispatch`, confirmation booléenne obligatoire, dépôt exact,
`refs/heads/main`. Aucune PR, fork, branche feature ou événement automatique.
Le workflow doit d'abord être relu et intégré sur main après accord ; aucune
procédure ne contourne les restrictions WIF pour le lancer depuis cette branche.

Le checkout utilise le SHA du dispatch et ne garde pas les credentials Git.
Avant l'authentification, un garde vérifie payload, dépôt, branche, confirmation,
SHA checkout et tête actuelle de main. Cette vérification est répétée à la fin.
Une mise à jour de main pendant le diagnostic invalide son résultat.
Les actions sont épinglées, SOPS est vérifié par SHA256, et seuls contents:read
et id-token:write sont demandés. Le verrou de concurrence est le même que celui
de la CD, sans annulation d'une exécution en cours.

Après authentification WIF et configuration **locale** du kubeconfig, le script :

1. Vérifie le contexte et l'identité effective du compte CD.
2. Vérifie les URL Jitsi/Caddy live et ACME production.
3. Interroge 49 autorisations, dont get du seul PVC nommé. Les verbes CRUD sont
   uniquement interrogés avec `auth can-i`, jamais exécutés.
4. Vérifie les deux releases déjà déployées, le LB et le PVC via les garde-fous.
5. Déchiffre SOPS dans un répertoire temporaire privé (0700, fichiers 0600),
   sans journaliser de valeur, puis effectue lint et rendus Helm hors cluster.
6. Compare les secrets, l'IP JVB, les ressources existantes et leur disponibilité.
7. Supprime le répertoire, y compris en cas d'échec SOPS ; une étape always()
   nettoie aussi en secours. L'action auth nettoie ses credentials fédérés.

Aucun `helm upgrade/install/rollback/uninstall`, `kubectl apply/patch/delete`,
rotation de secret, création PVC, IP ou LB. Aucun artefact ni cache contenant des
valeurs n'est publié. Les sorties potentiellement sensibles des outils sont
capturées et remplacées par des erreurs fixes sans stderr brut.

## Intégration et lancement : actions restantes, non exécutées

1. Après accord, créer le commit local des 11 fichiers revus et pousser
   `feature/jitsi-public-edge`. Attendre les CI push et PR du nouveau SHA.
2. Revoir la PR nº 3 vers `main` : elle inclut aussi les travaux HTTPS/CD
   précédents. Confirmer avant fusion que `GKE_CD_ENABLED` est toujours absente
   ou false. La fusion et le passage éventuel hors brouillon nécessitent un
   accord distinct ; ne pas activer la CD pour publier le diagnostic.
3. Après fusion autorisée, attendre la CI du **push main** et vérifier le SHA
   final de main ainsi que la présence du nouveau workflow sur cette branche.
   Le fichier doit exister sur la branche par défaut pour workflow_dispatch.
   Ni la CI feature ni une exécution avec --ref feature ne remplacent cette étape.
4. Vérifier que `diagnose-gke.yml` est disponible/actif, les APIs actives et le
   droit PVC nommé toujours présent. L'opérateur GitHub doit avoir le droit de
   lancer Actions ; le jeton du job ne remplace pas cette autorisation humaine.
5. Après accord explicite de lancement, utiliser la branche **main**, jamais la
   branche feature, et confirmer le mode sans déploiement :

```sh
# PREVU UNIQUEMENT : ne pas executer avant integration main et accord de lancement.
gh workflow run diagnose-gke.yml --repo SaminouA/projet-jitsi-helm \
  --ref main -f confirm_read_only=true
```

6. Identifier la bonne exécution et contrôler événement workflow_dispatch,
   branche main et head_sha correspondant au SHA main attendu, puis attendre
   la conclusion. Maintenir main stable pendant le diagnostic : une nouvelle
   tête fait échouer son garde final. Exemples de lectures futures :

```sh
gh run list --repo SaminouA/projet-jitsi-helm --workflow diagnose-gke.yml \
  --branch main --event workflow_dispatch --limit 5
gh run watch RUN_ID --repo SaminouA/projet-jitsi-helm --exit-status
```

7. Relire les résultats identité/RBAC/PVC/KMS/rendus/nettoyage. Une réussite
   n'active aucune variable ni ne déclenche la CD. Tout premier déploiement
   demandera une autorisation et une validation séparées.

Au contrôle de préparation : branche par défaut main, Actions activées et
provider WIF ACTIVE limité à `SaminouA/projet-jitsi-helm`/`refs/heads/main` ;
clé KMS primaire ENABLED. Le workflow diagnostic est absent de main (404),
la PR nº 3 est ouverte en brouillon sur ff74090, et les variables de dépôt sont
vides. Aucun lancement n'est donc présenté comme possible immédiatement depuis
la seule branche feature.

## Risques conservés visibles

Le compte CD conserve les droits applicatifs existants : l'absence de mutation
repose sur le code relu et ses garde-fous, pas sur une identité cloud totalement
read-only. Le déchiffrement utilise une opération KMS auditée et peut entraîner
une facturation d'opération et du temps runner ; il ne crée pas d'infrastructure.
Les secrets sont en clair temporairement dans la mémoire/disque du runner :
pas de debug, trace shell, artefact ou cache sensible ; nettoyage requis.

Les restrictions WIF actuelles utilisent les noms dépôt/branche ; le durcissement
par IDs immuables et workflow exact reste une amélioration séparée. Le dépôt
n'impose pas encore de revue humaine minimale ou d'environnement de déploiement
à approbation. La disponibilité réseau GKE depuis un runner reste à confirmer.
La CD ne rend pas ses deux upgrades transactionnels ; le rechargement de
PUBLIC_URL lors d'une future migration reste un sujet séparé. Le diagnostic
ne prouve ni TLS externe, renouvellement, reprise après panne ou réunion vidéo.


## Résultats de préparation locale

42 tests Python réussis (11 nouveaux scénarios du diagnostic simulé), validation
Helm public/local, Terraform sans backend et Caddyfile réussies. YAML et blocs
Bash vérifiés sans exécution GitHub. Le contrôle réel d'inventaire API réussit désormais pour les six services. Aucun déchiffrement
SOPS réel ou échange OIDC runner n'a été exécuté. Aucun commit/push ni mutation
cloud/RBAC/variable pendant la préparation de publication. Voir le rapport pour le détail et les limites.


## Instrumentation de l'échec whoami : correction locale non publiée

Le premier run réel `43955701042` a échoué au contrôle whoami après les étapes
OIDC et get-gke-credentials réussies. Ses logs n'exposent que le label expurgé ;
la cause exacte n'est pas établie. L'impersonation locale whoami réussit, ce qui
ne reproduit pas les credentials ou le réseau du runner et ne justifie pas
une extension RBAC.

Le script local ajoute, sans changer le workflow ni ses déclencheurs :

- recherche du binaire `gke-gcloud-auth-plugin` et test `--version`, sortie
  capturée sans affichage ni génération directe de token ;
- lecture du seul champ server du contexte minifié, sans export du kubeconfig,
  puis une connexion TCP sans credentials avec délai de cinq secondes ;
- whoami avec request-timeout de 15 secondes et limite processus de 30 secondes ;
- classification en mémoire des erreurs, avec messages fixes uniquement :
  PLUGIN_ABSENT/EXECUTION/TIMEOUT, AUTHENTIFICATION_CREDENTIALS/401, RBAC_403,
  RESEAU_DNS/TIMEOUT/TLS/CONNEXION_REFUSEE/TRANSPORT, ou INDETERMINE.

Un délai global whoami produit DELAI_INDETERMINE : il n'est pas attribué
aveuglément au réseau alors que le plugin peut aussi attendre. TCP OK ne prouve
pas TLS, authentification ou RBAC. Un échec TCP direct n'empêche pas whoami de
réussir via un proxy ; whoami reste la vérification autoritative de l'identité.
Un 403 indique un refus d'autorisation à analyser (RBAC/IAM éventuel), sans
justifier automatiquement l'attribution d'un nouveau rôle. Les catégories
reposent sur des signatures connues ; toute erreur inconnue reste INDETERMINE.

Aucune sortie brute stdout/stderr, URL endpoint, identité reçue, version brute,
token ou credential n'est publiée par ces probes. Une réponse whoami invalide
ou une identité inattendue arrête le diagnostic. Les erreurs continuent à
bloquer avant les vérifications applicatives et le déchiffrement SOPS.

Les nouveaux tests sont synthétiques, sans connexion réseau/plugin réel.
La correction doit être revue, publiée et intégrée sur main avec CI après
accord ; un nouvel accord de lancement sera ensuite requis. **Aucun résultat
GitHub de cette correction n'est encore disponible et aucune relance n'a eu lieu.**
