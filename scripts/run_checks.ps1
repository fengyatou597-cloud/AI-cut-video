$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."

Write-Host "Checking backend syntax..."
if (Test-Path "$Root\backend\.venv\Scripts\python.exe") {
  & "$Root\backend\.venv\Scripts\python.exe" -m compileall "$Root\backend\app"
} else {
  python -m compileall "$Root\backend\app"
}

Write-Host "Building frontend..."
Set-Location "$Root\frontend"
npm.cmd run build

Write-Host "All checks passed."
