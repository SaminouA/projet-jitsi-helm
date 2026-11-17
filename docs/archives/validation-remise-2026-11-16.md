> Document historique conservé. Pour l’état consolidé du 17 novembre 2026,
> consulter le [rapport final](../rapport.md), les [preuves](preuves-livraison.md)
> et le [plan oral final](presentation-finale.md). Les statuts antérieurs ci-dessous
> ne décrivent pas nécessairement la version livrée.

# Protocole de validation pour la remise

État du 16 novembre 2026 : contrôles HTTP et collecte ponctuelle effectués ;
aucune nouvelle réunion et aucune charge média exécutées.

## Réunion fonctionnelle à réaliser

1. Vérifier quatre pods Ready et zéro Warning récent. Garder l'accès Web actuel
   par port-forward ; ne pas exposer un nouveau service pour ce test.
2. Ouvrir une salle de démonstration avec trois navigateurs/participants consentants.
   Trois participants sont nécessaires pour observer le bridge plutôt que le seul P2P.
3. Vérifier jonction, audio bidirectionnel, vidéo, mute/unmute et départ/reconnexion.
   Relever navigateur, réseau, heure, durée, résolution et observations réelles.
4. Observer les statistiques WebRTC et JVB ; relever pertes, RTT, débit et ICE,
   sans enregistrer identifiants de salle ou médias dans Git.
5. Après départ, vérifier le retour à zéro participant et la stabilité des pods.

## Charge légère préparée, à exécuter avec les participants

Maximum trois participants, vidéo 360p si disponible, pendant trois minutes ;
aucun générateur automatique et aucune boucle HTTP concurrente.
Avant la réunion, collecter une minute au repos :

```sh
sh scripts/monitor-load.sh --scenario remise-repos --duration 60
```

Pendant la réunion bornée :

```sh
sh scripts/monitor-load.sh --scenario remise-3-participants --duration 180
```

Le collecteur observe toutes les 15 secondes et ne crée pas de charge média.
Surveiller `kubectl top nodes`, `kubectl top pods -n jitsi` et l'état des pods.
Arrêter immédiatement les participants si un nœud passe NotReady, si un pod
redémarre/OOM, si CPU ou mémoire dépasse 80 % pendant deux relevés, ou si la
qualité audio se dégrade. Ctrl+C arrête la collecte et conserve les relevés.
Ne pas augmenter le nombre de participants pour chercher la saturation.

Comparer repos/palier/retour au repos et publier uniquement les valeurs mesurées.
Ce protocole ne constitue ni un test de capacité maximale ni un benchmark.
En HTTPS, ajouter seulement après bootstrap autorisé : DNS A/AAAA, redirection,
certificat de production reconnu, BOSH sans contenu mixte et refus des routes
privées. Utiliser les commandes du guide HTTPS ; ne pas conclure avec `curl -k`.
