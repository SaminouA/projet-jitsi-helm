# Bootstrap HTTPS : séquence courte à approuver


> État actuel pour la publication : Jitsi révision 3, Caddy révision 2 en ACME
> production, DNS Web 34.78.71.58 et PVC 10Gi Bound. Le profil spécifique au
> domaine est maintenant versionné en production ; les commandes de bootstrap
> ci-dessous imposent explicitement staging. Les constats antérieurs et l'échec
> initial conservés plus bas sont historiques. Ne pas rejouer un bootstrap sur
> ces ressources existantes. La réunion à deux est confirmée manuellement par
> l'utilisatrice ; aucun test de charge ou partage d'écran n'est revendiqué.


Vérifications du 16 novembre 2026. **Commandes préparées, non exécutées.**
Utiliser Bash, depuis la racine, dans la même session. Arrêter à chaque étape
numérotée pour valider les résultats. Le guide complet, les quotas, coûts et
limites sont dans [https-duckdns.md](https-duckdns.md).

1. **Précontrôle et capture de la révision**, sans lire de secret.
   Les fichiers DuckDNS sont locaux ; les deux CI vertes concernent `c591ad4`.

```bash
set -euo pipefail
umask 077
export CLOUDSDK_CORE_PROJECT=project-fcf2ef91-c005-4910-a10
DOMAIN=jitsi-meet-m2.duckdns.org
test "$(kubectl config current-context)" = gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster
kubectl -n jitsi get pods,svc,pvc
helm list -n jitsi
helm lint --strict charts/jitsi-edge -f deploy/jitsi-edge-duckdns.yaml
mkdir -p deploy/local
REV=$(helm list -n jitsi --filter '^jitsi$' -o json | python3 -c \
  'import json,sys; r=json.load(sys.stdin); assert len(r)==1 and r[0]["status"]=="deployed"; print(r[0]["revision"])')
(set -o noclobber; printf '%s\n' "$REV" > deploy/local/jitsi-before-public.revision)
```

Si le fichier de révision existe, interrompre et le relire ; ne pas l'écraser.
Confirmer absence de release edge, de PVC homonyme et d'adresse homonyme avant
la suite. Ne pas continuer après une erreur ou une évolution de l'infrastructure.

2. **Après accord sur budget, bootstrap et exposition publique du Web** :
   réserver l'IP, créer le PVC puis installer Caddy staging. Aucun changement IAM.

```bash
gcloud compute addresses list --filter='name=jitsi-edge-ip' --format='table(name,address,status)'
# Continuer uniquement si les trois ressources homonymes sont absentes.
gcloud compute addresses create jitsi-edge-ip --region=europe-west1 \
  --network-tier=PREMIUM
kubectl apply -f deploy/jitsi-edge-storage.yaml
helm install jitsi-edge charts/jitsi-edge -n jitsi \
  -f deploy/jitsi-edge-duckdns.yaml --set acmeEnvironment=staging --wait --timeout 10m
EDGE_IP=$(gcloud compute addresses describe jitsi-edge-ip \
  --region=europe-west1 --format='value(address)')
test "$(kubectl -n jitsi get svc jitsi-edge -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" = "$EDGE_IP"
test "$(kubectl -n jitsi get pvc jitsi-edge-data -o jsonpath='{.status.phase}')" = Bound
kubectl -n jitsi get pods,svc,pvc
printf 'DuckDNS A doit devenir : %s\n' "$EDGE_IP"
```

Le PVC peut rester Pending avant le premier pod (WaitForFirstConsumer).
Ne pas attendre Bound avant l'installation. `helm --wait` ne garantit pas TLS.

3. **DNS puis staging** : dans DuckDNS, mettre A sur `$EDGE_IP`, retirer tout AAAA
   inadapté. Aucun jeton dans les commandes. Attendre la propagation, confirmer
   aussi via des résolveurs publics. Le contrôle ci-dessous impose l'unique IP
   Caddy au résolveur local ; ne pas contacter l'ancienne IP `37.67.80.37`.

```bash
python3 - "$DOMAIN" "$EDGE_IP" <<'PY'
import socket, sys
ips = {x[4][0] for x in socket.getaddrinfo(sys.argv[1], 443)}
assert ips == {sys.argv[2]}, ips
print('DNS local conforme :', ips)
PY
curl --head --max-time 15 "http://$DOMAIN/"
timeout 15 openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" \
  -showcerts </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

Attendre une redirection vers HTTPS sans port interne et un certificat staging
pour le bon domaine. L'émetteur staging n'est pas reconnu : aucun succès TLS
production n'est encore revendiqué. Diagnostic ACME si aucune émission.

4. **Après validation staging et accord production ACME**, obtenir un certificat
   reconnu. Ne pas migrer Jitsi tant que ces contrôles échouent.

```bash
helm upgrade jitsi-edge charts/jitsi-edge -n jitsi \
  -f deploy/jitsi-edge-duckdns.yaml --set acmeEnvironment=production \
  --wait --timeout 10m --no-hooks --hide-notes
