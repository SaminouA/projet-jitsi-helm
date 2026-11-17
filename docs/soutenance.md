> Document historique conservé. Pour l’état consolidé du 17 novembre 2026,
> consulter le [rapport final](rapport.md), les [preuves](preuves-livraison.md)
> et le [plan oral final](presentation-finale.md). Les statuts antérieurs ci-dessous
> ne décrivent pas nécessairement la version livrée.

# Soutenance Master 2 — Jitsi DevOps sur GCP

Support consolidé le 16 novembre 2026. Les états ci-dessous sont les dernières
observations documentées, pas une nouvelle vérification du cluster. Prévoir
12 minutes de présentation/démonstration, extensibles à 15 ; ne pas effectuer
un déploiement pendant la soutenance sans autorisation distincte.

## Fil conducteur et minutage

| Temps | Diapositive / propos | Preuve à montrer |
|---|---|---|
| 0:00–1:00 | Besoin : rendre une visioconférence reproductible, publique et contrôlée | URL HTTPS et objectifs, distinction configuration/disponibilité/usage |
| 1:00–2:30 | Architecture : HTTPS → Caddy → Web/BOSH → Prosody ; Jicofo et JVB | [Schémas](architecture.md), séparation Web TCP / média UDP |
| 2:30–3:45 | Terraform et GKE : cluster zonal, pool de deux e2-standard-2 | Sources .tf et lock provider ; état local exclu, aucune prétention HA |
| 3:45–5:00 | Helm/Kubernetes : chart communautaire 3.10.0, valeurs et révisions | Quatre composants, Services, endpoints ; Jitsi dernière révision observée 3 |
| 5:00–6:00 | Caddy/HTTPS : IP fixe Web, ACME production et PVC indépendant | Caddy révision 2 ; certificat reconnu, ports publics 80/443 et routes privées 404 |
| 6:00–7:30 | CI et sécurité : PR, tests, SOPS/KMS, OIDC et RBAC | CI main c3e8ead réussie, job CD skipped ; aucun secret affiché |
| 7:30–9:00 | Résultats et incident CD : test manuel réussi, whoami échoué | Témoignage utilisatrice et catégories du run 43959531200 ; correction exec ADC locale |
| 9:00–11:30 | Démonstration fonctionnelle si réseau/participants disponibles | Jitsitest, deux appareils, audio/vidéo avec consentement ; noter résultat réel du jour |
| 11:30–12:00 | Coûts, limites et étapes restantes | Pas de total facturé vérifié, CD non validée de bout en bout |

Version 10 minutes : réduire la démonstration à une minute et la lecture des
sources à l'architecture. Version 15 minutes : ajouter trois minutes de questions
ou d'explication OIDC ; ne pas lancer Actions pour occuper ce temps.

## Texte de présentation des points essentiels

« Terraform décrit le cluster et le pool. Helm installe les composants de Jitsi.
Caddy fournit HTTPS sur une IP Web distincte de l'IP UDP du bridge. La CI vérifie
les configurations ; les secrets versionnés restent chiffrés par SOPS/KMS. La CD
est définie mais désactivée et pas encore validée de bout en bout. »

« La séparation des preuves est importante : les pods prêts et HTTP 200 ne
prouvent pas une réunion. L'utilisatrice a confirmé une réunion à deux avec
ordinateur et téléphone, audio/vidéo dans les deux sens. Ce scénario ne dit pas
si les médias ont utilisé P2P ou JVB. »

« Le dernier diagnostic runner confirme OIDC/configuration GKE, plugin présent et
TCP accessible, puis échoue sur whoami avec INDETERMINE. La source de l'action
épinglée révèle un auth-provider gcp legacy. Je prépare un kubeconfig exec ADC
sans clé statique ; les tests locaux passent, mais cette correction n'a pas encore
été validée sur GitHub. Je n'élargis pas les permissions pour contourner l'erreur. »

## État des preuves utilisables

