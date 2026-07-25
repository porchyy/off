# PostureAI — Raspberry Pi Client

Lightweight Python client ที่รันบน Raspberry Pi เพื่อตรวจจับท่านั่ง (pose)
ด้วยกล้อง USB หรือ Pi Camera แล้วส่งคะแนนไปเก็บที่ backend

## โครงสร้าง

- `posture_client.py` — main loop: เปิดกล้อง, ประมวลผล pose, ส่ง
  `POST /api/samples` ไป backend
- `requirements.txt` — OpenCV, MediaPipe (Python), requests
- `config.example.yaml` — backend URL, camera index, send interval, risk
  thresholds

## ติดตั้งบน Pi

```bash
sudo apt-get install -y python3-picamera2 libatlas-base-dev
cd raspberrypi
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # แล้วแก้ค่าให้ตรงกับเครื่อง
```

## รัน

```bash
python posture_client.py --config config.yaml
```

## โหมดทำงาน

1. **Local detection**: ทุก N วินาทีจับ frame → MediaPipe Pose → คำนวณ score
   (คล้าย logic ใน `frontend/app.js`) → POST ไป backend
2. **Alert forwarding**: เมื่อ score ต่ำกว่า threshold ต่อเนื่องเกิน
   `riskSeconds` จะ POST `/api/alerts` ด้วย severity `risk` หรือ `caution`
3. **Offline buffer**: ถ้า backend ไม่ตอบ จะเก็บ samples ใน
   `buffer.sqlite` แล้วยิงใหม่เมื่อกลับมา online

## หมายเหตุ

- ตอนนี้ client เป็น skeleton — logic เต็มจะ map มาจาก MediaPipe
  thresholds ใน `frontend/app.js` ตอนพร้อม port
- ควรรันเป็น systemd service (`postureai-client.service`) เพื่อให้กลับมา
  ทำงานหลัง Pi reboot
