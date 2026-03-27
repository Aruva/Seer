# cleanup_rename.ps1
#
# Run this from the seer-main directory after the automated rename is done.
# It removes the old spellbot-named files/folders that couldn't be deleted
# from the sandbox.
#
# Usage:
#   cd C:\Users\HatiW\OneDrive\Desktop\discordrobit\seer-main
#   powershell -ExecutionPolicy Bypass -File scripts\cleanup_rename.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "SouthSeer - Cleanup old spellbot files after rename"
Write-Host "---------------------------------------------------"
Write-Host ""

# Step 1: Remove old src/spellbot/ directory
Write-Host "Step 1: Removing old src\spellbot\ directory..."
if (Test-Path "src\spellbot") {
    Remove-Item -Recurse -Force "src\spellbot"
    Write-Host "  Done - Removed src\spellbot\"
} else {
    Write-Host "  Already removed."
}

# Step 2: Remove old-named script files
Write-Host "Step 2: Removing old-named files..."

$oldFiles = @(
    "scripts\start-spellbot.sh",
    "scripts\start-spellapi.sh",
    "conf\grafana-spellbot.json",
    "docs\assets\css\spellbot.css",
    "docs\assets\js\spellbot.js"
)

foreach ($f in $oldFiles) {
    if (Test-Path $f) {
        Remove-Item -Force $f
        Write-Host "  Done - Removed $f"
    } else {
        Write-Host "  $f already removed."
    }
}

# Step 3: Clean up __pycache__ directories
Write-Host "Step 3: Cleaning __pycache__ directories..."
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -Path "src" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Recurse -Force $_.FullName
    Write-Host "  Done - Removed $($_.FullName)"
}

# Step 4: Verify
Write-Host ""
Write-Host "Step 4: Verifying no stale spellbot references..."
$remaining = Get-ChildItem -Recurse -File -Path "src" -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "spellbot" }
if ($remaining) {
    Write-Host "  WARNING: Found files with spellbot in name under src/:"
    $remaining | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "  No stale files found."
}

Write-Host ""
Write-Host "---------------------------------------------------"
Write-Host "Cleanup complete!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. docker compose up --build -d"
Write-Host "  2. Verify the bot starts and the API responds on :3008"
Write-Host "---------------------------------------------------"
