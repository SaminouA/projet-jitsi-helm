# Préparation du déploiement Jitsi Meet sur GKE

## Périmètre et état du projet

Le cluster GKE à deux nœuds et les composants Web, Prosody, Jicofo et JVB ont
été déployés auparavant, selon le retour du porteur du projet. L'interface Web
était accessible, mais l'entrée en réunion échouait. Le cluster a été détruit
volontairement pour réduire les coûts. Aucun test cloud n'est réalisé dans cette
phase. Les contrôles statiques ne prouvent pas le fonctionnement d'une réunion.

Le chart réutilisé sans modification est `charts-officiels/jitsi-meet`, version
3.10.0, images applicatives `stable-11248`. `jitsi/` est un ancien squelette
Nginx, pas le chart utilisé. `mes-valeurs.yaml` reste un exemple historique de
rendu : son domaine est fictif et ne constitue pas une cible de déploiement.

## Architecture retenue

```text
Navigateur -- HTTPS 443 --> Ingress GCE (certificat TLS)
                             |
                             +-- HTTP --> Service Web NodePort:8000 --> Web:8000
                                                                          |
                       /http-bind, proxy BOSH HTTP interne --> Prosody:5280

Participants -- UDP 10000 --> LoadBalancer public JVB --> JVB:10000
Jicofo / JVB -- XMPP interne --> Prosody
```

La surcharge `web.custom.configs._custom_config_js` fixe explicitement
`config.bosh = window.location.origin + '/http-bind';`. Elle est montée sur
`/config/custom-config.js` via le mécanisme prévu par le chart officiel.
Le navigateur utilise ainsi son protocole réel : HTTP en accès local, HTTPS
sur le site public. Cela évite de déduire le protocole de BOSH du HTTP interne.
La présence dans le `config.js` réellement servi reste à vérifier au déploiement.

Le navigateur utilise la même origine HTTPS pour la page et BOSH `/http-bind`.
Il ne doit jamais contacter un nom `*.svc.cluster.local`, ni un endpoint HTTP
Prosody directement. `XMPP_BOSH_URL_BASE=http://…:5280` est la destination
interne du proxy Web ; elle ne justifie pas à elle seule un diagnostic de contenu
mixte. `DISABLE_HTTPS=1` dans Web est conservé : TLS se termine à l'Ingress.
Les WebSockets XMPP restent désactivés pour réduire les variables de diagnostic.

Le domaine public doit pointer vers l'adresse de l'Ingress Web. Le certificat
doit couvrir exactement ce domaine. Le Secret Kubernetes de type
`kubernetes.io/tls` doit contenir ce certificat et sa clé dans le namespace de
Jitsi. Le générateur ne vérifie ni la propriété du DNS, ni l'existence du Secret,
ni la validité du certificat. Il produit seulement des valeurs Helm.

L'Ingress est sélectionné par l'annotation `kubernetes.io/ingress.class: gce`.
La surcharge publique passe Web en `NodePort` pour le backend classique GCE :
le profil local reste en `ClusterIP`. Cela évite de dépendre de NEGs implicites
pour un Service ClusterIP ; une variante NEG exigerait une configuration et une
validation dédiées. Ne pas ouvrir manuellement le NodePort aux participants :
l'accès prévu reste l'Ingress, avec ses sondes et règles réseau à vérifier.
Aucun contrôleur Nginx supplémentaire n'est prévu. La configuration garde HTTP
sans redirection automatique ; utiliser explicitement l'URL HTTPS. Une politique
de redirection pourra être ajoutée et testée séparément, notamment sans casser
les sondes de santé du load balancer. Le HTTP interne n'assure pas de chiffrement
entre pods : acceptable pour ce périmètre de démonstration, à réévaluer pour une
production.

## Deux profils distincts

`values-gke.yaml` est un profil de préparation : `http://localhost:8081` est
une URL complète réservée à un accès local via port-forward. Ce n'est pas l'URL
publique du projet. Le futur port-forward relierait le port local 8081 au port
8000 du Service Web. Il ne transporte pas l'UDP JVB.

Le fichier prépare déjà un Service JVB LoadBalancer UDP. **Ne pas installer ce
profil seul sur GKE** : cela pourrait créer un load balancer facturable, sans
rendre pour autant la visioconférence publique opérationnelle.

Une surcharge publique, ignorée par Git, doit être générée à partir de données
réelles. Après avoir défini les trois variables avec vos informations :

```sh
python3 scripts/gke-values.py \
  --domain "$JITSI_DOMAIN" \
  --tls-secret "$JITSI_TLS_SECRET" \
  --jvb-ip "$JVB_PUBLIC_IP" > values-gke.public.yaml
GKE_VALUES_FILE=values-gke.public.yaml sh scripts/validate.sh
```

Ces commandes génèrent et valident des fichiers locaux uniquement. La surcharge
s'utilise après `values-gke.yaml` dans l'ordre des arguments Helm `-f`. Aucune
commande de déploiement n'est exécutée par ces scripts.

Informations encore nécessaires :

- Un domaine réel contrôlé, et l'accès à sa zone DNS.
- Le choix d'obtention du certificat et le nom du Secret TLS réel. Un certificat
  déjà disponible est le chemin prévu ici ; cert-manager ou un certificat géré
  GCP nécessiteraient une configuration complémentaire, non incluse.
- L'IPv4 publique du LoadBalancer UDP JVB, distincte de l'IP Web.

