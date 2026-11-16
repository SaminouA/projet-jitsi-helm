# Jitsi Meet sur GKE : démonstration sans domaine

## Périmètre et architecture

Le cluster à deux nœuds et les quatre composants ont fonctionné auparavant selon
le porteur du projet ; l'entrée en réunion restait bloquée. Le cluster a été
détruit pour limiter les coûts. La présente préparation est entièrement locale.
Le chart officiel conservé est `charts-officiels/jitsi-meet` 3.10.0, application
stable-11248. `jitsi/` est un ancien squelette Nginx non utilisé.

```text
Chaque navigateur : http://localhost:8081
  -> tunnel local (SSH si poste distant) -> kubectl port-forward TCP
  -> Service Web ClusterIP:8000 -> Web:8000
  -> /http-bind -> proxy Web -> Prosody:5280 HTTP interne

Chaque navigateur -> IP publique du LB UDP:10000 -> JVB:10000
Jicofo et JVB -> Prosody XMPP interne
```

`PUBLIC_URL=http://localhost:8081`. Le chart monte `/config/custom-config.js`
avec `config.bosh = window.location.origin + '/http-bind';`. Le navigateur utilise
donc `http://localhost:8081/http-bind`. Le HTTP interne vers Prosody n'est pas une
URL exposée au navigateur. HTTPS est désactivé dans Web, sans redirection HTTP,
sans Ingress ni Gateway. Les navigateurs autorisent normalement caméra/micro sur
localhost, avec consentement utilisateur. Cette exception ne vaut pas pour une
IP LAN ou publique en HTTP. Tous les participants doivent utiliser leur propre
localhost, au même port, pas l'adresse du serveur SSH. Le transport entre le poste
et le serveur distant est protégé par SSH ; le média suit son chemin WebRTC.

Un seul JVB, un port nommé `rtp-udp-0`, UDP 10000 et un Service LoadBalancer.
`jvb.publicIPs` produit `JVB_ADVERTISE_IPS`. STUN, hostNetwork, hostPort et
useNodeIP sont désactivés pour éviter une adresse annoncée différente du LB.
Le port-forward transporte seulement TCP, jamais le média UDP. TURN reste
hors périmètre : un réseau bloquant l'UDP peut empêcher la réunion.

## Préparation locale et validations

