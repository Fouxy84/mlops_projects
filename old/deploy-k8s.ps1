# deploy-k8s.ps1
# Script de déploiement complet Kubernetes pour MLOps

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  MLOps Kubernetes Deployment via Docker Desktop" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Vérifier la connexion Kubernetes
Write-Host "[1] Verification de la connexion Kubernetes..." -ForegroundColor Yellow
kubectl cluster-info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Kubernetes n'est pas accessible !" -ForegroundColor Red
    Write-Host "   Activez Kubernetes dans Docker Desktop Settings -> Kubernetes" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Kubernetes est actif" -ForegroundColor Green
Write-Host ""

# 2. Créer le namespace et les configs
Write-Host "[2] Creation du namespace 'mlops' et des configurations..." -ForegroundColor Yellow
kubectl apply -f k8s/00-namespace-config.yaml
Write-Host "[OK] Namespace cree" -ForegroundColor Green
Write-Host ""

# 3. Attendre que le namespace soit prêt
Write-Host "[3] Attente de la disponibilite du namespace..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
Write-Host "[OK] Namespace pret" -ForegroundColor Green
Write-Host ""

# 4. Déployer les services dans l'ordre
Write-Host "[4] Deploiement des services..." -ForegroundColor Yellow
Write-Host "   - MLflow (data layer)" -ForegroundColor Cyan
kubectl apply -f k8s/01-mlflow.yaml
Start-Sleep -Seconds 3

Write-Host "   - Inference service" -ForegroundColor Cyan
kubectl apply -f k8s/02-inference.yaml
Start-Sleep -Seconds 2

Write-Host "   - Training service" -ForegroundColor Cyan
kubectl apply -f k8s/03-training.yaml
Start-Sleep -Seconds 2

Write-Host "   - Gateway (point d'entrée)" -ForegroundColor Cyan
kubectl apply -f k8s/04-gateway.yaml
Write-Host "[OK] Tous les services deployes" -ForegroundColor Green
Write-Host ""

# 5. Déployer la stack monitoring
Write-Host "[5] Deploiement de la stack Monitoring (Prometheus + Grafana)..." -ForegroundColor Yellow
kubectl apply -f monitoring/01-prometheus.yaml
Start-Sleep -Seconds 2
kubectl apply -f monitoring/02-grafana.yaml
Write-Host "[OK] Stack Monitoring deployee" -ForegroundColor Green
Write-Host ""

# 6. Attendre que les pods soient en cours d'exécution
Write-Host "[6] Attente du demarrage des pods (30 secondes max)..." -ForegroundColor Yellow
$timeout = 30
$elapsed = 0
$ready = $false

while ($elapsed -lt $timeout) {
    $pods = kubectl get pods -n mlops -o jsonpath='{.items[*].status.phase}' 2>$null
    if ($pods -match "Running" -and -not ($pods -match "Pending")) {
        $ready = $true
        break
    }
    Write-Host "   Attente... ($elapsed/$timeout sec)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
    $elapsed += 2
}

if ($ready) {
    Write-Host "[OK] Tous les pods sont prets" -ForegroundColor Green
} else {
    Write-Host "[WARN] Certains pods ne sont pas encore prets, continuons..." -ForegroundColor Yellow
}
Write-Host ""

# 7. Afficher l'état du déploiement
Write-Host "[7] Etat du deploiement :" -ForegroundColor Yellow
Write-Host ""
kubectl get pods -n mlops
Write-Host ""
kubectl get svc -n mlops
Write-Host ""

# 8. Afficher les instructions d'accès
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  [SUCCESS] Deploiement Kubernetes Reussi !" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "INSTRUCTIONS pour acceder aux services :" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Ouvrez 6 nouveaux terminals PowerShell et executez :" -ForegroundColor White
Write-Host ""
Write-Host "   Terminal 1 - Gateway (API principale)" -ForegroundColor Yellow
Write-Host "   kubectl port-forward -n mlops svc/gateway 8000:8000" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 2 - Inference service" -ForegroundColor Yellow
Write-Host "   kubectl port-forward -n mlops svc/inference 8001:8000" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 3 - Training service" -ForegroundColor Yellow
Write-Host "   kubectl port-forward -n mlops svc/training 8002:8000" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 4 - MLflow" -ForegroundColor Yellow
Write-Host "   kubectl port-forward -n mlops svc/mlflow 5000:5000" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 5 - Prometheus" -ForegroundColor Yellow
Write-Host "   kubectl port-forward -n mlops svc/prometheus 9090:9090" -ForegroundColor Gray
Write-Host ""
Write-Host "   Terminal 6 - Grafana" -ForegroundColor Yellow
Write-Host "   kubectl port-forward -n mlops svc/grafana 3000:3000" -ForegroundColor Gray
Write-Host ""

Write-Host "WEB INTERFACES :" -ForegroundColor Cyan
Write-Host "   - Gateway       : http://localhost:8000/health" -ForegroundColor White
Write-Host "   - MLflow        : http://localhost:5000" -ForegroundColor White
Write-Host "   - Prometheus    : http://localhost:9090" -ForegroundColor White
Write-Host "   - Grafana       : http://localhost:3000  (admin/admin)" -ForegroundColor White
Write-Host ""

Write-Host "USEFUL COMMANDS :" -ForegroundColor Cyan
Write-Host "   - Voir tous les pods      : kubectl get pods -n mlops" -ForegroundColor White
Write-Host "   - Voir les logs           : kubectl logs -n mlops deployment/inference" -ForegroundColor White
Write-Host "   - Decrire un pod          : kubectl describe pod pod-name -n mlops" -ForegroundColor White
Write-Host "   - Supprimer le deploiement: kubectl delete namespace mlops" -ForegroundColor White
Write-Host ""

Write-Host "Deploiement termine avec succes !" -ForegroundColor Green
