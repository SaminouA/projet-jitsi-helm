# Accès public HTTPS : préparation de jitsi-edge

> Mise à jour de publication : le bootstrap, TLS production et la migration
> Jitsi ont été réalisés avec autorisation. Jitsi est en révision 3, Caddy en
> révision 2, Web 34.78.71.58, JVB 34.62.165.81. Les sections de préparation
> ci-dessous conservent leur contexte historique ; le rapport et le README
> décrivent l'état actuel. La CD reste désactivée.

Préparation du 16 novembre 2026. Aucun bootstrap, certificat, DNS ou déploiement
public n'a été réalisé dans cette étape. Le profil localhost reste disponible.

## Architecture et ressources prévues

Internet TCP 80/443 → LoadBalancer régional L4 → Caddy TCP 8080/8443 →
`jitsi-jitsi-meet-web.jitsi.svc.cluster.local:8000` (ClusterIP).
Le navigateur utilise `https://DOMAINE_REEL` ; `/http-bind` reste sur cette même
origine HTTPS et Caddy termine TLS. Le Web communique avec Prosody en interne.
Le bridge conserve son LoadBalancer UDP 10000 et annonce sa propre IP publique :
le DNS Web doit pointer vers l'IP **Caddy**, jamais automatiquement vers l'IP JVB.

Le chart complémentaire `charts/jitsi-edge` rend un Deployment, un Service et
une ConfigMap. Il vise exclusivement la release `jitsi-edge` dans `jitsi`, avec
l'amont Web de la release existante `jitsi`. Une seule réplique et la stratégie
Recreate évitent l'accès concurrent au disque RWO ; ce choix entraîne une brève
indisponibilité lors des mises à jour. Aucun Ingress ni certificat Kubernetes
supplémentaire n'est nécessaire.

Le manifeste séparé `deploy/jitsi-edge-storage.yaml` prévoit un PVC de 10 Gi,
`standard-rwo`, monté sur `/data`. Il n'appartient pas à la release Helm : une
désinstallation du chart ne le supprime pas. La suppression explicite du PVC
peut supprimer son disque (politique Delete) et les clés privées ACME : elle
doit être autorisée et précédée d'une décision de sauvegarde. Ne pas archiver
ces données dans Git. `/config` et `/tmp` sont éphémères. Le conteneur fonctionne
sans root, sans token Kubernetes, avec système racine en lecture seule.

Caddy est épinglé en version 2.11.9 avec digest d'image. HTTP est redirigé vers
HTTPS. ACME utilise d'abord le serveur staging (certificat non reconnu par les
navigateurs), puis production après vérification DNS et autorisation. Les ports
publics 80/443 doivent être joignables pour les challenges et renouvellements.
Le DNS gratuit DuckDNS ne nécessite pas de plugin DNS Caddy pour cette méthode ;
son jeton ne doit entrer ni dans le chart ni dans les logs. Ne pas publier d'AAAA
sans véritable chemin IPv6 : le Service préparé est IPv4 uniquement.

Les sondes HTTP sur 8082 `/healthz` vérifient Caddy, pas l'émission d'un certificat
ni l'état de Prosody/JVB. Seuls TCP 80/443 figurent dans le Service public.
L'administration Caddy est désactivée ; HTTP/3 est désactivé pour ne pas annoncer
UDP 443 absent du Service. Les chemins privés `/colibri`, `/colibri-ws`,
`/metrics`, `/debug`, `/healthz` et `/about/health` sont bloqués sur l'entrée HTTPS.
Aucun contrôle JVB, port 8082 de sonde ou API d'administration n'est publié.
Il s'agit de contrôles statiques d'exposition, pas d'un audit réseau en exécution.
Aucune NetworkPolicy n'est ajoutée : la joignabilité interne reste à auditer.

Le WebSocket XMPP reste désactivé ; BOSH utilise `window.location.origin`.
L'annonce Colibri WebSocket JVB n'est pas activée : le chart actuel ne fournit
pas de route complète vers ce service. Le transport existant doit être testé
sur une réunion externe ; ne pas ajouter une URL `wss` sans configurer et auditer
la route correspondante. L'accès anonyme actuel doit être explicitement accepté
pour la démonstration ou remplacé par une politique d'authentification avant
une exploitation publique durable.

