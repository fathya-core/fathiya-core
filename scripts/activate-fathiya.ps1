param(
  [int]$ApiPort = 8765,
  [int]$WebPort = 5180,
  [switch]$OpenActions,
  [switch]$StrictActivation
)

$ErrorActionPreference = "Stop"

$apiUrl = "http://127.0.0.1:$ApiPort"
$webUrl = "http://127.0.0.1:$WebPort/agent-tasks/"
$toolsUrl = "${webUrl}?view=tools"

function Invoke-FathiyaJson {
  param([string]$Path)
  return Invoke-RestMethod -Uri "$apiUrl$Path" -TimeoutSec 60
}

function Open-FathiyaUrl {
  param([string]$Url)
  try {
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Url
    $startInfo.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($startInfo) | Out-Null
  } catch {
    Write-Host "Could not open URL automatically: $Url" -ForegroundColor Yellow
  }
}

try {
  $health = Invoke-FathiyaJson "/api/agent/health"
} catch {
  Write-Host "FATHIYA runtime is not reachable at $apiUrl" -ForegroundColor Red
  Write-Host "Start it with: powershell -ExecutionPolicy Bypass -File .\scripts\start-fathiya.ps1 -Detached"
  exit 1
}

$integrationsResponse = Invoke-FathiyaJson "/api/agent/integrations"
$integrations = @($integrationsResponse.integrations)
$byId = @{}
foreach ($integration in $integrations) {
  $byId[$integration.id] = $integration
}

$gates = @(
  [pscustomobject]@{
    id = "zapier_mcp"
    status = $byId.zapier_mcp.status
    next_step = $byId.zapier_mcp.next_step
    action_path = $byId.zapier_mcp.action_path
    app_count = $byId.zapier_mcp.details.app_count
    action_count = $byId.zapier_mcp.details.action_count
  }
  [pscustomobject]@{
    id = "github_codespaces"
    status = $byId.github_codespaces.status
    next_step = $byId.github_codespaces.next_step
    action_path = $byId.github_codespaces.action_path
    auth_state = $byId.github_codespaces.details.auth_state
  }
  [pscustomobject]@{
    id = "supabase"
    status = $byId.supabase.status
    next_step = $byId.supabase.next_step
    settings_path = $byId.supabase.settings_path
    migration_path = $byId.supabase.details.migration_path
  }
  [pscustomobject]@{
    id = "broker_testnet"
    status = $byId.broker_testnet.status
    next_step = $byId.broker_testnet.next_step
    settings_path = $byId.broker_testnet.settings_path
  }
)

$summary = [pscustomobject]@{
  runtime = [pscustomobject]@{
    ok = $health.status -eq "ok"
    api = $apiUrl
    web = $webUrl
    worker_online = [bool]$health.worker_online
    trading_running = [bool]$health.trading.running
    trading_mode = $health.trading.mode
    latest_trading_receipt = $health.trading.latest_receipt_id
  }
  ready_integrations = @($integrations | Where-Object { $_.status -eq "ready" } | Select-Object -ExpandProperty id)
  pending_gates = @($gates | Where-Object { $_.status -ne "ready" })
  local_execution_ready = [bool](
    $health.status -eq "ok" `
      -and $health.worker_online `
      -and $health.trading.running `
      -and $byId.local_execution_mesh.status -eq "ready" `
      -and $byId.huggingface_local.status -eq "ready" `
      -and $byId.openrouter.status -eq "ready"
  )
  upgrade_gates = @($gates | Where-Object {
    $_.status -ne "ready" -and $_.id -in @("zapier_mcp", "supabase", "broker_testnet")
  })
  blocking_gates = @($gates | Where-Object {
    $_.status -ne "ready" -and $_.id -notin @("zapier_mcp", "supabase", "broker_testnet")
  })
}

$summary | ConvertTo-Json -Depth 5

if ($OpenActions) {
  Write-Host "Opening FATHIYA tools workspace..." -ForegroundColor Cyan
  Open-FathiyaUrl $toolsUrl

  if ($byId.zapier_mcp.status -ne "ready" -and $byId.zapier_mcp.action_path) {
    Write-Host "Opening Zapier MCP authorization route..." -ForegroundColor Cyan
    $returnTo = [uri]::EscapeDataString($toolsUrl)
    Open-FathiyaUrl "$apiUrl$($byId.zapier_mcp.action_path)?return_to=$returnTo"
  }

  if ($byId.github_codespaces.status -ne "ready" -and $byId.github_codespaces.action_path) {
    Write-Host "Opening GitHub Codespaces authorization route..." -ForegroundColor Cyan
    $returnTo = [uri]::EscapeDataString($toolsUrl)
    Open-FathiyaUrl "$apiUrl$($byId.github_codespaces.action_path)?return_to=$returnTo"
  }

  if ($byId.supabase.status -ne "ready") {
    Write-Host "Supabase migration: $($byId.supabase.details.migration_path)" -ForegroundColor Yellow
    Write-Host "Then set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in FATHIYA settings." -ForegroundColor Yellow
  }

  if ($byId.broker_testnet.status -ne "ready") {
    Write-Host "Set Binance Spot Testnet keys in FATHIYA settings before enabling testnet orders." -ForegroundColor Yellow
  }
}

if (@($summary.blocking_gates).Count -gt 0) {
  Write-Host "FATHIYA local execution has blocking gates: $((@($summary.blocking_gates) | Select-Object -ExpandProperty id) -join ', ')" -ForegroundColor Red
  exit 2
}

if (@($summary.upgrade_gates).Count -gt 0) {
  Write-Host "FATHIYA local engine is executable now. Upgrade gates pending: $((@($summary.upgrade_gates) | Select-Object -ExpandProperty id) -join ', ')" -ForegroundColor Yellow
  if ($StrictActivation) {
    exit 2
  }
  exit 0
}

Write-Host "FATHIYA activation gates are ready." -ForegroundColor Green
