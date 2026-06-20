param(
  [int]$ApiPort = 8765,
  [int]$WebPort = 5180,
  [switch]$SkipInstall,
  [switch]$ForceInstall,
  [switch]$FullVite,
  [switch]$Detached,
  [switch]$OpenBrowser,
  [switch]$StartN8n,
  [switch]$RestartRuntime,
  [switch]$RestartWeb,
  [int]$N8nPort = 5678
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeRoot = Join-Path $RepoRoot "services\agent-runtime"
$VenvPath = Join-Path $RuntimeRoot ".venv"
$RuntimePython = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $RuntimeRoot)) {
  throw "Runtime service was not found at $RuntimeRoot"
}

if (-not (Test-Path $RuntimePython)) {
  Write-Host "Creating Python 3.13 virtual environment..."
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    & py -3.13 -m venv $VenvPath
  } else {
    & python -m venv $VenvPath
  }
}

function Test-RuntimeImport {
  try {
    & $RuntimePython -c "import fathiya_runtime" | Out-Null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

if (-not $SkipInstall) {
  $runtimeImportReady = Test-RuntimeImport
  if ($ForceInstall -or -not $runtimeImportReady) {
    Write-Host "Installing FATHIYA runtime package..."
    & $RuntimePython -m pip install -e $RuntimeRoot
  } else {
    Write-Host "FATHIYA runtime package is already importable; skipping reinstall."
  }

  if (-not (Test-Path (Join-Path $RepoRoot "node_modules"))) {
    Write-Host "Installing website dependencies..."
    Push-Location $RepoRoot
    try {
      npm install
    } finally {
      Pop-Location
    }
  }
}

Write-Host "Initializing local task store..."
& $RuntimePython -m fathiya_runtime.cli init

$apiUrl = "http://127.0.0.1:$ApiPort"
$webUrl = "http://127.0.0.1:$WebPort/agent-tasks"
$tradingUrl = "$webUrl/?view=trading"
$bugBountyUrl = "$webUrl/?view=bug-bounty"
$knowledgeUrl = "$webUrl/?view=knowledge"
$reportsUrl = "$webUrl/?view=reports"
$n8nUrl = "http://127.0.0.1:$N8nPort"

if (-not $env:FATHIYA_ENABLE_HF_RETRIEVAL) {
  $env:FATHIYA_ENABLE_HF_RETRIEVAL = "true"
}
if (-not $env:FATHIYA_ENABLE_LOCAL_GENERATION) {
  $env:FATHIYA_ENABLE_LOCAL_GENERATION = "true"
}
if (-not $env:FATHIYA_ENABLE_LOCAL_PLANNING) {
  $env:FATHIYA_ENABLE_LOCAL_PLANNING = "true"
}
if (-not $env:FATHIYA_LOCAL_MODEL) {
  $env:FATHIYA_LOCAL_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
}
if (-not $env:FATHIYA_LOCAL_MAX_NEW_TOKENS) {
  $env:FATHIYA_LOCAL_MAX_NEW_TOKENS = "160"
}
if (-not $env:FATHIYA_LOCAL_MAX_GENERATION_SECONDS) {
  $env:FATHIYA_LOCAL_MAX_GENERATION_SECONDS = "20"
}

$serveCommand = "Set-Location '$RuntimeRoot'; `$env:PYTHONPATH='$RuntimeRoot'; & '$RuntimePython' -m fathiya_runtime.cli serve --host 127.0.0.1 --port $ApiPort --poll-seconds 0.5"
$LogRoot = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force $LogRoot | Out-Null

function Test-HttpReady([string]$Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
    return [int]$response.StatusCode -lt 500
  } catch {
    return $false
  }
}

$apiProcess = $null
if ($RestartRuntime) {
  $apiListeners = @(Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue)
  $apiOwners = @($apiListeners | Select-Object -ExpandProperty OwningProcess -Unique)
  foreach ($owner in $apiOwners) {
    if ($owner) {
      Write-Host "Stopping existing FATHIYA runtime listener on port $ApiPort (process $owner) ..."
      Stop-Process -Id $owner -Force
    }
  }

  $staleRuntimeProcesses = @(
    Get-CimInstance Win32_Process |
      Where-Object {
        $_.ProcessId -ne $PID -and
        $_.CommandLine -like "*fathiya_runtime.cli serve*" -and
        $_.CommandLine -like "*--port $ApiPort*"
      }
  )
  foreach ($process in $staleRuntimeProcesses) {
    if ($process.ProcessId -and -not ($apiOwners -contains $process.ProcessId)) {
      Write-Host "Stopping stale FATHIYA runtime process on port $ApiPort (process $($process.ProcessId)) ..."
      Stop-Process -Id $process.ProcessId -Force
    }
  }

  if ($apiOwners.Count -gt 0 -or $staleRuntimeProcesses.Count -gt 0) {
    Start-Sleep -Seconds 2
  }
}

$n8nProcess = $null
function Start-LocalN8n {
  if (Test-HttpReady "$n8nUrl/healthz") {
    Write-Host "n8n is already running at $n8nUrl"
    return $null
  }

  $n8nCommand = $null
  $n8nCommandInfo = Get-Command "n8n.cmd" -ErrorAction SilentlyContinue
  if ($n8nCommandInfo) {
    $n8nCommand = $n8nCommandInfo.Source
  } else {
    $npmN8n = Join-Path $env:APPDATA "npm\n8n.cmd"
    if (Test-Path $npmN8n) {
      $n8nCommand = $npmN8n
    }
  }

  if (-not $n8nCommand) {
    throw "n8n CLI was not found. Install it with: npm install -g n8n"
  }

  Write-Host "Starting local n8n at $n8nUrl ..."
  $n8nOut = Join-Path $LogRoot "n8n-$N8nPort.out.log"
  $n8nErr = Join-Path $LogRoot "n8n-$N8nPort.err.log"
  $n8nCommandText = "`$env:N8N_HOST='127.0.0.1'; `$env:N8N_PORT='$N8nPort'; `$env:N8N_PROTOCOL='http'; `$env:N8N_LISTEN_ADDRESS='127.0.0.1'; `$env:N8N_SECURE_COOKIE='false'; & '$n8nCommand' start"
  $startedProcess = Start-Process `
    -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $n8nCommandText) `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $n8nOut `
    -RedirectStandardError $n8nErr `
    -PassThru

  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-HttpReady "$n8nUrl/healthz") {
      Write-Host "Started local n8n process $($startedProcess.Id)"
      Write-Host "n8n logs: $n8nOut"
      return $startedProcess
    }
  }

  throw "n8n did not become ready at $n8nUrl. Check $n8nErr"
}

