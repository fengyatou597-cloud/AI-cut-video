@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo ========================================
echo AI Video Rough Cut Assistant - Start
echo ========================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
  echo [INFO] Backend dependencies are not installed yet.
  echo Running install_windows.bat now...
  call "%~dp0install_windows.bat"
  if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed, so the website cannot start yet.
    pause
    exit /b 1
  )
)

if not exist "frontend\dist\index.html" (
  if not exist "frontend\node_modules" (
    echo [INFO] Frontend dependencies are missing.
    echo Please double-click install_windows.bat first, wait until it says "Installation finished",
    echo then run start_windows.bat again.
    pause
    exit /b 1
  )
  echo [INFO] Frontend build not found. Building it now...
  cd /d "%~dp0frontend"
  call npm.cmd run build
  if errorlevel 1 (
    echo [ERROR] Frontend build failed. Please check the message above.
    pause
    exit /b 1
  )
  cd /d "%~dp0"
)

echo Starting local website: http://localhost:8000
start "AI Rough Cut Local Website" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for local website to become ready...
set BACKEND_OK=0
for /l %%i in (1,1,30) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
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
start http://localhost:8000
echo.
echo Browser opened. When finished, close the "AI Rough Cut Local Website" command window.
pause
