# Préparation HTTPS — jitsi-meet-m2.duckdns.org


> État actuel pour la publication : Jitsi révision 3, Caddy révision 2 en ACME
> production, DNS Web 34.78.71.58 et PVC 10Gi Bound. Le profil spécifique au
> domaine est maintenant versionné en production ; les commandes de bootstrap
> ci-dessous imposent explicitement staging. Les constats antérieurs et l'échec
> initial conservés plus bas sont historiques. Ne pas rejouer un bootstrap sur
> ces ressources existantes. La réunion à deux est confirmée manuellement par
> l'utilisatrice ; aucun test de charge ou partage d'écran n'est revendiqué.


Contrôles du 16 novembre 2026. **Aucune commande de mutation ci-dessous n'a été
exécutée.** Réserver le sous-domaine n'autorise ni les coûts GCP, ni le bootstrap,
ni la migration, ni la CD. Les phases sont à exécuter séparément après accord.

## Configuration préparée et état constaté

- `deploy/jitsi-edge-duckdns.yaml` : domaine réel, ACME staging, nom proposé
  `jitsi-edge-ip`. Cette réservation GCP n'existe pas encore.
- `deploy/jitsi-duckdns.yaml` : URL Jitsi réelle ; surcharge du profil public.
- Les valeurs génériques, le profil localhost et les workflows restent inchangés.
- Git était propre sur `feature/jitsi-public-edge` au SHA `c591ad4`, identique au
  distant. Quatre pods Ready, zéro redémarrage, release `jitsi` révision 2 déployée,
  services/EndpointSlices présents, aucun Warning actuellement retourné.
- Aucune release edge, aucun PVC dans `jitsi`, aucune adresse réservée du projet.
- Résolution locale et DNS Google public : A `37.67.80.37`. DNS Google répond
  NOERROR sans réponse AAAA ; aucune IPv6 retournée par le résolveur local.
  Ce n'est pas une IP Caddy attribuée. Aucun HTTP/TLS n'a été testé sur cette IP.
  La propriété DuckDNS repose sur la réservation déclarée par l'utilisateur ; le
  contrôle DNS ne prouve ni la propriété ni la propagation mondiale.

## Capacité, quotas et permissions lus

Chaque nœud a 1930m CPU et 6170232Ki mémoire allouables. Les requêtes cumulées
sont 727m CPU par nœud ; mémoire demandée : 1874425088 et 1334699904 octets.
L'observation `kubectl top nodes` indique 94m/106m CPU et 2307Mi/2125Mi mémoire.
Caddy demande 100m et 128Mi, limite mémoire 256Mi, une réplique Recreate.
La marge de scheduling paraît suffisante sans nouveau nœud ; les limites mémoire
existantes sont surengagées (261 % et 134 %), donc cette lecture ne garantit pas
la capacité en charge. Aucun ResourceQuota/LimitRange dans `jitsi`.

| Quota | Usage / limite | Besoin prévu |
|---|---|---|
| Régional STATIC_ADDRESSES | 0 / 8 | +1 |
| Régional IN_USE_ADDRESSES | 3 / 8 | +1 pour la règle edge prévue |
| Régional SSD_TOTAL_GB | 80 / 500 | +10 Gi pour pd-balanced |
| Régional DISKS_TOTAL_GB | 0 / 4096 | Relevé complémentaire, pas le quota principal pd-balanced |
| EXTERNAL_NETWORK_LB_FORWARDING_RULES | 1 / 50 | +1 TCP pour deux ports discrets |
| REGIONAL_EXTERNAL_NETWORK_LB_BACKEND_SERVICES | 0 / 50 | +1 |
| Global FIREWALLS | 12 / 100 | Règles gérées par GKE |
| Global HEALTH_CHECKS | 1 / 75 | Contrôle géré par GKE |

