param(
  [string]$SiteId = "245709e3-40b9-458b-8fb7-996a41025891",
  [string]$Domain = "fathya-core.com",
  [string[]]$Aliases = @("www.fathya-core.com"),
  [string]$NetlifyToken = $env:NETLIFY_AUTH_TOKEN,
  [switch]$Apply,
  [switch]$ConfigureDns,
  [switch]$ProvisionSsl,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$ApiBase = "https://api.netlify.com/api/v1"

if ($PSVersionTable.PSVersion.Major -lt 7) {
  $pwsh = Get-Command pwsh.exe -ErrorAction SilentlyContinue
  if ($pwsh) {
    if ($NetlifyToken) {
      $env:NETLIFY_AUTH_TOKEN = $NetlifyToken
    }

    $relaunchArgs = @(
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      $PSCommandPath,
      "-SiteId",
      $SiteId,
      "-Domain",
      $Domain,
      "-Aliases"
    )
    $relaunchArgs += $Aliases
    if ($Apply) { $relaunchArgs += "-Apply" }
    if ($ConfigureDns) { $relaunchArgs += "-ConfigureDns" }
    if ($ProvisionSsl) { $relaunchArgs += "-ProvisionSsl" }
    if ($Json) { $relaunchArgs += "-Json" }

    & $pwsh.Source @relaunchArgs
    exit $LASTEXITCODE
  }
}

if ([System.Management.Automation.PSTypeName]"System.Net.ServicePointManager") {
  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
}

function Invoke-NetlifyApi {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$Method = "GET",
    [object]$Body = $null,
    [switch]$RequireToken
  )

  if ($RequireToken -and -not $NetlifyToken) {
    throw "NETLIFY_AUTH_TOKEN is required for this operation."
  }

  $headers = @{}
  if ($NetlifyToken) {
    $headers["Authorization"] = "Bearer $NetlifyToken"
  }

  $args = @{
    Uri = "$ApiBase$Path"
    Method = $Method
    Headers = $headers
  }
  if ($Body -ne $null) {
    $args["ContentType"] = "application/json"
    $args["Body"] = ($Body | ConvertTo-Json -Depth 10)
  }

  Invoke-RestMethod @args
}

function Resolve-Record {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Type
  )

  try {
    @(Resolve-DnsName $Name -Type $Type -ErrorAction Stop) | ForEach-Object {
      [pscustomobject]@{
        name = $_.Name
        type = $_.Type
        value = if ($_.IPAddress) { $_.IPAddress } else { $_.NameHost }
      }
    }
  } catch {
    [pscustomobject]@{
      name = $Name
      type = $Type
      value = $null
      error = $_.Exception.Message
    }
  }
}

