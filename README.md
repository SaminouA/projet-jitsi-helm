# Jitsi Meet sur GCP — Master 2 DevOps

Terraform décrit un cluster GKE à deux nœuds. Le chart utilisé est
`charts-officiels/jitsi-meet` ; `jitsi/` est un ancien squelette Nginx.
Le cluster est actuellement détruit. La CI réalise uniquement des validations.

Consulter [le rapport et le guide de préparation](docs/rapport.md) pour
l'architecture HTTPS/BOSH, l'exposition UDP JVB, les prérequis DNS/TLS/IP,
les commandes de validation et les limites des tests hors ligne.

Contrôle commun à la CI et aux hooks, avec Helm, Terraform et Python installés :

```sh
python3 -m pip install -r scripts/requirements.txt
sh scripts/validate.sh
```

Ne pas déployer `values-gke.yaml` seul : c'est un profil de préparation incomplet
pour l'accès public, qui pourrait créer un LoadBalancer JVB facturable.
