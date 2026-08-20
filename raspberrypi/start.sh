#!/usr/bin/env bash
# Start the Pi camera/posture client after a manual GPIO test.
set -Eeuo pipefail

sudo systemctl start postureai-client.service
sudo systemctl --no-pager --full status postureai-client.service