Prérequis : Helm 3.22.1, Terraform 1.16.6, Python 3, PyYAML ; pour la prochaine
session : gcloud, plugin d'authentification GKE et kubectl. Depuis la racine :

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
sh scripts/validate.sh
```

Pour réutiliser le provider local et éviter son téléchargement :

```sh
TF_OFFLINE_PLUGIN_DIR="$PWD/terraform/.terraform/providers" sh scripts/validate.sh
```

Le contrôle partagé entre CI et hooks vérifie les deux fichiers de valeurs,
BOSH et son montage, le Service Web privé, l'absence d'Ingress, le sélecteur JVB,
son port nommé, UDP 10000 et JVB_PORT. `terraform fmt -check` et `validate`
s'exécutent avec une copie des seuls `.tf` et du lock provider dans un dossier
temporaire, initialisée avec `-backend=false -lockfile=readonly`. Aucun état du
projet n'est copié, consulté ou modifié. Les options TF_DATA_DIR, TF_WORKSPACE
et TF_CLI_ARGS des commandes utilisées sont neutralisées. Les manifests Helm
contiennent des Secrets XMPP générés : ne pas les publier ; le script les garde
dans son répertoire temporaire supprimé, sans artifact CI ni affichage.

Les hooks utilisent `core.hooksPath=.githooks`. La CI a seulement lecture du
dépôt ; aucune authentification GCP et aucun déploiement. Elle vérifie le profil
de phase 1 sans IP réelle. La phase 2 se contrôle localement via GKE_VALUES_FILE.
Le générateur historique `scripts/gke-values.py` reste une alternative HTTPS
avec domaine, non utilisée ici ; `mes-valeurs.yaml` contient un domaine fictif
réservé au rendu historique, jamais à un déploiement.

## Prochaine session : commandes de déploiement, NON exécutées ici

Ces commandes créent des ressources payantes ou modifient le cluster. Elles
nécessitent l'autorisation de la session de déploiement. Ne pas créer un nouvel
état pour contourner un état absent ou inconnu. Retrouver d'abord le répertoire,
les identifiants et l'état utilisés lors du déploiement initial ; ne pas les
supprimer ni les réinitialiser arbitrairement. Le backend est actuellement local.
Les commandes Terraform doivent être exécutées dans cet environnement identifié.
Les variables suivantes reprennent la configuration du dépôt, sans IP inventée :

```sh
export GCP_PROJECT=project-fcf2ef91-c005-4910-a10
export GKE_ZONE=europe-west1-b
export GKE_CLUSTER=jitsi-cluster
export JITSI_NAMESPACE=jitsi
export JITSI_RELEASE=jitsi
```

La release retenue est `jitsi` dans le namespace `jitsi`. Sans nameOverride ni
fullnameOverride, les noms vérifiés dans le rendu sont : Services
`jitsi-jitsi-meet-web`, `jitsi-jitsi-meet-jvb` et `jitsi-jitsi-meet-prosody` ;
Deployments `jitsi-jitsi-meet-web`, `jitsi-jitsi-meet-jicofo`,
`jitsi-jitsi-meet-jvb-0` ; StatefulSet `jitsi-jitsi-meet-prosody`.
Ne pas réutiliser les anciennes commandes avec la release `mon-jitsi`.

### 1. Recréer le cluster après examen du plan

```sh
gcloud auth login
gcloud auth application-default login
gcloud config set project "$GCP_PROJECT"
terraform -chdir=terraform init -lockfile=readonly
terraform -chdir=terraform plan -out=tfplan
terraform -chdir=terraform apply tfplan
gcloud container clusters get-credentials "$GKE_CLUSTER" \
  --zone "$GKE_ZONE" --project "$GCP_PROJECT"
kubectl config current-context
kubectl get nodes
```

Vérifier le contexte/projet avant toute commande Helm. Le fichier tfplan peut
contenir des données sensibles ; il est ignoré par Git et sera supprimé après usage.

### 2. Phase 1 : créer le Service et obtenir l'IP réelle

```sh
helm upgrade --install "$JITSI_RELEASE" ./charts-officiels/jitsi-meet \
  --namespace "$JITSI_NAMESPACE" --create-namespace \
  -f values-gke.yaml --wait --timeout 10m
export JVB_SERVICE="${JITSI_RELEASE}-jitsi-meet-jvb"
export WEB_SERVICE="${JITSI_RELEASE}-jitsi-meet-web"
kubectl -n "$JITSI_NAMESPACE" get pods,svc
kubectl -n "$JITSI_NAMESPACE" get svc "$JVB_SERVICE" --watch
```

Attendre EXTERNAL-IP puis arrêter seulement la surveillance avec Ctrl+C.
Cette phase n'est pas encore un test de réunion : JVB n'annonce pas l'IP LB.
Si Helm expire, inspecter pods/événements, ne pas lancer une seconde installation.

```sh
export JVB_PUBLIC_IP="$(kubectl -n "$JITSI_NAMESPACE" get svc "$JVB_SERVICE" \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
test -n "$JVB_PUBLIC_IP" || { echo 'IP LB encore indisponible'; false; }
python3 scripts/jvb-values.py --jvb-ip "$JVB_PUBLIC_IP" > values-gke.demo.yaml
GKE_VALUES_FILE=values-gke.demo.yaml sh scripts/validate.sh
```

Exécuter la suite seulement si génération ET validation réussissent. Le générateur
refuse une IP vide, privée ou invalide, sans appeler GCP. Le fichier contient
uniquement `jvb.publicIPs`, sans domaine ni certificat, et est ignoré par Git.

### 3. Phase 2 : finaliser l'annonce JVB

```sh
helm upgrade "$JITSI_RELEASE" ./charts-officiels/jitsi-meet \
  --namespace "$JITSI_NAMESPACE" \
  -f values-gke.yaml -f values-gke.demo.yaml --wait --timeout 10m
