param(
  [Parameter(Mandatory=$true)][string]$OldDir,
  [Parameter(Mandatory=$false)][string]$NewDir = "",
  [Parameter(Mandatory=$false)][string]$OutRoot = ""
)

$ErrorActionPreference = "Stop"

function Resolve-FullPath([string]$p) {
  if ([string]::IsNullOrWhiteSpace($p)) { return $null }
  return (Resolve-Path -LiteralPath $p).Path
}

$root = (Resolve-Path -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$old = Resolve-FullPath $OldDir
if (-not $old) { throw "OLD_DIR not found: $OldDir" }

if ([string]::IsNullOrWhiteSpace($NewDir)) {
  $NewDir = Join-Path $root "dist\WboBAMP"
}
$new = Resolve-FullPath $NewDir
if (-not $new) { throw "NEW_DIR not found: $NewDir (expected dist\\WboBAMP; run build.bat first)" }

if ([string]::IsNullOrWhiteSpace($OutRoot)) {
  $OutRoot = Join-Path $root "fix_output"
}
if (-not (Test-Path -LiteralPath $OutRoot)) {
  New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
}
$outRootFull = (Resolve-Path -LiteralPath $OutRoot).Path

# Версия из main.py
$mainPy = Join-Path $root "main.py"
if (!(Test-Path -LiteralPath $mainPy)) { throw "main.py not found (for version)" }
$m = Select-String -LiteralPath $mainPy -Pattern '^\s*APP_VERSION\s*=\s*"(.+)"' | Select-Object -First 1
$ver = if ($m -and $m.Matches.Count -gt 0) { $m.Matches[0].Groups[1].Value.Trim() } else { "unknown" }
if ([string]::IsNullOrWhiteSpace($ver)) { $ver = "unknown" }
$safeVer = ($ver -replace '[^\w\.\-]', '_')

$outDir = Join-Path $outRootFull ("fix_" + $safeVer)
$stage = Join-Path $outDir "update_payload"

if (Test-Path -LiteralPath $outDir) {
  Remove-Item -Recurse -Force -LiteralPath $outDir
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

$excludeRel = @(
  "run_here.bat",
  "__pycache__\",
  ".git\",
  ".idea\",
  ".vscode\",
  "*.log"
)

function Test-Excluded([string]$rel) {
  $r = ($rel -replace '/', '\')
  foreach ($ex in $excludeRel) {
    if ($ex.EndsWith("\")) {
      if ($r.ToLower().StartsWith($ex.ToLower())) { return $true }
    } elseif ($ex.Contains("*")) {
      if ($r -like $ex) { return $true }
    } else {
      if ($r.ToLower() -eq $ex.ToLower()) { return $true }
    }
  }
  return $false
}

$added = New-Object System.Collections.Generic.List[string]
$modified = New-Object System.Collections.Generic.List[string]
$deleted = New-Object System.Collections.Generic.List[string]

# Added / Modified
$newFiles = Get-ChildItem -LiteralPath $new -File -Recurse
foreach ($f in $newFiles) {
  $rel = $f.FullName.Substring($new.Length).TrimStart('\')
  if (Test-Excluded $rel) { continue }

  $oldPath = Join-Path $old $rel
  $dstPath = Join-Path $stage $rel

  if (!(Test-Path -LiteralPath $oldPath)) {
    $added.Add($rel) | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dstPath) | Out-Null
    Copy-Item -LiteralPath $f.FullName -Destination $dstPath -Force
    continue
  }

  $hNew = (Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash
  $hOld = (Get-FileHash -Algorithm SHA256 -LiteralPath $oldPath).Hash
  if ($hNew -ne $hOld) {
    $modified.Add($rel) | Out-Null
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dstPath) | Out-Null
    Copy-Item -LiteralPath $f.FullName -Destination $dstPath -Force
  }
}

# Deleted (для информации)
$oldFiles = Get-ChildItem -LiteralPath $old -File -Recurse
foreach ($f in $oldFiles) {
  $rel = $f.FullName.Substring($old.Length).TrimStart('\')
  if (Test-Excluded $rel) { continue }
  $newPath = Join-Path $new $rel
  if (!(Test-Path -LiteralPath $newPath)) {
    $deleted.Add($rel) | Out-Null
  }
}

$zipName = "update_v$safeVer.zip"
$zipPath = Join-Path $outDir $zipName
$payloadFiles = Get-ChildItem -LiteralPath $stage -File -Recurse

$readme = Join-Path $outDir "README.txt"

if ($payloadFiles.Count -eq 0) {
  @(
    "Wbo BAMP - Fix package",
    "Version: $ver",
    ("Date: " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")),
    "",
    "No changed files found - update package was not created.",
    "",
    "OLD_DIR: $old",
    "NEW_DIR: $new"
  ) | Set-Content -LiteralPath $readme -Encoding UTF8

  Write-Host "[OK] Нет изменений. README: $readme"
  exit 0
}

if (Test-Path -LiteralPath $zipPath) { Remove-Item -Force -LiteralPath $zipPath }
Compress-Archive -LiteralPath (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("Wbo BAMP - Fix package (auto-update ZIP)") | Out-Null
$lines.Add("Version: $ver") | Out-Null
$lines.Add(("Date: " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))) | Out-Null
$lines.Add("") | Out-Null
$lines.Add("How to use:") | Out-Null
$lines.Add(" - Upload this ZIP to GitHub Release as an asset (asset name must include update and .zip, e.g. update_vX.zip)") | Out-Null
$lines.Add(" - The app will download and apply it (menu: Check for updates -> Download and apply)") | Out-Null
$lines.Add("") | Out-Null
$lines.Add("Fix description (fill in manually):") | Out-Null
$lines.Add(" - TODO: ...") | Out-Null
$lines.Add("") | Out-Null
$lines.Add("Changed files in the package:") | Out-Null
$lines.Add((" - Added:    " + $added.Count)) | Out-Null
$lines.Add((" - Modified: " + $modified.Count)) | Out-Null
$lines.Add((" - Deleted:  " + $deleted.Count + " (not removed by auto-updater)")) | Out-Null
$lines.Add("") | Out-Null

if ($added.Count -gt 0) {
$lines.Add("ADDED:") | Out-Null
  foreach ($x in ($added | Sort-Object)) { $lines.Add((" + " + $x)) | Out-Null }
  $lines.Add("") | Out-Null
}
if ($modified.Count -gt 0) {
  $lines.Add("MODIFIED:") | Out-Null
  foreach ($x in ($modified | Sort-Object)) { $lines.Add((" * " + $x)) | Out-Null }
  $lines.Add("") | Out-Null
}
if ($deleted.Count -gt 0) {
  $lines.Add("DELETED (manual / installer only):") | Out-Null
  foreach ($x in ($deleted | Sort-Object)) { $lines.Add((" - " + $x)) | Out-Null }
  $lines.Add("") | Out-Null
}

$lines.Add("OLD_DIR: $old") | Out-Null
$lines.Add("NEW_DIR: $new") | Out-Null

$lines | Set-Content -LiteralPath $readme -Encoding UTF8

Write-Host "[OK] ZIP: $zipPath"
Write-Host "[OK] README: $readme"

