param(
  [int]$ApiPort = 8765,
  [int]$WebPort = 5180,
  [string]$PublicDomain = "fathya-core.com",
  [string]$PublicWww = "www.fathya-core.com",
  [string]$ExpectedPublicBaseUrl = "https://thriving-fenglisu-ef18b1.netlify.app",
  [switch]$StrictActivation
)

$ErrorActionPreference = "Stop"

$apiUrl = "http://127.0.0.1:$ApiPort"
$webUrl = "http://127.0.0.1:$WebPort/agent-tasks"
$views = @(
  @{ Name = "operator"; Url = "$webUrl/" },
  @{ Name = "trading"; Url = "$webUrl/?view=trading" },
  @{ Name = "bug-bounty"; Url = "$webUrl/?view=bug-bounty" },
  @{ Name = "knowledge"; Url = "$webUrl/?view=knowledge" },
  @{ Name = "reports"; Url = "$webUrl/?view=reports" },
  @{ Name = "tools"; Url = "$webUrl/?view=tools" }
)

function Test-HttpStatus {
  param([string]$Url)
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
    return [pscustomobject]@{
      ok = $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
      status = $response.StatusCode
      error = ""
    }
  } catch {
    return [pscustomobject]@{
      ok = $false
      status = 0
      error = $_.Exception.Message
    }
  }
}

