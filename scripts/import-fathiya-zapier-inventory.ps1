param(
  [string]$SnapshotPath = "",
  [string]$InventoryPath = "",
  [string]$Inbox = "",
  [string]$RuntimeApi = "http://127.0.0.1:8765",
  [switch]$Scan,
  [switch]$NoInventoryUpdate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($InventoryPath)) {
  $InventoryPath = Join-Path $RepoRoot "knowledge\runtime\connected_tool_inventory_v1.json"
}
if ([string]::IsNullOrWhiteSpace($Inbox)) {
  $Inbox = Join-Path $RepoRoot "services\agent-runtime\runtime\knowledge-inbox"
}

function ConvertFrom-JsonText {
  param([Parameter(Mandatory = $true)][string]$Text)

  $trimmed = $Text.Trim()
  if ([string]::IsNullOrWhiteSpace($trimmed)) {
    throw "Zapier inventory snapshot is empty."
  }
  return $trimmed | ConvertFrom-Json
}

function Read-SnapshotPayload {
  if (-not [string]::IsNullOrWhiteSpace($SnapshotPath)) {
    if (-not (Test-Path -LiteralPath $SnapshotPath -PathType Leaf)) {
      throw "Snapshot file not found: $SnapshotPath"
    }
    return ConvertFrom-JsonText (Get-Content -LiteralPath $SnapshotPath -Raw)
  }

  $stdin = [Console]::In.ReadToEnd()
  return ConvertFrom-JsonText $stdin
}

function Expand-McpPayload {
  param([Parameter(Mandatory = $true)]$Payload)

  if ($null -ne $Payload.PSObject.Properties["content"] -and $Payload.content -is [array]) {
    $items = New-Object System.Collections.Generic.List[object]
    foreach ($entry in $Payload.content) {
      if ($null -eq $entry -or $null -eq $entry.PSObject.Properties["text"]) {
        continue
      }
      $nested = ConvertFrom-JsonText ([string]$entry.text)
      $expanded = Expand-McpPayload $nested
      foreach ($item in $expanded) {
        $items.Add($item)
      }
    }
    return $items.ToArray()
  }

  return @($Payload)
}

function Add-AppSummary {
  param(
    [Parameter(Mandatory = $true)]$AppsByName,
    [Parameter(Mandatory = $true)][string]$App,
    [int]$ActionCount = 0,
    [string[]]$Modes = @()
  )

  $name = $App.Trim()
  if ([string]::IsNullOrWhiteSpace($name)) {
    return
  }
  if (-not $AppsByName.Contains($name)) {
    $AppsByName[$name] = [ordered]@{
      app = $name
      action_count = 0
      modes = @()
    }
  }
  if ($ActionCount -gt [int]$AppsByName[$name].action_count) {
    $AppsByName[$name].action_count = $ActionCount
  }
  foreach ($mode in $Modes) {
    if (-not [string]::IsNullOrWhiteSpace($mode) -and $AppsByName[$name].modes -notcontains $mode) {
      $AppsByName[$name].modes += $mode
    }
  }
}

function Get-ActionMode {
  param($Action)

  $tool = ""
  if ($null -ne $Action.PSObject.Properties["tool"]) {
    $tool = [string]$Action.tool
  }
  if ($tool.ToLowerInvariant().Contains("read")) {
    return "read"
  }
  return "approval_gated_write"
}

function Get-StringArray {
  param($Value)

  $items = New-Object System.Collections.Generic.List[string]
  if ($Value -is [array]) {
    foreach ($item in $Value) {
      $text = [string]$item
      if (-not [string]::IsNullOrWhiteSpace($text)) {
        $items.Add($text.Trim())
      }
    }
  }
  return $items.ToArray()
}

