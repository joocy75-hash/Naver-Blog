#!/bin/bash
# Chrome CDP mode launcher for Naver Blog automation
# Usage: ./scripts/start-chrome.sh

CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR="$HOME/.chrome-naver-blog"
PORT="${CDP_PORT:-9222}"

# Check if Chrome is already running with remote debugging
if curl -s "http://127.0.0.1:${PORT}/json/version" > /dev/null 2>&1; then
    echo "Chrome CDP already running on port ${PORT}"
    curl -s "http://127.0.0.1:${PORT}/json/version" | python3 -c "import sys,json; v=json.load(sys.stdin); print(f\"Browser: {v.get('Browser', 'unknown')}\")"
    exit 0
fi

# Check if Chrome exists
if [ ! -f "$CHROME_BIN" ]; then
    echo "Error: Chrome not found at $CHROME_BIN"
    echo "Install Google Chrome or update CHROME_BIN path"
    exit 1
fi

echo "Starting Chrome with remote debugging on port ${PORT}..."
echo "Profile: ${PROFILE_DIR}"

"$CHROME_BIN" \
    --remote-debugging-port="${PORT}" \
    --user-data-dir="${PROFILE_DIR}" \
    --disable-blink-features=AutomationControlled \
    --no-first-run \
    --no-default-browser-check \
    --window-size=1920,1080 \
    --lang=ko-KR \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    &

sleep 2

if curl -s "http://127.0.0.1:${PORT}/json/version" > /dev/null 2>&1; then
    echo "Chrome CDP started successfully on port ${PORT}"
else
    echo "Warning: Chrome started but CDP not responding yet. Wait a moment and retry."
fi
