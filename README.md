<div align="center">

# 🧘 PostureAI — OfficeGuardian

**ระบบติดตามท่านั่งอัจฉริยะแบบ Local-First ด้วย AI**  
*Real-time posture monitoring powered by MediaPipe · Privacy-first · No cloud required*

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![Node.js](https://img.shields.io/badge/Node.js-22%2B-339933?style=for-the-badge&logo=node.js&logoColor=white)](https://nodejs.org)
[![Tests](https://img.shields.io/badge/Tests-22%2F22%20PASS-2ea44f?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com/porchyy/offf)
[![SQLite](https://img.shields.io/badge/SQLite-Local-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 📖 ภาพรวม

**PostureAI** คือแอปพลิเคชันตรวจสอบท่านั่งแบบ real-time บนเบราว์เซอร์  
ใช้ **MediaPipe Pose** วิเคราะห์จุดสำคัญบนร่างกายผ่านกล้อง โดยประมวลผลทั้งหมด **บนเครื่องของผู้ใช้**  
วิดีโอจากกล้อง **ไม่ถูกส่งออกไปยังเซิร์ฟเวอร์** และ **ไม่ถูกบันทึกลงดิสก์**

> 🔒 **Privacy-first**: ระบบเก็บเฉพาะคะแนน, มุมโดยประมาณ, เวลา และเหตุการณ์แจ้งเตือน ไว้ใน SQLite บนเครื่องคุณ

---

## ✨ ฟีเจอร์หลัก

| ฟีเจอร์ | รายละเอียด |
|---------|------------|
| 🎯 **วิเคราะห์ท่านั่งแบบ Real-time** | ใช้ MediaPipe Pose ตรวจจับ landmark บนร่างกาย คำนวณคะแนน 0–100 |
| 🔴 **Office Syndrome Risk** | แสดงระดับความเสี่ยงเป็นสี (เขียว/แดง) ตามคะแนนและเวลาที่นั่งผิดท่าต่อเนื่อง |
| 🔔 **แจ้งเตือนหลายช่องทาง** | Popup, เสียง Beep, Desktop Notification |
| ⚙️ **ตั้งค่าได้เอง** | ปรับ threshold คะแนนเสี่ยง, เวลาก่อนแจ้งเตือน, เปิด/ปิดเสียง |
| 📊 **กราฟสถิติ** | คะแนนเฉลี่ยรายวัน + แจ้งเตือนรายสัปดาห์ย้อนหลัง |
| 📤 **Export ข้อมูล** | ดาวน์โหลดประวัติเป็น CSV หรือ JSON |
| 🗑️ **ลบข้อมูลได้ทันที** | ปุ่มลบข้อมูลทั้งหมดในแอป |
| 🧪 **Unit Tests ครบถ้วน** | มีชุดทดสอบแบบอัตโนมัติ 22/22 Tests (Frontend + Backend) |
| 🍓 **Raspberry Pi Client** | Python client รองรับการทำงานบน Pi ด้วย OpenCV + MediaPipe |
| 🐳 **Docker Ready** | `docker compose up --build` พร้อมใช้งาน |

---

## 🏗️ โครงสร้างโปรเจกต์

```
OfficeGuardian-AI/
├── frontend/               # 🌐 Vite + Vanilla JS (port 5173)
│   ├── index.html          #    หน้าหลัก
│   ├── app.js              #    โลจิกหลัก + MediaPipe integration
│   ├── pose-utils.js       #    มอดูลคำนวณคะแนนและมุมท่าทาง
│   ├── storage.js          #    Backend API client wrapper + localStorage fallback
│   ├── app.css / risk.css  #    Styling
│   ├── tests/              #    🧪 Unit tests สำหรับ Frontend (node --test)
│   └── vite.config.js      #    Proxy /api → FastAPI backend
│
├── backend/                # ⚙️ FastAPI + SQLAlchemy (port 8000)
│   ├── app/
│   │   ├── main.py         #    FastAPI app + CORS + lifespan bootstrap + static serve
│   │   ├── routes.py       #    API routes ทั้งหมด
│   │   ├── config.py       #    pydantic-settings (env vars)
│   │   ├── models.py       #    SQLAlchemy ORM models
│   │   ├── schemas.py      #    Pydantic request/response schemas
│   │   ├── database.py     #    SQLite engine + session factory
│   │   ├── settings_store.py #  Default settings + upsert helper
│   │   └── export.py       #    CSV export helper
│   ├── tests/              #    🧪 Unit tests สำหรับ Backend (pytest)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── raspberrypi/            # 🍓 Python client สำหรับ Raspberry Pi
├── database/               # 🗄️ SQLite file (postureai.sqlite)
├── docker/                 # 🐳 Dockerfile + nginx.conf
├── docker-compose.yml
├── docs/                   # 📄 specs, wireframes, prototype
└── README.md
```

---

## 🚀 เริ่มใช้งาน

### วิธีที่ 1: Docker (แนะนำ)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

> SQLite ถูก mount ไว้ที่ `./database/postureai.sqlite` — ข้อมูลถาวร

---

### วิธีที่ 2: รันแบบ Dev (แยก Service)

> **ต้องมี:** Node.js 22+ และ Python 3.12+

#### ขั้นตอนที่ 1 — เริ่ม Backend

```powershell
# Windows (PowerShell)
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m app
```

```bash
# macOS / Linux
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app
```

✅ Backend พร้อมที่ → **http://localhost:8000**  
📖 Swagger UI → **http://localhost:8000/docs**

#### ขั้นตอนที่ 2 — เริ่ม Frontend

```bash
cd frontend
npm install
npm run dev
```

✅ Frontend พร้อมที่ → **http://localhost:5173**  
*(Vite จะ proxy `/api/*` ไปยัง `http://localhost:8000` อัตโนมัติ)*

---

## 🧪 การรันทดสอบ (Automated Testing)

โปรเจกต์นี้มีชุดทดสอบอัตโนมัติ (Unit Tests) ครอบคลุมทั้ง Frontend และ Backend:

```bash
# รัน Unit Tests ทั้งหมด (ทั้ง Frontend และ Backend)
npm test

# รันเฉพาะ Frontend Unit Tests (Node.js Native Test Runner)
npm run test:frontend

# รันเฉพาะ Backend Unit Tests (Pytest + FastAPI TestClient)
npm run test:backend
```

---

## 🔌 API Reference

| Method | Endpoint | คำอธิบาย |
|--------|----------|-----------|
| `GET` | `/api/health` | ตรวจสถานะ server + SQLite |
| `GET` | `/api/settings` | อ่านค่าตั้งค่าทั้งหมด |
| `PUT` | `/api/settings` | บันทึกค่าตั้งค่า |
| `POST` | `/api/samples` | บันทึกคะแนน posture รายครั้ง |
| `POST` | `/api/alerts` | บันทึกเหตุการณ์แจ้งเตือน |
| `GET` | `/api/summary` | สรุปข้อมูลวันนี้ (samples + alerts) |
| `GET` | `/api/stats` | ข้อมูลกราฟรายวัน/สัปดาห์ |
| `GET` | `/api/export?format=csv` | Export ข้อมูลเป็น CSV |
| `GET` | `/api/export?format=json` | Export ข้อมูลเป็น JSON |
| `DELETE` | `/api/data` | ลบข้อมูล samples + alerts ทั้งหมด |

> ดู interactive docs ได้ที่ **http://localhost:8000/docs** เมื่อรัน backend

---

## ⚙️ Environment Variables

| Variable | Default | คำอธิบาย |
|----------|---------|-----------|
| `POSTUREAI_DATA_DIR` | `./database` | ตำแหน่งไฟล์ SQLite |
| `POSTUREAI_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins |
| `POSTUREAI_HOST` | `0.0.0.0` | Bind address |
| `POSTUREAI_PORT` | `8000` | HTTP port |

---

## 🔒 ความเป็นส่วนตัว (Privacy)

- ✅ AI pose detection ทำงานใน **browser** ของผู้ใช้เท่านั้น
- ✅ วิดีโอจากกล้อง **ไม่ถูกส่งออก** ไปยัง server ใดๆ
- ✅ ไม่มีการบันทึกวิดีโอลงดิสก์
- ✅ Server บันทึกเฉพาะ: คะแนน, มุมโดยประมาณ, เวลา, รายการแจ้งเตือน
- ✅ ลบข้อมูลได้ทุกเมื่อจากปุ่ม **"ลบข้อมูลในเครื่อง"** ในแอป

> ⚕️ **คำเตือน:** คะแนนที่แสดงเป็นเครื่องมือช่วยปรับพฤติกรรมเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์

---

## 🛠️ Tech Stack

| ชั้น | เทคโนโลยี | เวอร์ชัน |
|------|-----------|---------|
| Frontend Framework | Vite | 5.4 |
| AI / Pose Detection | MediaPipe Pose | 0.10 |
| Backend Framework | FastAPI | 0.115 |
| ASGI Server | Uvicorn | 0.32 |
| ORM | SQLAlchemy | 2.0 |
| Testing (Frontend) | Node Test Runner | Node 22+ |
| Testing (Backend) | Pytest + TestClient | 8.3 |
| Database | SQLite (local) | — |
| Python Runtime | Python | 3.12+ |
| Node.js Runtime | Node.js | 22+ |
| Container | Docker + Compose | — |

---

## 📚 เอกสารเพิ่มเติม

- [Backend — FastAPI details](backend/README.md)
- [Frontend — Vite setup](frontend/README.md)
- [Raspberry Pi client](raspberrypi/README.md)
- [Database schema](database/README.md)
- [Docker setup](docker/README.md)
- [Project docs](docs/README.md)

---

<div align="center">

Made with ❤️ for healthier workdays · **PostureAI / OfficeGuardian**

</div>
