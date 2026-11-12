# Ergo Agent Frontend

Modern AI Posture Ergonomic Dashboard built with Vanilla ES Modules, Vite, and Apple Health glassmorphic design system. Features on-device MediaPipe Pose tracking and real-time Server-Sent Events (SSE) telemetry streaming from Raspberry Pi edge nodes.

## โครงสร้าง

- `index.html` — Entry point พร้อม Apple Health design tokens และ clean semantic layout
- `app.js` — Camera capture, MediaPipe inference, WebRTC stream listener, SSE telemetry (`/api/stream`), UI state bindings
- `pose-utils.js` — Ergonomic scoring algorithm (Neck, Shoulders, Trunk coronal lean, Visibility threshold)
- `storage.js` — Dual-storage abstraction (FastAPI backend with token auth vs. zero-config localStorage fallback)
- `app.css` / `risk.css` — Apple Health glassmorphic palette (`#30D158`, `#FF9F0A`, `#FF453A`, `#0A84FF`)
- `tests/` — Node.js native test suite (`pose.test.js`, `storage.test.js`)

## Development

```powershell
cd frontend
npm install
npm run dev
```

เปิด `http://localhost:5173` — Vite จะ proxy `/api/*` และ `/ws/*` ไปยัง FastAPI backend
(ค่า default `http://localhost:8000`, override ได้ด้วย env
`ERGO_AGENT_BACKEND_URL=http://host:port` หรือ `POSTUREAI_BACKEND_URL`)

## Testing

```powershell
npm test
```

รัน unit tests ทั้งหมดด้วย Node.js Native Test Runner (`node --test`) ครอบคลุม:
- การคำนวณคะแนน MediaPipe Pose (Score, Neck, Shoulders, Torso coronal lean)
- การคัดกรอง Landmark ความชัดเจนต่ำ (Visibility threshold)
- LocalStorage fallback storage (Demo mode)
- การบันทึก/อ่านตั้งค่า, Samples, Alerts, Summary, Stats, ดาวน์โหลดรายงาน Excel (`ErgoAgent_YYYY-MM-DD.xlsx`) และ Clear data

## Production Build

```powershell
npm run build
```

ได้ static files ที่ `frontend/dist/`. FastAPI backend (`backend/app/main.py`)
จะ serve `dist/` อัตโนมัติถ้าโฟลเดอร์นี้มีอยู่ — เปิด `http://localhost:8000`
ที่เดียวจบ

## Standalone / Demo Mode

ถ้าเปิดผ่าน static server ที่ไม่มี `/api/health` หรือไม่มี backend รันอยู่ แอปจะสลับเป็นโหมด
localStorage เองอัตโนมัติ — เหมาะสำหรับ GitHub Pages หรือ offline workstation testing
