$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$excludedDirs = @(
  ".git",
  "backend\.venv",
  "backend\storage",
  "frontend\node_modules",
  "frontend\dist",
  "logs",
  "release"
)

$secretPatterns = @(
  "sk-[A-Za-z0-9_\-]{12,}",
  '"ai_api_key"\s*:\s*"[^"]+',
  '"ai_text_api_key"\s*:\s*"[^"]+',
  '"ai_vision_api_key"\s*:\s*"[^"]+',
  ("C:\\Users\\" + [regex]::Escape($env:USERNAME)),
  ("D:\\" + "AI视频粗剪输出")
)

function Test-IsExcluded($path) {
  $relative = $path.Substring($root.Path.TrimEnd("\").Length).TrimStart("\").Replace("/", "\")
  foreach ($dir in $excludedDirs) {
    if ($relative -eq $dir -or $relative.StartsWith("$dir\")) {
      return $true
    }
  }
  return $false
}

$files = Get-ChildItem -Path $root -Recurse -File -Force |
  Where-Object { -not (Test-IsExcluded $_.FullName) }

$hits = @()
foreach ($pattern in $secretPatterns) {
  $matches = $files | Select-String -Pattern $pattern -SimpleMatch:$false -ErrorAction SilentlyContinue
  if ($matches) {
    $hits += $matches
  }
}

Write-Host "Release preflight scan"
Write-Host "Root: $root"
Write-Host "Scanned files: $($files.Count)"

if ($hits.Count -gt 0) {
  Write-Host ""
  Write-Host "[FAIL] Found possible local paths or secrets in files that may be committed:" -ForegroundColor Red
  $hits | Select-Object Path, LineNumber, Line | Format-List
  exit 1
}

Write-Host "[OK] No obvious secrets or local Jianying paths found outside ignored runtime folders." -ForegroundColor Green

if (Get-Command git -ErrorAction SilentlyContinue) {
  Write-Host ""
  Write-Host "Git status:"
  git status --short
} else {
  Write-Host ""
  Write-Host "Git is not installed or not in PATH. You can use GitHub Desktop instead."
}
