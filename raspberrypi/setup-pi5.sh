#!/usr/bin/env bash
# PostureAI — Raspberry Pi 5 all-in-one installer (Pi Camera + web + backend).
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_USER="${SUDO_USER:-$USER}"
DOCKER_BIN="$(command -v docker || true)"
COMPOSE_BIN=""
COMPOSE_MODE=""

fail() { echo "ERROR: $*" >&2; exit 1; }

compose_cmd() {
    if [ "$COMPOSE_MODE" = "plugin" ]; then
        sudo "$DOCKER_BIN" compose "$@"
    else
        sudo "$COMPOSE_BIN" "$@"
    fi
}

if [ "$(uname -m)" != "aarch64" ]; then
    fail "This installer requires a 64-bit ARM Raspberry Pi OS (aarch64)."
fi
if [ ! -r /etc/os-release ]; then
    fail "Cannot identify the operating system. Raspberry Pi OS Bookworm is required."
fi
. /etc/os-release
if [ "${VERSION_CODENAME:-}" != "bookworm" ]; then
    fail "Raspberry Pi OS Bookworm is required (found ${PRETTY_NAME:-unknown})."
fi
if [ "$EUID" -eq 0 ]; then
    fail "Run this script as your normal Pi user, without sudo."
fi

echo "[1/6] Installing Pi, Docker, camera, and audio dependencies..."
sudo apt-get update
sudo apt-get install -y \
    docker.io python3-venv python3-picamera2 python3-opencv \
    libgl1 alsa-utils espeak-ng python3-gpiozero i2c-tools raspi-config curl openssl

echo "Enabling I2C for BH1750..."
sudo raspi-config nonint do_i2c 0

DOCKER_BIN="$(command -v docker || true)"
[ -n "$DOCKER_BIN" ] || fail "docker was not installed successfully"
if sudo "$DOCKER_BIN" compose version >/dev/null 2>&1; then
    COMPOSE_MODE="plugin"
    COMPOSE_EXEC="$DOCKER_BIN compose"
    COMPOSE_DISPLAY="sudo docker compose"
else
    echo "Docker Compose plugin is unavailable; installing the Bookworm docker-compose package..."
    sudo apt-get install -y docker-compose
    COMPOSE_BIN="$(command -v docker-compose || true)"
    [ -n "$COMPOSE_BIN" ] || fail "Docker Compose was not installed successfully"
    sudo "$COMPOSE_BIN" version >/dev/null || fail "Docker Compose is unavailable after installation"
    COMPOSE_MODE="standalone"
    COMPOSE_EXEC="$COMPOSE_BIN"
    COMPOSE_DISPLAY="sudo docker-compose"
fi

# The compose file enables administrator protection. Keep the secret out of
# git, but let Docker Compose load it automatically from the project root.
ENV_FILE="$PROJECT_DIR/.env"
if ! grep -q '^POSTUREAI_ADMIN_TOKEN=.' "$ENV_FILE" 2>/dev/null; then
    echo "Creating a local administrator token..."
    umask 077
    TOKEN="$(openssl rand -hex 32)"
    printf 'POSTUREAI_ADMIN_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

echo "[2/6] Granting camera/audio/I2C access to $INSTALL_USER..."
sudo usermod -aG docker,video,audio,gpio,i2c "$INSTALL_USER"

echo "[3/6] Creating the Pi sensor environment..."
cd "$SCRIPT_DIR"
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-sensors.txt
# This client no longer uses the previous YOLO runtime.  Remove it from this
# project venv so the Pi cannot accidentally load an old detector.
.venv/bin/python -m pip uninstall -y yolov5 ultralytics huggingface-hub torch torchvision || true
rm -f models/small640.pt models/yolov8n-pose.pt
MODEL_PATH="$PROJECT_DIR/frontend/public/models/pose_landmarker_full.task"
if [ ! -s "$MODEL_PATH" ]; then
    echo "Downloading MediaPipe Pose Landmarker Full model..."
    mkdir -p "$(dirname "$MODEL_PATH")"
    curl -fL --retry 2 -o "$MODEL_PATH" \
        https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
