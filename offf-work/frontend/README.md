# PostureAI Frontend

Static HTML/JS/CSS ที่ใช้ MediaPipe Pose ใน browser — ปรับแค่ path ให้ทำงาน
ภายใต้ Vite (build tool) โดยไม่เปลี่ยน logic เดิม

## โครงสร้าง

- `index.html` — entry point (ใช้ relative path กับ Vite)
- `app.js` — camera, MediaPipe, scoring, alerts
- `storage.js` — thin client for the FastAPI backend `/api/*` routes
- `app.css` — UI styling

## Dev

```powershell
cd frontend
npm install
npm run dev
```

เปิด `http://localhost:5173` — Vite จะ proxy `/api/*` ไปยัง FastAPI backend
(ค่า default `http://localhost:8000`, override ได้ด้วย env
`POSTUREAI_BACKEND_URL=http://host:port`)

## Build

```powershell
npm run build
```

ได้ static files ที่ `frontend/dist/`. FastAPI backend (`backend/app/main.py`)
จะ serve `dist/` อัตโนมัติถ้าโฟลเดอร์นี้มีอยู่ — เปิด `http://localhost:8000`
ที่เดียวจบ

## ต้องมี backend เสมอ

Build นี้ **ไม่มีโหมดตัวอย่าง/localStorage แล้ว** — ตอนโหลดหน้าเว็บ แอปจะ
เรียก `GET /api/health` ก่อนเสมอ ถ้าเรียกไม่ได้จะขึ้นแบนเนอร์แดง "เชื่อมต่อ
backend ไม่ได้" พร้อมปุ่ม "ลองใหม่" และปิดปุ่ม "เริ่มการวิเคราะห์" ไว้จนกว่า
backend จะตอบกลับ — เพราะฉะนั้นต้องรัน backend (`docker compose up` หรือ
`python -m app`) ก่อนเปิดหน้านี้เสมอ (ใช้งานแบบ static-only บน GitHub
Pages ไม่ได้อีกต่อไป)
