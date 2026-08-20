#!/usr/bin/env bash
# Stop the Pi camera/posture client without shutting down the Pi or web stack.
set -Eeuo pipefail

sudo systemctl stop postureai-client.service
echo "postureai-client stopped (GPIO outputs were released)."
