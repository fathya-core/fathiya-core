param(
  [int]$ApiPort = 8765,
  [int]$WebPort = 5180,
  [switch]$FullVite,
  [switch]$StartN8n,
  [switch]$RestartRuntime,
  [switch]$RestartWeb,
  [switch]$NoBrowser,
  [switch]$SkipInstall,
  [switch]$RunEngine,
  [switch]$RunTrading,
  [switch]$RunBugBounty,
  [switch]$RunKnowledge,
  [switch]$RunTools
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$startScript = Join-Path $PSScriptRoot "start-fathiya.ps1"
$checkScript = Join-Path $PSScriptRoot "check-fathiya.ps1"
$activateScript = Join-Path $PSScriptRoot "activate-fathiya.ps1"

function Invoke-FathiyaCommand {
  param(
    [Parameter(Mandatory = $true)]
    [string]$CommandId,
    [Parameter(Mandatory = $true)]
    [string]$Label
  )

  $body = @{ command_id = $CommandId } | ConvertTo-Json -Compress
  $uri = "http://127.0.0.1:$ApiPort/api/agent/command-center/run"
  Write-Host ""
  Write-Host "Running FATHIYA command: $Label ($CommandId)" -ForegroundColor Cyan
  $result = Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -Body $body
  $task = $result.task
  Write-Host "Task queued: $($task.id)" -ForegroundColor Green
  Write-Host "Status: $($task.status) | Step: $($task.current_step)" -ForegroundColor DarkGray
  Write-Host "Open reports: http://127.0.0.1:$WebPort/agent-tasks/?view=reports" -ForegroundColor DarkGray
}

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
if ($RestartWeb) { $startArgs += "-RestartWeb" }
if (-not $NoBrowser) { $startArgs += "-OpenBrowser" }
if ($SkipInstall) { $startArgs += "-SkipInstall" }
$shouldRunCommand = $RunEngine -or $RunTrading -or $RunBugBounty -or $RunKnowledge -or $RunTools

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
  if (-not $shouldRunCommand) {
    exit 0
  }
}
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

if ($RunEngine) {
  Invoke-FathiyaCommand -CommandId "agent_os_full_execute" -Label "agent execution engine"
}
if ($RunTrading) {
  Invoke-FathiyaCommand -CommandId "lane_trading" -Label "paper trading agent"
}
if ($RunBugBounty) {
  Invoke-FathiyaCommand -CommandId "lane_bug_bounty" -Label "bug bounty lane"
}
if ($RunKnowledge) {
  Invoke-FathiyaCommand -CommandId "lane_knowledge" -Label "knowledge intake and reports"
}
if ($RunTools) {
  Invoke-FathiyaCommand -CommandId "lane_tool_bridge" -Label "tool bridge inventory"
}

exit 0
