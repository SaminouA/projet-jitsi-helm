# Résultat du test unique — exécuté puis nettoyé le 17 novembre 2026

Une seule injection pod-kill Web a été réalisée après autorisation. Nouveau pod
Ready en environ 2 s ; disponibilité HTTPS confirmée environ 15,3 s après la
requête, avec 3 HTTP502 et 3 erreurs de transport échantillonnées. Les autres
pods, Secrets applicatifs, PVC/IP et révisions Jitsi 4/Caddy 3 sont inchangés.
Nettoyage confirmé : PodChaos, release, namespace, 23 CRD, RBAC et webhooks du test
retirés. [Preuve expurgée](../tests/chaos/results-summary.json).

**Ne pas rejouer les commandes ci-dessous : elles décrivent la préparation
historique d’un essai déjà exécuté. Le pod cible initial n’existe plus. Toute
nouvelle expérience nécessite un nouvel accord et une réévaluation complète.**

La procédure préparatoire originale est conservée ci-dessous ; les mentions
« non exécuté » y décrivent son état avant l’autorisation, pas le résultat actuel.

---

# Chaos Mesh : préparation du test Web unique, aucune installation effectuée

État vérifié le 17 novembre 2026 : GKE Standard, deux nœuds COS, kernel 6.12.110+,
containerd 2.2.7 ; API apps/rbac/admissionregistration/apiextensions v1 disponibles.
Nœuds à 4–5 % CPU et 36–38 % mémoire, cinq pods Jitsi/Caddy prêts. Jicofo et JVB
indiquent zéro conférence/participant. Ces contrôles devront être actualisés
immédiatement avant la future installation et l’injection autorisées.

## Verdict et périmètre

**GO conditionnel pour installer et tester un unique pod-kill Web après accord.**
Pas de garantie de compatibilité runtime tant que le contrôleur/webhook n’est
pas Ready. Refuser l’injection si un contrôle échoue, si une réunion apparaît,
si le pod cible a changé, si les permissions négatives ne sont pas confirmées
ou si le temps de récupération maximal de 120 s n’est pas accepté.

L’action pod-kill utilise Get/Delete Kubernetes, sans appel au daemon runtime :
[source Chaos Mesh 2.8.8](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.8/controllers/chaosimpl/podchaos/podkill/impl.go).
La compatibilité des fautes container-kill, réseau, kernel ou pod-failure n’est
pas déduite de ce constat et ces actions sont exclues de cette expérience.

Le chart officiel 2.8.8 a été téléchargé et son SHA256 comparé à l’index officiel.
Le plan [plan.json](../tests/chaos/plan.json) conserve le digest, l’inventaire CRD
et le nom/UID préparés. Le chart n’offre pas chaosDaemon.create ; le post-renderer
obligatoire retire le DaemonSet et son ServiceAccount, ainsi que le RBAC dashboard
qui est encore rendu même avec dashboard.create=false. Il réduit le rôle cible
à pods get/list/watch, **delete du seul nom Web approuvé**, événements et PodChaos.
Aucun create/update/patch de pod, aucun accès aux secrets applicatifs dans jitsi.
Les autres droits du contrôleur concernent ses ressources de contrôle dans son
namespace et des lectures cluster ; aucun changement IAM Google requis.

Rendu validé localement : 1 Deployment/1 réplique, 1 Service ClusterIP, 1 SA,
4 Secrets TLS temporaires, 2 ClusterRoles, 1 ClusterRoleBinding, 1 Role,
2 RoleBindings, 1 MutatingWebhookConfiguration, 2 ValidatingWebhookConfigurations
et 23 CRD. Les clés/certificats générés du rendu ne sont jamais affichés/exportés.
Aucun DaemonSet/hostPath/hostNetwork/conteneur privileged, dashboard, DNS serveur,
Prometheus, BPF, PVC ou LoadBalancer. Le mode post-renderé est spécifique à ce
pod-kill et ne doit pas être réutilisé pour d’autres types de faute.

Coût prévu : un contrôleur temporaire sur les nœuds existants, request 50m CPU /
256 Mi, limites 300m /512 Mi. Aucun nouveau nœud, disque, IP ou LB prévu.
Trafic de téléchargement d’image et logs/metrics éventuellement facturables selon
la tarification existante. Si le pod reste Pending, arrêter : ne pas ajouter de
capacité ou changer l’autoscaling pour ce test. Aucune ressource n’a été créée.