kubectl -n "$JITSI_NAMESPACE" rollout status \
  "deployment/${JITSI_RELEASE}-jitsi-meet-jvb-0" --timeout=180s
kubectl -n "$JITSI_NAMESPACE" get svc "$JVB_SERVICE" \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}{"\n"}{.spec.ports}{"\n"}'
kubectl -n "$JITSI_NAMESPACE" exec "deployment/${JITSI_RELEASE}-jitsi-meet-jvb-0" \
  -- printenv JVB_ADVERTISE_IPS JVB_PORT
```

Comparer l'IP du Service et celle annoncée ; elles doivent être identiques et
le port égal à 10000. La mise à jour conserve le Service existant ; si son IP
change lors d'une recréation, régénérer la surcharge et refaire la phase 2.
Vérifier les règles pare-feu/health checks GKE si l'UDP reste inaccessible :

```sh
kubectl -n "$JITSI_NAMESPACE" describe svc "$JVB_SERVICE"
gcloud compute firewall-rules list --project "$GCP_PROJECT"
```

Ne pas exposer Prosody ni ouvrir manuellement tous les ports des nœuds.

## Accès depuis VS Code Remote SSH

Dans un terminal VS Code **sur le serveur distant**, garder ce processus actif :

```sh
kubectl -n "$JITSI_NAMESPACE" port-forward --address 127.0.0.1 \
  "svc/$WEB_SERVICE" 8081:8000
```

Dans l'onglet **Ports** de VS Code, transférer le port distant 8081 et vérifier
que le port local attribué est aussi 8081, avec accès local/privé. Libérer 8081
s'il est occupé ; ne pas accepter silencieusement un autre port. Ouvrir dans le
navigateur de l'ordinateur local `http://localhost:8081`. Le localhost du serveur
SSH et celui du poste sont distincts : les deux niveaux de tunnel sont nécessaires.
Ne pas écouter sur 0.0.0.0 et ne pas publier un lien VS Code public.

## Autres participants : tunnel SSH limité, sans accès Kubernetes

Le responsable maintient le port-forward ci-dessus sur le serveur SSH. Chaque
participant utilise son propre compte SSH dédié et sa propre clé, sans kubeconfig
ni identifiants GCP. L'administrateur configure sur ce serveur un accès limité :
transfert local uniquement vers 127.0.0.1:8081, aucun shell ni session, aucun agent
ou X11, authentification par clé, pas de mot de passe. Exemple de bloc sshd à
adapter aux vrais comptes (à vérifier avec sshd -t avant rechargement ; non
appliqué ici) :

```text
Match Group jitsi-demo
    AuthenticationMethods publickey
    PasswordAuthentication no
    AllowTcpForwarding local
    PermitOpen 127.0.0.1:8081
    AllowAgentForwarding no
    X11Forwarding no
    PermitTTY no
    MaxSessions 0
```

Les comptes, le groupe et les clés doivent être réellement provisionnés par
l'administrateur ; vérifier les restrictions effectives avec `sshd -T -C` pour
chaque compte. MaxSessions 0 interdit les sessions tout en permettant les tunnels.
Aucun participant ne reçoit l'accès administrateur du serveur. Le serveur doit
être joignable en SSH ; sinon cette méthode est bloquée et il faut organiser un
accès réseau autorisé, pas exposer Web en HTTP public.

Sur chaque ordinateur participant, après définition de SSH_DEMO_USER et
SSH_DEMO_HOST avec son compte et le serveur réels :

```sh
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8081:127.0.0.1:8081 "$SSH_DEMO_USER@$SSH_DEMO_HOST"
```

Vérifier l'empreinte du serveur ; ne pas désactiver StrictHostKeyChecking.
Garder le tunnel actif puis ouvrir `http://localhost:8081/demo-master2` sur
chaque ordinateur. Le nom `demo-master2` est un nom de salle de démonstration.
Les participants n'ont pas besoin de kubectl. Ne pas cumuler un tunnel VS Code
et SSH manuel sur le même port local. Tout utilisateur du même serveur capable
d'accéder à son loopback peut joindre ce Web : utiliser un serveur de confiance
et limiter la durée de la session. L'authentification Jitsi est désactivée.

