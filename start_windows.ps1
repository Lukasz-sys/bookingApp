$ErrorActionPreference = "Stop"
Write-Host "=== System rezerwacji wizyt: Docker full stack ===" -ForegroundColor Cyan

function Remove-ContainerIfExists {
    param([string]$Name)
    $idsRaw = docker ps -aq --filter "name=^/$Name$" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Nie udało się sprawdzić kontenera $Name, pomijam." -ForegroundColor DarkYellow
        return
    }
    $ids = @($idsRaw | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    if ($ids.Count -gt 0) {
        Write-Host "Usuwam stary kontener: $Name" -ForegroundColor DarkYellow
        docker rm -f $ids | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Nie udało się usunąć kontenera $Name" }
    } else {
        Write-Host "Brak starego kontenera: $Name" -ForegroundColor DarkGray
    }
}

Write-Host "[1/4] Sprawdzam i usuwam stare kontenery, jeżeli istnieją..." -ForegroundColor Yellow
Remove-ContainerIfExists "booking_postgres"
Remove-ContainerIfExists "booking_api"
Remove-ContainerIfExists "booking_frontend"

Write-Host "[2/4] Czyszczę stare zasoby Compose tego projektu..." -ForegroundColor Yellow
docker compose down --remove-orphans -v
# docker compose down może zwrócić 0 nawet gdy nic nie było uruchomione — to OK.

Write-Host "[3/4] Buduję obrazy bez cache..." -ForegroundColor Yellow
docker compose build --no-cache
if ($LASTEXITCODE -ne 0) { throw "docker compose build nie powiodło się" }

Write-Host "[4/4] Uruchamiam PostgreSQL, FastAPI i frontend Nginx..." -ForegroundColor Yellow
docker compose up -d --force-recreate
if ($LASTEXITCODE -ne 0) { throw "docker compose up nie powiodło się" }

Write-Host "" 
Write-Host "Gotowe." -ForegroundColor Green
Write-Host "Frontend: http://localhost:8080" -ForegroundColor Green
Write-Host "CSS test: http://localhost:8080/styles.css" -ForegroundColor Green
Write-Host "API:      http://localhost:8000/health" -ForegroundColor Green
Write-Host "Docs:     http://localhost:8000/docs" -ForegroundColor Green
Write-Host "" 
Write-Host "Jeżeli przeglądarka pokazuje starą wersję bez styli: Ctrl + F5." -ForegroundColor Yellow
