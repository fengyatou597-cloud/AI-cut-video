#!/usr/bin/env bash
set -u

cd "$(dirname "$0")"

echo "========================================"
echo "AI Video Rough Cut Assistant - macOS Check"
echo "========================================"
echo

if command -v python3 >/dev/null 2>&1; then
  python3 --version
else
  echo "[MISSING] python3 was not found. Install Python 3.11+ first."
fi

if [ -f "frontend/dist/index.html" ]; then
  echo "[OK] Frontend build found. Node.js is optional for normal use."
else
  if command -v node >/dev/null 2>&1; then
    node --version
  else
    echo "[MISSING] Node.js was not found. It is required because frontend/dist is missing."
  fi

  if command -v npm >/dev/null 2>&1; then
    npm --version
  else
    echo "[MISSING] npm was not found. It is required because frontend/dist is missing."
  fi
fi

if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -version | head -n 1
else
  echo "[OPTIONAL] ffmpeg was not found. Video metadata and thumbnails will be limited."
fi

if command -v ffprobe >/dev/null 2>&1; then
  ffprobe -version | head -n 1
else
  echo "[OPTIONAL] ffprobe was not found. Duration and resolution detection will be limited."
fi

echo
echo "If Python is OK, run:"
echo "  ./install_mac.sh"