## Vérifications fonctionnelles de la prochaine session

Dans le navigateur local : autoriser caméra/micro ; vérifier `window.isSecureContext`
et `navigator.mediaDevices` dans la console, puis les requêtes réseau BOSH.
Depuis le terminal où le tunnel est disponible :

```sh
curl --fail http://localhost:8081/ -o /dev/null
curl --fail http://localhost:8081/config.js | rg 'bosh|http-bind'
curl -i -H 'Content-Type: text/xml' --data \
  '<body rid="1" xmlns="http://jabber.org/protocol/httpbind" to="meet.jitsi" wait="5" hold="1" ver="1.6"/>' \
  http://localhost:8081/http-bind
```

Attendre une réponse BOSH XML de Prosody, normalement HTTP 200 avec une session ;
une page HTML, 404/502 ou une terminaison d'erreur impose un diagnostic. Ce POST
n'est qu'un contrôle de signalisation, pas une authentification/réunion complète.
Vérifier que le config.js servi contient la surcharge BOSH ; le rendu Helm seul
ne prouve pas son intégration par l'image. Dans le navigateur, les requêtes doivent
cibler localhost:8081/http-bind, jamais le DNS Kubernetes interne.

```sh
helm test "$JITSI_RELEASE" -n "$JITSI_NAMESPACE" --logs
kubectl -n "$JITSI_NAMESPACE" logs "deployment/${JITSI_RELEASE}-jitsi-meet-web" --tail=100
kubectl -n "$JITSI_NAMESPACE" logs "statefulset/${JITSI_RELEASE}-jitsi-meet-prosody" --tail=100
kubectl -n "$JITSI_NAMESPACE" logs "deployment/${JITSI_RELEASE}-jitsi-meet-jicofo" --tail=100
kubectl -n "$JITSI_NAMESPACE" logs "deployment/${JITSI_RELEASE}-jitsi-meet-jvb-0" --tail=100
```

Helm test ne vérifie que la réponse HTTP Web interne. Réunir trois ordinateurs
sur la même salle, idéalement sur deux réseaux, pendant 10–15 min ; confirmer
son/image bidirectionnels, départ/reconnexion, candidats ICE vers l'IP LB:10000
et utilisation du bridge via les statistiques WebRTC et logs. Un test à deux
peut utiliser P2P. Un test `nc -u` seul ne prouve pas l'ouverture UDP/WebRTC.
Masquer jetons, noms de salles et données personnelles avant de partager des logs.

## Nettoyage après la démonstration, sur autorisation

Ne pas exécuter ces commandes pendant la préparation. Fermer les tunnels avec
Ctrl+C, retirer les accès SSH temporaires selon la procédure administrateur.
Supprimer la release avant le cluster afin de laisser GKE nettoyer son LB :

```sh
helm uninstall "$JITSI_RELEASE" --namespace "$JITSI_NAMESPACE" --wait --timeout 10m
kubectl -n "$JITSI_NAMESPACE" get svc,pvc
# Vérifier la disparition du LB et de ses règles avant de détruire GKE :
gcloud compute forwarding-rules list --project "$GCP_PROJECT"
gcloud compute addresses list --project "$GCP_PROJECT"
terraform -chdir=terraform plan -destroy -out=tfplan-destroy
terraform -chdir=terraform apply tfplan-destroy
# Inventaire final en lecture seule :
gcloud container clusters list --project "$GCP_PROJECT"
gcloud compute forwarding-rules list --project "$GCP_PROJECT"
gcloud compute addresses list --project "$GCP_PROJECT"
gcloud compute disks list --project "$GCP_PROJECT"
rm -f terraform/tfplan terraform/tfplan-destroy values-gke.demo.yaml
```

Ne jamais supprimer l'état Terraform. Ne pas supprimer automatiquement d'autres
ressources du projet : identifier leur propriétaire. Les fichiers de plan sont
locaux ; le motif tfplan-* est ignoré par Git. Contrôler les IP réservées, disques,
LB résiduels et la facturation. Les nœuds, stockage, LB et trafic peuvent coûter
de l'argent pendant la session ; ne pas laisser l'infrastructure active inutilement.

