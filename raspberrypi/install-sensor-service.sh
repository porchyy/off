#!/usr/bin/env bash
# Install the BH1750/TOF200C publisher as a persistent systemd service.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_USER="${SUDO_USER:-$USER}"
SERVICE_FILE="/etc/systemd/system/postureai-sensors.service"
ENV_FILE="/etc/default/postureai-sensors"

fail() { echo "ERROR: $*" >&2; exit 1; }

if [ "$EUID" -eq 0 ]; then
    fail "Run this script as your normal Pi user, without sudo."
fi
if [ "$(uname -m)" != "aarch64" ]; then
    fail "This installer requires 64-bit Raspberry Pi OS (aarch64)."
fi

echo "[1/4] Enabling I2C and installing sensor dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv i2c-tools raspi-config
sudo raspi-config nonint do_i2c 0
getent group i2c >/dev/null || fail "The i2c group is unavailable"
sudo usermod -aG i2c "$INSTALL_USER"

echo "[2/4] Preparing the sensor Python environment..."
python3 -m venv --system-site-packages "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/python" -m pip install --upgrade pip
"$SCRIPT_DIR/.venv/bin/python" -m pip install -r "$SCRIPT_DIR/requirements-sensors.txt"

echo "[3/4] Registering postureai-sensors.service..."
if [ ! -f "$ENV_FILE" ]; then
    printf 'POSTUREAI_LUX_CALIBRATION=1.0\n' | sudo tee "$ENV_FILE" >/dev/null
fi
sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=PostureAI BH1750 and TOF200C sensor client
Wants=network-online.target postureai-stack.service
After=network-online.target postureai-stack.service

[Service]
Type=simple
User=$INSTALL_USER
SupplementaryGroups=i2c
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=$ENV_FILE
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/sensor_web_client.py --backend-url http://127.0.0.1:8000 --interval 0.5 --lux-calibration \${POSTUREAI_LUX_CALIBRATION}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "[4/4] Starting the sensor service..."
sudo systemctl daemon-reload
sudo systemctl enable --now postureai-sensors.service

echo
echo "Sensor service installed: $SERVICE_FILE"
echo "Status: sudo systemctl status postureai-sensors --no-pager"
echo "Logs:   sudo journalctl -u postureai-sensors -f"
echo "API:    curl http://127.0.0.1:8000/api/sensors/latest"
echo "If I2C was disabled before this run, reboot the Pi once."
