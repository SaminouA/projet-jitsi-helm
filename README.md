# Jitsi Meet sur GCP — Master 2 DevOps

Accès public : **https://jitsi-meet-m2.duckdns.org**. Caddy termine TLS avec un
certificat Let's Encrypt de production, puis transmet au Web privé et à BOSH.
L'IP Web est `34.78.71.58` ; JVB utilise un LoadBalancer séparé en UDP 10000
sur `34.62.165.81`. Aucun Ingress n'est déployé.

État vérifié le 16 novembre 2026 : release `jitsi` révision 3, `jitsi-edge`
révision 2, quatre composants Jitsi et Caddy prêts, PVC Caddy 10Gi Bound.
L'utilisatrice confirme un test manuel à deux participants (ordinateur et
téléphone), audio et vidéo dans les deux sens sur la salle `jitsitest`.
Le trajet P2P/JVB n'a pas été instrumenté ; aucun résultat de partage d'écran
ou de charge n'est revendiqué pour cet essai.

Le chart applicatif est `charts-officiels/jitsi-meet` ; `jitsi/` est un ancien
squelette. Le chart complémentaire est `charts/jitsi-edge`. La configuration
publique versionnée est composée de `values-gke.yaml`,
`deploy/jitsi-duckdns.yaml` (dont l'IP JVB existante) et des secrets SOPS traités
uniquement dans un contexte privé autorisé. Le profil Caddy spécifique au domaine
est `deploy/jitsi-edge-duckdns.yaml`, désormais en production. Le chart générique
reste par défaut staging ; tout nouveau bootstrap doit utiliser explicitement
staging avant production et faire l'objet d'une autorisation de coût.

```sh
python3 -m pip install -r scripts/requirements.txt
sh scripts/validate.sh
```

La validation conserve un rendu localhost explicite et accepte aussi le profil
HTTPS public. Les tests statiques ne prouvent pas une réunion. Le retour au
profil localhost nécessite une surcharge explicite et un rechargement des pods ;
un port-forward seul ne modifie pas la configuration publique déployée.

La CI valide ; la CD intégrée reste désactivée. OIDC et la lecture des métadonnées
GKE ont réussi sur le runner, mais l’identité Kubernetes a échoué. La correction
exec ADC reste locale ; RBAC/PVC/SOPS runner et CD de bout en bout restent à valider.
Le workflow CD conserve un mécanisme d’authentification à adapter après ce diagnostic.
Aucun secret ou sauvegarde Helm ne doit être affiché ou ajouté à Git.

Consulter le [rapport](docs/rapport.md), la [soutenance](docs/soutenance.md),
le [guide HTTPS](docs/https-duckdns.md) et la [séquence de bootstrap](docs/bootstrap-https-court.md).
Les créations/suppressions GCP sont soumises à accord ; le PVC indépendant et
l'adresse réservée ne disparaissent pas avec une simple désinstallation Helm.

Pour la remise : [architecture](docs/architecture.md), [validation CD contrôlée](docs/validation-cd-controlee.md) et [checklist](docs/checklist-remise.md).
