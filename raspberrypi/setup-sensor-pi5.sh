#!/bin/bash
# Install only the camera sensor client on Raspberry Pi 5 (no Docker/web stack).
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

sudo apt-get update
sudo apt-get install -y python3-venv python3-picamera2 python3-opencv libgl1 alsa-utils curl

# Picamera2 is supplied by Raspberry Pi OS, so expose system packages to the venv.
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

echo "Setup complete. Test the sensor with:"
echo "  cd $(pwd)"
echo "  .venv/bin/python posture_client.py --config config.yaml --test-camera -v"
