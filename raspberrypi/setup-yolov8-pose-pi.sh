#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing raspberrypi/.venv. Run setup-pi5.sh first." >&2
  exit 1
fi

# Remove the retired fixed good/bad classifier and its incompatible runtime.
.venv/bin/python -m pip uninstall -y mediapipe yolov5 huggingface-hub
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-yolov8-pose.txt
rm -f models/small640.pt
mkdir -p models
curl -fL --retry 3 \
  https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-pose.pt \
  -o models/yolov8n-pose.pt

echo "YOLOv8-Pose front-view runtime and model are ready."
