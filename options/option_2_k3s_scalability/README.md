# Option 2 - K3s Scalability + Streamlit + Monitoring

## Objectif

Prevoir une evolution plus complete du projet sans casser la stack Docker Compose actuelle.

Cette option introduit:

- une cible Kubernetes legere avec `K3s`
- une exposition plus propre des services
- une possibilite d'ajouter Streamlit comme front metier
- un monitoring cluster + applicatif plus complet

## Pourquoi K3s

K3s est un choix pertinent ici car il est:

- plus leger qu'un cluster Kubernetes classique
- plus simple a lancer en local ou sur petite VM
- suffisant pour montrer la scalabilite, le deploiement et la supervision

## Positionnement

La stack actuelle reste la reference pour:

- le developpement
- la demo locale
- la CI

K3s devient une option d'extension si le projet doit aller vers:

- la haute disponibilite
- la replication de services
- l'auto-healing
- une meilleure separation entre front, APIs, monitoring et orchestration

## Architecture cible

```text
[ User ]
   |
   v
[ Ingress ]
   |
   +--> [ Streamlit UI ]
   |
   +--> [ Gateway ]
            |
            +--> [ predict-text-api ]
            +--> [ predict-image-api ]
            +--> [ training-api ]

[ metrics-server ]
       |
[ Prometheus ] [ Grafana ] [ Alertmanager ]
       |
[ Loki ] [ Promtail ] [ Traefik metrics ]
       |
[ Airflow ] [ MLflow ]
```

## Composants proposes

- `gateway`
- `predict-text-api`
- `predict-image-api`
- `training-api`
- `streamlit-ui`
- `metrics-server`
- `prometheus`
- `grafana`
- `alertmanager`
- `kube-state-metrics`
- `node-exporter`
- `traefik`
- `loki`
- `promtail`
- `mlflow`

## Monitoring recommande

Pour une evolution K3s credible, il faut superviser a la fois:

- le cluster K3s lui-meme
- l'entree reseau
- les APIs metier
- les logs

### Stack recommande

#### Socle Kubernetes

- `metrics-server`
  Permet de voir CPU et memoire par node et par pod, et sert de base si on ajoute plus tard du `HPA`.
- `kube-prometheus-stack`
  Fournit `Prometheus`, `Grafana`, `Alertmanager`, `kube-state-metrics` et `node-exporter`.
- `Traefik metrics`
  K3s embarque Traefik par defaut, ce qui permet de monitorer l'ingress et les erreurs HTTP a l'entree.

#### Logs

- `Loki + Promtail`
  Permet de centraliser les logs des pods et de corriger plus vite une panne applicative ou un probleme de routing.

### Ce qu'il faut monitorer

#### Niveau cluster

- CPU et memoire des nodes
- CPU et memoire des pods
- nombre de pods redemarrant
- pods `Pending`, `CrashLoopBackOff` ou `Error`
- disponibilite des deployments

#### Niveau Kubernetes

- nombre de replicas prets
- pods non disponibles
- saturation des requests/limits
- evenements de redemarrage

#### Niveau ingress

- nombre de requetes Traefik
- taux d'erreur `4xx` et `5xx`
- latence moyenne par route

#### Niveau applicatif

Les APIs actuelles exposent deja des metriques Prometheus, donc il faut continuer a scraper:

- `gateway`
- `predict-text-api`
- `predict-image-api`
- `training-api`
- plus tard `streamlit-ui`

Metriques interessantes a remonter:

- `mlops_gateway_requests_total`
- `mlops_gateway_request_duration_seconds`
- `mlops_predictions_total`
- `mlops_prediction_duration_seconds`
- `mlops_training_requests_total`
- `mlops_training_runs_total`

## Dashboards a prevoir

Pour une demo K3s claire, il est utile d'avoir 4 dashboards ou vues Grafana.

### 1. Vue cluster

- CPU node
- memoire node
- nombre de pods
- pods en erreur

### 2. Vue ingress

- volume de trafic entrant
- latence moyenne
- erreurs `4xx`
- erreurs `5xx`

### 3. Vue APIs MLOps

- trafic du gateway
- latence du gateway
- nombre de predictions par modele
- taux d'erreur sur `predict/svm`, `predict/cnn`, `predict/multimodal`

### 4. Vue training

- nombre de runs d'entrainement
- duree moyenne de train
- erreurs de train
- disponibilite du `training-api`

## Alertes utiles

Des alertes simples suffisent deja a rendre la cible K3s plus industrielle:

- pod `gateway` indisponible
- pod `predict-image-api` ou `predict-text-api` indisponible
- plus de `5xx` sur le gateway sur 5 minutes
- latence moyenne trop elevee sur le gateway
- trop de redemarrages de pods
- manque de memoire sur un node

## Idee de phase

### Phase 1

Migrer uniquement:

- `gateway`
- `predict-text-api`
- `predict-image-api`
- `training-api`
- `metrics-server`
- `kube-prometheus-stack`

### Phase 2

Ajouter:

- `streamlit-ui`
- `prometheus`
- `grafana`
- `ingress`
- `alertmanager`
- `traefik metrics`

### Phase 3

Brancher:

- `autoscaling`
- `persistent volumes`
- `secrets`
- `CI/CD deploiement K3s`
- `loki`
- `promtail`
- alertes applicatives plus fines

## Lancement cible

Exemple de flux:

```powershell
kubectl apply -k options/option_2_k3s_scalability/manifests
```

## Benefices

- meilleure scalabilite horizontale des APIs
- separation plus propre des roles techniques
- possibilite de faire evoluer Streamlit en front metier
- meilleure observabilite du cluster et des APIs
- base pour des alertes et de l'auto-healing
- base credible pour un projet plus industriel

## Limites

- plus complexe que Docker Compose
- demande une gestion des secrets et du stockage plus rigoureuse
- Airflow et MLflow doivent etre consolides avant une vraie mise en production
- la partie monitoring K3s ajoute de nouveaux composants a administrer