$webHealthUrl = "http://127.0.0.1:$WebPort/agent-tasks/"
if ($RestartWeb) {
  $webListeners = @(Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue)
  $webOwners = @($webListeners | Select-Object -ExpandProperty OwningProcess -Unique)
  foreach ($owner in $webOwners) {
    if ($owner) {
      Write-Host "Stopping existing FATHIYA operator UI listener on port $WebPort (process $owner) ..."
      Stop-Process -Id $owner -Force
    }
  }
  if ($webOwners.Count -gt 0) {
    Start-Sleep -Seconds 2
  }
}
$webAlreadyRunning = Test-HttpReady $webHealthUrl
$webListener = Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue
if ($webListener -and -not $webAlreadyRunning) {
  $owners = @($webListener | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
  throw "Web port $WebPort is already in use by process(es): $owners. It does not look like FATHIYA at $webHealthUrl. Stop that process or run with -WebPort <another-port>."
}

if ($StartN8n) {
  $n8nProcess = Start-LocalN8n
}

if (Test-HttpReady "$apiUrl/api/agent/tasks") {
  Write-Host "FATHIYA local runtime is already running at $apiUrl"
} else {
  Write-Host "Starting FATHIYA local runtime at $apiUrl ..."
  $apiProcess = Start-Process `
    -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $serveCommand) `
    -WorkingDirectory $RuntimeRoot `
    -WindowStyle Hidden `
    -PassThru
}

Start-Sleep -Seconds 2

if (-not (Test-HttpReady "$apiUrl/api/agent/tasks")) {
  throw "FATHIYA local runtime did not become ready at $apiUrl"
}

if ($OpenBrowser -and -not $Detached) {
  Start-Process $webUrl
}

Write-Host ""
Write-Host "FATHIYA is starting."
Write-Host "Runtime API: $apiUrl"
Write-Host "Operator UI: $webUrl"
Write-Host "Trading: $tradingUrl"
Write-Host "Bug bounty: $bugBountyUrl"
Write-Host "Knowledge: $knowledgeUrl"
Write-Host "Reports: $reportsUrl"
if ($Detached) {
  Write-Host "Detached mode is enabled. The runtime and operator UI will keep running after this script exits."
} else {
  Write-Host "Press Ctrl+C to stop the website. The script will stop the runtime process it started."
}
Write-Host ""

Push-Location $RepoRoot
try {
  if ($webAlreadyRunning) {
    Write-Host "FATHIYA operator UI is already running at $webHealthUrl"
    if ($OpenBrowser) {
      Start-Process $webUrl
    }
    if (-not $Detached -and $apiProcess) {
      Write-Host "Runtime API was started by this script. Press Ctrl+C to stop it."
      while ($true) {
        Start-Sleep -Seconds 5
        if ($apiProcess.HasExited) {
          throw "FATHIYA local runtime process exited unexpectedly."
        }
      }
    }
  } elseif ($Detached) {
    $webLog = Join-Path $LogRoot "fathiya-operator-$WebPort.log"
    $webErr = Join-Path $LogRoot "fathiya-operator-$WebPort.err.log"
    if ($FullVite) {
      $webCommand = "`$env:VITE_FATHIYA_LOCAL_API_URL='$apiUrl'; npm run dev -- --host 127.0.0.1 --port $WebPort"
      $webWorkingDirectory = $RepoRoot
    } else {
      $liteRoot = Join-Path $RepoRoot "operator-lite"
      $webCommand = "& '$RuntimePython' -m http.server $WebPort --bind 127.0.0.1"
      $webWorkingDirectory = $liteRoot
    }
    $webProcess = Start-Process `
      -FilePath "powershell" `
      -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $webCommand) `
      -WorkingDirectory $webWorkingDirectory `
      -WindowStyle Hidden `
      -RedirectStandardOutput $webLog `
      -RedirectStandardError $webErr `
      -PassThru
    Start-Sleep -Seconds 2
    if (-not (Test-HttpReady $webHealthUrl)) {
      throw "FATHIYA operator UI did not become ready at $webHealthUrl. Check $webErr"
    }
    Write-Host "Started FATHIYA operator UI process $($webProcess.Id)"
    if ($apiProcess) {
      Write-Host "Started FATHIYA runtime API process $($apiProcess.Id)"
    }
    Write-Host "Operator UI: $webUrl"
    Write-Host "Trading: $tradingUrl"
    Write-Host "Bug bounty: $bugBountyUrl"
    Write-Host "Knowledge: $knowledgeUrl"
    Write-Host "Reports: $reportsUrl"
    Write-Host "Logs: $webLog"
    if ($OpenBrowser) {
      Start-Process $webUrl
    }
  } elseif ($FullVite) {
    $env:VITE_FATHIYA_LOCAL_API_URL = $apiUrl
    npm run dev -- --host 127.0.0.1 --port $WebPort
  } else {
    Push-Location (Join-Path $RepoRoot "operator-lite")
    try {
      & $RuntimePython -m http.server $WebPort --bind 127.0.0.1
    } finally {
      Pop-Location
    }
  }
} finally {
  Pop-Location
  if (-not $Detached -and $apiProcess -and -not $apiProcess.HasExited) {
    Write-Host "Stopping FATHIYA local runtime..."
    Stop-Process -Id $apiProcess.Id -Force
  }
  if (-not $Detached -and $n8nProcess -and -not $n8nProcess.HasExited) {
    Write-Host "Stopping local n8n..."
    Stop-Process -Id $n8nProcess.Id -Force
  }
}
