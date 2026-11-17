# Présentation finale — Jitsi Meet sur GKE

Plan de soutenance de 12 minutes, à adapter à la durée imposée. Il s'agit du
contenu proposé des diapositives, pas d'un diaporama déjà exporté ou présenté.

À compléter avant rendu : nom de l'étudiante, établissement, intitulé exact du
Master, enseignant, année universitaire et grille officielle. Remise : 18 novembre 2026.

## 1. Besoin et problématique — 45 s

**À afficher :** titre du rapport ; besoin de visioconférence ; question : comment
déployer, sécuriser et valider une plateforme reproductible sur un budget limité ?
**À dire :** le travail couvre infrastructure, application, automatisation et preuves.
L'objectif n'est pas de démontrer une capacité de production illimitée.
**Visuel :** page de titre, identité académique réelle à compléter.

## 2. Objectifs et méthode — 45 s

**À afficher :** déclarer → déployer → sécuriser → mesurer → automatiser.
Séparer résultat observé, validation statique et perspective.
**À dire :** progression par étapes, arrêt des expérimentations à risque et
conservation des incidents. Deux nœuds e2-standard-2 imposent un budget de ressources.
**Preuve :** tableau de conformité et historique Git.

## 3. Architecture commentée — 75 s

**À afficher :** navigateur HTTPS → LB TCP → Caddy → Web/BOSH → Prosody ;
Jicofo organise ; JVB relaie les médias via UDP 10000 et son LB séparé.
**À dire :** Docker construit les images ; Kubernetes orchestre les conteneurs ;
GKE gère le plan de contrôle. Le runtime du cluster est containerd.
Le proxy conserve les certificats ACME sur PVC ; aucun Ingress GKE.
**Visuel :** schéma du rapport, clairement présenté comme schéma et non capture.
**Limite :** une réunion à deux peut utiliser P2P.

## 4. Infrastructure et Terraform — 60 s

**À afficher :** cluster + node pool ; deux nœuds ; backend GCS privé/versionné.
**À dire :** Terraform décrit le souhaité et compare au réel via son état.
Migration du backend et plan readonly GitHub réellement validés.
**Preuve :** run 44116737677 et synthèse JSON, sans afficher l'état complet.
**Limite :** workflow apply préparé mais jamais exécuté ; environnement de revue
et secret de transport restent à configurer. Ne pas annoncer un apply automatique réussi.

## 5. Helm, HTTPS et incidents réseau — 60 s

**À afficher :** chart Jitsi 3.10.0, chart edge, valeurs distinctes ; BOSH même origine.
**À dire :** l'accès initial utilisait localhost et deux tunnels ; recréer le
transfert VS Code a corrigé un tunnel TCP sans réponse HTTP. L'évolution HTTPS
DuckDNS/Caddy a rendu possible l'accès public sans acheter de domaine.
**Preuve :** révisions historiques Jitsi 4 / edge 3, HTTP redirigé vers HTTPS.
**Limite :** coût des LB/PVC ; certificat gratuit ne signifie pas infrastructure gratuite.

## 6. Secrets et identité — 60 s

**À afficher :** GitHub OIDC → WIF → compte de service ; SOPS → KMS → fichier temporaire.
**À dire :** pas de clé JSON permanente ; rôles IAM et RBAC sont deux contrôles
complémentaires. Base64 Kubernetes n'est pas du chiffrement.
**Preuve :** fichier SOPS chiffré et workflow ; aucune valeur déchiffrée à l'écran.
**Limite :** aucune démonstration de rotation complète des secrets.

## 7. CI et CD : résultats distincts — 75 s

**À afficher :** CI verte ; CD Helm historique réussie ; flags désactivés ;
Terraform apply et nouveaux pipelines Malleus/Chaos non exécutés.
**À dire :** la CI vérifie rendu, configuration et tests Python ; elle ne prouve
pas une réunion. Le CD Helm OIDC/SOPS a réellement déployé. L'apply contrôlé
exige la revue du plan exact et ne doit pas être déclenché pour la soutenance.
**Preuve :** CI 44167828378, CD réelle 44057014445, CD suivante skipped 44167893494.
**Incident :** expression runner.temp interdite au niveau job corrigée par PR 14.

## 8. Validation fonctionnelle et référence — 75 s

**À afficher :** deux utilisateurs : audio/vidéo/chat ; trois : activité JVB étayée.
Référence 120,001 s / 8 relevés ; palier 300,001 s / 20 relevés.

| Mesure | Repos | Palier 3, fenêtre complète |
|---|---:|---:|
| CPU JVB moyen | 8,632 mCPU | 85,794 mCPU |
| Mémoire JVB moyenne | 303,580 Mi | 305,922 Mi |

