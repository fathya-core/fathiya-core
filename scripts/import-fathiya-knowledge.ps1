param(
  [string[]]$Source = @(
    "C:\Users\pc\OneDrive\Desktop\AWARENESS_KNOWLEDGE_ROADMAP-and-securty.zip",
    "C:\Users\pc\OneDrive\Desktop\Gmail - Deep research performance gains with multi-model Fusion.pdf"
  ),
  [string]$Inbox = "",
  [string]$RuntimeApi = "http://127.0.0.1:8765",
  [switch]$Scan
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($Inbox)) {
  $Inbox = Join-Path $RepoRoot "services\agent-runtime\runtime\knowledge-inbox"
}

$resolvedInbox = (New-Item -ItemType Directory -Force -Path $Inbox).FullName
$receiptRoot = New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "services\agent-runtime\runtime\knowledge-imports")

function Get-SafeFileName {
  param([Parameter(Mandatory = $true)][string]$Name)

  $safe = $Name
  foreach ($char in [System.IO.Path]::GetInvalidFileNameChars()) {
    $safe = $safe.Replace([string]$char, "-")
  }
  $safe = $safe.Trim()
  if ([string]::IsNullOrWhiteSpace($safe)) {
    return "knowledge-source"
  }
  return $safe
}

function Resolve-DestinationPath {
  param(
    [Parameter(Mandatory = $true)][string]$TargetDirectory,
    [Parameter(Mandatory = $true)][string]$FileName,
    [Parameter(Mandatory = $true)][string]$SourceHash
  )

  $safeName = Get-SafeFileName $FileName
  $candidate = Join-Path $TargetDirectory $safeName
  if (-not (Test-Path -LiteralPath $candidate)) {
    return $candidate
  }

  $existingHash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($existingHash -eq $SourceHash) {
    return $candidate
  }

  $stem = [System.IO.Path]::GetFileNameWithoutExtension($safeName)
  $ext = [System.IO.Path]::GetExtension($safeName)
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  return Join-Path $TargetDirectory "$stem-$stamp$ext"
}

$supported = @(".csv", ".json", ".md", ".pdf", ".txt", ".zip")
$copied = New-Object System.Collections.Generic.List[object]
$missing = New-Object System.Collections.Generic.List[object]
$unsupported = New-Object System.Collections.Generic.List[object]

foreach ($item in $Source) {
  if ([string]::IsNullOrWhiteSpace($item)) {
    continue
  }

  if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
    $missing.Add([pscustomobject]@{ source = $item; reason = "not_found" })
    continue
  }

  $sourceItem = Get-Item -LiteralPath $item
  $extension = $sourceItem.Extension.ToLowerInvariant()
  if ($supported -notcontains $extension) {
    $unsupported.Add([pscustomobject]@{ source = $sourceItem.FullName; extension = $extension; reason = "unsupported_extension" })
    continue
  }

  $sourceHash = (Get-FileHash -LiteralPath $sourceItem.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  $destination = Resolve-DestinationPath -TargetDirectory $resolvedInbox -FileName $sourceItem.Name -SourceHash $sourceHash
  $alreadyPresent = $false
  if (Test-Path -LiteralPath $destination) {
    $alreadyPresent = ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -eq $sourceHash)
  }
  if (-not $alreadyPresent) {
    Copy-Item -LiteralPath $sourceItem.FullName -Destination $destination
  }

  $copied.Add([pscustomobject]@{
    source = $sourceItem.FullName
    destination = $destination
    sha256 = $sourceHash
    bytes = $sourceItem.Length
    already_present = $alreadyPresent
  })
}

$scanResult = $null
if ($Scan) {
  $base = $RuntimeApi.TrimEnd("/")
  try {
    $scanResult = Invoke-RestMethod -Uri "$base/api/agent/intake/scan" -Method Post -TimeoutSec 60
  } catch {
    $scanResult = [pscustomobject]@{
      error = $_.Exception.Message
      hint = "Knowledge files were copied, but the runtime API did not accept a scan request."
    }
  }
}

$receipt = [pscustomobject]@{
  schema = "fathiya_knowledge_import_v1"
  imported_at = (Get-Date).ToUniversalTime().ToString("o")
  inbox = $resolvedInbox
  copied = $copied.ToArray()
  missing = $missing.ToArray()
  unsupported = $unsupported.ToArray()
  scan = $scanResult
}

$receiptPath = Join-Path $receiptRoot.FullName ("knowledge-import-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8

[pscustomobject]@{
  ok = ($missing.Count -eq 0 -and $unsupported.Count -eq 0)
  copied_count = $copied.Count
  missing_count = $missing.Count
  unsupported_count = $unsupported.Count
  receipt = $receiptPath
  inbox = $resolvedInbox
  scan_requested = [bool]$Scan
} | ConvertTo-Json -Depth 4