fi
CLASSIFIER_MODEL="$SCRIPT_DIR/models/kanden_posture_classifier.onnx"
if [ ! -s "$CLASSIFIER_MODEL" ]; then
    echo "Downloading Kanden ONNX posture classifier..."
    mkdir -p "$(dirname "$CLASSIFIER_MODEL")"
    curl -fL --retry 2 -o "$CLASSIFIER_MODEL" \
        https://huggingface.co/SeiyaCM/KandenAiHackathonPostureModel/resolve/main/exported/posture_classifier.onnx
fi
if [ ! -f config.yaml ]; then
    cp config.example.yaml config.yaml
fi

# Keep existing hardware/network settings, but switch an existing installation
# back to the original MediaPipe Pose settings.
.venv/bin/python - config.yaml <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
detection = config.setdefault("detection", {})
for key in ("confidence", "iou", "image_size", "model_url"):
    detection.pop(key, None)
detection.update({
    "enabled": True,
    "interval": 0.1,
    "overlay_smoothing_alpha": 0.65,
    "overlay_hold_seconds": 0.2,
    "overlay_min_visibility": 0.35,
    "metric_smoothing_alpha": 0.35,
    "mode": "mediapipe",
    "score_source": "upper_body",
    "model": "../frontend/public/models/pose_landmarker_full.task",
})
classifier = config.setdefault("posture_classifier", {})
classifier.update({
    "enabled": False,
    "model": "models/kanden_posture_classifier.onnx",
    "interval": 0.5,
    "min_confidence": 0.65,
})
path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
PY

echo "[4/6] Building and starting the web/backend containers..."
cd "$PROJECT_DIR"
mkdir -p database
compose_cmd up --build -d --remove-orphans

echo "Waiting for backend health check..."
for attempt in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
        break
    fi
    if [ "$attempt" -eq 30 ]; then
        compose_cmd ps
        fail "backend did not become healthy; inspect logs with: $COMPOSE_DISPLAY logs backend"
    fi
    sleep 2
done

# Register the environmental sensor publisher before camera/MediaPipe checks.
# A camera failure must not prevent the environment sensor from starting.
echo "Registering the persistent BH1750 service..."
sudo tee /etc/systemd/system/postureai-sensors.service >/dev/null <<EOF
[Unit]
Description=PostureAI BH1750 sensor client
Wants=network-online.target postureai-stack.service
After=network-online.target postureai-stack.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=$INSTALL_USER
SupplementaryGroups=i2c
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/sensor_web_client.py --backend-url http://127.0.0.1:8000 --interval 0.5
Restart=always
RestartSec=3
TimeoutStopSec=10
# Safety guard; the client also closes/reuses every HTTP connection.
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now postureai-sensors.service

echo "[5/6] Verifying MediaPipe, Pi Camera, and backend..."
cd "$SCRIPT_DIR"
.venv/bin/python posture_client.py --config config.yaml --check

echo "[6/6] Registering services to start after every reboot..."
sudo tee /etc/systemd/system/postureai-stack.service >/dev/null <<EOF
[Unit]
Description=PostureAI web and backend containers
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$COMPOSE_EXEC up -d --remove-orphans
ExecStop=$COMPOSE_EXEC down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/postureai-client.service >/dev/null <<EOF
[Unit]
Description=PostureAI Pi Camera sensor client
Wants=network-online.target
After=network-online.target postureai-stack.service
Requires=postureai-stack.service

[Service]
Type=simple
User=$INSTALL_USER
SupplementaryGroups=video audio gpio
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/posture_client.py --config $SCRIPT_DIR/config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now postureai-stack.service
sudo systemctl enable --now postureai-client.service
sudo systemctl enable --now postureai-sensors.service

PI_IP="$(hostname -I | awk '{print $1}')"
echo
echo "PostureAI is ready. Open: http://$PI_IP:3000"
echo "Status: sudo systemctl status postureai-stack postureai-client postureai-sensors"
echo "Camera/AI logs: sudo journalctl -u postureai-client -f"
echo "Sensor logs:    sudo journalctl -u postureai-sensors -f"
echo "Containers: $COMPOSE_DISPLAY ps"
echo "Web/API health: curl http://127.0.0.1:8000/api/health"
