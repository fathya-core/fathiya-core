param(
  [int]$ApiPort = 8765,
  [int]$WebPort = 5180,
  [switch]$FullVite,
  [switch]$StartN8n,
  [switch]$RestartRuntime,
  [switch]$NoBrowser,
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$startScript = Join-Path $PSScriptRoot "start-fathiya.ps1"
$checkScript = Join-Path $PSScriptRoot "check-fathiya.ps1"
$activateScript = Join-Path $PSScriptRoot "activate-fathiya.ps1"

$startArgs = @(
  "-ExecutionPolicy", "Bypass",
  "-File", $startScript,
  "-ApiPort", $ApiPort,
  "-WebPort", $WebPort,
  "-Detached"
)

if ($FullVite) { $startArgs += "-FullVite" }
if ($StartN8n) { $startArgs += "-StartN8n" }
if ($RestartRuntime) { $startArgs += "-RestartRuntime" }
if (-not $NoBrowser) { $startArgs += "-OpenBrowser" }
if ($SkipInstall) { $startArgs += "-SkipInstall" }

Write-Host "Starting or attaching to FATHIYA..." -ForegroundColor Cyan
& powershell @startArgs
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Checking FATHIYA runtime and operator pages..." -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File $checkScript -ApiPort $ApiPort -WebPort $WebPort
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Activation summary:" -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File $activateScript -ApiPort $ApiPort -WebPort $WebPort
if ($LASTEXITCODE -eq 2) {
  Write-Host "FATHIYA is running with pending activation gates. Open the Tools page to finish external credentials." -ForegroundColor Yellow
  exit 0
}
exit $LASTEXITCODE
