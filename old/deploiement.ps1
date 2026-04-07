# deploiement.ps1
Write-Host "1. Nettoyage des anciens conteneurs et volumes"
Write-Host "docker-compose down -v"
docker-compose down -v

Write-Host ""
Write-Host "2. Rebuild des images de conteneurs"
Write-Host "docker-compose build --no-cache"
docker-compose build --no-cache

Write-Host ""
Write-Host "3. Lancement des services sans logs (-d)-deploiement"
Write-Host "docker-compose up -d"
docker-compose up -d

Write-Host ""
Write-Host "4. Liste des services"
Write-Host "docker-compose ps"
docker-compose ps

Write-Host ""
Write-Host "6. logs de services specifiques"
#docker-compose logs -f training
docker-compose logs -f inference
# docker-compose logs -f gateway
# docker-compose logs -f mlflow