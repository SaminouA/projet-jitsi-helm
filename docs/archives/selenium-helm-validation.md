# Selenium corrigé et intégration Helm de test — préparation locale

## Statut et diagnostic

L’image publiée au run [44084988109](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44084988109)
n’est PAS validée média : getUserMedia a échoué avec NotFoundError. Le pipeline
Python/tee sans pipefail a masqué ce code et permis la publication. Les tests
Malleus natifs à deux et trois participants restent des preuves distinctes.

La source Selenium 4.26 explique la cause probable : le nœud configure
/usr/bin/google-chrome dans son stereotype et ce binary prend priorité sur le
wrapper demandé par le client. Les quatre options synthétiques, présentes
uniquement dans notre wrapper, pouvaient donc être ignorées. Ce comportement
est établi dans les sources, mais les paramètres actifs de l’ancien run n’ont
pas été relevés : la cause reste une hypothèse fortement étayée.

Sources officielles épinglées :
[Dockerfile NodeChrome](https://github.com/SeleniumHQ/docker-selenium/blob/4.26.0-20241101/NodeChrome/Dockerfile),
[générateur de configuration](https://github.com/SeleniumHQ/docker-selenium/blob/4.26.0-20241101/NodeBase/generate_config),
[fusion des capacités](https://github.com/SeleniumHQ/selenium/blob/selenium-4.26.0/java/src/org/openqa/selenium/grid/node/config/SessionCapabilitiesMutator.java).

Corrections locales :
- Le Dockerfile enregistre /opt/jitsi/chrome-wrapper dans
  /opt/selenium/browser_binary_location ; permissions répertoire/wrapper 0755,
  médias 0644, utilisateur final seluser.
- Le workflow utilise bash, set -euo pipefail et conserve explicitement le code
  Python ; affiche les catégories/mesures même en cas d’échec, puis échoue.
  La publication exige le succès de l’étape média.
- Le précontrôle compare les SHA256 Y4M/WAV générés avec ceux lisibles depuis
  l’image sous son utilisateur par défaut, et relève Chrome/ChromeDriver.
- Le test utilise CDP pour vérifier les quatre options exactes effectivement
  actives, sans exposer la ligne de commande complète. Caméra et microphone
  sont testés séparément : catégorie video-capture ou audio-capture en cas
  d’échec. Pistes actives, dimensions, plus de cinq images décodées et RMS audio
  supérieur à 0,001 sont exigés. Une session Chrome seule ne suffit pas.

Les formats et chemins sont cohérents avec les fixtures testées localement.
La présence effective et la compatibilité dans la future image corrigée restent
à confirmer sur runner : aucun téléchargement ni construction locale.

## Prochaine validation GitHub — non exécutée

Après accord : publier le correctif limité à Selenium selon la protection de
main, attendre la CI et lancer une seule fois build-selenium.yml manuellement.
Le runner doit contrôler les fichiers/options/signaux avant de publier un
nouveau tag SHA. En cas d’échec, arrêt et aucune publication. Vérifier ensuite
le digest et le manifeste anonyme GHCR. Ne pas réutiliser le tag non validé.
Aucun workflow n’a été lancé pendant cette reprise.

## Chart séparé, désactivé par défaut

[charts/jitsi-load-test](../../charts/jitsi-load-test/Chart.yaml) ne modifie ni les
charts ni les releases Jitsi/Caddy. Sans valeurs supplémentaires, aucun objet
n’est rendu. Le chart ne fait pas partie des workflows de déploiement existants.

Une fois activé explicitement : un Deployment Selenium, une réplique, Service
ClusterIP 4444 uniquement ; VNC/noVNC désactivés, aucun LoadBalancer, PVC, RBAC
ou ServiceAccount ajouté. Pas de jeton de ServiceAccount monté. Les temporaires
et /dev/shm utilisent des emptyDir mémoire bornés (comptés dans la mémoire du
conteneur). UID/GID Selenium 1200/1201 correspondent à l’image officielle et
restent à vérifier lors du futur essai ; aucun composant privilégié.

Le Job Malleus est désactivé par défaut, puis suspendu par défaut lorsqu’on
l’active. Zéro retry, échéance 240 s, TTL 3600 s pour recueillir les preuves.
Profils bornés à 2 ou 3 participants et 60 ou 90 s. Le nombre de participants ne
peut pas dépasser les sessions Grid. L’URL Grid dérive du nom de release.
Les caches Maven, driver, target et /tmp sont des emptyDir écrits par UID 10001.
Aucune clé ni stockage persistant. Les images doivent être épinglées par digest
et déclarées validées explicitement ; ce drapeau est une attestation opérateur,
pas une validation effectuée par Helm.

Préparation/rendus locaux seulement :

```bash
helm lint --strict charts/jitsi-load-test
helm template load charts/jitsi-load-test
python3 -B -m unittest discover -s tests
```

Pour le futur essai, préparer hors Git un fichier de valeurs contenant les
images réellement validées sous forme registry/repository@sha256:digest ;
selenium.enabled=true, selenium.imageValidated=true ; malleus.enabled=true,
malleus.imageValidated=true, malleus.suspend=true. Ne pas inventer les digests.
Les commandes ci-dessous sont une procédure NON exécutée, nécessitant accord :

```bash
# Après précontrôles capacité, quotas, zéro conférence et images accessibles.
helm template load charts/jitsi-load-test -n jitsi-load-test -f /tmp/jitsi-load-approved.yaml
helm upgrade --install load charts/jitsi-load-test -n jitsi-load-test --create-namespace -f /tmp/jitsi-load-approved.yaml --wait --timeout 180s
kubectl rollout status deployment/load-selenium -n jitsi-load-test --timeout=120s
kubectl get svc,endpoints,pods,jobs -n jitsi-load-test
# Vérifier readiness Grid puis autorisation séparée avant de démarrer la charge.
kubectl patch job load-malleus -n jitsi-load-test --type merge -p '{"spec":{"suspend":false}}'
kubectl logs -n jitsi-load-test job/load-malleus
kubectl get job,pods,events -n jitsi-load-test
# Après collecte des preuves et arrêt du test : release de test uniquement.
helm uninstall load -n jitsi-load-test
```

## Blocages avant un vrai test Kubernetes

1. Publier et valider réellement l’image Selenium corrigée sur GitHub.
2. L’image Malleus est locale seulement : construction reproductible et
   publication future nécessaires. Sa compilation a été testée avec cache
   externe, pas son exécution complète dans Kubernetes. Le profil actuel
   contient des émetteurs audio ; pour un test vidéo seul, un profil dédié
   devra être validé avant lancement, sans réannoncer un test audio.
3. Les dépendances Maven ne sont pas embarquées : téléchargement au démarrage
   ou cache reproductible à prévoir ; un Job peut dépasser 240 s sur cache vide.
4. Vérifier ressources/allocation et place sur les nœuds avant pull des images.
   Requests cumulées : 350m CPU, 1280 MiB mémoire ; limites cumulées 2500m et
   3840 MiB, sans compter les pods système/Jitsi. Aucun constat de capacité
   actuelle du cluster n’est fait pendant cette préparation locale.
5. Le test média local au conteneur ne valide pas une réunion : vérifier ensuite
   pistes, débit vidéo de chaque client/JVB et images décodées, caméra activée.
   Un exit Maven 0 ou Job Complete seul n’est pas une preuve de trafic vidéo.
6. Le Service reste accessible aux clients du cluster ; aucun mécanisme
   d’authentification WebDriver ni NetworkPolicy n’est ajouté. Le réserver à
   une fenêtre de test contrôlée et le supprimer ensuite.

Verdict : GO pour préparer un unique build GitHub contrôlé après intégration
et accord ; NO-GO pour annoncer l’image fonctionnelle ou lancer le Job GKE.

## Mise à jour : essai correctif réellement réussi

La préparation décrite plus haut a désormais été suivie d’un unique essai
[44094388902](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/44094388902)
réussi. Les [mesures expurgées](../../tests/load/selenium-image-results.json)
confirment une piste audio/vidéo, 61 images 1280×720 décodées, RMS 0,0648 et
options synthétiques actives. L’ancienne image reste non validée ; seule la
nouvelle image/digest possède cette preuve de capture locale au conteneur.
Le [profil préparé Grid seul](../../tests/load/values-grid-validated.yaml) référence
ce digest, sans lancer Malleus. Aucune réunion ni charge GKE avec cette image.

Le workflow build-malleus.yml reste uniquement préparé localement. Il utilise
--source pour préparer le contexte sur runner, sans cache privé, puis vérifie
Java/Maven et la compilation avec cache public externe, y compris hors réseau.
La publication éventuelle ne validerait pas une réunion et n’embarquerait pas
le cache Maven. Les téléchargements à froid et l’échéance du Job restent à
résoudre avant son premier lancement. Ne pas déclarer imageValidated pour
Malleus sur la seule base du présent document.
