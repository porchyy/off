#!/usr/bin/env bash
# Build and start the OffSyn Tech web and backend containers.
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if sudo docker compose version >/dev/null 2>&1; then
    COMPOSE=(sudo docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(sudo docker-compose)
else
    echo "Docker Compose is not installed. Install docker-compose or the Docker Compose plugin first." >&2
    exit 1
fi

if [ ! -f .env ] || ! grep -q '^POSTUREAI_ADMIN_TOKEN=.' .env; then
    echo "Missing POSTUREAI_ADMIN_TOKEN in $PROJECT_DIR/.env" >&2
    echo "Run raspberrypi/setup-pi5.sh or create .env before building." >&2
    exit 1
fi

"${COMPOSE[@]}" up --build -d --remove-orphans
"${COMPOSE[@]}" ps

echo "Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
