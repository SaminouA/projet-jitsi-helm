# Vidéo Malleus et images Docker — résultats du 17 novembre 2026

Deux paliers vidéo réels ont réussi sur Jitsi public : deux puis trois
participants, une conférence, 90 secondes configurées par palier. L’audio était
désactivé (audio_senders=0) : les tests audio précédents ne sont pas rejoués.
La [synthèse vidéo](../../tests/load/video-results-summary.json) conserve aussi
le premier palier interrompu par le garde disque ; les preuves audio/Chaos restent
séparées et inchangées. Les vidéos sont synthétiques, pas des captures utilisateur.

## Ce qui a effectivement fonctionné

Même Torture commit 4c00915e97006ff2224bb509eb3582bf3a10ca85, Selenium 4.26.0 et
Chrome/ChromeDriver 130.0.6723.116 que dans la phase audio. Une fixture dédiée
Y4M I420 **1280×720 à 30 images/s**, deux frames synthétiques répétées, a été
générée en RAM, ainsi qu’un WAV factice. Le nom attendu FourPeople_1280x720_30.y4m
contient maintenant ce vrai format dans le répertoire dédié, sans remplacer
l’ancien alias ou média de la phase audio.

Avant toute conférence, getUserMedia vidéo seul a confirmé une capture 640×360,
15 images/s avec cette source. Le test Malleus demande ensuite une sortie 360p
à 15 images/s maximum, P2P=false, lecture des vidéos autorisée et activation
explicite de Start camera dans ses propres sessions Grid. Aucun réglage Helm
ou serveur Jitsi n’est modifié. Le correctif combine fixture, contraintes et
activation client ; il ne prouve pas qu’une seule de ces modifications explique
tous les échecs précédents.

La validation exige pour **chaque** client : joined/connected, piste vidéo non
muette, débit vidéo montant ET descendant positifs, ainsi que tous les endpoints
JVB actifs et du trafic JVB dans les deux sens dans le même échantillon. Des
éléments HTML vidéo montrent également des images décodées ; leurs compteurs
ne sont pas présentés comme des statistiques RTP framesReceived.

| Palier complet | 2 participants | 3 participants |
|---|---:|---:|
| Cas Malleus JUnit | 1 réussi | 1 réussi |
| Durée configurée | 90 s | 90 s |
| Durée cas JUnit | 92,700 s | 95,085 s |
| Durée totale wrapper | 110,03 s | 115,48 s |
| Échantillons prouvant vidéo pour tous | 4 sur 41,40 s | 3 sur 31,23 s |
| CPU JVB maximal échantillonné | 119m | 175m |
| Mémoire JVB maximale | 290 Mi | 292 Mi |
| CPU/mémoire maximum nœud | 15 % / 39 % | 17 % / 39 % |
| Minimum disque libre VM | 795 MiB | 794 MiB |
| Minimum MemAvailable VM | 3996 MiB | 4331 MiB |
| Redémarrages / disponibilité finale | 0 / 5 pods prêts | 0 / 5 pods prêts |

Les fenêtres mesurées ne sont pas un plateau continu de 90 secondes : les
navigateurs doivent rejoindre puis activer leurs médias, et les compteurs sont
échantillonnés. Le motif vidéo est très peu complexe et ne représente ni une
webcam HD réelle ni la capacité maximale du serveur. Les tailles vidéo affichées
peuvent être adaptées par Jitsi. Dix participants ne sont pas tentés : générateur
à deux vCPU et budget disque étroit, sans preuve de marge pour dix navigateurs
et leurs flux décodés. Le profil reste volontairement borné à trois.

## Garde disque et répertoires temporaires en RAM

Le premier essai avait déjà montré pistes/trafic vidéo, mais les fichiers
Chromium temporaires ont fait passer le disque de 796 à 264 MiB libres.
Le garde de 300 MiB a arrêté le générateur ; aucun succès complet n’est revendiqué
pour ce lancement (Maven interrompu, aucun JUnit final). Après fermeture des
navigateurs, environ 797 MiB sont revenus, sans suppression d’autres données.

Le Grid a ensuite été relancé avec TMPDIR et java.io.tmpdir dans un sous-répertoire
RAM de /dev/shm (3,9 GiB disponibles initialement). Le seuil vidéo est porté à
500 MiB disque libre, avec au moins 1 GiB MemAvailable et 512 MiB tmpfs libres.
Pas de modification de /tmp global, de montage système ou de configuration Docker.

Commandes réellement utilisées, depuis le dépôt (ne pas rejouer de charge sans
fenêtre et absence de conférence revalidées) :

```bash
python3 scripts/generate-synthetic-media.py --output /dev/shm/jitsi-m2-video/resources
mkdir -p /dev/shm/jitsi-grid-video
TMPDIR=/dev/shm/jitsi-grid-video java -Djava.io.tmpdir=/dev/shm/jitsi-grid-video \
  -Xmx256m -jar /tmp/jitsi-load-tools/selenium-server.jar standalone \
  --config tests/load/selenium-grid.toml
# Dans un autre terminal, apres garde-fous :
python3 scripts/run-malleus-light.py --video --participants 2 --duration 90
# Seulement apres resultat et ressources verifies :
python3 scripts/run-malleus-light.py --video --participants 3 --duration 90
python3 scripts/summarize-malleus-video.py
```

Le Grid a été arrêté à la fin, après confirmation de zéro session. Les fixtures
et contextes RAM sont temporaires : le générateur permet de les recréer après
redémarrage, sans écraser des médias existants.