Sans IP réservée déjà disponible, l'IP JVB ne sera connue qu'après création
future du Service LoadBalancer autorisée. Il faudra alors injecter son adresse
avec `jvb.publicIPs` et mettre à jour JVB avant le test. Avec une adresse réservée,
son association au LB devra être configurée selon le mécanisme GKE retenu ; le
générateur ne réserve ni n'attache une adresse. Une recréation du LB peut changer
son IP : vérifier à chaque fois la correspondance avec l'adresse annoncée.

## Chemin média JVB

Un seul JVB est prévu, sur UDP 10000, derrière un LoadBalancer L4. Le trafic
média ne passe pas par l'Ingress HTTP. `jvb.publicIPs` devient la variable
`JVB_ADVERTISE_IPS` dans le pod. STUN est désactivé pour éviter d'annoncer une
adresse NAT différente de celle du LB. `useNodeIP` reste désactivé : l'adresse
interne d'un nœud ne constitue pas une adresse publique utilisable.

Lors de la prochaine session GCP autorisée, vérifier l'adresse attribuée, les
règles pare-feu UDP 10000, les health checks et l'accessibilité depuis un réseau
externe. Ne pas exposer les ports XMPP de Prosody publiquement. TURN est désactivé
pour le premier objectif ; certains réseaux restrictifs nécessiteront un relais
TURN/TURNS et des tests supplémentaires.

## Validation reproductible hors cloud

Prérequis : Helm 3.22.1, Terraform 1.16.6 (compatible avec `versions.tf`), Python
3 et la dépendance suivante. La CI installe les mêmes versions d'outils.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
sh scripts/validate.sh
```

Le téléchargement de dépendances peut nécessiter Internet, mais aucun accès GCP
ni identifiant cloud n'est requis. Pour réutiliser les providers déjà présents
et effectuer les contrôles sans téléchargement Terraform :

```sh
TF_OFFLINE_PLUGIN_DIR="$PWD/terraform/.terraform/providers" sh scripts/validate.sh
```

Le script commun aux hooks et à GitHub Actions :

1. Exécute `helm lint --strict` et `helm template` pour les deux fichiers existants.
2. Inspecte le rendu GKE : URL locale complète, BOSH interne, type du Service Web selon le profil,
   Service JVB LoadBalancer et UDP 10000. Avec `GKE_VALUES_FILE`, vérifie également
   la cohérence URL HTTPS / DNS Ingress / référence TLS et l'IP annoncée par JVB.
3. Exécute `terraform fmt -check`, copie seulement les fichiers `.tf` et le lock
   provider dans un répertoire temporaire, puis y lance `init -backend=false
   -input=false -lockfile=readonly` et `validate`.
4. Supprime ce répertoire temporaire. Aucun état, backend ni dossier `.terraform`
   du projet n'est copié ou modifié. Le script neutralise `TF_DATA_DIR`,
   `TF_WORKSPACE` et les injections `TF_CLI_ARGS` pour les commandes utilisées.

Les hooks exigent ces outils installés et bloquent commit/push en cas d'échec.
Leur activation locale se fait avec `git config core.hooksPath .githooks` ; cette
option est déjà configurée dans le dépôt de travail inspecté. La CI couvre les
pushes sur toutes les branches et les PR vers `main`, avec permission de lecture
du dépôt uniquement. Elle ne déploie rien et n'utilise aucun secret cloud.

## Résultats de cette phase et limites

- Lint strict et rendu complet des deux profils : réussis.
- Contrôles d'invariants du rendu GKE local : réussis.
- Format et validation Terraform isolée avec provider Google 7.46.1 : réussis.
- Profil public avec données réelles : non testé, données externes indisponibles.
- Revue finale : correction du sélecteur de Deployment JVB (`…-jvb-0`),
  vérification du mapping Service/port nommé/pod UDP et fixation explicite de
  BOSH sur l'origine du navigateur. Service public Web corrigé en NodePort.
- Les manifests rendus peuvent contenir les Secrets XMPP générés par le chart :
  ils restent dans un répertoire temporaire supprimé, sans affichage ni artifact
  CI. Le générateur public ne produit aucune clé ni certificat : seulement des
  références et paramètres réseau.
- CI distante : non exécutée (aucun commit ni push).
- Aucune ressource cloud créée ; aucun état Terraform consulté ou modifié.

La topologie Terraform existante est conservée. L'absence de backend distant,
les paramètres codés en dur et l'identité de déploiement GitHub Actions devront
être traités dans la phase de déploiement continu. Une initialisation locale sans
backend ne valide ni IAM, ni quotas, ni APIs GCP, ni faisabilité du déploiement.

## Prochaine validation fonctionnelle, après autorisation cloud

Vérifier successivement DNS, certificat et sondes Ingress ; `config.js` servi ;
requêtes BOSH et absence de contenu mixte ; authentification XMPP Jicofo/JVB ;
puis statistiques ICE et trafic UDP. Conserver les logs et captures utiles au
rapport sans secrets. Un test à trois participants sur au moins deux réseaux,
pendant 10–15 minutes, doit confirmer le passage média par JVB (un appel à deux
peut utiliser le pair-à-pair). Tester également départ et reconnexion.

Budget restant indicatif : 2–4 h pour reprise GKE et signalisation, 1–2 h pour
les tests média, hors délais DNS/certificats. Le pipeline de déploiement reste
une étape distincte. Après la session, appliquer la procédure de nettoyage
autorisée et vérifier les ressources résiduelles facturables (LB, IP, disques).
