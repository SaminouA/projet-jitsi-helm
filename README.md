# Jitsi Meet sur GCP — Master 2 DevOps

Architecture de demonstration sans domaine : Web prive par port-forward sur
`http://localhost:8081`, BOSH de meme origine, JVB public via LoadBalancer UDP
10000. Aucun Ingress ni certificat requis. Le cluster est actuellement detruit.

La release retenue est `jitsi`, dans le namespace `jitsi`. Les Services sont
`jitsi-jitsi-meet-web` et `jitsi-jitsi-meet-jvb` ; le Deployment du bridge est
`jitsi-jitsi-meet-jvb-0`.

Le chart utilise est `charts-officiels/jitsi-meet` ; `jitsi/` est un ancien
squelette Nginx. Consulter le [guide et rapport](docs/rapport.md) pour les deux
phases de deploiement, VS Code Remote SSH, les participants et le nettoyage.

```sh
python3 -m pip install -r scripts/requirements.txt
sh scripts/validate.sh
```

La CI ne deploie rien. Les tests locaux ne valident pas la visioconference.
Installer `values-gke.yaml` sur GKE cree un LoadBalancer facturable et requiert
une autorisation. L'IP annoncee par JVB doit ensuite etre finalisee avec
`scripts/jvb-values.py`. Le generateur historique `scripts/gke-values.py`
concerne uniquement l'alternative publique HTTPS avec domaine, non retenue.
