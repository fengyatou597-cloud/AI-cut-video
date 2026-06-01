$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$releaseRoot = Join-Path $root "release"
$releaseDir = Join-Path $releaseRoot "ai-video-rough-cut-assistant"
$releaseZip = Join-Path $releaseRoot "ai-video-rough-cut-assistant.zip"
$rootPath = $root.Path.TrimEnd("\")

Set-Location $root

$excludeDirs = @(
  ".git",
  "release",
  "logs",
  "backend\.venv",
  "backend\storage",
  "frontend\node_modules"
)

$excludeFiles = @(
  ".env"
)

function Test-ShouldExcludeDir($relativePath) {
  $normalized = $relativePath.Replace("/", "\").Trim("\")
  $parts = $normalized.Split("\")
  if ($parts -contains "__pycache__") {
    return $true
  }
  foreach ($dir in $excludeDirs) {
    if ($normalized -eq $dir -or $normalized.StartsWith("$dir\")) {
      return $true
    }
  }
  return $false
}

function Test-ShouldExcludeFile($relativePath) {
  $name = Split-Path $relativePath -Leaf
  if ($excludeFiles -contains $name) {
    return $true
  }
  if ($name.EndsWith(".pyc") -or $name.EndsWith(".log") -or $name.EndsWith(".zip") -or $name.EndsWith(".db")) {
    return $true
  }
  if ($name.EndsWith(".sqlite") -or $name.EndsWith(".sqlite3")) {
    return $true
  }
  return $false
}

if (Test-Path $releaseDir) {
  $resolvedRelease = Resolve-Path $releaseDir
  if (-not $resolvedRelease.Path.StartsWith((Resolve-Path $releaseRoot).Path)) {
    throw "Refusing to remove unexpected release path: $resolvedRelease"
  }
  Remove-Item -LiteralPath $releaseDir -Recurse -Force
}

if (Test-Path $releaseZip) {
  Remove-Item -LiteralPath $releaseZip -Force
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

$items = Get-ChildItem -Path $root -Recurse -Force
foreach ($item in $items) {
  $fullPath = $item.FullName
  if (-not $fullPath.StartsWith($rootPath)) {
    continue
  }
  $relative = $fullPath.Substring($rootPath.Length).TrimStart("\")
  if ([string]::IsNullOrWhiteSpace($relative) -or $relative -eq ".") {
    continue
  }
  if ($item.PSIsContainer) {
    if (Test-ShouldExcludeDir $relative) {
      continue
    }
    New-Item -ItemType Directory -Path (Join-Path $releaseDir $relative) -Force | Out-Null
    continue
  }
  if (Test-ShouldExcludeDir (Split-Path $relative -Parent)) {
    continue
  }
  if (Test-ShouldExcludeFile $relative) {
    continue
  }
  $target = Join-Path $releaseDir $relative
  New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
  Copy-Item -LiteralPath $item.FullName -Destination $target -Force
}

Write-Host "Clean release copy created:"
Write-Host $releaseDir
Write-Host ""
Compress-Archive -Path $releaseDir -DestinationPath $releaseZip -Force
Write-Host "Release zip created:"
Write-Host $releaseZip
Write-Host ""
Write-Host "Share the zip with coworkers, upload it to GitHub Releases, or initialize Git inside the folder."