function Convert-ActionSchema {
  param($Action)

  $mode = Get-ActionMode $Action
  $schema = [ordered]@{
    name = [string]$Action.name
    key = [string]$Action.key
    tool_name = [string]$Action.tool_name
    mode = $mode
    required_params = @()
    optional_params = @()
  }
  if ($null -ne $Action.PSObject.Properties["dynamic_properties_depends_on"]) {
    $schema.dynamic_properties_depends_on = Get-StringArray $Action.dynamic_properties_depends_on
  }
  if ($null -ne $Action.PSObject.Properties["params"] -and $Action.params -is [array]) {
    $required = New-Object System.Collections.Generic.List[string]
    $optional = New-Object System.Collections.Generic.List[string]
    $params = New-Object System.Collections.Generic.List[object]
    foreach ($param in $Action.params) {
      if ($null -eq $param -or $null -eq $param.PSObject.Properties["key"]) {
        continue
      }
      $key = [string]$param.key
      if ([string]::IsNullOrWhiteSpace($key)) {
        continue
      }
      $safeParam = [ordered]@{ key = $key }
      if ($null -ne $param.PSObject.Properties["label"]) {
        $safeParam.label = [string]$param.label
      }
      if ($null -ne $param.PSObject.Properties["required"]) {
        $safeParam.required = [bool]$param.required
      }
      $params.Add($safeParam)
      if ($safeParam.required) {
        $required.Add($key)
      } else {
        $optional.Add($key)
      }
    }
    $schema.required_params = $required.ToArray()
    $schema.optional_params = $optional.ToArray()
    if ($params.Count -gt 0) {
      $schema.params = $params.ToArray()
    }
  }
  return $schema
}

$payloads = Expand-McpPayload (Read-SnapshotPayload)
$appsByName = [ordered]@{}
$actionSamples = [ordered]@{}
$actionSchemas = [ordered]@{}
$agentProviderActions = [ordered]@{}

foreach ($payload in $payloads) {
  if ($payload -is [array]) {
    foreach ($entry in $payload) {
      $payloads += $entry
    }
    continue
  }

  if ($null -ne $payload.PSObject.Properties["apps"] -and $payload.apps -is [array]) {
    foreach ($app in $payload.apps) {
      Add-AppSummary -AppsByName $appsByName -App ([string]$app.app) -ActionCount ([int]$app.action_count)
    }
  }

  if ($null -eq $payload.PSObject.Properties["app"]) {
    continue
  }
  $appName = [string]$payload.app
  if ([string]::IsNullOrWhiteSpace($appName)) {
    continue
  }

  $actions = @()
  if ($null -ne $payload.PSObject.Properties["actions"] -and $payload.actions -is [array]) {
    $actions = $payload.actions
  }
  if ($actions.Count -eq 0) {
    if ($null -ne $payload.PSObject.Properties["action_count"]) {
      Add-AppSummary -AppsByName $appsByName -App $appName -ActionCount ([int]$payload.action_count)
    }
    continue
  }

  $readNames = New-Object System.Collections.Generic.List[string]
  $writeNames = New-Object System.Collections.Generic.List[string]
  $schemas = New-Object System.Collections.Generic.List[object]
  foreach ($action in $actions) {
    $mode = Get-ActionMode $action
    $name = [string]$action.name
    if ([string]::IsNullOrWhiteSpace($name)) {
      continue
    }
    if ($mode -eq "read") {
      $readNames.Add($name)
    } else {
      $writeNames.Add($name)
    }
    $schemas.Add((Convert-ActionSchema $action))
  }

  $modes = @()
  if ($readNames.Count -gt 0) { $modes += "read" }
  if ($writeNames.Count -gt 0) { $modes += "approval_gated_write" }
  Add-AppSummary -AppsByName $appsByName -App $appName -ActionCount $actions.Count -Modes $modes

  $sample = [ordered]@{}
  if ($readNames.Count -gt 0) {
    $sample.read = $readNames.ToArray()
  }
  if ($writeNames.Count -gt 0) {
    $sample.approval_gated_write = $writeNames.ToArray()
  }
  $actionSamples[$appName] = $sample
  $actionSchemas[$appName] = $schemas.ToArray()
  $agentProviderActions[$appName] = $sample
}

$capturedAt = (Get-Date).ToUniversalTime().ToString("o")
$apps = @($appsByName.Values | Sort-Object { $_.app })
$zapierSource = [ordered]@{
  name = "codex_hosted_zapier_mcp"
  captured_at = $capturedAt
  source = "live Codex Zapier MCP enabled-action inventory"
  apps = $apps
  action_samples = $actionSamples
  action_schemas = $actionSchemas
  execution_notes = @(
    "Imported from live Zapier MCP list-enabled output. Internal routing identifiers are intentionally not stored in this receipt-safe inventory.",
    "Read actions may be auto-prepared by FATHIYA. External writes remain approval-gated by runtime policy."
  )
}

