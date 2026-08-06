# PostureAI

PostureAI คือระบบติดตามท่านั่งสำหรับพื้นที่ทำงาน โดยใช้ Raspberry Pi 5 และกล้องที่เชื่อมต่อกับ Pi ตรวจวิเคราะห์ท่าทางแบบต่อเนื่อง แล้วแสดงผลบน dashboard ภายในเครือข่ายเดียวกัน

ระบบประเมินตำแหน่งคอ ไหล่ และลำตัว เพื่อสร้างคะแนนท่านั่งและแจ้งเตือนเมื่อพบความเสี่ยงจากการนั่งผิดท่าต่อเนื่อง เหมาะสำหรับใช้เป็นเครื่องมือช่วยปรับพฤติกรรม ไม่ใช่อุปกรณ์หรือซอฟต์แวร์สำหรับวินิจฉัยทางการแพทย์

## สิ่งที่ระบบทำได้

- รับภาพสดจาก Pi Camera ผ่าน WebRTC ในเครือข่ายภายใน
- วิเคราะห์ landmark ของร่างกายด้วย MediaPipe Pose บน Raspberry Pi
- แสดงคะแนนท่านั่ง, คอเอียง, ไหล่ไม่สมดุล และแนวลำตัวบน dashboard
- แจ้งเตือนผ่านเสียงบน Pi, ไฟ LED และการแจ้งเตือนบนหน้าเว็บตามค่าที่ตั้งไว้
- บันทึกเฉพาะคะแนน ตัวชี้วัด เวลา และเหตุการณ์แจ้งเตือนลง SQLite
- ดูสถิติย้อนหลัง ปรับค่าเกณฑ์ความเสี่ยง และ export ข้อมูลเป็น CSV หรือ JSON (เก็บสูงสุด 30 วัน)
- ทำงานต่อได้เมื่อ backend หลุดชั่วคราวด้วย SQLite buffer บน Pi
- เลือกใช้ Roboflow เพื่อจำแนกท่าทางเพิ่มเติมได้

## ภาพรวมระบบ

```text
Pi Camera
   │
   ▼
Raspberry Pi 5
  ├─ MediaPipe Pose วิเคราะห์ภาพภายในอุปกรณ์
  ├─ แจ้งเตือนเสียง / LED
  ├─ ส่ง video stream ตรงไปยัง Dashboard ผ่าน WebRTC
  └─ ส่งคะแนนและเหตุการณ์ไปยัง Backend
                                      │
                                      ▼
                         FastAPI + SQLite
                                      │
                                      ▼
                         Dashboard บนเว็บเบราว์เซอร์
```

ภาพจากกล้องเดินทางระหว่าง Pi และ dashboard ผ่าน WebRTC และไม่ได้ถูกบันทึกลงฐานข้อมูล ส่วน backend เก็บเฉพาะข้อมูลผลการวิเคราะห์และการแจ้งเตือน

> หากเปิด `roboflow.enabled` ระบบจะส่งภาพตัวอย่างไปยังบริการ Roboflow Cloud เพื่อรับผลการจำแนกเพิ่ม จึงควรเปิดใช้เฉพาะเมื่อได้รับอนุญาตตามนโยบายความเป็นส่วนตัวขององค์กร

## องค์ประกอบของโปรเจ็กต์

| โฟลเดอร์ | หน้าที่ |
| --- | --- |
| `frontend/` | Dashboard แบบ Vite + Vanilla JavaScript สำหรับดูภาพสด คะแนน สถิติ และตั้งค่าระบบ |
| `backend/` | FastAPI API, WebRTC signaling และ SQLite persistence |
| `raspberrypi/` | Pi client สำหรับกล้อง การวิเคราะห์ MediaPipe การแจ้งเตือน และ offline buffer |
| `database/` | ตำแหน่งเก็บ SQLite ของระบบเมื่อใช้งานผ่าน Docker |
| `docker/` | Dockerfile และ Nginx configuration |
| `docs/` | คู่มือติดตั้ง Pi และเอกสารออกแบบ |

## เริ่มต้นใช้งานด้วย Docker

ต้องมี Docker Compose v2 (คำสั่ง `docker compose`) หากบน Pi ขึ้นหน้า `Usage: docker ...`
ให้รัน `sudo apt update && sudo apt install -y docker-compose-v2` หรือใช้
`raspberrypi/setup-pi5.sh` ซึ่งติดตั้งและตรวจสอบให้เอง