**À dire :** le palier comprend la montée en charge ; il ne contient pas trois
participants à chaque relevé. Les valeurs Metrics Server peuvent être répétées.
**Preuve :** synthèse recalculée et rapport. Capture de salle seulement si disponible,
avec accord des participants et sans donnée privée.

## 9. Malleus/Selenium et ressources — 75 s

**À afficher :** médias synthétiques ; Chrome/Selenium pilotés par Malleus ;
premier essai GKE arrêté pour saturation ; second essai low CPU terminé.
**Résultats :** deux clients, 388877 et 260389 octets RTP reçus ; 694 et 632
images décodées ; fenêtre stricte observée 56,35 s ; CPU nœuds maximum 61 %.
**À dire :** réduire les limites CPU et séparer Selenium du JVB a permis le test.
Les images GHCR sont épinglées par digest ; leur build seul n'est pas une réunion.
**Limites :** scénario configuré 90 s, sans preuve de 90 s continues de vidéo ;
ni HD ni capacité maximale démontrée. Nouveau workflow dédié non exécuté.

## 10. Chaos Mesh et récupération — 60 s

**À afficher :** une injection pod-kill ciblant uniquement Web ; récupération
HTTPS 15,331 s après requête d'injection ; nouveau pod Ready ; autres composants préservés.
**À dire :** tester la récupération ne signifie pas garantir une disponibilité
continue : des réponses 502 et erreurs de transport ont été observées.
**Preuve :** synthèse Chaos, contrôle des UID et nettoyage temporaire.
**Limites :** aucune conférence active durant l'injection ; pas de test de panne
JVB ni de haute disponibilité ; nouveau workflow manuel non exécuté.

## 11. Bilan, coûts et limites — 45 s

**À afficher :** ce qui fonctionne, ce qui reste partiel, ce qui n'a pas été exécuté.
**À dire :** deux VM, disques, deux LB, trafic, stockage et KMS sont facturables.
Le nettoyage doit préserver les preuves, les certificats et l'état distant tant
qu'une décision de conservation n'est pas prise. Aucun nettoyage cloud durant l'oral.
**Preuve :** tableau de conformité ; pas de montant inventé ni de benchmark extrapolé.

## 12. Conclusion et perspectives — 45 s

**À afficher :** chaîne reproductible et sécurisée ; validation fondée sur preuves ;
perspectives : apply contrôlé, exécution des nouveaux pipelines, observabilité et HA.
**À dire :** les objectifs exécutés sont séparés des mécanismes préparés.
Demander confirmation du barème pour les exigences d'automatisation encore partielles.

## Démonstrations possibles, uniquement en lecture seule

Préparer avant l'oral des captures **réelles** : CI réussie avec SHA, CD Helm
historique, plan readonly, tableaux des essais, erreur/récupération Chaos.
Masquer les informations personnelles, jamais fabriquer une capture manquante.

Si l'accès réseau fonctionne et que le maintien du cluster est autorisé :
ouvrir seulement la page HTTPS et les preuves GitHub ; ne pas rejoindre une salle
ni lancer un workflow pendant la démonstration sans autorisation distincte.
Un contrôle déjà authentifié peut lire `kubectl get pods -n jitsi` ; il n'est
pas nécessaire de l'exécuter pour expliquer les résultats historiques.

Solution de repli hors ligne : rapport, schéma, synthèses JSON et captures
préparées. Indiquer leur date ; ne pas les présenter comme une observation en direct.
Le temps d'une démonstration remplace une partie des diapositives, il ne s'ajoute
pas automatiquement aux 12 minutes.

## Questions à préparer

- Pourquoi Helm et Terraform ensemble ? Infrastructure et application ont des cycles différents.
- Pourquoi deux LB ? Signalisation HTTPS et transport média UDP répondent à des besoins distincts.
- Comment prouver JVB ? Statistiques, ICE et RTP ; une configuration seule ne suffit pas.
- Pourquoi pas plus de charge ? Budget CPU et saturation observée, sans extrapolation de capacité.
- Pourquoi OIDC ? Identité courte durée sans clé statique ; restrictions dépôt/branche/environnement.
- L'apply est-il validé ? Non ; plan readonly exécuté, apply contrôlé seulement préparé.
- Le chaos démontre-t-il la HA ? Non ; récupération mesurée avec une interruption temporaire.

Sources : [rapport](rapport.md), [preuves](preuves-livraison.md),
[conformité](conformite-finale.md). Vérifier l'identité académique, les captures,
la durée imposée et l'export PDF avant remise.