function Test-Origin {
  param([string]$Origin)
  try {
    $response = Invoke-WebRequest `
      -Method Options `
      -Uri "$apiUrl/api/agent/health" `
      -Headers @{
        Origin = $Origin
        "Access-Control-Request-Method" = "GET"
        "Access-Control-Request-Private-Network" = "true"
      } `
      -UseBasicParsing `
      -TimeoutSec 10
    return [pscustomobject]@{
      origin = $Origin
      ok = $response.StatusCode -eq 204 -and $response.Headers["Access-Control-Allow-Origin"] -contains $Origin
      private_network = $response.Headers["Access-Control-Allow-Private-Network"] -contains "true"
      status = $response.StatusCode
    }
  } catch {
    return [pscustomobject]@{
      origin = $Origin
      ok = $false
      private_network = $false
      status = 0
      error = $_.Exception.Message
    }
  }
}

function Test-AgentOsPage {
  param(
    [string]$Name,
    [string]$Url
  )

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
    $content = [string]$response.Content
    $hasDeployMarker = $content.Contains("FATHIYA_DEPLOY_MARKER_20260621_AGENT_OS")
    $hasOldStopText = $content.Contains("يتوقف عند")
    $hasPrimaryRequestView = $content.Contains("FATHIYA_PRIMARY_REQUEST_VIEW_V2")
    $hasIdentity = (
      $content.Contains("FATHIYA") -or
      $content.Contains("فتحية") -or
      $content.Contains("المنشأة السيادية الذكية") -or
      $content.Contains("المنصة السيادية الذكية")
    )
    $hasOperatorConsole = (
      $content.Contains("agent-os") -or
      $content.Contains("agent-tasks") -or
      $content.Contains("وكيل التداول") -or
      $content.Contains("صيد الثغرات") -or
      $content.Contains("محرك الوكلاء") -or
      $content.Contains("صيد ثغرات بزر واحد")
    )
    $isCurrentOperator = (($hasDeployMarker -or ($hasIdentity -and $hasOperatorConsole)) -and $hasPrimaryRequestView -and -not $hasOldStopText)
    return [pscustomobject]@{
      name = $Name
      url = $Url
      ok = $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
      status = [int]$response.StatusCode
      current_operator = $isCurrentOperator
      has_deploy_marker = $hasDeployMarker
      has_old_stop_text = $hasOldStopText
      has_primary_request_view = $hasPrimaryRequestView
      has_fathiya_identity = $hasIdentity
      has_operator_console = $hasOperatorConsole
      etag = ($response.Headers["ETag"] -join ",")
      age = ($response.Headers["Age"] -join ",")
      error = ""
    }
  } catch {
    return [pscustomobject]@{
      name = $Name
      url = $Url
      ok = $false
      status = 0
      current_operator = $false
      has_deploy_marker = $false
      has_old_stop_text = $false
      has_primary_request_view = $false
      has_fathiya_identity = $false
      has_operator_console = $false
      etag = ""
      age = ""
      error = $_.Exception.Message
    }
  }
}

$health = $null
try {
  $health = Invoke-RestMethod -Uri "$apiUrl/api/agent/health" -TimeoutSec 10
} catch {
  Write-Host "FATHIYA check failed: runtime API is not reachable at $apiUrl" -ForegroundColor Red
  Write-Host $_.Exception.Message
  exit 1
}

$viewResults = $views | ForEach-Object {
  $result = Test-HttpStatus $_.Url
  [pscustomobject]@{
    name = $_.Name
    url = $_.Url
    ok = $result.ok
    status = $result.status
    error = $result.error
  }
}

$originResults = @(
  Test-Origin "https://fathya-core.com"
  Test-Origin "https://www.fathya-core.com"
  Test-Origin "https://fathya-project.github.io"
)

$expectedBase = $ExpectedPublicBaseUrl.TrimEnd("/")
$publicSiteResults = @(
  Test-AgentOsPage "expected-netlify" "$expectedBase/agent-tasks/"
  Test-AgentOsPage "apex-domain" "https://$PublicDomain/agent-tasks/"
  Test-AgentOsPage "www-domain" "https://$PublicWww/agent-tasks/"
)
$expectedPublicPage = $publicSiteResults | Where-Object { $_.name -eq "expected-netlify" } | Select-Object -First 1
$apexPublicPage = $publicSiteResults | Where-Object { $_.name -eq "apex-domain" } | Select-Object -First 1
$wwwPublicPage = $publicSiteResults | Where-Object { $_.name -eq "www-domain" } | Select-Object -First 1
$publicDomainCurrent = [bool](
  $expectedPublicPage.current_operator -and
  $apexPublicPage.current_operator -and
  $wwwPublicPage.current_operator
)
$publicDomainStatus = if ($publicDomainCurrent) {
  "ready"
} elseif ($expectedPublicPage.current_operator -and -not ($apexPublicPage.current_operator -and $wwwPublicPage.current_operator)) {
  "domain_stale"
} else {
  "build_stale"
}

$integrations = @()
$integrationSummary = $null
try {
  $integrationResponse = Invoke-RestMethod -Uri "$apiUrl/api/agent/integrations" -TimeoutSec 60
  $integrations = @($integrationResponse.integrations)
  $integrationSummary = $integrationResponse.summary
} catch {
  $integrations = @()
  $integrationSummary = [pscustomobject]@{
    total = 0
    ready = 0
    partial = 0
    needs_setup = 0
    needs_operator = 0
    error = $_.Exception.Message
  }
}

$zapierDiagnostics = $null
try {
  $zapierDiagnostics = (Invoke-RestMethod -Uri "$apiUrl/api/agent/oauth/zapier/diagnostics" -TimeoutSec 15).zapier_mcp
} catch {
  $zapierDiagnostics = [pscustomobject]@{
    activation_state = "unknown"
    connected = $false
    direct_execution = $false
    inventory_available = $false
    app_count = 0
    action_count = 0
    error = $_.Exception.Message
  }
}

function Get-Integration {
  param([string]$Id)
  return $integrations | Where-Object { $_.id -eq $Id } | Select-Object -First 1
}

$zapierIntegration = Get-Integration "zapier_mcp"
$codespacesIntegration = Get-Integration "github_codespaces"
$supabaseIntegration = Get-Integration "supabase"
$testnetIntegration = Get-Integration "broker_testnet"

$zapierActionPath = "/api/agent/oauth/zapier/start"
if ($null -ne $zapierIntegration -and $zapierIntegration.action_path) {
  $zapierActionPath = $zapierIntegration.action_path
}
$codespacesStatus = $null
$codespacesSummary = $null
$codespacesNextStep = $null
$codespacesAuthState = $null
$codespacesRequiredScope = $null
if ($null -ne $codespacesIntegration) {
  $codespacesStatus = $codespacesIntegration.status
  $codespacesSummary = $codespacesIntegration.summary
  $codespacesNextStep = $codespacesIntegration.next_step
  if ($null -ne $codespacesIntegration.details) {
    $codespacesAuthState = $codespacesIntegration.details.auth_state
    $codespacesRequiredScope = $codespacesIntegration.details.required_scope
  }
}
$supabaseStatus = $null
$supabaseSummary = $null
$supabaseNextStep = $null
$supabaseMigrationPath = $null
if ($null -ne $supabaseIntegration) {
  $supabaseStatus = $supabaseIntegration.status
  $supabaseSummary = $supabaseIntegration.summary
  $supabaseNextStep = $supabaseIntegration.next_step
  if ($null -ne $supabaseIntegration.details) {
    $supabaseMigrationPath = $supabaseIntegration.details.migration_path
  }
}
$testnetStatus = $null
$testnetSummary = $null
$testnetNextStep = $null
if ($null -ne $testnetIntegration) {
  $testnetStatus = $testnetIntegration.status
  $testnetSummary = $testnetIntegration.summary
  $testnetNextStep = $testnetIntegration.next_step
}

$activationGates = @(
  [pscustomobject]@{
    id = "zapier_mcp_live_execution"
    ok = [bool](
      $zapierDiagnostics.connected `
        -and $zapierDiagnostics.direct_execution `
        -and -not $zapierDiagnostics.expired `
        -and -not $zapierDiagnostics.needs_reconnect
    )
    status = $zapierDiagnostics.activation_state
    summary = if ($zapierDiagnostics.connected -and $zapierDiagnostics.direct_execution) {
      if ($zapierDiagnostics.expired -or $zapierDiagnostics.needs_reconnect) {
        "Zapier MCP inventory is visible, but OAuth must be refreshed before live execution."
      } else {
        "Zapier MCP live execution is connected locally."
      }
    } else {
      "Zapier inventory is visible, but local OAuth live execution is not connected."
    }
    next_step = $zapierActionPath
    inventory = [pscustomobject]@{
      available = [bool]$zapierDiagnostics.inventory_available
      app_count = $zapierDiagnostics.app_count
      action_count = $zapierDiagnostics.action_count
      agent_provider_count = $zapierDiagnostics.agent_provider_count
    }
  }
  [pscustomobject]@{
    id = "github_codespaces_scope"
    ok = $codespacesStatus -eq "ready"
    status = $codespacesStatus
    summary = $codespacesSummary
    next_step = $codespacesNextStep
    auth_state = $codespacesAuthState
    required_scope = $codespacesRequiredScope
  }
  [pscustomobject]@{
    id = "supabase_production_queue"
    ok = $supabaseStatus -eq "ready"
    status = $supabaseStatus
    summary = $supabaseSummary
    next_step = $supabaseNextStep
    migration_path = $supabaseMigrationPath
  }
  [pscustomobject]@{
    id = "broker_testnet"
    ok = $testnetStatus -eq "ready"
    status = $testnetStatus
    summary = $testnetSummary
    next_step = $testnetNextStep
  }
  [pscustomobject]@{
    id = "public_domain_current"
    ok = $publicDomainCurrent
    status = $publicDomainStatus
    summary = if ($publicDomainCurrent) {
      "$PublicDomain و $PublicWww يعرضان نسخة فتحية الحالية."
    } elseif ($expectedPublicPage.current_operator) {
      "النشر الصحيح يعمل على $expectedBase، لكن $PublicDomain أو $PublicWww لا يعرضان النسخة الحالية."
    } else {
      "النشر المتوقع لا يعرض علامة فتحية الحالية؛ أعد البناء والنشر قبل تعديل DNS."
    }
    next_step = if ($publicDomainCurrent) {
      "لا إجراء مطلوب."
    } elseif ($expectedPublicPage.current_operator) {
      "اربط $PublicDomain و $PublicWww بالنشر $expectedBase؛ في GoDaddy غيّر www بعيدًا عن site-dns.bolt.host، ثم شغّل scripts/link-fathiya-domain.ps1 -Apply بعد ضبط NETLIFY_AUTH_TOKEN."
    } else {
      "أعد بناء ونشر operator-lite، ثم أعد فحص الدومين."
    }
    pages = $publicSiteResults
  }
)

