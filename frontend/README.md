# PostureAI Frontend

Static HTML/JS/CSS ที่ใช้ MediaPipe Pose ใน browser — ปรับแค่ path ให้ทำงาน
ภายใต้ Vite (build tool) โดยไม่เปลี่ยน logic เดิม

## โครงสร้าง

- `index.html` — entry point (ใช้ relative path กับ Vite)
- `app.js` — camera, MediaPipe, scoring, alerts
- `storage.js` — backend (HTTP) vs demo (localStorage) abstraction
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

## โหมดตัวอย่าง (no backend)

ถ้าเปิดผ่าน static server ที่ไม่มี `/api/health` แอปจะสลับเป็นโหมด
localStorage เองอัตโนมัติ — ใช้สำหรับ GitHub Pages หรือ dev ที่ไม่ต้องการ
เก็บข้อมูล