## Profils et validation hors cluster

`values-gke.yaml` porte désormais l’URL HTTPS publique. Pour un profil localhost,
surcharger explicitement `publicURL=http://localhost:8081`. Ordre des valeurs du profil
public : `values-gke.yaml`, `values-jitsi-public.yaml`, URL réelle générée,
overlay contenant l'IP réelle JVB, secrets déchiffrés temporairement.
Les valeurs structurantes publiques n'ont pas de domaine par défaut.
`tests/fixtures/*` utilise uniquement `jitsi.invalid` et ne doit jamais être
appliqué au cluster. Le générateur refuse ces domaines réservés et les IP :

```sh
# À utiliser uniquement une fois le domaine réel et la réservation approuvés.
python3 scripts/public-values.py --domain "$JITSI_PUBLIC_DOMAIN" \
  --address-name "$JITSI_EDGE_ADDRESS_NAME" --acme staging
```

Ce générateur n'appelle aucun service cloud, refuse d'écraser des valeurs déjà
présentes et écrit `deploy/local/{jitsi,edge}.yaml`, exclus de Git. Il ne valide
pas la propriété du DNS ni l'existence de la réservation.

Commandes locales exécutables sans cluster (le téléchargement est vérifié par
SHA512 et reste temporaire ; il ne lance aucun serveur) :

```sh
validation_dir=$(mktemp -d)
sh scripts/fetch-caddy.sh "$validation_dir"
CADDY_BIN="$validation_dir/caddy" python3 scripts/validate-edge.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n scripts/deploy-gke.sh
sh -n scripts/fetch-caddy.sh
sh scripts/validate.sh
rm -rf -- "$validation_dir"
```

Résultats obtenus : 25 tests Python réussis, lint/rendu des deux charts, contrôle
du profil Jitsi fusionné, validation réelle du Caddyfile par `caddy validate`,
syntaxe Bash et validations Helm/Terraform existantes réussis. Terraform init et
validate opèrent sur une copie temporaire sans backend ni état du projet.
Aucun SOPS n'a été déchiffré pour ces tests. Les tests vérifient notamment le refus
des ports privés, hostNetwork, token de service et domaine fictif de déploiement.

## CI/CD préparée et migration à autoriser

Le job CI `Validation Helm` est conservé et étendu aux fixtures publiques,
à Caddy et aux tests Python. Les garde-fous CD existants restent en place :
OIDC, CI push main réussie, dépôt d'origine, SHA exact et encore tête de main,
concurrence sérialisée, SOPS/KMS temporaire privé et nettoyage.
Le défaut est `JITSI_ACCESS_PROFILE=localhost` ; le mode public exige aussi
`JITSI_EDGE_CD_ENABLED=true`, le domaine et le nom d'adresse réservée dans les
variables GitHub. `GKE_CD_ENABLED` demeure nécessaire.

La CD publique ne réalise **pas** le bootstrap : elle exige les objets edge
existants, appartenant à la bonne release, un LoadBalancer déjà attribué et un
PVC Bound. Elle refuse changement de réservation, de ports ou migration DNS.
Le droit RBAC `get persistentvolumeclaims` sera requis en plus des contrôles
existants (dont suppressions Helm et lecture Pods/ReplicaSets). Il n'a pas été
attribué ni vérifié sur le cluster dans cette préparation.
Les mises à jour des deux releases ne sont pas transactionnelles : l'échec de
Jitsi après une mise à jour Caddy nécessite une analyse et un retour arrière
contrôlé. Les sondes ne prouvent pas TLS : une vérification externe reste requise.

Ordre futur, soumis à autorisation :

1. Choisir le vrai sous-domaine, vérifier les quotas/IP et accepter les coûts.
2. Réserver une IPv4 régionale statique compatible avec le Service annoté
   `cloud.google.com/l4-rbs` et `networking.gke.io/load-balancer-ip-addresses`.
