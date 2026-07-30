#!/bin/bash
# ==============================================================================
# PostureAI / OfficeGuardian — Raspberry Pi 5 One-Command Automated Setup
# ==============================================================================

set -e

echo "🚀 [PostureAI] Starting Raspberry Pi 5 System Setup..."

# 1. Update APT and install required dependencies
echo "📦 [1/4] Installing system dependencies & Docker..."
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-v2 python3-venv git curl

# Add current user to docker group
sudo usermod -aG docker $USER || true

# 2. Build and launch full-stack containers
echo "🐳 [2/4] Building & launching Docker Compose stack..."
cd "$(dirname "$0")/.."

# Wait until Docker daemon is ready
echo "⏳ Waiting for Docker daemon..."
sudo systemctl start docker 2>/dev/null || true
until sudo docker info >/dev/null 2>&1; do sleep 1; done

sudo docker compose down --remove-orphans || true
sudo docker compose up --build -d

# 3. Create Systemd Service for Auto-Start on Reboot
echo "⚙️ [3/4] Registering Systemd auto-start service..."
SERVICE_PATH="/etc/systemd/system/postureai.service"
PROJECT_DIR="$(pwd)"

sudo bash -c "cat <<EOF > $SERVICE_PATH
[Unit]
Description=PostureAI OfficeGuardian Container Stack
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=simple
Restart=on-failure
RestartSec=5s
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable postureai.service

# 4. Display Access Details
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=============================================================================="
echo "✅ [PostureAI] Setup Completed Successfully!"
echo "=============================================================================="
echo "🌐 Local LAN Access URL:  http://$PI_IP:3000"
echo "⚙️  Backend Health Check: http://$PI_IP:8000/api/health"
echo "🔄 Auto-start service registered (postureai.service enabled)"
echo "=============================================================================="
