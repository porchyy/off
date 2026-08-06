# Docker — PostureAI

Dockerfile และ compose files สำหรับ deploy

- `docker-compose.yml` ที่ root ของ repo จะอ้างอิงไฟล์ในนี้ (ดู
  `docker-compose.yml` ที่ root)
- มี backend image และ frontend image; frontend build artifacts ถูก serve
  จาก Nginx และ Nginx proxy `/api` ไปยัง backend

## Images

| Service | Build context | Image tag |
| --- | --- | --- |
| `backend` | `../backend` | `postureai-backend:latest` |
| `frontend` | `../frontend` (static) | `nginx:alpine` |

## Volumes

- `../database:/app/database` — SQLite persistence (shared between
  backend service และ host)

`web` เปิดพอร์ต `3000` สำหรับ LAN แต่ `backend` bind พอร์ต `8000` กับ loopback
ของ Pi เท่านั้น เพื่อให้ API ถูกเรียกผ่าน Nginx ตาม origin เดียวกัน
