# Test vidéo Helm préparé : 2 participants, 90 secondes

**GO technique pour une installation contrôlée, en attente d’accord.**
Aucune commande de déploiement ci-dessous n’a été exécutée. Le Job reste suspendu.

Les [valeurs préparées](../tests/load/values-video-2x90.yaml) épinglent uniquement :
- Selenium validé caméra/micro : digest 5b898424cffed5b99a0c8acbb558c0e3f3e4a2fbb0aac48bb54af60b445dcd86.
- Malleus autonome : digest 01de65fb72bf78ded0191caa6302916f04850b94bdb6d1d943b0ceae6ce87092.

Preuves : [Selenium](../tests/load/selenium-image-results.json),
[Malleus](../tests/load/malleus-image-results.json). Malleus exécute réellement
son orchestration et TestNG hors réseau avec zéro participant : ce n’est pas
une preuve de réunion vidéo conteneurisée. Les tests natifs précédents restent
la preuve à deux et trois participants ; ils ne sont pas réattribués à ces images.

## Précontrôles effectués

Cinq pods de production Ready, zéro redémarrage, aucune réunion Jicofo/JVB.
Deux nœuds Ready, CPU 5–6 %, mémoire 36–39 %, DiskPressure=False et 14–14,4 Gio
libres. Requests existantes de 727m/827m CPU laissent de la place aux 350m
supplémentaires ; mémoire demandée supplémentaire 1280 MiB. Limites de test :
2500m CPU, 3840 MiB RAM ; temporaires Grid RAM inclus dans la limite mémoire.
Ces limites maximales ne sont pas des consommations mesurées. Une contention
CPU ou mémoire reste possible ; surveiller et arrêter au seuil de 80 % nœud
ou au moindre redémarrage/dégradation d’un composant de production.

Droits de création namespace/Deployment/Service/Job vérifiés sans modification.
Aucune NetworkPolicy actuellement ; Service uniquement ClusterIP 4444, sans
LoadBalancer, IP publique, PVC, secrets ni jeton ServiceAccount. Aucun nouveau
nœud/disque prévu. Ne pas changer l’autoscaling pour ce test ; arrêter en cas
de manque de capacité au lieu de créer une ressource payante.

## Commandes futures — après autorisation explicite

Recontrôler impérativement zéro conférence, santé et ressources immédiatement
avant installation puis juste avant levée de suspension. Ne pas démarrer si la
mesure n’est pas fiable. Tester le contexte et les valeurs avant toute mutation.

```bash
kubectl config current-context
helm lint --strict charts/jitsi-load-test -f tests/load/values-video-2x90.yaml
helm template load charts/jitsi-load-test -n jitsi-load-test -f tests/load/values-video-2x90.yaml
# Installation autorisée uniquement ; Job toujours suspendu.
helm upgrade --install load charts/jitsi-load-test -n jitsi-load-test --create-namespace -f tests/load/values-video-2x90.yaml --wait --timeout 180s
kubectl rollout status deployment/load-selenium -n jitsi-load-test --timeout=120s
kubectl get svc,endpoints,pods,jobs -n jitsi-load-test
kubectl port-forward -n jitsi-load-test service/load-selenium 14444:4444 --address 127.0.0.1
```

Garder ce port-forward dans un terminal dédié. Dans un deuxième terminal,
lancer l’observateur local : il n’utilise que nos sessions Grid dédiées,
active la caméra si nécessaire et collecte des compteurs expurgés privés.
Il ne crée pas de participant et ne mesure pas le JVB.

```bash
python3 -B scripts/observe-malleus-video.py --grid http://127.0.0.1:14444 --participants 2 --duration 180
```

Dans un troisième terminal, après dernier contrôle et accord pour la charge :

```bash
kubectl patch job load-malleus -n jitsi-load-test --type merge -p '{"spec":{"suspend":false}}'
kubectl logs -n jitsi-load-test -f job/load-malleus
kubectl top nodes
kubectl top pods -n jitsi-load-test
kubectl get pods -n jitsi
```

Une conférence sur https://jitsi-meet-m2.duckdns.org, deux émetteurs vidéo,
audio_senders=0, durée 90 s, capture demandée 640×360, maximum 15 fps, P2P coupé.
Deadline du Job 240 s et zéro retry. Aucun test audio supplémentaire.

En parallèle, relever les stats JVB/Jicofo avec les commandes en lecture seule
déjà utilisées dans le rapport : deux participants, endpoints actifs, débits
montant/descendant positifs. HTTPS /, /config.js et /http-bind doivent rester
accessibles. Succès = Job/JUnit réussi ET médias réels côté clients ET trafic
JVB, sans dégradation de production. Un Job Complete seul ne suffit pas.

