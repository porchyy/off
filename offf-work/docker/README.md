# Docker — PostureAI

Dockerfile และ compose files สำหรับ deploy

- `docker-compose.yml` ที่ root ของ repo จะอ้างอิงไฟล์ในนี้ (ดู
  `docker-compose.yml` ที่ root)
- ปัจจุบันมีแค่ backend image; frontend build artifacts ถูก serve
  จาก FastAPI เอง (ดู `backend/app/main.py`)

## Images

| Service | Build context | Image tag |
| --- | --- | --- |
| `backend` | `../backend` | `postureai-backend:latest` |
| `frontend` | `../frontend` (static) | `nginx:alpine` |

## Volumes

- `../database:/app/database` — SQLite persistence (shared between
  backend service และ host)
