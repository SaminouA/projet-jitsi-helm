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

## État des validations

Validé localement : lint/rendu Helm des deux profils, invariants de phase 1,
format et validation Terraform isolée, syntaxe et refus des IP invalides.
Non validés : IP LB réelle, phase 2 avec données réelles, config.js réellement
servi, BOSH en exécution, tunnels VS Code/SSH, restrictions SSH effectives,
caméra/micro, ICE/UDP, conférence à trois, nettoyage cloud et CI distante des
modifications actuelles. Aucun accès ni changement d'état Terraform, aucune
ressource cloud créée ou modifiée dans cette préparation. Aucun commit/push.
