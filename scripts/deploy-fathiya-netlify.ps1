param(
  [switch]$OpenLogin
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

try {
  if ($OpenLogin) {
    npx netlify-cli login
  }

  npm run build
  npx netlify-cli deploy --prod --dir dist
} finally {
  Pop-Location
}
