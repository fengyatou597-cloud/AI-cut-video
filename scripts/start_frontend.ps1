param(
  [int]$Port = 5173
)

Set-Location "$PSScriptRoot\..\frontend"
if (-not (Test-Path "node_modules")) {
  npm.cmd install
}
npm.cmd run dev -- --host 0.0.0.0 --port $Port