$summary = [pscustomobject]@{
  runtime = [pscustomobject]@{
    ok = $health.status -eq "ok"
    worker_online = [bool]$health.worker_online
    planning_route = $health.agent_loop.planning_route
    local_model = $health.agent_loop.local_model
    openrouter_configured = [bool]$health.agent_loop.openrouter_configured
  }
  knowledge = [pscustomobject]@{
    running = [bool]$health.knowledge_intake.running
    tracked_files = $health.knowledge_intake.tracked_files
    enqueued_count = $health.knowledge_intake.enqueued_count
    supported_extensions = $health.knowledge_intake.supported_extensions
  }
  trading = [pscustomobject]@{
    running = [bool]$health.trading.running
    mode = $health.trading.mode
    symbol = $health.trading.symbol
    cadence_seconds = $health.trading.cycle_target_seconds
    latest_receipt_id = $health.trading.latest_receipt_id
  }
  web = $viewResults
  public_site = $publicSiteResults
  allowed_origins = $originResults
  integrations = [pscustomobject]@{
    summary = $integrationSummary
    ready = @($integrations | Where-Object { $_.status -eq "ready" } | Select-Object -ExpandProperty id)
    partial = @($integrations | Where-Object { $_.status -eq "partial" } | Select-Object -ExpandProperty id)
    needs_setup = @($integrations | Where-Object { $_.status -eq "needs_setup" } | Select-Object -ExpandProperty id)
    needs_operator = @($integrations | Where-Object { $_.status -eq "needs_operator" } | Select-Object -ExpandProperty id)
  }
  activation_gates = $activationGates
}