## État des validations à la fin de la préparation hors ligne

Cet état décrit la phase de préparation ; les résultats de la session du
15 novembre 2026 sont consignés dans la section suivante.

Validé localement : lint/rendu Helm des deux profils, invariants de phase 1,
format et validation Terraform isolée, syntaxe et refus des IP invalides.
Non validés : IP LB réelle, phase 2 avec données réelles, config.js réellement
servi, BOSH en exécution, tunnels VS Code/SSH, restrictions SSH effectives,
caméra/micro, ICE/UDP, conférence à trois, nettoyage cloud et CI distante des
modifications actuelles. Aucun accès ni changement d'état Terraform, aucune
ressource cloud créée ou modifiée dans cette préparation. Aucun commit/push.


## Validation fonctionnelle de Jitsi — 15 novembre 2026

### Déploiement et accès à l'interface

Le cluster GKE `jitsi-cluster` est opérationnel avec deux nœuds `Ready`.
La release Helm `jitsi`, dans le namespace `jitsi`, est déployée avec succès
à la révision 2. Les pods Web, Prosody, Jicofo et JVB sont `Running`.

L'accès depuis Windows repose sur deux transferts successifs. Sur la VM, le
port-forward Kubernetes relie le port loopback 8081 au port 8000 du Service Web :

```sh
kubectl -n jitsi port-forward --address 127.0.0.1 \
  svc/jitsi-jitsi-meet-web 8081:8000
```

Dans VS Code Remote SSH, le port distant 8081 est ensuite transféré vers le
port local Windows 8081. L'interface est accessible dans le navigateur Windows
à `http://localhost:8081`, sans domaine ni certificat TLS pour cet accès local.

### Incident de transfert VS Code et résolution

Le premier transfert VS Code acceptait les connexions TCP mais ne transmettait
aucune réponse HTTP. Les contrôles sur la VM ont confirmé que le processus
`kubectl port-forward` écoutait correctement sur `127.0.0.1:8081`, que le Service
Web disposait d'un endpoint prêt et qu'une requête HTTP locale recevait
`200 OK`. Le chemin Kubernetes vers Web fonctionnait donc pendant l'incident.

La suppression du transfert de port dans VS Code, puis sa recréation manuelle
vers le port distant 8081, ont rétabli l'accès depuis Windows. Cette manipulation
concernait uniquement le transfert VS Code ; elle n'a pas nécessité de modifier
le déploiement Jitsi ou les règles réseau GCP.

### Résultats du test à un participant

Les contrôles techniques ont confirmé une réponse HTTP 200 de Web, la présence
de la surcharge BOSH dans le `config.js` servi et l'ouverture d'une session BOSH
via le proxy Web. Depuis Windows, la salle « demo » a été rejointe avec succès.
La caméra affichait l'image à l'écran, le microphone était détecté et
l'utilisateur était identifié comme modérateur.

Le test fonctionnel avec un seul participant est validé. Il confirme l'accès à
l'interface, l'entrée dans une salle et l'utilisation locale des périphériques.
La détection du microphone ne prouve pas la transmission du son à un autre
participant ; l'aperçu caméra ne prouve pas non plus la transmission vidéo.

### Résultats du test à deux participants

Deux participants, « nadira » et « test », se sont connectés simultanément à
la salle « demo ». Les essais ont été réalisés avec deux sessions sur un même
ordinateur Windows, via `http://localhost:8081` et le transfert de port
VS Code Remote SSH.

La transmission vidéo entre les deux sessions est validée. La transmission
audio a été confirmée par l'utilisatrice. Le chat collectif et les messages
privés sont fonctionnels ; la liste des participants affiche les deux
utilisateurs. Ces résultats complètent le premier test à un participant et
valident les fonctions observées dans cette configuration locale.

### Validation de Jitsi Videobridge — conférence à trois participants

