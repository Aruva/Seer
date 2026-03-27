# rebuild.ps1
# Takes down all Seer containers and rebuilds them from scratch.
#
# Usage:
#   cd C:\Users\HatiW\OneDrive\Desktop\discordrobit\seer-main
#   powershell -ExecutionPolicy Bypass -File rebuild.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "SouthSeer - Full Rebuild"
Write-Host "------------------------"
Write-Host ""

Write-Host "Stopping all containers..."
docker compose down

Write-Host "Rebuilding all containers (no cache)..."
docker compose up --build -d

Write-Host ""
Write-Host "------------------------"
Write-Host "Done. All containers rebuilt."
docker compose ps
