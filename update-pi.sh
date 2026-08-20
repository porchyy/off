#!/usr/bin/env bash
# Update an existing OffSyn Tech installation on Raspberry Pi 5.
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PI_DIR="$PROJECT_DIR/raspberrypi"
PI_PYTHON="$PI_DIR/.venv/bin/python"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

cd "$PROJECT_DIR"
[ -d .git ] || fail "$PROJECT_DIR is not a Git repository"
[ -x build.sh ] || fail "$PROJECT_DIR/build.sh is missing or not executable"
[ -x "$PI_PYTHON" ] || fail "Pi virtual environment is missing; run raspberrypi/setup-pi5.sh first"

# Refuse to overwrite local tracked edits. Runtime files such as config.yaml,
# .env, database files, and the Pi buffer are ignored and remain untouched.
if ! git diff --quiet || ! git diff --cached --quiet; then
    fail "tracked files have local changes; commit or stash them before updating"
fi

echo "[1/5] Pulling the latest code..."
OLD_REVISION="$(git rev-parse HEAD)"
git pull --ff-only
NEW_REVISION="$(git rev-parse HEAD)"

echo "[2/5] Updating Raspberry Pi Python dependencies when required..."
if [ "$OLD_REVISION" != "$NEW_REVISION" ] && \
   ! git diff --quiet "$OLD_REVISION" "$NEW_REVISION" -- \
       raspberrypi/requirements.txt raspberrypi/requirements-sensors.txt; then
    "$PI_PYTHON" -m pip install -r "$PI_DIR/requirements.txt"
    "$PI_PYTHON" -m pip install -r "$PI_DIR/requirements-sensors.txt"
else
    echo "Pi requirements unchanged; skipping pip install."
fi

echo "[3/5] Building and restarting the backend and dashboard..."
"$PROJECT_DIR/build.sh"

echo "[4/5] Restarting Raspberry Pi services..."
sudo systemctl daemon-reload
if systemctl list-unit-files postureai-client.service --no-legend 2>/dev/null | grep -q postureai-client; then
    sudo systemctl restart postureai-client.service
else
    echo "postureai-client.service is not installed; skipping."
fi
if systemctl list-unit-files postureai-sensors.service --no-legend 2>/dev/null | grep -q postureai-sensors; then
    sudo systemctl restart postureai-sensors.service
else
    echo "postureai-sensors.service is not installed; skipping."
fi

echo "[5/5] Verifying services..."
if systemctl list-unit-files postureai-client.service --no-legend 2>/dev/null | grep -q postureai-client; then
    sudo systemctl --no-pager --full status postureai-client.service
fi
if systemctl list-unit-files postureai-sensors.service --no-legend 2>/dev/null | grep -q postureai-sensors; then
    sudo systemctl --no-pager --full status postureai-sensors.service
fi

PI_ADDRESS="$(hostname -I | awk '{print $1}')"
echo
echo "Update complete: $OLD_REVISION -> $NEW_REVISION"
echo "Dashboard: http://$PI_ADDRESS:3000"
echo "Local config preserved: $PI_DIR/config.yaml"
