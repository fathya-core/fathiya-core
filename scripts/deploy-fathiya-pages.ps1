param(
  [switch]$SkipBuild,
  [switch]$NoTrigger,
  [switch]$NoWait,
  [string]$Repo = "fathya-core/fathiya-core",
  [string]$Message = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$deployRoot = Join-Path $env:TEMP ("fathiya-pages-" + (Get-Date -Format "yyyyMMddHHmmss"))

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][scriptblock]$Body
  )
  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  & $Body
}

Push-Location $repoRoot
try {
  if (-not $SkipBuild) {
    Invoke-Step "Build FATHIYA" {
      npm run build
    }
  }

  $distClient = Resolve-Path -LiteralPath (Join-Path $repoRoot "dist/client")
  Invoke-Step "Clone gh-pages" {
    git clone --branch gh-pages --single-branch "https://github.com/$Repo" $deployRoot
  }

  $resolvedDeployRoot = (Resolve-Path -LiteralPath $deployRoot).Path
  $resolvedTempRoot = (Resolve-Path -LiteralPath $env:TEMP).Path
  if (-not $resolvedDeployRoot.StartsWith($resolvedTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean non-temp path: $resolvedDeployRoot"
  }

  Invoke-Step "Stage dist/client into gh-pages" {
    Get-ChildItem -LiteralPath $resolvedDeployRoot -Force |
      Where-Object { $_.Name -ne ".git" } |
      Remove-Item -Recurse -Force
    Copy-Item -Path (Join-Path $distClient.Path "*") -Destination $resolvedDeployRoot -Recurse -Force
    if (-not (Test-Path -LiteralPath (Join-Path $resolvedDeployRoot ".nojekyll"))) {
      New-Item -ItemType File -Path (Join-Path $resolvedDeployRoot ".nojekyll") | Out-Null
    }
  }

  Push-Location $resolvedDeployRoot
  try {
    $status = git status --short
    if (-not $status) {
      Write-Host "No gh-pages changes to publish." -ForegroundColor Yellow
    } else {
      $head = (git -C $repoRoot rev-parse --short HEAD).Trim()
      $commitMessage = if ($Message) { $Message } else { "Deploy FATHIYA Pages $head" }
      Invoke-Step "Commit gh-pages" {
        git add -A
        git commit -m $commitMessage
      }
      Invoke-Step "Push gh-pages" {
        git push origin gh-pages
      }
    }
  } finally {
    Pop-Location
  }

  if (-not $NoTrigger) {
    Invoke-Step "Trigger GitHub Pages build" {
      gh api -X POST "repos/$Repo/pages/builds" | Out-Host
    }

    if (-not $NoWait) {
      Invoke-Step "Wait for GitHub Pages" {
        for ($i = 0; $i -lt 36; $i++) {
          $build = gh api "repos/$Repo/pages/builds/latest" | ConvertFrom-Json
          Write-Host "pages status=$($build.status) commit=$($build.commit)"
          if ($build.status -in @("built", "errored")) {
            if ($build.status -ne "built") {
              throw "GitHub Pages build ended with status $($build.status)."
            }
            break
          }
          Start-Sleep -Seconds 5
        }
      }
    }
  }

  Invoke-Step "Verify public Pages operator" {
    $url = "https://fathya-core.github.io/fathiya-core/operator-lite/agent-tasks/?v=$(Get-Date -Format yyyyMMddHHmmss)"
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
    $html = $response.Content
    $result = [pscustomobject]@{
      url = $url
      status = [int]$response.StatusCode
      last_modified = ($response.Headers["Last-Modified"] -join ",")
      has_agent_os = $html.Contains("agent-os")
      command_panel_hidden = $html.Contains("card command-panel view-hidden")
      deploy_strip_hidden = $html.Contains("card deploy-strip view-hidden")
      command_tools_only = $html.Contains('const commandVisible = selected === "tools"')
      length = $html.Length
    }
    $result | ConvertTo-Json -Depth 4
    if (-not $result.has_agent_os -or -not $result.command_panel_hidden -or -not $result.command_tools_only) {
      throw "Published Pages operator does not contain the expected FATHIYA launch view markers."
    }
  }
} finally {
  Pop-Location
}
