# Malleus / Selenium Grid : test léger réel du 17 novembre 2026

Cette section conserve les résultats historiques de la phase audio. La vidéo
a ensuite été validée séparément à deux et trois participants : voir
[les tests vidéo et images Docker](malleus-video-docker.md) et
[leur synthèse dédiée](../tests/load/video-results-summary.json).

Les résultats expurgés sont dans [results-summary.json](../tests/load/results-summary.json).
Les résultats JUnit, journaux et observations détaillées restent dans
`tests/results/`, ignoré par Git et privé. Ne pas publier les journaux bruts des
navigateurs : ils peuvent contenir des identifiants de session ou de participants.
Une réussite Malleus sans pistes et sans trafic média ne prouve pas une charge
vidéo ; le script distingue désormais ce cas par un code de sortie 2.

## Périmètre et garde-fous

Générateurs sur la machine de travail, hors GKE : Grid standalone, soit tous les
composants Selenium Grid dans un processus local, limité à 3 navigateurs.
Aucun namespace, pod de test, VM, disque, IP ou LB ajouté au cluster. Aucun
changement de Terraform, IAM, secrets ou releases Helm. Les conférences
simulées ne sont jamais simultanées entre les paliers : un palier = une seule conférence.

Avant chaque palier : contexte GKE attendu, pods prêts, Jicofo et JVB à zéro
conférence/participant. Arrêt si CPU ou mémoire d’un nœud atteint 80 %, pod non
prêt/remplacé/redémarré, disque générateur sous 300 MiB, activité concurrente
inattendue, erreur de collecte ou dépassement du délai borné. Ne jamais lancer
le script sans nouvel accord couvrant le test de charge et sa fenêtre.

Les paramètres P2P=false, préjoin et résolution sont des surcharges des seuls
navigateurs de test, pas une migration de configuration de production. Les
sources audio/vidéo sont factices ; aucune capture de micro/caméra utilisateur.

## Résultat final vérifié

Deux paliers finaux ont validé une transmission **audio synthétique** via JVB :
2 puis 3 participants, 90 s configurées par palier, un cas Malleus réussi chacun.
Les durées totales sont 118,74 s et 127,53 s, et les fenêtres échantillonnées
prouvant l’audio pour tous couvrent respectivement 46,40 s et 34,40 s.
JVB atteint 121m puis 122m CPU et 285 Mi mémoire ; les nœuds restent au maximum
à 14 % CPU/38 % mémoire. Aucun redémarrage de pod. **La vidéo automatisée reste
non validée** : aucune piste vidéo ni bitrate vidéo positif observé.
Sept lancements sont conservés : un échec local, quatre succès préliminaires de
connexion sans preuve média, puis ces deux succès audio. Le Grid a été arrêté
et HTTPS/revisions/PVC/IP sont restés conformes après les essais.

## Outils utilisés et difficultés constatées

| Outil | Version réelle |
|---|---|
| Jitsi Meet Torture | Commit `4c00915e97006ff2224bb509eb3582bf3a10ca85` |
| Selenium serveur et dépendance Java | 4.26.0 |
| Chrome for Testing / ChromeDriver | 130.0.6723.116, versions assorties |
| OpenJDK | 17.0.21 |
| Maven | 3.8.7 |

Aucun Java/Maven/navigateur n’était installé au début. Les dépendances natives
ont été installées localement, car le disque ne disposait que d’environ 2 Go
libres ; une image Selenium supplémentaire aurait consommé trop de place.
Les sources et binaires sont sous /tmp, le cache Maven sous ~/.m2 ; ne pas
effacer des images/conteneurs existants pour faire de la place. Aucun conteneur
Docker Jitsi existant n’a été modifié.

Le premier lancement a échoué avant toute connexion : Chrome/DevToolsActivePort,
sandbox Ubuntu indisponible. Le paramètre legacy de Torture est inversé :
`-Dchrome.disable.nosanbox=false` ajoute --no-sandbox au navigateur local. Aucune
restriction système AppArmor, IAM ou permission cluster n’a été modifiée. Le
Grid écoute exclusivement sur 127.0.0.1 ; arrêter le générateur après le test.

