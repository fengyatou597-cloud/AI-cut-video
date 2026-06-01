@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo AI Video Rough Cut Assistant - Environment Check
echo ========================================
echo.

where python >nul 2>nul && python --version || (
  where py >nul 2>nul && py -3 --version || echo [MISSING] Python was not found in PATH or via py launcher.
)
if exist "frontend\dist\index.html" (
  echo [OK] Frontend build found. Node.js is optional for normal use.
) else (
  where node >nul 2>nul && node --version || echo [MISSING] Node.js was not found in PATH. It is required because frontend\dist is missing.
  where npm.cmd >nul 2>nul && call npm.cmd --version || echo [MISSING] npm was not found in PATH. It is required because frontend\dist is missing.
)
where ffmpeg >nul 2>nul && ffmpeg -version | findstr /B "ffmpeg" || echo [OPTIONAL] ffmpeg was not found. Video metadata and thumbnails will be limited.
where ffprobe >nul 2>nul && ffprobe -version | findstr /B "ffprobe" || echo [OPTIONAL] ffprobe was not found. Duration and resolution detection will be limited.

echo.
echo If Python is OK, run install_windows.bat next.
pause
