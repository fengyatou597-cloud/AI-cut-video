#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "========================================"
echo "AI Video Rough Cut Assistant - macOS Install"
echo "========================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 was not found. Install Python 3.11+ first."
  echo "Recommended: https://www.python.org/downloads/macos/"
  exit 1
fi

echo "[1/3] Preparing backend Python environment..."
cd backend
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
fi

cd ..
if [ -f "frontend/dist/index.html" ]; then
  echo "[2/3] Frontend build found. Node.js is not required for normal use."
else
  echo "[2/3] Frontend build missing. Node.js is required to build it."
  if ! command -v node >/dev/null 2>&1; then
    echo "[ERROR] Node.js was not found, and frontend/dist is missing."
    echo "Recommended: https://nodejs.org/"
    exit 1
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] npm was not found. Reinstall Node.js 20+."
    exit 1
  fi
  cd frontend
  npm install
  npm run build
  cd ..
fi

echo "[3/3] Installation finished."
echo
echo "Next time, run:"
echo "  ./start_mac.sh"
echo
echo "It will open http://localhost:8000"
