$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$releaseRoot = Join-Path $root "release"
$baseDir = Join-Path $releaseRoot "ai-video-rough-cut-assistant"
$portableDir = Join-Path $releaseRoot "ai-video-rough-cut-assistant-windows-portable"
$portableZip = Join-Path $releaseRoot "ai-video-rough-cut-assistant-windows-portable.zip"
$pythonRuntime = "C:\Users\$env:USERNAME\.cache\codex-runtimes\codex-primary-runtime\dependencies\python"
$sourceSitePackages = Join-Path $root "backend\.venv\Lib\site-packages"

if (-not (Test-Path $baseDir)) {
  & (Join-Path $PSScriptRoot "make_release_copy.ps1")
}

if (-not (Test-Path (Join-Path $baseDir "frontend\dist\index.html"))) {
  throw "frontend\dist is missing. Run npm.cmd run build in frontend first."
}

if (-not (Test-Path (Join-Path $pythonRuntime "python.exe"))) {
  throw "Portable Python runtime was not found: $pythonRuntime"
}

if (-not (Test-Path $sourceSitePackages)) {
  throw "Backend dependencies were not found: $sourceSitePackages"
}

if (Test-Path $portableDir) {
  $resolvedPortable = Resolve-Path $portableDir
  if (-not $resolvedPortable.Path.StartsWith((Resolve-Path $releaseRoot).Path)) {
    throw "Refusing to remove unexpected release path: $resolvedPortable"
  }
  Remove-Item -LiteralPath $portableDir -Recurse -Force
}

if (Test-Path $portableZip) {
  Remove-Item -LiteralPath $portableZip -Force
}

Copy-Item -LiteralPath $baseDir -Destination $portableDir -Recurse -Force

$portableStorage = Join-Path $portableDir "backend\storage"
if (Test-Path $portableStorage) {
  Remove-Item -LiteralPath $portableStorage -Recurse -Force
}

$targetPython = Join-Path $portableDir "runtime\python"
New-Item -ItemType Directory -Path (Split-Path $targetPython -Parent) -Force | Out-Null
Copy-Item -LiteralPath $pythonRuntime -Destination $targetPython -Recurse -Force

$targetSitePackages = Join-Path $targetPython "Lib\site-packages"
if (Test-Path $targetSitePackages) {
  Remove-Item -LiteralPath $targetSitePackages -Recurse -Force
}
New-Item -ItemType Directory -Path $targetSitePackages -Force | Out-Null
$robocopyOutput = & robocopy $sourceSitePackages $targetSitePackages /E /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -gt 7) {
  throw "Failed to copy backend dependencies into portable Python. robocopy exit code: $LASTEXITCODE`n$robocopyOutput"
}

$portableStart = @'
@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo ========================================
echo AI Video Rough Cut Assistant - Portable Start
echo ========================================
echo.

set "PYTHON_EXE=%~dp0runtime\python\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Portable Python runtime is missing.
  echo Please use the full windows-portable zip, or run install_windows.bat with Python 3.11+ installed.
  pause
  exit /b 1
)

if not exist "frontend\dist\index.html" (
  echo [ERROR] Frontend build is missing: frontend\dist\index.html
  echo Please use the full release zip.
  pause
  exit /b 1
)

echo Checking portable backend dependencies...
"%PYTHON_EXE%" -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, multipart, pyJianYingDraft" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Portable backend dependencies are incomplete.
  echo Please use the full windows-portable zip, or run install_windows.bat on a machine with Python installed.
  pause
  exit /b 1
)

set "APP_PORT=8765"
echo Starting local website: http://localhost:%APP_PORT%
set "BACKEND_DIR=%~dp0backend"
start "AI Rough Cut Local Website" cmd /k "cd /d ""%BACKEND_DIR%"" && ""%PYTHON_EXE%"" -m uvicorn app.main:app --host 127.0.0.1 --port %APP_PORT%"

echo Waiting for local website to become ready...
set BACKEND_OK=0
for /l %%i in (1,1,30) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://localhost:%APP_PORT%/api/health -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 set BACKEND_OK=1
  if "!BACKEND_OK!"=="1" goto ready
  timeout /t 1 /nobreak >nul
)

echo.
echo [WARN] The local website did not become ready within 30 seconds.
echo Please check the command window titled "AI Rough Cut Local Website" for error messages.
pause
exit /b 1

:ready
echo.
echo Local website is ready.
start http://localhost:%APP_PORT%
echo.
echo Browser opened. When finished, close the "AI Rough Cut Local Website" command window.
pause
'@

Set-Content -Path (Join-Path $portableDir "start_windows.bat") -Value $portableStart -Encoding ASCII

$portableReadme = @'
Windows portable package

This package includes a Python runtime and backend dependencies.

First use:
1. Extract the whole zip.
2. Double-click start_windows.bat.
3. The browser should open http://localhost:8765.

You do not need to run install_windows.bat first.

ffmpeg is still recommended if you want video duration, resolution, and thumbnails.

If Windows SmartScreen blocks the file, choose "More info" and "Run anyway".
This happens because this is not a signed installer.
'@

Set-Content -Path (Join-Path $portableDir "README_WINDOWS_PORTABLE.txt") -Value $portableReadme -Encoding UTF8

Compress-Archive -Path $portableDir -DestinationPath $portableZip -Force

Write-Host "Windows portable release created:"
Write-Host $portableDir
Write-Host ""
Write-Host "Windows portable zip created:"
Write-Host $portableZip