## Dockerfiles préparés et image réellement construite

- [Dockerfile Selenium](../../tests/load/docker/Dockerfile.selenium) : base officielle
  Selenium 4.26.0 épinglée par digest amd64, fixtures Y4M/WAV, wrapper Chrome avec
  caméra/microphone factices, sessions limitées à trois. **Image non construite** :
  sa base non présente nécessite environ 600 MiB compressés avant même extraction,
  incompatible avec la marge disque restante. Les tests vidéo réalisés ci-dessus
  utilisent le Grid natif, pas cette image.
- [Dockerfile Malleus](../../tests/load/docker/Dockerfile.malleus) : base Java Jicofo
  déjà en cache, épinglée par digest ; entrypoint Jicofo remplacé, aucun serveur
  Jicofo lancé. Java 21, Maven 3.8.7, source Torture épinglée, utilisateur 10001.
  Aucun kubeconfig, état Terraform, secret applicatif ou clé SA copié.
- [Job suspendu](../../tests/load/docker/job-malleus.yaml), sans token SA, borné en
  temps/CPU/mémoire/stockage éphémère. **Non déployé** ; namespace/Service Grid et
  distribution de l’image aux nœuds sont des prérequis futurs, non créés.

Image locale construite : **jitsi-malleus:m2-video-20261117**, ID
29dc9daac1308ecd0b30804b172a43d9991e22ca65ce3be0056b4f2cb8d8ec3d.
Docker CLI affiche environ 1,13 GB, dont l’essentiel est partagé avec la base
déjà présente. Différence de disque libre avant/après la construction légère :
environ **19,5 MiB** ; minimum observé pendant cette construction 752,27 MiB.
La construction a duré 23,28 s, limitée à un CPU/768 MiB, réseau coupé.
Ces limites ne sont pas des mesures de RSS consommée.

La première tentative embarquant le cache Maven a été arrêtée au seuil de
sécurité : 416,45 MiB libres, aucun tag final construit. Le builder classique
consommait plus que l’estimation initiale. Seules les couches produites par cette
tentative ont été retirées ; les quatre images/conteneurs préexistants ont été
préservés. Le contexte final sans cache ne fait que 10,31 MiB en RAM.
La [preuve de construction](../../tests/load/docker/build-results.json) conserve
les deux tentatives, sans effacer l’échec initial.

La variante finale ne contient pas les dépendances/cache Maven. Maven/Java ont
été vérifiés dans le conteneur ; **test-compile a réussi** avec réseau désactivé,
cache public hôte monté en lecture seule et target en tmpfs. Aucun nouveau test
Jitsi n’a été exécuté depuis l’image. En usage autonome futur, les dépendances
publiques devront être téléchargées ou fournies par un cache autorisé.

Préparation/reproduction de la variante légère :

```bash
# Un nouveau repertoire vide est requis ; aucun ecrasement des contextes existants.
python3 scripts/prepare-malleus-image-context.py --directory /dev/shm/jitsi-malleus-context-new
# Recalculer le budget disque avant de construire ; garder une reserve et surveiller.
sudo docker build --pull=false --network=none --memory=768m --memory-swap=768m \
  --cpu-period=100000 --cpu-quota=100000 --force-rm --rm \
  -t jitsi-malleus:m2-video-20261117 -f /dev/shm/jitsi-malleus-context-new/Dockerfile.malleus \
  /dev/shm/jitsi-malleus-context-new
sudo docker run --rm --network=none --read-only --memory=512m --cpus=1 \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m jitsi-malleus:m2-video-20261117 --version
```

La préparation vérifie le SHA512 Maven publié par les archives officielles
Apache ; Maven Central fournit le binaire. L’option --with-cache est réservée à
une machine disposant d’un budget adapté, pas à cette VM. Ne jamais docker prune
ou supprimer des images/conteneurs existants pour contourner le garde disque.

Pour une future image Selenium, préparer un contexte contenant Dockerfile.selenium,
chrome-wrapper.sh et resources/ générées. Quand un espace suffisant est disponible,
construire puis valider l’image avant usage. À l’exécution, publier 4444 seulement
sur 127.0.0.1 et fournir /tmp en tmpfs suffisamment grand ainsi que --shm-size ;
ne pas écrire les gros fichiers Chromium dans la couche disque de la VM.
Aucune image n’a été poussée dans un registre et aucun registre GCP n’a été créé.

L’entrypoint Malleus conteneurisé exécute l’outil ; son code retour seul ne prouve
pas la vidéo. L’activation caméra et la vérification de transport doivent rester
assurées par le contrôleur Selenium/observateur, comme dans les tests natifs.
La combinaison image Selenium + Job Malleus n’a pas été validée de bout en bout.
Le Job reste suspendu pour éviter toute exécution accidentelle avant ces contrôles.

## État final et preuves

Les [contrôles finaux](../../tests/load/video-final-checks.json) confirment les cinq
pods et UID inchangés depuis Chaos, zéro redémarrage, Jitsi 4/Caddy 3, PVC/IP et
Secrets applicatifs inchangés, HTTPS /, /config.js et /http-bind en 200 avec
confiance normale, zéro conférence. Aucun Terraform apply, IAM, nouvelle branche
ou PR. La PR Terraform nº 7 et les fichiers d’état restent intacts.

Preuves privées sous tests/results/*-malleus-video-* et
20261117-video-images[-lean] ; aucun journal brut de navigateur à publier.
La vidéo est maintenant validée à deux et trois participants synthétiques,
sans réécrire les conclusions historiques de la phase audio.