curl --head --max-time 15 "https://$DOMAIN/"
timeout 15 openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" \
  -verify_hostname "$DOMAIN" -verify_return_error </dev/null
test "$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' "https://$DOMAIN/colibri/stats")" = 404
```

5. **Après accord de migration Jitsi**, préserver les valeurs live et vérifier
   que la révision capturée est toujours la dernière révision déployée.

```bash
test "$(helm list -n jitsi --filter '^jitsi$' -o json | python3 -c \
  'import json,sys; r=json.load(sys.stdin); assert len(r)==1 and r[0]["status"]=="deployed"; print(r[0]["revision"])')" = "$REV"
helm upgrade jitsi charts-officiels/jitsi-meet -n jitsi --reuse-values \
  -f values-jitsi-public.yaml -f deploy/jitsi-duckdns.yaml \
  --wait --timeout 10m --no-hooks --hide-notes
kubectl -n jitsi get pods,svc,endpointslices
test "$(kubectl -n jitsi get svc jitsi-jitsi-meet-jvb -o jsonpath='{.status.loadBalancer.ingress[0].ip}')" = 34.62.165.81
curl --fail --silent --show-error --max-time 15 -o /dev/null "https://$DOMAIN/config.js"
curl --fail --silent --show-error --max-time 15 -o /dev/null "https://$DOMAIN/http-bind"
```

Les HTTP 200 ne prouvent pas une réunion. Vérifier l'absence de contenu mixte et
faire l'essai à trois participants prévu dans `validation-remise.md`.
La réutilisation des valeurs évite d'extraire/déchiffrer des secrets ici ; ne pas
ajouter `--debug`, ni afficher les valeurs Helm ou Secrets. Aucune CD activée.

## Retour arrière, après accord

Relire l'historique et confirmer qu'aucune autre livraison n'est intervenue.
Restaurer la révision capturée, puis vérifier le profil localhost. Le port-forward
est bloquant ; le lancer dans un autre terminal après les autres contrôles.

```bash
helm history jitsi -n jitsi
REV=$(cat deploy/local/jitsi-before-public.revision)
[[ "$REV" =~ ^[0-9]+$ ]]
helm rollback jitsi "$REV" -n jitsi --wait --timeout 10m --no-hooks
kubectl -n jitsi get pods,svc,endpointslices
# Si la release edge est bien celle creee par ce bootstrap et retrait approuve :
helm uninstall jitsi-edge -n jitsi --wait --timeout 10m
# Le PVC/disque et l'adresse restent conserves et potentiellement facturables.
```

Puis, dans un autre terminal :

```bash
kubectl -n jitsi port-forward --address=127.0.0.1 svc/jitsi-jitsi-meet-web 8081:8000
```

Ouvrir `http://localhost:8081` et contrôler BOSH. Retirer le DNS public selon la
décision approuvée. La libération de l'IP, après disparition réelle des règles LB,
et toute suppression de disque/PVC requièrent un accord de nettoyage distinct ;
voir le guide complet. Ne jamais toucher au LB UDP JVB existant.

## Décision attendue et risques

À approuver séparément : coûts/exposition et bootstrap, DNS, production ACME,
migration Jitsi, puis éventuel retrait/nettoyage. La lecture PVC du compte CD
reste refusée ; sa correction ne bloque pas ce bootstrap opérateur mais requiert
un accord avant toute modification RBAC. Fusion PR et activation CD sont exclues.

Risques : une réplique et disque zonal, coupure lors des mises à jour Recreate,
accès anonyme public de démonstration, DNS/ACME non encore validés, coût variable
selon trafic, ressources réseau résiduelles après échec. Conserver un PVC garde
les clés ACME et sa facturation ; le supprimer peut détruire ces clés.
Un rollback Jitsi seul laisse le Web exposé par Caddy jusqu'au retrait edge.


## Exécution autorisée des étapes 1 et 2 — arrêt sur erreur

Le 16 novembre 2026, les précontrôles et le lint ont réussi. La révision Jitsi 2
est conservée dans `deploy/local/jitsi-before-public.revision`, sans secret et
sans écrasement. La première tentative de réservation a échoué avec :
`IP Version is not supported for regional addresses.`

La commande préparée contenait à tort `--ip-version=IPV4`. L'aide locale confirme
que cette option est réservée aux adresses globales et que la valeur par défaut
est IPV4. Les commandes ci-dessus sont corrigées en supprimant cette option,
mais **aucune nouvelle tentative n'a été exécutée**.

Arrêt conformément à la demande : aucune adresse réservée dans le projet après
l'échec, aucun PVC ni release edge créé. Les quatre pods Jitsi restent Ready,
sans redémarrage ; la release reste déployée en révision 2. DuckDNS, production
ACME, profil Jitsi et permissions n'ont pas été modifiés.
Pour une reprise, refaire les précontrôles et vérifier la révision déjà capturée
sans réexécuter son écriture exclusive, puis reprendre à la réservation corrigée.
