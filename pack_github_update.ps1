# Собирает ZIP для GitHub Releases — совместим с автообновлением в приложении
# (имя файла содержит "update" и .zip; внутри — одна папка WboBAMP как после build.bat).
#
# Использование (из корня репозитория):
#   .\build.bat
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\pack_github_update.ps1
#
# Параметры:
#   -SourceDir  Путь к собранной onedir-папке (по умолчанию dist\WboBAMP)
#   -OutDir     Куда положить архив (по умолчанию fix_output\github-update)
#   -Label      Доп. суффикк к имени файла (например hotfix1)

param(
    [string]$SourceDir = "dist\WboBAMP",
    [string]$OutDir = "fix_output\github-update",
    [string]$Label = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$src = Join-Path $root $SourceDir
if (-not (Test-Path -LiteralPath $src)) {
    Write-Error "Не найдена папка сборки: $src — сначала выполните build.bat (PyInstaller dist\WboBAMP)."
}

$mainPy = Join-Path $root "main.py"
if (-not (Test-Path -LiteralPath $mainPy)) {
    Write-Error "Не найден main.py в $root"
}

$verMatch = Select-String -LiteralPath $mainPy -Pattern 'APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
$ver = if ($verMatch) { $verMatch.Matches[0].Groups[1].Value } else { "dev" }

$suffix = if ([string]::IsNullOrWhiteSpace($Label)) { "" } else { "_$Label" }
$outName = "update_WboBAMP_v${ver}${suffix}.zip"

$outAbs = Join-Path $root $OutDir
New-Item -ItemType Directory -Force -Path $outAbs | Out-Null
$zipPath = Join-Path $outAbs $outName
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

# Один корневой каталог WboBAMP внутри ZIP — как ожидает _apply_update_zip в main.py
Compress-Archive -LiteralPath $src -DestinationPath $zipPath -Force

Write-Host "OK: $zipPath"
Write-Host "Загрузите этот файл как asset к релизу на GitHub (вместе с установщиком при необходимости)."