Le tier par défaut est PREMIUM. Le LB JVB existant est régional EXTERNAL/UDP,
Premium, IP `34.62.165.81` ; il reste séparé du futur TCP 80/443 Caddy.
Le cluster est en 1.36.4-gke.2377000 : annotation `l4-rbs` conservée ; le nom de
réservation est utilisé par `networking.gke.io/load-balancer-ip-addresses`.
Les quotas sont un instantané, pas une réservation de capacité fournisseur.
La lecture de la configuration de facturation du projet retourne billingEnabled=true ;
aucun tarif contractuel ni montant de facture n’est ainsi vérifié.

`testIamPermissions` confirme pour l'identité opérateur les permissions testées
addresses create/get/list/use/delete, disks create/use, forwardingRules create,
backendServices create, healthChecks create et firewalls create. Cela ne valide
pas à lui seul les droits du contrôleur GKE pour toutes les opérations réseau.
Les tests Kubernetes opérateur create PVC/Deployment/Service/ConfigMap,
patch Deployment et delete Service répondent yes. Aucune attribution modifiée.
Le compte CD répond **no** à get PVC : ajouter ce droit minimal, après revue,
sera nécessaire uniquement avant une future CD publique. Aucun droit nouveau
n'est requis dans le conteneur Caddy, qui n'a pas de jeton Kubernetes.

## Stockage et coûts supplémentaires

Le CSI PD GKE est activé ; `standard-rwo` utilise **pd-balanced zonal**, avec
WaitForFirstConsumer, RWO et reclaimPolicy Delete. Le PVC demandé est 10Gi,
indépendant de Helm. Il peut rester Pending avant le premier pod : ne pas attendre
Bound avant l'installation edge. Le driver annonce ReadWriteOnceWithFSType ;
fsGroup 1000 et UID/GID 1000 sont préparés pour `/data`. L'écriture effective et
la conservation après redémarrage restent à tester après bootstrap. `/config`
et `/tmp` sont éphémères. Une réplique et Recreate impliquent une interruption
à la mise à jour ; le disque zonal ne garantit pas une haute disponibilité.
La suppression du PVC peut effacer le disque et les clés ACME : exclue du retour
arrière proposé. Une sauvegarde serait une opération supplémentaire à autoriser.

Tarifs publics consultés le 16 novembre 2026, USD hors taxes/remises :

- Groupe des cinq premières règles régionales : référence 0,025 USD/h, soit
  18,25 USD/730 h. Une règle JVB existe déjà dans le même projet/région : avec
  une règle edge supplémentaire, le groupe resterait sous cinq. L'incrément
  de ce poste devrait donc être nul si la même grille régionale s'applique ;
  ne pas ajouter automatiquement 18,25 USD. À confirmer sur la facturation.
- Traitement LB : référence 0,008 USD/GiB entrant et sortant, plus transfert
  Internet/interzone selon trafic et destinations. Par exemple 10 GiB traités
  représentent 0,08 USD à ce tarif, hors transfert.
- IPv4 rattachée à une règle : pas de charge IPv4 distincte ; réservation
  inutilisée : référence 0,01 USD/h, soit 7,30 USD/730 h si laissée inutilisée.
- Disque : 10 × tarif pd-balanced zonal europe-west1. La page ouverte affiche
  0,000136986 USD/GiB/h dans sa sélection par défaut, soit environ 1 USD/730 h
  pour 10 GiB. **Ce montant n'est pas une cotation Belgique vérifiée** : confirmer
  le SKU europe-west1/devise du compte avant accord budgétaire.
- Aucun nouveau nœud prévu ; GKE et nœuds existants continuent à être facturés.
  Logs, sauvegardes éventuelles et trafic restent variables. Aucun total mensuel
  supplémentaire exact n'est validé et aucun plafond de dépense n'est configuré.