**Date : 15 novembre 2026.** Les participants « nadira », « test » et « test3 »
étaient connectés simultanément à la salle « demo » lors du diagnostic en
lecture seule. Deux lectures de l'API JVB `/colibri/stats` ont été réalisées à
15:56:39 et 15:56:55, heure de Paris, avec un intervalle mesuré de
**15,271 secondes**.

| Indicateur | Première mesure | Seconde mesure |
|---|---:|---:|
| `healthy` | `true` | `true` |
| `conferences` | 1 | 1 |
| `inactive_conferences` | 0 | 0 |
| `participants` | 3 | 3 |
| `endpoints` | 3 | 3 |
| `p2p_conferences` | 0 | 0 |
| `bit_rate_download` | 829 | 693 |
| `bit_rate_upload` | 892 | 722 |
| `packet_rate_download` | 269 | 245 |
| `packet_rate_upload` | 257 | 232 |

Les débits et taux de paquets sont conservés comme valeurs brutes de l'API,
sans conversion ni attribution d'unités non vérifiées. Les compteurs cumulés
suivants n'ont pas varié sur cet intervalle :

| Compteur | Valeur aux deux mesures | Variation |
|---|---:|---:|
| `total_bytes_received` | 143 354 | 0 |
| `total_bytes_sent` | 10 500 | 0 |
| `total_packets_received` | 1 813 | 0 |
| `total_packets_sent` | 214 | 0 |

Leur stabilité ne constitue pas une preuve d'augmentation du trafic pendant
les 15,271 secondes. Aucune explication de leur mode d'actualisation n'a été
établie par ce diagnostic.

Les compteurs ICE indiquaient **5 succès et 0 échec** ; il s'agit des totaux
observés, pas nécessairement de cinq nouvelles connexions pendant l'intervalle.
Les logs récents JVB montraient `ICE connected` et une transition vers
`Completed`, sans erreur ICE détectée dans la fenêtre examinée.

Dans le fonctionnement habituel de Jitsi, deux participants peuvent échanger
leurs médias directement en mode pair-à-pair. L'arrivée d'un troisième
participant provoque normalement le passage au pont vidéo plutôt que le
maintien de cette connexion P2P à deux. Jicofo organise la conférence et
l'utilisation du bridge ; JVB reçoit les flux des participants et les
retransmet aux destinataires. Dans cette architecture, son accès média public
est exposé par le LoadBalancer UDP 10000, indépendamment des tunnels TCP
utilisés pour l'interface Web et BOSH.

L'activité média sur JVB est **fortement étayée** par la conférence active à
trois endpoints, l'absence de conférence comptabilisée en P2P et les débits
entrants et sortants non nuls. Les connexions ICE réussies soutiennent ce
constat de connectivité. Ces observations ne constituent toutefois pas une
validation individuelle de chaque flux audio et vidéo reçu par chacun des
participants ; elles ne doivent pas être confondues avec une mesure de qualité
ou de capacité.

### Tests de performance — référence au repos

**Date : 15 novembre 2026.** Le scénario `reference-repos-confirme` a été
observé de 16:21:27 à 16:23:27, heure de Paris. Les données proviennent de
`tests/results/20261115T152127.518271Z_reference-repos-confirme/` et ont été collectées avec `scripts/monitor-load.sh`, sans générer
de charge.

La collecte s'est achevée normalement après **120,001 secondes**, sans
interruption : **8 relevés**, cadence configurée de 15 secondes et **zéro
erreur de collecte**. Les relevés vont du lancement à la seconde 105.0 ;
la durée totale inclut l'attente finale. Les fichiers JSONL sont lisibles et
le nombre de relevés correspond au bilan `summary.json`.

Sur tous les relevés, `conferences=0`, `participants=0` et `endpoints=0`.
JVB est resté `healthy=true`. Cette exécution constitue donc une référence
au repos valide pour la période observée, contrairement au scénario précédent
`reference-sans-participants`, qui comportait encore trois participants.