La vidéo attendue par Malleus, resources/FourPeople_1280x720_30.y4m, est absente
du clone officiel. Le média fourni fakeVideoStream.y4m est réellement **320×180,
5 images/s**. Un alias local vers ce fichier permet de satisfaire le chemin
attendu sans télécharger une vidéo volumineuse ni modifier le code officiel.
**Cet alias ne transforme pas le média en 720p30.** Les clients sont configurés
à 180p. Des clients rejoignant sans piste ont aussi été observés ; le wrapper
active explicitement « Unmute microphone » et « Start camera » dans ses seules
sessions synthétiques, puis relève pistes, état de connexion et bitrate.

## Reproduction préparée

Installation des paquets effectuée localement pour cette session (à adapter à
une autre machine ; ne pas la rejouer sans besoin) :

```bash
sudo apt-get install -y --no-install-recommends openjdk-17-jdk-headless maven \
  libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libdrm2 libxkbcommon0 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 \
  libcups2t64 libpango-1.0-0 libcairo2
```

Sources officielles : [Jitsi Meet Torture](https://github.com/jitsi/jitsi-meet-torture),
[configuration TOML Selenium](https://www.selenium.dev/documentation/grid/configuration/toml_options/).
Le script utilise les chemins locaux du tableau ci-dessus ; les outils ne sont
pas ajoutés au dépôt. Pour une nouvelle machine, télécharger depuis les releases
officielles Selenium et Chrome for Testing, épingler les versions et vérifier
l’intégrité avant usage. Ne pas utiliser une image latest en remplacement silencieux.

Depuis le clone officiel déjà présent :

```bash
cd /tmp/jitsi-meet-torture-light
git rev-parse HEAD
# Seulement si absent : alias vers la vraie fixture legere, aucun ecrasement.
if [ ! -e resources/FourPeople_1280x720_30.y4m ]; then
  ln -s fakeVideoStream.y4m resources/FourPeople_1280x720_30.y4m
fi
mvn -B -DskipTests -Dcheckstyle.skip=true test-compile
```

Depuis le dépôt projet, démarrer le Grid dans un terminal dédié :

```bash
java -Xmx256m -jar /tmp/jitsi-load-tools/selenium-server.jar standalone \
  --config tests/load/selenium-grid.toml
```

Puis, après accord et vérification qu’aucune réunion n’est active :

```bash
python3 scripts/run-malleus-light.py --participants 2 --duration 60
# Uniquement apres resultat et sante verifies ; ne pas enchainer aveuglement :
python3 scripts/run-malleus-light.py --participants 3 --duration 90
```

La commande Maven exacte et le SHA outil sont enregistrés dans chaque summary.json
privé. La durée demandée n’est pas un plateau mesuré de même durée : lancement,
jonction et arrêt prennent du temps. Le fichier expurgé distingue durée configurée,
durée totale, durée JUnit et intervalle observé avec tous les participants.
Les métriques kubectl top sont des échantillons Metrics Server, pas une mesure
continue ou un dimensionnement de capacité. Les compteurs bitrate JVB bruts ne
sont pas convertis en unités non vérifiées.

Après le dernier test, vérifier zéro conférence, pods/releases/PVC/IP/HTTPS,
fermer toutes les sessions de notre Grid et arrêter son processus (Ctrl+C dans
son terminal). Aucun nettoyage du cluster ou rollback Helm ne fait partie de ce test.

## Chaos Mesh : reste à faire, non exécuté

Aucune CRD Chaos Mesh n’a été retrouvée lors de cette session. Il reste à faire
valider son installation et les droits privilégiés nécessaires, choisir une
version compatible GKE/containerd, puis limiter les expériences au namespace et
au seul composant convenus. Première expérience proposée : PodChaos borné sur
un pod Web, sans réunion active ; définir HTTP avant/pendant/après, temps de
récupération et procédure d’arrêt. La seule réplique Web implique une interruption
attendue pendant la faute : ne pas présenter cela comme de la haute disponibilité.
Prévoir les observations Cloud Monitoring et les preuves, sans toucher au PVC,
aux secrets, aux nœuds, au JVB ou au réseau global pour un premier essai.
