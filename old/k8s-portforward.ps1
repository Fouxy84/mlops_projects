# k8s-portforward.ps1
# Lancer tous les port-forwards pour accéder aux services K8s

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Kubernetes Port-Forward Setup" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Fonction pour lancer un port-forward en arrière-plan
function Start-PortForward {
    param(
        [string]$ServiceName,
        [string]$LocalPort,
        [string]$RemotePort,
        [string]$Description
    )
    
    Write-Host "[*] Demarrage du port-forward : $Description" -ForegroundColor Yellow
    Write-Host "    Local: http://localhost:$LocalPort" -ForegroundColor Gray
    Write-Host ("    Service: {0}:{1}" -f $ServiceName, $RemotePort) -ForegroundColor Gray
    
    Start-Process -NoNewWindow -ArgumentList @(
        "kubectl",
        "port-forward",
        "-n", "mlops",
        "svc/$ServiceName",
        "$LocalPort`:$RemotePort"
    )
    
    Start-Sleep -Seconds 2
}

# Lancer tous les port-forwards
Write-Host ""
Write-Host "Lancement de tous les port-forwards..." -ForegroundColor Cyan
Write-Host ""

Start-PortForward -ServiceName "gateway" -LocalPort "8000" -RemotePort "8000" -Description "Gateway (API principale)"
Start-PortForward -ServiceName "inference" -LocalPort "8001" -RemotePort "8000" -Description "Inference Service"
Start-PortForward -ServiceName "training" -LocalPort "8002" -RemotePort "8000" -Description "Training Service"
Start-PortForward -ServiceName "mlflow" -LocalPort "5000" -RemotePort "5000" -Description "MLflow Tracking"
Start-PortForward -ServiceName "prometheus" -LocalPort "9090" -RemotePort "9090" -Description "Prometheus Metrics"
Start-PortForward -ServiceName "grafana" -LocalPort "3000" -RemotePort "3000" -Description "Grafana Dashboard"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  TOUS LES SERVICES SONT ACCESSIBLES !" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "WEB INTERFACES :" -ForegroundColor Cyan
Write-Host "  - Gateway       : http://localhost:8000/health" -ForegroundColor White
Write-Host "  - Inference     : http://localhost:8001/health" -ForegroundColor White
Write-Host "  - Training      : http://localhost:8002/health" -ForegroundColor White
Write-Host "  - MLflow        : http://localhost:5000" -ForegroundColor White
Write-Host "  - Prometheus    : http://localhost:9090" -ForegroundColor White
Write-Host "  - Grafana       : http://localhost:3000  (admin/admin)" -ForegroundColor White
Write-Host ""

Write-Host "COMMANDES UTILES :" -ForegroundColor Cyan
Write-Host "  - Voir les pods      : kubectl get pods -n mlops" -ForegroundColor White
Write-Host "  - Logs inference     : kubectl logs -n mlops deployment/inference -f" -ForegroundColor White
Write-Host "  - Logs training      : kubectl logs -n mlops deployment/training -f" -ForegroundColor White
Write-Host "  - Logs gateway       : kubectl logs -n mlops deployment/gateway -f" -ForegroundColor White
Write-Host "  - Logs mlflow        : kubectl logs -n mlops deployment/mlflow -f" -ForegroundColor White
Write-Host "  - Voir resources     : kubectl top pods -n mlops" -ForegroundColor White
Write-Host "  - Describe pod       : kubectl describe pod pod-name -n mlops" -ForegroundColor White
Write-Host ""

Write-Host "SERVICES KUBERNETES :" -ForegroundColor Cyan
Write-Host "  - Gateway HPA (2 replicas)  : http://localhost:8000" -ForegroundColor White
Write-Host "  - Inference HPA (2 replicas): http://localhost:8001" -ForegroundColor White
Write-Host "  - Training (1 replica)      : http://localhost:8002" -ForegroundColor White
Write-Host ""

Write-Host "Les port-forwards tournent en arrière-plan. Appuyez sur CTRL+C pour arrêter." -ForegroundColor Yellow
Write-Host ""
