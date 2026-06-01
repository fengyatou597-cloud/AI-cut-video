param(
  [int]$Port = 8000
)

Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Creating backend virtual environment..."
  python -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port $Port
