param(
  [string]$Domain = "fathya-core.com",
  [string]$Www = "www.fathya-core.com",
  [string]$Repo = "fathya-core/fathiya-core",
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$expectedA = @(
  "185.199.108.153",
  "185.199.109.153",
  "185.199.110.153",
  "185.199.111.153"
)
$expectedWww = "fathya-core.github.io"

function Resolve-Values {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Type
  )
  try {
    @(Resolve-DnsName -Name $Name -Type $Type -ErrorAction Stop) | ForEach-Object {
      if ($_.IPAddress) { $_.IPAddress.TrimEnd(".") } elseif ($_.NameHost) { $_.NameHost.TrimEnd(".") }
    }
  } catch {
    @()
  }
}

function Test-ContainsSameSet {
  param([string[]]$Actual, [string[]]$Expected)
  $actualSet = @($Actual | Sort-Object -Unique)
  $expectedSet = @($Expected | Sort-Object -Unique)
  if ($actualSet.Count -ne $expectedSet.Count) { return $false }
  for ($i = 0; $i -lt $expectedSet.Count; $i++) {
    if ($actualSet[$i] -ne $expectedSet[$i]) { return $false }
  }
  return $true
}

$apexA = @(Resolve-Values -Name $Domain -Type "A")
$wwwCname = @(Resolve-Values -Name $Www -Type "CNAME")
$pages = $null
try {
  $pages = gh api "repos/$Repo/pages" | ConvertFrom-Json
} catch {
  $pages = [pscustomobject]@{
    status = "unknown"
    cname = $null
    html_url = "https://fathya-core.github.io/fathiya-core/"
    error = $_.Exception.Message
  }
}

$apexReady = Test-ContainsSameSet -Actual $apexA -Expected $expectedA
$wwwReady = (($wwwCname | Select-Object -First 1) -eq $expectedWww)
$pagesHasCname = ($pages.cname -eq $Domain)

$nextActions = @()
if (-not $apexReady) {
  $nextActions += "In GoDaddy DNS, replace the apex A records for $Domain with: $($expectedA -join ', ')."
}
if (-not $wwwReady) {
  $nextActions += "In GoDaddy DNS, set $Www as a CNAME to $expectedWww."
}
if ($apexReady -and $wwwReady -and -not $pagesHasCname) {
  $nextActions += "After DNS propagates, set GitHub Pages custom domain to $Domain."
}
if (-not $apexReady -or -not $wwwReady) {
  $nextActions += "Do not set the GitHub Pages custom domain yet; keeping the github.io URL prevents redirecting users to stale DNS."
}
if ($pages.status -ne "built") {
  $nextActions += "GitHub Pages status is $($pages.status); run scripts/deploy-fathiya-pages.ps1 first."
}

$result = [pscustomobject]@{
  domain = $Domain
  github_pages_url = $pages.html_url
  github_pages_status = $pages.status
  github_pages_cname = $pages.cname
  current_dns = [pscustomobject]@{
    apex_a = $apexA
    www_cname = $wwwCname
  }
  expected_dns = [pscustomobject]@{
    apex_a = $expectedA
    www_cname = $expectedWww
  }
  ready_for_pages_custom_domain = ($apexReady -and $wwwReady)
  next_actions = $nextActions
}

if ($Json) {
  $result | ConvertTo-Json -Depth 6
  exit 0
}

Write-Host "FATHIYA GitHub Pages domain check" -ForegroundColor Cyan
Write-Host "GitHub Pages: $($result.github_pages_url) status=$($result.github_pages_status) cname=$($result.github_pages_cname)"
Write-Host "Current apex A: $($apexA -join ', ')"
Write-Host "Expected apex A: $($expectedA -join ', ')"
Write-Host "Current www CNAME: $($wwwCname -join ', ')"
Write-Host "Expected www CNAME: $expectedWww"
Write-Host "Ready for GitHub custom domain: $($result.ready_for_pages_custom_domain)"
Write-Host ""
Write-Host "Next actions:"
foreach ($item in $nextActions) {
  Write-Host "- $item"
}