```bash
umask 077
printf 'POSTUREAI_ADMIN_TOKEN=%s\n' "$(openssl rand -hex 32)" > .env
chmod 600 .env
docker compose up --build
```

หลัง service พร้อมใช้งาน:

| บริการ | ที่อยู่ |
| --- | --- |
| Dashboard | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| API documentation | `http://localhost:8000/docs` |

ข้อมูล SQLite จะถูกเก็บใน `database/` ของโปรเจ็กต์

Dashboard ที่ `:3000` เปิดจากอุปกรณ์ใน LAN ได้ ส่วน API `:8000` ถูกจำกัดไว้ที่ Pi
เพื่อไม่ให้เรียก endpoint โดยตรงจากเครื่องอื่น การบันทึกค่าและลบข้อมูลต้องกรอกรหัสผู้ดูแล
ที่ตั้งใน `POSTUREAI_ADMIN_TOKEN` ผ่าน dashboard

## พัฒนาแบบแยก service

### Backend

ต้องมี Python 3.12 ขึ้นไป

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app
```

Backend จะทำงานที่ `http://localhost:8000`

### Frontend

ต้องมี Node.js 22 ขึ้นไป

```bash
cd frontend
npm install
npm run dev
```

เปิด dashboard ที่ `http://localhost:5173` โดย Vite จะส่งต่อ `/api` ไปยัง backend ในเครื่องตามค่าเริ่มต้น

## ตั้งค่า Raspberry Pi 5

Pi client ต้องติดตั้ง Python dependencies, MediaPipe model และตั้งค่าการเชื่อมต่อกับ backend ก่อนเริ่มใช้จริง

```bash
cd raspberrypi
./setup-sensor-pi5.sh
cp config.example.yaml config.yaml
# แก้ backend_url และค่ากล้องใน config.yaml ให้ตรงกับระบบ
.venv/bin/python posture_client.py --config config.yaml --check
.venv/bin/python posture_client.py --config config.yaml
```

ดูรายละเอียดการต่อกล้อง การตั้งค่าเสียง และ LED ได้ที่ [คู่มือ Raspberry Pi](raspberrypi/README.md)

## การทดสอบ

### Frontend

```bash
cd frontend
npm test
```

### Backend

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

### Raspberry Pi client

```bash
cd raspberrypi
pytest
```

## API โดยย่อ

| กลุ่ม | Endpoint |
| --- | --- |
| สถานะระบบ | `GET /api/health` |
| การตั้งค่า | `GET`, `PUT /api/settings` |
| ข้อมูลท่านั่ง | `POST /api/samples`, `GET /api/summary`, `GET /api/stats` |
| การแจ้งเตือน | `POST /api/alerts` |
| ส่งออก/ลบข้อมูล | `GET /api/export`, `DELETE /api/data` |
| สถานะกล้อง | `GET /api/camera/status` |
| WebRTC signaling | `WS /api/camera/webrtc` |

รายละเอียด request และ response ดูได้จาก Swagger UI ที่ `/docs` เมื่อรัน backend

## เอกสารเพิ่มเติม

- [Frontend](frontend/README.md)
- [Backend](backend/README.md)
- [Raspberry Pi 5 client](raspberrypi/README.md)
- [Docker](docker/README.md)
- [Database](database/README.md)
- [เอกสารและคู่มือเพิ่มเติม](docs/README.md)

## ความเป็นส่วนตัวและข้อควรระวัง

- MediaPipe ประมวลผล landmark บน Raspberry Pi และไม่จัดเก็บวิดีโอลง SQLite
- Dashboard และ Pi ควรอยู่ในเครือข่ายที่เชื่อถือได้; ผู้ดูแลต้องใช้รหัสผ่านเพื่อแก้การตั้งค่าหรือลบข้อมูล และระบบนี้ยังไม่รองรับการเปิดใช้งานบนอินเทอร์เน็ตสาธารณะ
- คะแนนท่านั่งเป็นข้อมูลช่วยติดตามและปรับพฤติกรรมเท่านั้น ไม่ใช่ผลวินิจฉัยทางการแพทย์