| Ressource | CPU min. (mCPU) | CPU moyen (mCPU) | CPU max. (mCPU) | Mémoire min. (Mio) | Mémoire moyenne (Mio) | Mémoire max. (Mio) |
|---|---:|---:|---:|---:|---:|---:|
| JVB | 6,299 | 8,632 | 11,070 | 303,578 | 303,580 | 303,582 |
| Nœud `…ddx2` | 123,128 | 128,622 | 140,299 | 2220,863 | 2224,256 | 2227,859 |
| Nœud `…jjk0` | 118,544 | 128,161 | 138,823 | 2055,973 | 2058,711 | 2061,828 |

Les valeurs CPU sont converties depuis les quantités Kubernetes :
1 mCPU = 1 000 000 nanocœurs et 1 CPU = 1 000 mCPU. Pour la mémoire,
1 Mio = 1 024 Kio = 1 048 576 octets. Les moyennes sont arithmétiques sur les
8 relevés, en sommant les conteneurs pour le pod JVB. Metrics Server peut
retourner une même observation à plusieurs lectures ; les nombres d'horodatages
source distincts sont : nœud …ddx2 : 4, nœud …jjk0 : 4, JVB : 4. Les minima et maxima sont ceux des
observations collectées, pas des pics instantanés garantis.

Les quatre pods Web, Prosody, Jicofo et JVB sont restés `Running` et `Ready`
sur tous les relevés, avec un compteur de redémarrages égal à zéro.
La disponibilité observée des pods ne remplace pas un test utilisateur ou
une mesure HTTP continue. Cette référence courte décrit la consommation au
repos ; elle ne permet pas de déduire une capacité maximale ni la performance
sous charge.

### Tests de performance — palier à trois participants

**Date : 15 novembre 2026.** Le scénario `palier-3-participants` est comparé
à la dernière exécution de `reference-repos-confirme` du même jour. Sources :

- `tests/results/20261115T152127.518271Z_reference-repos-confirme/`
- `tests/results/20261115T152725.078684Z_palier-3-participants/`

Les bilans `summary.json` indiquent respectivement **120,001 secondes et
8 relevés** pour le repos, puis **300,001 secondes et 20 relevés** pour le
palier. Les deux collectes sont terminées sans interruption, avec zéro échec
de requête. Les fichiers `errors.jsonl` sont vides et aucun relevé ne contient
d'erreur de collecte. La cadence configurée est de 15 secondes. Pour le palier,
le premier et le dernier relevés sont séparés de 285 secondes ; la durée totale
inclut l'attente finale.

#### Comparaison des ressources

| Ressource | Scénario | CPU min. (mCPU) | CPU moyen (mCPU) | CPU max. (mCPU) | Mémoire min. (Mio) | Mémoire moyenne (Mio) | Mémoire max. (Mio) |
|---|---|---:|---:|---:|---:|---:|---:|
| JVB | Repos | 6,299 | 8,632 | 11,070 | 303,578 | 303,580 | 303,582 |
| JVB | Palier 3 | 3,089 | 85,794 | 142,609 | 303,582 | 305,922 | 307,879 |
| Nœud `…ddx2` | Repos | 123,128 | 128,622 | 140,299 | 2220,863 | 2224,256 | 2227,859 |
| Nœud `…ddx2` | Palier 3 | 105,472 | 198,941 | 302,259 | 2223,504 | 2228,494 | 2232,629 |
| Nœud `…jjk0` | Repos | 118,544 | 128,161 | 138,823 | 2055,973 | 2058,711 | 2061,828 |
| Nœud `…jjk0` | Palier 3 | 113,430 | 129,523 | 162,221 | 2052,543 | 2057,631 | 2060,398 |

Conversions : 1 mCPU = 1 000 000 nanocœurs ; 1 Mio = 1 024 Kio.
Les moyennes arithmétiques portent sur tous les relevés de chaque scénario,
en sommant les conteneurs pour JVB. Les compteurs CPU/mémoire ont quatre
horodatages source distincts par ressource au repos et dix au palier : des
lectures successives réutilisent certaines observations Metrics Server.

#### Conférence, média et stabilité