| Élément | Statut à annoncer |
|---|---|
| Jitsi HTTPS public | Déployé ; certificat production et routes vérifiés antérieurement |
| Salle jitsitest | Test manuel confirmé par l'utilisatrice : ordinateur + téléphone simultanés, audio/vidéo bidirectionnels |
| Main | c3e8ead17a35e234c1789c6d80da2e89c87a77fe au dernier contrôle |
| CI main | [Run 43958608127 réussi](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43958608127) |
| CD main | [Run 43958671759 skipped](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43958671759), aucune étape exécutée |
| Diagnostic | [Run 43959531200 échoué](https://github.com/SaminouA/projet-jitsi-helm/actions/runs/43959531200), aucune réussite SOPS/KMS runner |
| Correction exec ADC | Préparée/testée localement, non publiée lors de la finalisation |
| Partage d'écran / charge publique | Aucun résultat revendiqué ; ne pas les ajouter au bilan oral |
| Résultats du 15 novembre | Historiques distincts, déjà décrits dans le rapport ; pas un benchmark de la version publique actuelle |

## Démonstration, à répéter avant le jour J

Préparation opérateur : vérifier les cinq pods, LB/PVC et HTTPS en lecture seule,
avec accord de connexion au cluster ; fermer les terminaux de secrets, les états
Terraform et les sauvegardes. Préparer les pages GitHub des runs déjà réalisés.
Aucun lancement de diagnostic/CD ne fait partie de la démo par défaut.

```bash
kubectl -n jitsi get pods,svc,pvc,endpointslices
helm list -n jitsi
curl --head --max-time 15 https://jitsi-meet-m2.duckdns.org/
```

1. Afficher l'architecture et l'URL ; montrer le certificat dans le navigateur.
2. Montrer les deux releases et les quatre composants Jitsi prêts.
3. Ouvrir `https://jitsi-meet-m2.duckdns.org/jitsitest` sur l'ordinateur et le
   téléphone, autoriser les périphériques, utiliser des écouteurs pour éviter
   le larsen. Faire confirmer audio/vidéo dans chaque sens ; pas de capture média
   sans consentement. Le résultat du jour est à noter, pas à préremplir.
4. Montrer GitHub : PR relue, CI réussie, CD skipped et diagnostic échoué expurgé.
   Expliquer la différence entre leurs conclusions ; ne pas prétendre que la CD
   fonctionne parce que le site est accessible.
5. Quitter les deux clients et vérifier le retour au repos si une observation
   a été autorisée. Ne pas exécuter un test de charge ou partage d'écran improvisé.

## Si le réseau de l'école bloque DuckDNS ou UDP

Plan A : utiliser, avec l'autorisation de l'établissement, un partage de connexion
mobile pour l'ordinateur et le téléphone. Tester avant la séance. Cela ne prouve
pas le fonctionnement sur le réseau filtré ; l'absence de TURN reste une limite.
Ne pas désactiver la vérification TLS et ne pas modifier les politiques réseau.

Plan B : si seul DNS/accès Web est filtré mais que l'API GKE est accessible et
qu'un tunnel est autorisé, préparer une démonstration **technique HTTP/TLS** :

```bash
# Terminal distinct : tunnel local, sans modification d'objet Kubernetes.
kubectl -n jitsi port-forward --address=127.0.0.1 service/jitsi-edge 8443:443
```

Puis dans un autre terminal :

```bash
curl --head --max-time 15 \
  --connect-to jitsi-meet-m2.duckdns.org:443:127.0.0.1:8443 \
  https://jitsi-meet-m2.duckdns.org/
```

Le nom HTTPS et la vérification du certificat restent corrects. Cette commande
ne configure pas le navigateur et ne prouve aucun média. Ne pas promettre une
réunion via ce seul tunnel. Un port-forward Web 8081 ne rétablit pas le profil
localhost tant que Jitsi annonce l'URL publique : ne pas migrer l'application
pendant la soutenance pour contourner le filtrage.

Plan C hors ligne : montrer les sources, le schéma, les tests locaux et le
registre de preuves du rapport. Préparer demain des captures expurgées des runs
et du test manuel avec consentement ; aucune capture ou vidéo inexistante n'est
présentée comme déjà disponible. Le professeur doit savoir que la démo live est
empêchée par le réseau et que les observations citées sont antérieures.

## Questions probables et réponses courtes

| Question | Réponse fondée sur le projet |
|---|---|
| Pourquoi GKE ? | Plan de contrôle managé ; l'étude se concentre sur packaging, réseau et exploitation. Pas de comparaison exhaustive de fournisseurs. |
| Que gère Terraform ? | Cluster et pool. Pas les releases Helm, ni tout WIF/IAM/HTTPS. Le réseau par défaut et des manipulations opérateur restent des dépendances. |
| Pourquoi séparer Terraform et Helm ? | Infrastructure et application ont des cycles différents ; aucun provider Helm Terraform dans cette version. |
| Le chart est-il officiel Jitsi ? | Il vient de jitsi-contrib/jitsi-helm. Le nom local charts-officiels ne constitue pas une certification de l'éditeur. |
| Pourquoi deux IP publiques ? | TCP 80/443 pour le Web/TLS, UDP 10000 pour le bridge ; le DNS Web doit pointer vers Caddy. |
| Pourquoi BOSH même origine ? | Le navigateur reste sur HTTPS ; Web relaie la signalisation vers Prosody en interne, sans URL HTTP publique/mixed content. |
| Deux participants prouvent-ils JVB ? | Non. Le P2P est possible ; il faut une conférence instrumentée et des statistiques pour identifier le trajet. |
| Pourquoi pas Ingress/cert-manager ? | Caddy termine TLS dans le profil retenu. C'est un choix pédagogique, pas une exclusion générale des autres approches. |
| Pourquoi un PVC Caddy ? | Conserver état et clés ACME entre pods. RWO + une réplique implique Recreate ; le PVC indépendant reste après uninstall. |
| Base64 chiffre-t-il un Secret ? | Non. SOPS chiffre les valeurs versionnées ; KMS autorise le déchiffrement de leur clé de données. Les contrôles d'accès Kubernetes restent essentiels. |
| OIDC évite quoi ? | Une clé privée permanente de compte Google dans GitHub. Il faut néanmoins restreindre dépôt, branche, identité et droits. |
| Qu'est-ce que RBAC autorise ici ? | Opérations Helm dans jitsi, lecture pods/replicasets et get du seul PVC Caddy. Ce n'est pas un compte entièrement read-only. |
| Pourquoi le diagnostic est-il non déployant ? | Code relu, commandes admises en lecture, garde main/SHA et absence d'upgrade/apply ; les droits cloud existants ne suffisent pas à imposer cette sûreté seuls. |
| Pourquoi whoami échoue-t-il ? | Source action legacy gcp identifiée, plugin présent et TCP OK ; cause exacte masquée. Correction exec ADC encore non confirmée sur runner. |
| Pourquoi la CD est-elle désactivée ? | Diagnostic pas encore complet et auth CD à corriger ; activation séparée après revue/CI et autorisation, pas besoin de cacher cet écart. |
| Quel rollback ? | Révisions capturées juste avant essai, rollback Jitsi puis edge si concernées, contrôle URL et rechargement si nécessaire ; aucune suppression du PVC. |
| HA et montée en charge ? | Non démontrées : cluster zonal, un JVB et un Caddy. Aucun chiffre de capacité maximale. |
| Combien coûte le projet ? | Nœuds/GKE, réseau/LB, disque et trafic. Les hypothèses sont dans le rapport ; pas de total mensuel facturé ou plafond validé. |
| Comment sécuriser une exploitation durable ? | Politique d'accès Jitsi, supervision, sauvegardes/reprise testées, état Terraform distant verrouillé et protections humaines GitHub ; évolutions proposées, pas déployées. |

## Répétition et fin de séance

Renseigner nom officiel, établissement, encadrant et année universitaire avant
export. Répéter le minutage, vérifier batteries/casques et le plan réseau autorisé.
Garder les preuves offline à portée. Conclure sur ce qui est acquis (HTTPS et
usage manuel) et ce qui reste à valider (diagnostic complet et CD), sans annoncer
une mise en production industrielle ou un résultat de charge inexistant.
