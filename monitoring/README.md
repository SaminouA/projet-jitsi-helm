# Observabilité Jitsi

GKE et Managed Prometheus fournissent déjà les métriques d'infrastructure.
Le manifeste `jvb-podmonitoring.yaml` propose la collecte du bridge via le
port interne `http` (8080), à 30 s, avec une liste de dix métriques.
Le manifeste a été validé puis appliqué après autorisation le 18 novembre.
Le collecteur a atteint la cible et l'API a renvoyé les dix métriques.
Trois points successifs à 30 s ont confirmé `up=1` et la santé JVB à 1.
Les conférences et endpoints étaient à zéro au repos. La collecte peut
être facturée.

Pour la soutenance, importer `grafana-jitsi.json` dans Grafana OSS local,
lié à localhost. Choisir une source Prometheus en HTTP GET dont l'URL est
`https://monitoring.googleapis.com/v1/projects/PROJECT_ID/location/global/prometheus`.
La source doit envoyer un jeton OAuth temporaire dans l'en-tête sécurisé
`Authorization`, avec une identité déjà autorisée à lire Cloud Monitoring.
Renouveler le jeton à expiration. Ne jamais versionner le jeton.
Pour une connexion durable, étudier le data source syncer de Google.
L'import local n'a pas encore été validé. La console Cloud Monitoring
peut afficher les requêtes PromQL pour la démonstration sans Grafana.

Les panneaux CPU, mémoire, réseau, Ready et redémarrages ont renvoyé des
séries réelles via l'API. La disponibilité affichée est la readiness
Kubernetes. Les compteurs de redémarrages sont distincts d'un remplacement
d'UID. Les débits JVB sont des débits RTP/RTCP agrégés, avec un panneau
distinct pour les endpoints émettant de la vidéo. Pour la vidéo seule,
présenter les mesures navigateur Malleus du run nº 8. Les preuves
historiques sont dans le dossier de remise. Aucun compte, service public
ou composant Grafana dans le cluster n'est nécessaire à cette proposition.

Pour la démonstration, présenter les nœuds puis les cinq pods Jitsi,
le trafic entrant et sortant, la readiness et les redémarrages. Après
validation de la collecte, présenter la santé JVB et les endpoints au
repos, puis les observations historiques des deux runs approuvés.