function Test-AgentOsPage {
  param([Parameter(Mandatory = $true)][string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
    $titleMatch = [regex]::Match($response.Content, "<title[^>]*>(.*?)</title>", "IgnoreCase,Singleline")
    $title = if ($titleMatch.Success) { ($titleMatch.Groups[1].Value -replace "\s+", " ").Trim() } else { "" }
    $hasDeployMarker = $response.Content.Contains("FATHIYA_DEPLOY_MARKER_20260621_AGENT_OS")
    $hasOldStopText = $response.Content.Contains("يتوقف عند")
    $hasPrimaryRequestView = $response.Content.Contains("FATHIYA_PRIMARY_REQUEST_VIEW_V2")
    $hasIdentity = (
      $response.Content.Contains("FATHIYA") -or
      $response.Content.Contains("فتحية") -or
      $response.Content.Contains("المنشأة السيادية الذكية") -or
      $response.Content.Contains("المنصة السيادية الذكية")
    )
    $hasOperatorConsole = (
      $response.Content.Contains("agent-tasks") -or
      $response.Content.Contains("وكيل التداول") -or
      $response.Content.Contains("صيد الثغرات") -or
      $response.Content.Contains("محرك الوكلاء") -or
      $response.Content.Contains("المسار السريع للتداول") -or
      $response.Content.Contains("صيد ثغرات بزر واحد")
    )
    $isCurrentOperator = (($hasDeployMarker -or ($hasIdentity -and $hasOperatorConsole)) -and $hasPrimaryRequestView -and -not $hasOldStopText)
    [pscustomobject]@{
      url = $Url
      status_code = [int]$response.StatusCode
      title = $title
      has_agent_os = $response.Content.Contains("agent-os")
      has_workspace_home = $response.Content.Contains("workspace-home")
      has_deploy_marker = $hasDeployMarker
      has_old_stop_text = $hasOldStopText
      has_primary_request_view = $hasPrimaryRequestView
      has_fathiya_identity = $hasIdentity
      has_operator_console = $hasOperatorConsole
      is_current_operator = $isCurrentOperator
      etag = ($response.Headers["ETag"] -join ",")
      age = ($response.Headers["Age"] -join ",")
    }
  } catch {
    [pscustomobject]@{
      url = $Url
      status_code = $null
      has_agent_os = $false
      has_workspace_home = $false
      has_deploy_marker = $false
      has_old_stop_text = $false
      has_primary_request_view = $false
      has_fathiya_identity = $false
      has_operator_console = $false
      is_current_operator = $false
      error = $_.Exception.Message
    }
  }
}

$siteBefore = Invoke-NetlifyApi -Path "/sites/$SiteId"
$changes = @()
$applyError = $null

if ($Apply) {
  try {
    $updateBody = @{
      custom_domain = $Domain
      domain_aliases = $Aliases
    }
    $siteAfter = Invoke-NetlifyApi -Path "/sites/$SiteId" -Method "PATCH" -Body $updateBody -RequireToken
    $changes += "updated_site_custom_domain"

    if ($ConfigureDns) {
      Invoke-NetlifyApi -Path "/sites/$SiteId/dns" -Method "PUT" -RequireToken | Out-Null
      $changes += "configured_netlify_dns"
    }

    if ($ProvisionSsl) {
      Invoke-NetlifyApi -Path "/sites/$SiteId/ssl" -Method "POST" -Body @{} -RequireToken | Out-Null
      $changes += "requested_tls_certificate"

      try {
        $siteAfter = Invoke-NetlifyApi -Path "/sites/$SiteId" -Method "PATCH" -Body @{ force_ssl = $true } -RequireToken
        $changes += "enabled_force_ssl"
      } catch {
        $changes += "force_ssl_pending_certificate"
      }
    }
  } catch {
    $applyError = if ($_.ErrorDetails.Message) { $_.ErrorDetails.Message } else { $_.Exception.Message }
    $changes += "failed_to_update_site_custom_domain"
    $siteAfter = $siteBefore
  }
} else {
  $siteAfter = $siteBefore
}

$apexRecords = @(Resolve-Record -Name $Domain -Type "A")
$aliasRecords = @()
foreach ($alias in $Aliases) {
  $aliasRecords += @(Resolve-Record -Name $alias -Type "CNAME")
}

$netlifyBaseUrl = if ($siteAfter.ssl_url) { [string]$siteAfter.ssl_url } else { "https://$($siteAfter.name).netlify.app" }
$netlifyUrl = "$($netlifyBaseUrl.TrimEnd('/'))/agent-tasks/"
$domainUrl = "https://$Domain/agent-tasks/"
$netlifyPage = Test-AgentOsPage -Url $netlifyUrl
$domainPage = Test-AgentOsPage -Url $domainUrl
$aliasPages = @()
foreach ($alias in $Aliases) {
  $aliasPages += [pscustomobject]@{
    alias = $alias
    page = Test-AgentOsPage -Url "https://$alias/agent-tasks/"
  }
}

$nextActions = @()
if (-not $Apply) {
  $nextActions += "Set NETLIFY_AUTH_TOKEN and rerun with -Apply to attach the domain to this Netlify site."
}
if ($siteAfter.custom_domain -ne $Domain) {
  $nextActions += "Netlify custom_domain is not $Domain yet."
}
if ($applyError) {
  $nextActions += "Domain attach failed: $applyError"
}
if (-not $netlifyPage.is_current_operator) {
  $nextActions += "The Netlify deploy check did not find the current FATHIYA marker; rebuild and redeploy before changing DNS."
}
if (-not $domainPage.is_current_operator) {
  $nextActions += "$Domain is still serving a stale operator build; attach this custom domain to $($siteAfter.name).netlify.app or update DNS/domain routing."
}
foreach ($aliasPage in $aliasPages) {
  if (-not $aliasPage.page.is_current_operator) {
    $nextActions += "$($aliasPage.alias) is not serving the current FATHIYA operator build."
  }
}
$nextActions += "In DNS, keep the apex on Netlify-compatible A records and point www to $($siteAfter.name).netlify.app instead of Bolt."

$result = [pscustomobject]@{
  applied = [bool]$Apply
  changes = $changes
  apply_error = $applyError
  site = [pscustomobject]@{
    id = $siteAfter.id
    name = $siteAfter.name
    ssl_url = $siteAfter.ssl_url
    custom_domain = $siteAfter.custom_domain
    domain_aliases = $siteAfter.domain_aliases
    repo_url = $siteAfter.repo_url
  }
  desired = [pscustomobject]@{
    custom_domain = $Domain
    domain_aliases = $Aliases
    netlify_target = "$($siteAfter.name).netlify.app"
  }
  dns = [pscustomobject]@{
    apex_a = $apexRecords
    aliases = $aliasRecords
  }
  page_checks = [pscustomobject]@{
    netlify = $netlifyPage
    domain = $domainPage
    aliases = $aliasPages
  }
  next_actions = $nextActions
}

if ($Json) {
  $result | ConvertTo-Json -Depth 8
  exit 0
}

Write-Host "FATHIYA domain link check"
Write-Host "Site: $($result.site.name) ($($result.site.id))"
Write-Host "Netlify custom_domain: $($result.site.custom_domain)"
Write-Host "Desired domain: $Domain"
Write-Host "Netlify page has agent OS: $($result.page_checks.netlify.has_agent_os)"
Write-Host "Public domain has agent OS: $($result.page_checks.domain.has_agent_os)"
Write-Host "Netlify page current marker: $($result.page_checks.netlify.has_deploy_marker)"
Write-Host "Public domain current marker: $($result.page_checks.domain.has_deploy_marker)"
Write-Host "Netlify page current operator: $($result.page_checks.netlify.is_current_operator)"
Write-Host "Public domain current operator: $($result.page_checks.domain.is_current_operator)"
Write-Host ""
Write-Host "Next actions:"
foreach ($item in $result.next_actions) {
  Write-Host "- $item"
}
