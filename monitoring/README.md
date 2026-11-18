# Supervision Jitsi sur GKE

Cloud Monitoring fournit les séries d'infrastructure GKE. Les collecteurs Google Cloud Managed Service for Prometheus utilisent le [PodMonitoring JVB](jvb-podmonitoring.yaml) pour récupérer toutes les 30 secondes dix métriques applicatives depuis `/metrics` sur le port interne 8080. La série `up` indique le succès de la collecte.

Grafana OSS 13.2.4 fonctionne sur la VM avec une base SQLite persistante sur disque et écoute sur `127.0.0.1:18300`. Sa source **Managed Prometheus** utilise HTTP GET et l'URL `https://monitoring.googleapis.com/v1/projects/PROJECT_ID/location/global/prometheus`. Un timer systemd renouvelle au démarrage puis toutes les cinq minutes le jeton OAuth transmis côté serveur dans l'en-tête sécurisé `Authorization`, à partir de l'identité de l'opérateur autorisée à lire Cloud Monitoring. Le service et le timer sont activés au démarrage de la VM. En cas d'échec, systemd retente le renouvellement. La source et le dashboard conservent leurs UID dans la base SQLite. Le renouvellement dépend de la validité des identifiants ADC existants et de leur droit de lecture.

Le [dashboard Grafana](grafana-jitsi.json) est importé en sélectionnant **Managed Prometheus** comme source. Les 19 requêtes PromQL des 14 panneaux sont vérifiées via l'API de requête de Grafana. Le dashboard s'ouvre sur les 15 dernières minutes et s'actualise toutes les 30 secondes.

- Le CPU, la mémoire et le débit réseau décrivent l'activité des nœuds et des pods selon le panneau.
- La disponibilité affichée correspond à la readiness des conteneurs Kubernetes. Un remplacement de pod reçoit un nouvel UID.
- Les conférences, endpoints, paquets, débit RTP/RTCP, stress et santé décrivent l'activité du bridge. Des valeurs à zéro sont normales au repos. Le débit RTP/RTCP agrège les médias et un panneau distinct compte les endpoints qui émettent de la vidéo.
- Le panneau **Collecte JVB** affiche la série `up`. Une valeur de 1 confirme que la cible répond au collecteur.