3. Créer le PVC et installer la release edge ; contrôler LB, disque et sondes.
4. Pointer le DNS vers l'IPv4 Caddy ; vérifier A/AAAA et propagation.
5. Vérifier ACME staging, puis autoriser production et le certificat reconnu.
6. Migrer explicitement Jitsi vers le profil public avec l'IP JVB existante et
   les secrets SOPS/KMS, sans rotation involontaire.
7. Tester BOSH et une réunion à trois participants sur des réseaux distincts,
   relever les statistiques JVB, puis autoriser éventuellement le mode CD public.

Commandes de vérification en lecture seule, à adapter après bootstrap :

```sh
kubectl get storageclass standard-rwo -o yaml
kubectl -n jitsi get deploy,pods,svc,pvc
kubectl -n jitsi get endpointslices
kubectl auth can-i get persistentvolumeclaims -n jitsi
helm status jitsi-edge -n jitsi
helm status jitsi -n jitsi
gcloud compute addresses list --project project-fcf2ef91-c005-4910-a10
gcloud compute forwarding-rules list --project project-fcf2ef91-c005-4910-a10
# Depuis un poste externe, après définition du vrai domaine :
nslookup "$JITSI_PUBLIC_DOMAIN"
curl --head "http://$JITSI_PUBLIC_DOMAIN/"
curl --head "https://$JITSI_PUBLIC_DOMAIN/"
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  "https://$JITSI_PUBLIC_DOMAIN/colibri/stats"
openssl s_client -connect "$JITSI_PUBLIC_DOMAIN:443" \
  -servername "$JITSI_PUBLIC_DOMAIN" -verify_return_error </dev/null
```

Attendus futurs : redirection HTTP vers HTTPS, certificat reconnu en production,
HTTP 404 sur le contrôle privé, BOSH sans contenu mixte dans le navigateur.
Ne pas contourner la validation TLS avec `curl -k` pour conclure à un succès.

## Ressources facturables et nettoyage futur

Aucune ressource n'a été créée. Prévision : un pod (requêtes 100 mCPU et 128 Mi,
limite mémoire 256 Mi) sur les nœuds existants, un disque persistant 10 Gi, une
IPv4 régionale et un LoadBalancer L4 avec ses ressources réseau gérées par GKE.
Aucun nouveau nœud n'est prévu ; la capacité réelle reste à contrôler.

Le tarif indicatif des cinq premières règles de forwarding est collectif,
0,025 USD/h par groupe tarifaire concerné, soit 18,25 USD sur 730 h. Le LB JVB
existant peut déjà occuper le même groupe régional : ne pas ajouter aveuglément
18,25 USD au total, ni en déduire que le nouveau LB sera gratuit. Traitement des
données, trafic sortant Internet et disque régional sont à chiffrer avec les SKU
europe-west1 et la consommation réelle. L'IPv4 rattachée à une règle de forwarding
n'a pas le même tarif qu'une réservation inutilisée, qui reste facturable.
Les nœuds/GKE continuent leur facturation existante. Aucun montant mensuel global
n'est validé ici ; consulter le calculateur et la facturation avant création.

Après la démonstration, une autorisation distincte doit couvrir la suppression
contrôlée de la release edge, la vérification de disparition du LB et de ses
règles, la libération de l'adresse et la décision explicite de conserver ou
supprimer PVC/disque/état ACME. Désinstaller Helm ne suffit pas à supprimer le
PVC indépendant ni l'adresse réservée. Aucune commande de nettoyage n'est lancée.

Sources techniques : [HTTPS automatique Caddy](https://caddyserver.com/docs/automatic-https),
[stockage Caddy](https://caddyserver.com/docs/conventions),
[tarification réseau GCP](https://cloud.google.com/vpc/network-pricing).


## Domaine réel réservé : préparation complémentaire

Le sous-domaine déclaré est désormais `jitsi-meet-m2.duckdns.org`. Les surcharges
réelles et le mode opératoire de bootstrap/retour arrière sont détaillés dans
[la préparation DuckDNS](https-duckdns.md). Le nom `jitsi-edge-ip` y est proposé,
mais aucune réservation GCP n'a été créée. Cette préparation n'active pas la CD.