$failedViews = @($viewResults | Where-Object { -not $_.ok })
$failedOrigins = @($originResults | Where-Object { -not $_.ok -or -not $_.private_network })
$failedActivation = @($activationGates | Where-Object { -not $_.ok })
$upgradeActivation = @($failedActivation | Where-Object {
  $_.id -in @("zapier_mcp_live_execution", "supabase_production_queue", "broker_testnet", "public_domain_current")
})
$blockingActivation = @($failedActivation | Where-Object {
  $_.id -notin @("zapier_mcp_live_execution", "supabase_production_queue", "broker_testnet", "public_domain_current")
})
$failedRuntime = -not $summary.runtime.ok -or -not $summary.runtime.worker_online

$summary | ConvertTo-Json -Depth 6

if ($failedRuntime -or $failedViews.Count -gt 0 -or $failedOrigins.Count -gt 0 -or $blockingActivation.Count -gt 0) {
  Write-Host "FATHIYA check: FAIL" -ForegroundColor Red
  exit 1
}

if ($upgradeActivation.Count -gt 0) {
  Write-Host "FATHIYA runtime check: PASS" -ForegroundColor Green
  Write-Host "FATHIYA local engine is executable. Upgrade gates pending: $($upgradeActivation.Count)" -ForegroundColor Yellow
  if ($StrictActivation) {
    exit 2
  }
  exit 0
}

Write-Host "FATHIYA check: PASS, runtime and activation gates are ready." -ForegroundColor Green
