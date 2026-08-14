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
sudo apt-get install -y python3-venv python3-picamera2 python3-opencv libgl1 alsa-utils espeak-ng python3-gpiozero curl

# Picamera2 is supplied by Raspberry Pi OS, so expose system packages to the venv.
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

echo "Setup complete. Test the sensor with:"
echo "  cd $(pwd)"
echo "  .venv/bin/python posture_client.py --config config.yaml --test-camera -v"