$inventory = [ordered]@{}
if ((Test-Path -LiteralPath $InventoryPath -PathType Leaf) -and -not $NoInventoryUpdate) {
  $existing = Get-Content -LiteralPath $InventoryPath -Raw | ConvertFrom-Json
  foreach ($property in $existing.PSObject.Properties) {
    $inventory[$property.Name] = $property.Value
  }
}
if ($inventory.Count -eq 0) {
  $inventory.schema_version = "connected_tool_inventory_v1"
  $inventory.policy = [ordered]@{
    read_actions = "automatic"
    owned_local_actions = "automatic"
    external_writes = "awaiting_approval"
    financial_actions = "awaiting_approval"
    live_security_actions = "awaiting_approval"
    destructive_actions = "awaiting_approval"
  }
}

$inventory.schema_version = "connected_tool_inventory_v1"
$inventory.captured_at = $capturedAt
$inventory.source = "live Zapier MCP enabled-action inventory and local runtime checks"
$inventory.zapier_mcp_status = [ordered]@{
  inventory = "active"
  action_execution = "codex_hosted_inventory_current; local_oauth_required_for_runtime_execution"
  note = "FATHIYA has a current receipt-safe Zapier action map. Local runtime execution still uses local Zapier OAuth before dispatch."
}
$inventory.zapier_apps = $apps
$inventory.action_samples = $actionSamples
$inventory.action_schemas = $actionSchemas
$inventory.agent_provider_actions = $agentProviderActions

$sources = New-Object System.Collections.Generic.List[object]
if ($inventory.Contains("additional_zapier_mcp_sources") -and $inventory.additional_zapier_mcp_sources -is [array]) {
  foreach ($source in $inventory.additional_zapier_mcp_sources) {
    if ($null -ne $source.PSObject.Properties["name"] -and [string]$source.name -eq "codex_hosted_zapier_mcp") {
      continue
    }
    $sources.Add($source)
  }
}
$sources.Add($zapierSource)
$inventory.additional_zapier_mcp_sources = $sources.ToArray()

if (-not $NoInventoryUpdate) {
  $inventoryDirectory = Split-Path -Parent $InventoryPath
  New-Item -ItemType Directory -Force -Path $inventoryDirectory | Out-Null
  $inventory | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath $InventoryPath -Encoding UTF8
}

$resolvedInbox = (New-Item -ItemType Directory -Force -Path $Inbox).FullName
$missionPath = Join-Path $resolvedInbox ("zapier-live-inventory-{0}.md" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$providerLines = $apps | ForEach-Object { "- $($_.app): $($_.action_count) actions; modes=$([string]::Join(',', $_.modes))" }
$mission = @"
# FATHIYA Zapier Live Inventory Mission

Captured: $capturedAt

Goal: understand the live connected Zapier apps and turn them into executable agent routes inside FATHIYA.

Current live apps:
$($providerLines -join "`n")

Operator policy:
- Read-only actions are eligible for automatic preparation.
- External write actions must be prepared as tasks and pass the runtime approval gate before dispatch.
- Do not expose internal routing identifiers to the operator.

Required comprehension output:
- Identify the strongest immediate agent routes for Agents, GitHub, Gmail, Outlook, Netlify, Webhooks, and Zapier Tables.
- For each route, decide whether it can run as read-only now or must wait for approval/OAuth.
- Produce a short execution checklist that the FATHIYA operator page can show.
"@
$mission | Set-Content -LiteralPath $missionPath -Encoding UTF8

$scanResult = $null
if ($Scan) {
  $base = $RuntimeApi.TrimEnd("/")
  try {
    $scanResult = Invoke-RestMethod -Uri "$base/api/agent/intake/scan" -Method Post -TimeoutSec 60
  } catch {
    $scanResult = [pscustomobject]@{
      error = $_.Exception.Message
      hint = "Zapier inventory was imported, but the runtime API did not accept a scan request."
    }
  }
}

$actionTotal = 0
foreach ($app in $apps) {
  $actionTotal += [int]$app.action_count
}

[pscustomobject]@{
  ok = $true
  captured_at = $capturedAt
  app_count = $apps.Count
  action_count = $actionTotal
  inventory = if ($NoInventoryUpdate) { $null } else { (Resolve-Path $InventoryPath).Path }
  mission = $missionPath
  scan_requested = [bool]$Scan
  scan = $scanResult
} | ConvertTo-Json -Depth 8