Le palier ne maintient pas trois participants pendant toute la collecte :
quatre relevés indiquent zéro conférence et zéro endpoint, un relevé indique
une conférence avec deux endpoints mais aucun endpoint local actif, puis
quinze relevés indiquent une conférence avec trois endpoints et trois
endpoints locaux actifs. Ces quinze observations vont de 16:28:40 à 16:32:10,
heure de Paris. Les moyennes ci-dessus incluent donc la montée en charge et
ne sont pas les moyennes d'un régime constant à trois participants.

| Statistique JVB | Repos : min. / moyenne / max. | Palier : min. / moyenne / max. |
|---|---:|---:|
| `conferences` | 0 / 0 / 0 | 0 / 0,8 / 1 |
| `participants` et `endpoints` | 0 / 0 / 0 | 0 / 2,35 / 3 |
| `local_active_endpoints` | 0 / 0 / 0 | 0 / 2,25 / 3 |
| `bit_rate_download` | 0 / 0 / 0 | 0 / 594,85 / 827 |
| `bit_rate_upload` | 0 / 0 / 0 | 0 / 724,3 / 1 029 |
| `packet_rate_download` | 0 / 0 / 0 | 0 / 207,9 / 315 |
| `packet_rate_upload` | 0 / 0 / 0 | 0 / 321,85 / 452 |

Les débits et taux de paquets conservent les valeurs brutes de l'API, sans
unités ajoutées. Une conférence inactive et une conférence P2P sont chacune
signalées sur un relevé transitoire ; aucun des quinze relevés à trois
endpoints actifs n'est comptabilisé en P2P ou comme conférence inactive.
JVB reste `healthy=true` sur tous les relevés.

`total_ice_failed`, `endpoints_ice_failed`, `relays_ice_failed` et
`dtls_failed_endpoints` restent à zéro. `total_ice_succeeded` passe de 5 à 8,
soit trois succès supplémentaires pendant le palier. Les compteurs cumulés
`total_bytes_received`, `total_bytes_sent`, `total_packets_received` et
`total_packets_sent` restent respectivement à 126 702 372, 133 997 464,
355 307 et 320 743 : aucune augmentation n'est observée sur cet intervalle.
Ils ne doivent pas être utilisés comme preuve d'un volume transféré pendant
le test ; les débits non nuls et les endpoints actifs étayent l'activité média.

Les pods Web, Prosody, Jicofo et JVB sont `Running` et `Ready` sur les 20
relevés du palier, comme sur les 8 relevés de repos. Leurs compteurs de
redémarrages restent à zéro. Ce constat porte sur les instants échantillonnés,
pas sur une disponibilité continue mesurée par un client. L'absence d'erreur
de collecte ou d'échec ICE ne constitue pas une analyse exhaustive des logs.

#### Portée du résultat

Le CPU moyen JVB est plus élevé que lors du repos, tandis que sa mémoire
reste proche de la référence. Ce résultat décrit un petit palier observé ;
il ne détermine ni la capacité maximale du bridge, ni une limite de
participants supportés, ni une performance garantie.

Les durées des scénarios diffèrent, le palier inclut l'arrivée des participants
et les mesures Metrics Server ne sont pas toutes indépendantes. Aucun profil
constant de résolution, de cadence vidéo ou de nombre d'émetteurs n'est
consigné dans ces fichiers. Ils ne valident ni chaque flux reçu, ni les
échanges entre réseaux distincts, ni la latence ou la qualité audio/vidéo.
Les performances des postes générateurs et des tunnels ne sont pas mesurées.
Des paliers stabilisés, répétés et à des charges supérieures seront nécessaires
pour poursuivre l'évaluation.

### Limites et validations restantes

Les échanges entre deux réseaux différents restent à valider séparément.
Le diagnostic à trois participants étaye l'activité média du bridge, mais
une vérification des statistiques WebRTC côté navigateurs et des observations
de chaque participant reste nécessaire pour valider individuellement les
flux reçus. Le chemin média du précédent test à deux participants n'a pas été
établi rétrospectivement.

Les tests à des charges supérieures restent à réaliser. Les valeurs brutes de débit
ci-dessus ne constituent pas une évaluation de performance ; aucune mesure
de latence, de qualité ou de capacité sous charge n'a été validée à ce stade.