Arrêt immédiat si participants inattendus, erreur HTTPS, pod de production
redémarré, pression mémoire/disque ou seuil 80 % atteint : supprimer uniquement
le Job de test, puis nettoyer la release de test après collecte des preuves.

```bash
# Arrêt du générateur si nécessaire ; jamais de pod de production.
kubectl delete job load-malleus -n jitsi-load-test
# Après collecte des logs, métriques, événements et résultat du test :
helm uninstall load -n jitsi-load-test
```

Ne supprimer ni namespace de production, ni PVC, ni release Jitsi/Caddy.
L’arrêt du port-forward complète le nettoyage local. Ne pas réessayer
spontanément un second palier si le premier échoue.

## Correction locale après l’arrêt CPU du premier essai

Le premier essai a réellement été exécuté puis arrêté par sécurité : voir
[la preuve du résultat partiel](../tests/load/k8s-video-results.json). Il ne
valide pas les 90 secondes complètes. Aucun second essai n’est autorisé à ce
stade. Le futur profil doit ajouter
[values-video-2x90-low-cpu.yaml](../tests/load/values-video-2x90-low-cpu.yaml).

Selenium : request 750m CPU/1 Gio, limite 900m/2 Gio, heap Java 256 Mio.
Malleus : request 250m/256 Mio, limite 300m/768 Mio. Total requests 1000m et
1280 Mio ; total limites 1200m et 2816 Mio. Ces paramètres remplacent les
anciens budgets de la première version, sans changer les images ni le média.

L’anti-affinité obligatoire au scheduling vise le composant jvb de la release
jitsi, dans le namespace jitsi, avec topologyKey kubernetes.io/hostname. Elle
n’ajoute aucun label et ne modifie aucun pod de production. Avec les placements
constatés, Selenium ira sur le nœud jjk0. Si ce placement devient impossible,
laisser Pending et arrêter : ne pas enlever la contrainte ni ajouter de nœud.
L’anti-affinité n’expulse pas un pod déjà lancé si le JVB change de nœud ensuite ;
le contrôle de stabilité des pods de production doit alors interrompre le test.

Capacité vérifiée : chaque nœud 1930m CPU/6025,6 Mio allocatables. Sur jjk0,
1203m et 4752,7 Mio libres selon requests existantes. Même si les deux pods de
test y sont placés, restent 203m et 3472,7 Mio non réservés. L’usage réel CPU
était 6 % et RAM 37 % ; les autres composants peuvent toujours connaître des
pics, donc le plafond des pods de test ne garantit pas un plafond du nœud.
Le pool décrit contient deux e2-standard-2, sans configuration d’autoscaling
activé renvoyée. Aucun changement du pool ni ressource payante prévu.

Rendu vérifié localement, commande non mutante :

```bash
helm lint --strict charts/jitsi-load-test -f tests/load/values-video-2x90.yaml -f tests/load/values-video-2x90-low-cpu.yaml
helm template load charts/jitsi-load-test -n jitsi-load-test -f tests/load/values-video-2x90.yaml -f tests/load/values-video-2x90-low-cpu.yaml
```

Après nouvel accord seulement, reprendre l’installation précédente en ajoutant
le second fichier -f. Vérifier effectivement le nœud Selenium avant de lever
la suspension. Garder les seuils d’arrêt 80 %, relever l’échantillon déclencheur
avant exception, et collecter les compteurs RTP dès l’arrivée des sessions.
Le throttling CPU et le heap Grid plus petits peuvent ralentir le démarrage :
ce risque reste à valider ; aucun succès du deuxième essai n’est revendiqué.

## Résultat du deuxième et dernier essai

Après nouvel accord, le profil low CPU a été appliqué une seule fois. Placement
hors JVB et limites effectives vérifiés avant le lancement. Job Complete,
Malleus exit 0/BUILD SUCCESS, un cas exécuté sans échec ; CPU nœud maximal 61 %.
Les deux clients reçoivent et décodent réellement 694/632 images selon les
compteurs RTP ; JVB bidirectionnel. Scénario configuré 90 s, suite 126,214 s,
vidéo strictement observée sur 56,35 s d’échantillons : pas de revendication de
90 s continues de vidéo mesurée. Les détails sont dans la
[synthèse du dernier essai](../tests/load/k8s-video-low-cpu-results.json).
Toutes les ressources de test sont nettoyées et Jitsi est sain. Les commandes
ci-dessus documentent la procédure, elles n’autorisent aucune nouvelle tentative.