Risque accepté à obtenir : Web a une seule réplique ; sa suppression peut
produire temporairement 502/503 ou une erreur réseau HTTPS. Le remplacement est
assuré par le Deployment existant, pas par une restauration Chaos Mesh. Le
contrôle API est enregistré via des webhooks, limités ici aux ressources Chaos ;
la readiness et leur suppression finale sont obligatoires. Les limites RBAC
nominatives protègent JVB/Jicofo/Prosody/Caddy contre une suppression par ce SA.

## Procédure prête, à ne pas exécuter avant accord

1. Revalider contexte, zéro conférence, santé, IP/PVC et releases Jitsi 4/edge 3.
   Vérifier que chaos-testing, la release chaos-mesh et les CRD du plan sont
   absents ; sinon arrêter, ne pas réutiliser/supprimer des ressources d’autrui.
   Capturer dans /tmp un inventaire privé : CRD présentes, absence de namespace
   et de release, UID des cinq pods, Services/PVC et révisions Helm.
2. Confirmer le nom/UID actuel du Web et son propriétaire ReplicaSet/Deployment.
   Les fichiers préparés ciblent jitsi-jitsi-meet-web-8454659c99-gpjzl, UID
   2a77025e-3511-4fb7-8df0-e4a0b9e799b6. Si ce couple a changé, régénérer le plan,
   le manifest et le rôle nominatif, puis refaire la validation avant injection.
3. Après autorisation explicite de création namespace/CRD/RBAC/webhooks/Secrets
   temporaires et du test, installer le chart vérifié. Ne pas utiliser un autre
   nom de release ou namespace avec ce post-renderer.

```bash
set -euo pipefail
EXPECTED_CONTEXT=gke_project-fcf2ef91-c005-4910-a10_europe-west1-b_jitsi-cluster
[[ "$(kubectl config current-context)" == "$EXPECTED_CONTEXT" ]]
export CHAOS_WEB_POD=jitsi-jitsi-meet-web-8454659c99-gpjzl
helm install chaos-mesh /tmp/jitsi-chaos-chart/chaos-mesh \
  --namespace chaos-testing --create-namespace \
  -f tests/chaos/values-controller-only.yaml \
  --post-renderer ./scripts/chaos-web-postrender.py \
  --atomic --wait --timeout 180s
kubectl -n chaos-testing get pods,deploy,svc
```

Même avec --atomic, un échec peut laisser namespace et CRD. Ne jamais déclencher
l’expérience pour « voir si cela fonctionne » lorsque le contrôleur est en erreur.
Aucune modification de firewall GCP, du runtime ou de droits supplémentaires
n’est autorisée implicitement par cette préparation.

4. Contrôler l’identité/les droits effectifs du SA installé. Attendus : yes pour
   delete du nom exact, no pour delete sans nom, create/update/patch de pods,
   get de secrets jitsi et delete de chacun des quatre autres pods. Aucun daemon
   ni composant facultatif ne doit être présent.

```bash
CHAOS_AS=system:serviceaccount:chaos-testing:chaos-controller-manager
kubectl auth can-i delete "pods/$CHAOS_WEB_POD" -n jitsi --as="$CHAOS_AS"
kubectl auth can-i delete pods -n jitsi --as="$CHAOS_AS"
kubectl auth can-i patch pods -n jitsi --as="$CHAOS_AS"
kubectl auth can-i get secrets -n jitsi --as="$CHAOS_AS"
```

5. Lancer l’[observateur en lecture](../scripts/observe-chaos-web.py) dans un
   terminal séparé, attendre baseline/HTTPS200, vérifier encore zéro conférence.
   Valider le manifest contre l’API et afficher le diff sans mutation. Puis,
   seulement si l’injection unique est autorisée et tous les contrôles réussis :

```bash
python3 scripts/observe-chaos-web.py
# Dans un autre terminal, pendant l'observation et apres les controles :
kubectl create --dry-run=server -f tests/chaos/podchaos-web-once.yaml
kubectl create -f tests/chaos/podchaos-web-once.yaml
```

