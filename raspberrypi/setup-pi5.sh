#!/usr/bin/env bash
# PostureAI — Raspberry Pi 5 all-in-one installer (Pi Camera + web + backend).
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_USER="${SUDO_USER:-$USER}"
DOCKER_BIN="$(command -v docker || true)"

fail() { echo "ERROR: $*" >&2; exit 1; }

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
    docker.io docker-compose-v2 python3-venv python3-picamera2 python3-opencv \
    libgl1 alsa-utils python3-gpiozero curl openssl

DOCKER_BIN="$(command -v docker || true)"
[ -n "$DOCKER_BIN" ] || fail "docker was not installed successfully"
sudo "$DOCKER_BIN" compose version >/dev/null || fail "Docker Compose v2 is unavailable after installation"

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

echo "[2/6] Granting camera/audio access to $INSTALL_USER..."
sudo usermod -aG docker,video,audio,gpio "$INSTALL_USER"

echo "[3/6] Creating the Pi sensor environment..."
cd "$SCRIPT_DIR"
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
MODEL_PATH="$PROJECT_DIR/frontend/public/models/pose_landmarker_full.task"
if [ ! -s "$MODEL_PATH" ]; then
    echo "Downloading MediaPipe Pose Landmarker Full model..."
    mkdir -p "$(dirname "$MODEL_PATH")"
    curl -fL --retry 2 -o "$MODEL_PATH" \
        https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
fi
if [ ! -f config.yaml ]; then
    cp config.example.yaml config.yaml
fi

echo "[4/6] Building and starting the web/backend containers..."
cd "$PROJECT_DIR"
mkdir -p database
sudo "$DOCKER_BIN" compose up --build -d --remove-orphans

echo "Waiting for backend health check..."
for attempt in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
        break
    fi
    if [ "$attempt" -eq 30 ]; then
        sudo "$DOCKER_BIN" compose ps
        fail "backend did not become healthy; inspect logs with: sudo docker compose logs backend"
    fi
    sleep 2
done

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
ExecStart=$DOCKER_BIN compose up -d --remove-orphans
ExecStop=$DOCKER_BIN compose down
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

PI_IP="$(hostname -I | awk '{print $1}')"
echo
echo "PostureAI is ready. Open: http://$PI_IP:3000"
echo "Status: sudo systemctl status postureai-stack postureai-client"
echo "Logs:   sudo journalctl -u postureai-client -f"
echo "Containers: sudo docker compose ps"
echo "Web/API health: curl http://127.0.0.1:8000/api/health"
