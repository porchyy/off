#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing raspberrypi/.venv. Run setup-pi5.sh first." >&2
  exit 1
fi

.venv/bin/python -m pip uninstall -y mediapipe
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-yolov5.txt
mkdir -p models
curl -fL --retry 3 \
  https://raw.githubusercontent.com/itakurah/Sitting-Posture-Detection-YOLOv5/main/data/inference_models/small640.pt \
  -o models/small640.pt

echo "YOLOv5 sitting-posture runtime and model are ready."
