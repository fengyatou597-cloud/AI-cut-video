#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "========================================"
echo "AI Video Rough Cut Assistant - macOS Start"
echo "========================================"
echo

if [ ! -x "backend/.venv/bin/python" ]; then
  echo "[INFO] Backend dependencies are not installed yet."
  echo "Run ./install_mac.sh first."
  exit 1
fi

if [ ! -f "frontend/dist/index.html" ]; then
  if [ ! -d "frontend/node_modules" ]; then
    echo "[INFO] Frontend dependencies are missing."
    echo "Run ./install_mac.sh first."
    exit 1
  fi
  echo "[INFO] Frontend build not found. Building it now..."
  (cd frontend && npm run build)
fi

echo "Starting local website: http://localhost:8000"
cd backend
"./.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
cd ..

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Waiting for local website to become ready..."
READY=0
for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:8000/api/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" != "1" ]; then
  echo "[WARN] The local website did not become ready within 30 seconds."
  echo "Check the terminal output above for errors."
  exit 1
fi

echo "Local website is ready."
if command -v open >/dev/null 2>&1; then
  open "http://localhost:8000"
else
  echo "Open this URL in your browser: http://localhost:8000"
fi

echo
echo "Keep this terminal window open while using the app."
echo "Press Ctrl+C here to stop the local website."
wait "$SERVER_PID"
