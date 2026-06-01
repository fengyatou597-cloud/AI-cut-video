@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo AI Video Rough Cut Assistant - Install
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Please install Python 3.11 or newer and enable "Add python.exe to PATH".
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
  ) else (
    set PYTHON_CMD=py -3
  )
) else (
  set PYTHON_CMD=python
)

echo [1/3] Preparing backend Python environment...
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail

if not exist ".env" copy ".env.example" ".env" >nul

if exist "%~dp0frontend\dist\index.html" (
  echo [2/3] Frontend build found. Node.js is not required for normal use.
) else (
  echo [2/3] Frontend build missing. Node.js is required to build it.
  where node >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Node.js was not found, and frontend/dist is missing.
    echo Please install Node.js 20 or newer: https://nodejs.org/
    pause
    exit /b 1
  )
  cd /d "%~dp0frontend"
  call npm.cmd install
  if errorlevel 1 goto fail
  call npm.cmd run build
  if errorlevel 1 goto fail
)

echo [3/3] Installation finished.
echo.
echo Next time, double-click start_windows.bat to launch the local website.
echo It will open http://localhost:8000
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation failed. Please copy or screenshot the messages above.
pause
exit /b 1
