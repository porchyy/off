#!/bin/bash
# Install only the camera sensor client on Raspberry Pi 5 (no Docker/web stack).
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

if [ "$(uname -m)" != "aarch64" ]; then
    echo "ERROR: This installer requires 64-bit Raspberry Pi OS (aarch64)." >&2
    exit 1
fi

sudo apt-get update
sudo apt-get install -y python3-venv python3-picamera2 python3-opencv libgl1 alsa-utils python3-gpiozero curl

# Picamera2 is supplied by Raspberry Pi OS, so expose system packages to the venv.
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip uninstall -y mediapipe
.venv/bin/python -m pip install -r requirements-yolov5.txt
MODEL_PATH="$SCRIPT_DIR/models/small640.pt"
if [ ! -s "$MODEL_PATH" ]; then
    echo "Downloading upstream YOLOv5 sitting-posture model..."
    mkdir -p "$(dirname "$MODEL_PATH")"
    curl -fL --retry 3 -o "$MODEL_PATH" \
        https://raw.githubusercontent.com/itakurah/Sitting-Posture-Detection-YOLOv5/main/data/inference_models/small640.pt
fi

if [ ! -f config.yaml ]; then
    cp config.example.yaml config.yaml
fi

echo "Setup complete. Test the sensor with:"
echo "  cd $(pwd)"
echo "  .venv/bin/python posture_client.py --config config.yaml --test-camera -v"
