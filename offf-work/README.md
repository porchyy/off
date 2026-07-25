# PostureAI

แอปติดตามท่านั่งแบบ local-first ใช้กล้องและ MediaPipe Pose เพื่อประมวลผลบน
เครื่องของผู้ใช้ วิดีโอจากกล้องไม่ถูกบันทึกหรืออัปโหลด — ระบบเก็บเฉพาะคะแนน
posture, มุมโดยประมาณ, เวลา และเหตุการณ์แจ้งเตือน

## โครงสร้างโปรเจกต์

```
OfficeGuardian-AI/
├── frontend/          # static HTML/JS (Vite build)
├── backend/           # FastAPI + SQLite
├── raspberrypi/       # Python client สำหรับ Pi (MediaPipe + OpenCV)
├── database/          # SQLite file + legacy data
├── docs/              # specs, wireframes, prototype
├── docker/            # Dockerfile.backend / .frontend / nginx.conf
├── docker-compose.yml # backend + web
└── README.md          # (ไฟล์นี้)
```

## เริ่มใช้งานแบบเร็ว (Docker)

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (docs: `/docs`)
- Frontend: http://localhost:3000
- SQLite ถูก mount ไว้ที่ `./database/postureai.sqlite` — ข้อมูลอยู่ถาวร

## เริ่มใช้งานแบบแยก service (dev)

ต้องมี Node.js 22+ (frontend) และ Python 3.12+ (backend)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
copy .env.example .env            # Windows
# cp .env.example .env            # macOS/Linux
python -m app
```

เปิด http://localhost:8000/docs เพื่อดู OpenAPI

### Frontend

```bash
cd frontend
npm install
npm run dev
```

เปิด http://localhost:5173 — Vite จะ proxy `/api/*` ไป `http://localhost:8000`
อัตโนมัติ (override ได้ด้วย `POSTUREAI_BACKEND_URL` env var)

### Pi client (optional)

```bash
cd raspberrypi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
python posture_client.py --config config.yaml
```

## ต้องมี backend เสมอ

เวอร์ชันนี้ตัดโหมดตัวอย่าง/localStorage ออกแล้ว — frontend ต้องเชื่อมต่อ
FastAPI backend จริงเสมอ ถ้าเปิดหน้าเว็บแล้ว `GET /api/health` เรียกไม่ได้
(เช่น ลืมรัน backend หรือ deploy เป็น static site เฉยๆ) แอปจะโชว์แบนเนอร์
แจ้งเตือนพร้อมปุ่ม "ลองใหม่" และปิดปุ่มเริ่มการวิเคราะห์ไว้จนกว่าจะเชื่อม
ต่อได้ — ผลคือ **deploy แบบ static-only บน GitHub Pages ใช้ไม่ได้อีกต่อไป**
ต้องมี hosting ที่รัน backend ได้จริง (VPS, Docker host, Raspberry Pi ฯลฯ)

## ฟีเจอร์หลัก

- วิเคราะห์ท่านั่งแบบเรียลไทม์ด้วย MediaPipe Pose ใน browser
- แสดงความเสี่ยง Office Syndrome เป็นสีเขียว/แดงตามคะแนนและเวลานั่งผิดท่า
  ต่อเนื่อง
- ตั้งค่า threshold คะแนนเสี่ยง, เวลาค้างก่อนขึ้นแดง, path ฐานข้อมูล, เสียงเตือน
  และ desktop notification
- แจ้งเตือนจริงด้วย popup, เสียง beep และ desktop notification
- เก็บข้อมูลลง SQLite ที่ `./database/postureai.sqlite` (เปลี่ยนได้ด้วย
  `POSTUREAI_DATA_DIR`)
- Export ประวัติเป็น CSV/JSON
- กราฟคะแนนเฉลี่ยรายวันและจำนวนแจ้งเตือนย้อนหลัง

## API

| Method | Path | คำอธิบาย |
| --- | --- | --- |
| GET | `/api/health` | ตรวจสถานะ server และ SQLite |
| GET | `/api/settings` | อ่านค่าตั้งค่า |
| PUT | `/api/settings` | บันทึกค่าตั้งค่า |
| POST | `/api/samples` | บันทึกคะแนน posture |
| POST | `/api/alerts` | บันทึกเหตุการณ์แจ้งเตือน |
| GET | `/api/summary` | สรุปข้อมูลวันนี้ |
| GET | `/api/stats` | ข้อมูลสำหรับกราฟ |
| GET | `/api/export?format=csv` | export CSV |
| GET | `/api/export?format=json` | export JSON |
| DELETE | `/api/data` | ลบข้อมูล samples และ alerts |

## ความเป็นส่วนตัว

- AI pose detection ทำงานใน browser ของผู้ใช้
- วิดีโอไม่ถูกส่งไปยัง server และไม่ถูกเก็บลงดิสก์
- Server local เก็บเฉพาะคะแนน, มุมโดยประมาณ, เวลา และรายการแจ้งเตือน
- กด **ลบข้อมูลในเครื่อง** ในแอปเพื่อล้างประวัติทั้งหมด
- คะแนนนี้เป็นเครื่องมือช่วยปรับพฤติกรรม ไม่ใช่อุปกรณ์หรือคำวินิจฉัยทางการแพทย์

## อ่านเพิ่ม

- [Backend details](backend/README.md)
- [Frontend details](frontend/README.md)
- [Pi client](raspberrypi/README.md)
- [Database](database/README.md)
- [Docker](docker/README.md)
- [Docs index](docs/README.md)

## ขอบเขตเวอร์ชันนี้

เวอร์ชันนี้เหมาะกับการใช้งานบนเครื่องเดียว ข้อมูลไม่ซิงก์ข้ามเครื่องและ
ยังไม่มีระบบบัญชีผู้ใช้ หากต้องการเปิดใช้งานหลายคนหรือออนไลน์สาธารณะ
ควรเพิ่ม authentication, HTTPS, database server, backup และนโยบายสิทธิ์
ข้อมูลก่อนนำขึ้น public internet
