# Kubernetes Deployment Guide

## Overview
This guide covers deploying the MLOps platform on Kubernetes with:
- Minikube for local development
- Production-ready manifests with HPA (Horizontal Pod Autoscaling)
- Prometheus + Grafana monitoring
- Secrets management

## Prerequisites

### Local Development (Minikube)
```bash
# Install Minikube
brew install minikube
minikube start --cpus=4 --memory=8192

# Enable metrics server (for HPA)
minikube addons enable metrics-server

# Configure kubectl
kubectl config use-context minikube
```

### Production
- Kubernetes 1.20+ cluster
- kubectl 1.20+
- Helm 3.0+ (optional, for package management)
- Container registry (DockerHub, GCR, GHCR)

## Deployment Steps

### Step 1: Create Namespace & ConfigMaps
```bash
kubectl apply -f k8s/00-namespace-config.yaml
```

### Step 2: Update Secrets (IMPORTANT!)
Edit `k8s/00-namespace-config.yaml` before deploying:
```yaml
stringData:
  ADMIN_PASSWORD: "your-secure-password"  # Generate: openssl rand -hex 32
  JWT_SECRET: "your-jwt-secret"           # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Deploy secrets:
```bash
kubectl apply -f k8s/00-namespace-config.yaml
```

### Step 3: Deploy Data Layer (MLflow)
```bash
kubectl apply -f k8s/01-mlflow.yaml

# Check deployment
kubectl get pods -n mlops
kubectl logs -n mlops deployment/mlflow
```

### Step 4: Deploy Inference Service
```bash
# Update image references in k8s/02-inference.yaml
sed -i 's/your-org/your-registry/g' k8s/02-inference.yaml

kubectl apply -f k8s/02-inference.yaml

# Verify HPA
kubectl get hpa -n mlops
```

### Step 5: Deploy Training Service
```bash
kubectl apply -f k8s/03-training.yaml
```

### Step 6: Deploy Gateway (Entry Point)
```bash
kubectl apply -f k8s/04-gateway.yaml

# Get external IP
kubectl get svc gateway -n mlops
```

### Step 7: Deploy Monitoring Stack
```bash
kubectl apply -f monitoring/01-prometheus.yaml
kubectl apply -f monitoring/02-grafana.yaml

# Forward ports to local machine
kubectl port-forward -n mlops svc/prometheus 9090:9090 &
kubectl port-forward -n mlops svc/grafana 3000:3000 &
```

## Verification

### Health Checks
```bash
# Check all pods are running
kubectl get pods -n mlops

# Check services
kubectl get svc -n mlops

# Check Persistent Volumes
kubectl get pvc -n mlops
```

### Port Forwarding (Development)
```bash
# Gateway
kubectl port-forward -n mlops svc/gateway 8000:8000 &

# Inference
kubectl port-forward -n mlops svc/inference 8001:8000 &

# Training
kubectl port-forward -n mlops svc/training 8002:8000 &

# MLflow
kubectl port-forward -n mlops svc/mlflow 5000:5000 &

# Prometheus
kubectl port-forward -n mlops svc/prometheus 9090:9090 &

# Grafana
kubectl port-forward -n mlops svc/grafana 3000:3000 &
```

### Test Endpoints
```bash
# Gateway
curl http://localhost:8000/health

# Inference
curl http://localhost:8001/health

# Training
curl http://localhost:8002/health

# MLflow
curl http://localhost:5000

# Prometheus
curl http://localhost:9090/metrics

# Grafana
open http://localhost:3000
# Login: admin / admin (change password!)
```

## Scaling

### Manual Scaling
```bash
# Scale inference to 3 replicas
kubectl scale deployment inference -n mlops --replicas=3

# Check status
kubectl get rs -n mlops
```

### Automatic Scaling
HPA is configured in each deployment:
- **Inference**: 2-5 replicas (CPU 70%, Memory 80%)
- **Gateway**: 2-4 replicas (CPU 60%)

Monitor HPA status:
```bash
kubectl get hpa -n mlops -w
kubectl describe hpa inference -n mlops
```

## Updates & Rolling Deployments

### Update Image
```bash
# Update image
kubectl set image deployment/inference \
  inference=ghcr.io/your-org/inference:v2.0 \
  -n mlops

# Check rollout status
kubectl rollout status deployment/inference -n mlops

# Rollback if needed
kubectl rollout undo deployment/inference -n mlops
```

### Rolling Update with Blue-Green
```bash
# Create new version
kubectl set image deployment/inference \
  inference=ghcr.io/your-org/inference:v2.0 \
  -n mlops

# Monitor progress
kubectl rollout status deployment/inference -n mlops -w
```

## Monitoring

### Prometheus Metrics
Available metrics:
- `mlops_requests_total` - Total API requests
- `mlops_request_duration_seconds` - Request latency
- `mlops_model_predictions_total` - Model predictions
- `mlops_model_prediction_duration_seconds` - Model latency
- `mlops_errors_total` - Error count
- `mlops_data_drift_score` - Data drift detection

### Grafana Dashboards
1. Open http://localhost:3000
2. Login: admin / admin
3. Import dashboard from JSON (configure in k8s manifests)
4. Set up alerts

### Logs
```bash
# View pod logs
kubectl logs -n mlops deployment/inference -f

# Tail all containers in namespace
kubectl logs -n mlops -f -l app=inference --all-containers

# Search logs
kubectl logs -n mlops deployment/inference | grep "ERROR"
```

## Troubleshooting

### Pod Not Starting
```bash
# Check pod status
kubectl describe pod -n mlops <pod-name>

# Check events
kubectl get events -n mlops --sort-by='.lastTimestamp'

# Check logs
kubectl logs -n mlops <pod-name>
```

### PVC Issues
```bash
# Check PVC status
kubectl get pvc -n mlops
kubectl describe pvc mlops-data -n mlops

# Check node disk space
kubectl top nodes
```

### Service Connection Issues
```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
nslookup inference.mlops.svc.cluster.local

# Test service connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  wget -O- http://inference:8000/health
```

## Production Checklist

- [ ] Use strong secrets (generate with openssl/python)
- [ ] Set resource requests/limits appropriately
- [ ] Configure Ingress with TLS
- [ ] Set up external logging (ELK, Datadog, etc.)
- [ ] Configure backup for MLflow database
- [ ] Set up monitoring alerts
- [ ] Test failover procedures
- [ ] Document runbooks for common issues
- [ ] Set up RBAC and network policies
- [ ] Configure container image scanning

## Cleanup

```bash
# Delete all MLOps resources
kubectl delete namespace mlops

# Or selectively
kubectl delete deployment inference -n mlops
kubectl delete service inference -n mlops
kubectl delete pvc mlops-data -n mlops
```

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)
- [Grafana Kubernetes Datasource](https://grafana.com/grafana/plugins/grafana-kubernetes-app/)