Sources : [tarification réseau](https://cloud.google.com/vpc/network-pricing),
[disques](https://cloud.google.com/compute/disks-image-pricing),
[paramètres Service GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/service-load-balancer-parameters).

## Phase 1 — bootstrap staging, après accord explicite

Depuis la racine du projet, utiliser Bash. Refaire les précontrôles si l'état a
changé ; confirmer budget/SKU, accès anonyme de démonstration et exposition du
Web existant pendant le staging. Une IP, un disque et un LB seront facturables.

```bash
set -euo pipefail
export CLOUDSDK_CORE_PROJECT=project-fcf2ef91-c005-4910-a10
export JITSI_PUBLIC_DOMAIN=jitsi-meet-m2.duckdns.org
export JITSI_EDGE_ADDRESS_NAME=jitsi-edge-ip
test "$(kubectl config current-context)" = gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster
helm list -n jitsi
kubectl -n jitsi get pods,svc,pvc
# Confirmer a nouveau l'absence de jitsi-edge et de reservation homonyme.
gcloud compute addresses list --filter='name=jitsi-edge-ip' --format='table(name,address,status)'

# MUTATIONS PAYANTES : uniquement apres accord.
gcloud compute addresses create jitsi-edge-ip \
  --region=europe-west1 --network-tier=PREMIUM
kubectl apply -f deploy/jitsi-edge-storage.yaml
helm install jitsi-edge charts/jitsi-edge -n jitsi \
  -f deploy/jitsi-edge-duckdns.yaml --set acmeEnvironment=staging --wait --timeout 10m

kubectl -n jitsi get pods,svc,pvc -o wide
kubectl -n jitsi get events --field-selector type=Warning
EDGE_IP=$(gcloud compute addresses describe jitsi-edge-ip \
  --region=europe-west1 --format='value(address)')
test "$(kubectl -n jitsi get svc jitsi-edge -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" = "$EDGE_IP"
test "$(kubectl -n jitsi get pvc jitsi-edge-data -o jsonpath='{.status.phase}')" = Bound
printf 'IP Caddy a configurer dans DuckDNS : %s\n' "$EDGE_IP"
```

Dans le tableau de bord DuckDNS, définir A vers cette IP Caddy, jamais vers l'IP
JVB ni l'ancienne IP. Ne pas mettre de jeton DuckDNS dans Git ou les commandes.
Ne pas ajouter d'AAAA sans chemin IPv6. Puis vérifier A/AAAA via plusieurs
résolveurs et la propagation. `helm --wait` vérifie les sondes, pas le certificat.

```bash
python3 - <<'PY'
import socket
print(sorted({x[4][0] for x in socket.getaddrinfo('jitsi-meet-m2.duckdns.org', 443)}))
PY
curl --head --max-time 15 http://jitsi-meet-m2.duckdns.org/
openssl s_client -connect jitsi-meet-m2.duckdns.org:443 \
  -servername jitsi-meet-m2.duckdns.org -showcerts </dev/null
```

En staging, le certificat est volontairement non reconnu. Examiner l'émetteur
et les diagnostics ACME sans conclure à un succès TLS production. Si la phase
échoue, diagnostiquer les événements sans relancer aveuglément l'installation.

## Phase 2 — production ACME, après validation staging et accord

```bash
helm upgrade jitsi-edge charts/jitsi-edge -n jitsi \
  -f deploy/jitsi-edge-duckdns.yaml --set acmeEnvironment=production \
  --wait --timeout 10m --no-hooks --hide-notes
curl --head --max-time 15 https://jitsi-meet-m2.duckdns.org/
openssl s_client -connect jitsi-meet-m2.duckdns.org:443 \
  -servername jitsi-meet-m2.duckdns.org -verify_return_error </dev/null
curl --silent --show-error --max-time 15 --output /dev/null \
  --write-out '%{http_code}\n' https://jitsi-meet-m2.duckdns.org/colibri/stats
```

Attendre certificat reconnu et 404 sur la route privée. Pas de `curl -k`.
Avant migration Jitsi, le Web peut encore annoncer localhost ; un succès TLS
ne prouve pas le fonctionnement de la conférence.

## Phase 3 — migration Jitsi, après accord et certificat reconnu

Enregistrer la révision immédiatement avant migration, pas une valeur historique
figée. Aucune extraction de secret nécessaire : `--reuse-values` conserve les
valeurs effectives (dont secrets et IP JVB). Ne pas faire `helm get values` dans
les logs. Cette procédure manuelle préserve les valeurs live ; la future CD
utilisera son propre chemin de fusion SOPS contrôlé.

```bash
umask 077
mkdir -p deploy/local
test ! -e deploy/local/jitsi-before-public.revision
helm list -n jitsi --filter '^jitsi$' -o json | python3 -c \
  'import json,sys; r=json.load(sys.stdin); assert len(r)==1 and r[0]["status"]=="deployed"; print(r[0]["revision"])' \
  > deploy/local/jitsi-before-public.revision
helm upgrade jitsi charts-officiels/jitsi-meet -n jitsi --reuse-values \
  -f values-jitsi-public.yaml -f deploy/jitsi-duckdns.yaml \
  --wait --timeout 10m --no-hooks --hide-notes
kubectl -n jitsi get pods,svc,endpointslices
```

Ensuite contrôler Web/config/BOSH, absence de contenu mixte et réaliser la réunion
à trois participants du protocole `docs/validation-remise.md`. Aucune réunion
n'est validée par cette préparation. Ne pas activer les WebSockets Colibri sans
routage complet ; l'IP JVB et son LB UDP existants doivent rester identiques.

## Retour arrière — commandes préparées, non exécutées

Si seule la configuration Jitsi vient de migrer et qu'aucune autre mise à jour
n'est intervenue, restaurer la révision capturée (relire `helm history` avant) :

```bash
helm history jitsi -n jitsi
JITSI_BEFORE_REVISION=$(cat deploy/local/jitsi-before-public.revision)
[[ "$JITSI_BEFORE_REVISION" =~ ^[0-9]+$ ]]
helm rollback jitsi "$JITSI_BEFORE_REVISION" -n jitsi \
  --wait --timeout 10m --no-hooks
kubectl -n jitsi get pods,svc,endpointslices
kubectl -n jitsi port-forward --address=127.0.0.1 svc/jitsi-jitsi-meet-web 8081:8000
```

Le navigateur revient à `http://localhost:8081`. Valider BOSH et l'IP JVB. Garder
Caddy en ligne maintient l'exposition publique du Web, même après retour Jitsi.
Pour retirer cette exposition et le LB du bootstrap, après accord de retour
arrière et uniquement si la release est celle créée ici :

```bash
export CLOUDSDK_CORE_PROJECT=project-fcf2ef91-c005-4910-a10
EDGE_IP=$(gcloud compute addresses describe jitsi-edge-ip \
  --region=europe-west1 --format='value(address)')
helm uninstall jitsi-edge -n jitsi --wait --timeout 10m
kubectl -n jitsi get svc,pvc
# Attendre effectivement la disparition des ressources reseau gerees par GKE.
gcloud compute forwarding-rules list --filter="IPAddress=$EDGE_IP" \
  --format='table(name,region,IPAddress)'
gcloud compute addresses describe jitsi-edge-ip --region=europe-west1 \
  --format='yaml(address,status,users)'
```

Conserver le PVC/disque ACME : aucune suppression de PVC proposée. Une fois les
règles disparues, l'adresse sans utilisateur et la décision DNS prise, sa
libération requiert l'accord de nettoyage (perte de l'IP, abandon du DNS pointé) :

```bash
gcloud compute addresses delete jitsi-edge-ip --region=europe-west1
```

Retirer ou modifier le DNS DuckDNS manuellement selon la décision approuvée.
Le disque conservé reste facturable ; l'adresse inutilisée aussi tant qu'elle
n'est pas libérée. Ne pas supprimer le LB JVB ni utiliser Terraform destroy.

## CI/CD et localhost

Les deux fichiers de valeurs réels n'activent rien : le profil par défaut CD
reste localhost, `GKE_CD_ENABLED` reste inchangée, et aucune variable GitHub n'a
été créée. Le profil public requiert en plus `JITSI_ACCESS_PROFILE=public-edge`,
`JITSI_EDGE_CD_ENABLED=true`, `JITSI_PUBLIC_DOMAIN=jitsi-meet-m2.duckdns.org` et
`JITSI_EDGE_ADDRESS_NAME=jitsi-edge-ip` : valeurs futures documentées, non définies.
La CD exige déjà release edge/LB/PVC Bound et droit get PVC ; elle ne crée pas le
bootstrap. Ne jamais activer la CD localhost après migration publique : elle
pourrait restaurer l'URL localhost. Toute activation ou bascule reste à approuver.

Les fichiers `values-gke.yaml` et `values-jitsi-public.yaml` n'ont pas été modifiés.
Avant migration, localhost reste le comportement déployé. Après migration, un
simple port-forward ne restaure pas la configuration localhost : utiliser le
rollback documenté. CI statique et certificats/réunions sont des validations
séparées ; aucun succès de CI n'autorise une migration.


## Validations locales réellement exécutées

Avec les deux nouvelles surcharges : lint strict edge, rendu Helm et invariants
réseau/stockage réussis ; `caddy validate` réussi pour le domaine réel en staging
et en production, sans lancer de serveur. Le profil Jitsi fusionné avec le domaine
réel passe `check-render.py --edge`. Les 25 tests Python existants et
`scripts/validate.sh` (profils Jitsi/localhost et Terraform sans backend dans une
copie temporaire) réussissent. `git diff --check` ne signale pas d'erreur.
La CI distante n'a pas été relancée : ces nouvelles modifications sont locales.
Aucun test TLS externe, montage réel du volume, renouvellement ACME ou réunion
publique n'est validé. Aucun secret déchiffré et aucune ressource créée.


## Dernière vérification et séquence courte

La [séquence courte](bootstrap-https-court.md) précise les points d'arrêt et
les vérifications DNS/TLS/rollback. Contrôle renouvelé le 16 novembre : quotas
identiques, aucune réservation d'IP ni aucun PVC, quatre pods Ready sans Warning.
Les 48 autorisations opérateur Helm testées et les quatre permissions IAM de
réservation testées sont confirmées. get PVC reste refusé au compte CD.
Lint/rendus et `caddy validate` staging/production sont à nouveau réussis,
ainsi que le rendu Jitsi public. Aucun serveur ni déploiement lancé.
La PR nº 3 est ouverte avec deux checks verts sur `c591ad4`, qui n'inclut pas
les nouvelles surcharges locales. Une IPv4 régionale est possible au regard des
quotas ; l'allocation fournisseur ne sera confirmée qu'après réservation autorisée.


## Exécution autorisée des étapes 1 et 2 — arrêt sur erreur

Le 16 novembre 2026, les précontrôles et le lint ont réussi. La révision Jitsi 2
est conservée dans `deploy/local/jitsi-before-public.revision`, sans secret et
sans écrasement. La première tentative de réservation a échoué avec :
`IP Version is not supported for regional addresses.`

La commande préparée contenait à tort `--ip-version=IPV4`. L'aide locale confirme
que cette option est réservée aux adresses globales et que la valeur par défaut
est IPV4. Les commandes ci-dessus sont corrigées en supprimant cette option,
mais **aucune nouvelle tentative n'a été exécutée**.

Arrêt conformément à la demande : aucune adresse réservée dans le projet après
l'échec, aucun PVC ni release edge créé. Les quatre pods Jitsi restent Ready,
sans redémarrage ; la release reste déployée en révision 2. DuckDNS, production
ACME, profil Jitsi et permissions n'ont pas été modifiés.
Pour une reprise, refaire les précontrôles et vérifier la révision déjà capturée
sans réexécuter son écriture exclusive, puis reprendre à la réservation corrigée.