Le dry-run serveur ne sera réalisé qu’après installation autorisée : la CRD
n’existe pas actuellement. Ne pas remplacer create par apply/réapplication
répétée et ne pas créer de Schedule/Workflow. Le sélecteur inclut namespace,
labels Web et nom explicite ; le RBAC delete confirme indépendamment ce nom.
Il n’y a pas de duration pour pod-kill : c’est une suppression ponctuelle,
avec gracePeriod=10, puis remplacement par Kubernetes. Aucun PodChaos n’est
préparé pour JVB, Jicofo, Prosody, Caddy ou les nœuds.

## Mesures et conditions de réussite préparées

L’observateur n’injecte aucune faute. Il collecte HTTP avec TLS normal environ
chaque seconde, noms/UID/Ready/terminaison/redémarrages environ toutes les deux
itérations, CPU/mémoire toutes les dix, événements sans messages sensibles.
Les délais réseau influencent la cadence : indiquer la précision réelle.
Dossiers privés ignorés tests/results/*-chaos-web, sans publication de logs bruts.

Réussite à démontrer, non constatée à ce jour : un seul ancien UID Web supprimé,
nouveau UID Web Ready, HTTPS200 rétabli, délai depuis première dégradation
observée mesuré, UID des quatre autres pods inchangés, PVC/IP et révisions Helm
inchangés. Un remplacement remet restartCount à zéro : comparer les UID, pas
seulement ce compteur. Une absence d’échec HTTP échantillonné ne prouve pas une
absence absolue d’interruption. Aucun résultat de réunion n’est déduit du test.

Si le Web ne revient pas prêt sous 120 s, arrêter l’expérience et diagnostiquer
Deployment/ReplicaSet/events ; ne pas réappliquer le PodChaos. Ne pas redéployer
Helm ou modifier les secrets/PVC. Le Deployment doit recréer son pod existant ;
si une intervention supplémentaire est nécessaire, demander accord sur cette
intervention concrète.

## Nettoyage complet prévu, après la mesure ou en cas d’échec

1. Archiver les états/conditions/events du seul PodChaos, sans secrets. Vérifier
   son UID enregistré à la création, puis le supprimer normalement et attendre
   la fin de ses finalizers ; ne pas forcer leur retrait.
2. Confirmer le nouveau Web Ready/HTTPS200 et les autres UID inchangés.
3. Vérifier qu’aucune autre ressource des 23 CRD, dans aucun namespace, n’a été
   créée par un autre utilisateur. Arrêter le nettoyage destructif si c’est le cas.
4. Désinstaller uniquement la release chaos-mesh de chaos-testing ; Helm enlève
   ses webhooks, Roles/Bindings (y compris celui de jitsi), SA, Service et Secrets.
5. Les CRD ne sont pas supprimées automatiquement : supprimer uniquement les
   noms du plan confirmés absents dans l’inventaire pré-installation et sans
   instance restante. Ne jamais utiliser un wildcard global ou supprimer des
   CRD préexistantes.
6. Vérifier que le namespace créé pour ce test ne contient aucune ressource
   étrangère puis le supprimer. Ne pas supprimer jitsi, PVC/PV ou release Jitsi/Caddy.
7. Recontrôler l’absence des objets installés, les cinq pods, PVC, IP, HTTPS et
   releases 4/3, puis conserver les preuves expurgées.

Commandes centrales préparées, non exécutées :

```bash
kubectl -n jitsi delete podchaos jitsi-web-kill-once --wait=true --timeout=60s
helm uninstall chaos-mesh -n chaos-testing --wait --timeout 120s
# Seulement apres preuve d'absence initiale et d'absence d'instances restantes :
python3 - <<'PY'
import json, subprocess
from pathlib import Path
plan = json.loads(Path('tests/chaos/plan.json').read_text())
for name in plan['crds']:
    data = json.loads(subprocess.check_output(['kubectl', 'get', name, '-A', '-o', 'json'], text=True))
    if data['items']:
        raise SystemExit('CRD encore utilisee : nettoyage refuse')
# L'inventaire prive pre-installation doit avoir ete compare humainement avant ce bloc.
subprocess.run(['kubectl', 'delete', 'crd', *plan['crds'], '--wait=true', '--timeout=60s'], check=True)
PY
kubectl delete namespace chaos-testing --wait=true --timeout=120s
```

En cas d’échec d’installation, adapter uniquement aux objets effectivement créés
et enregistrés. Aucun nettoyage n’a été exécuté pendant cette préparation.
