# PostureAI — Raspberry Pi Client

Lightweight Python client ที่รันบน Raspberry Pi เพื่อตรวจจับท่านั่ง (pose)
ด้วย **MediaPipe Pose Landmarker Full** ผ่านกล้อง USB หรือ Pi Camera แล้วส่งคะแนนไปเก็บที่ backend

## โครงสร้าง

- `posture_client.py` — main loop: เปิดกล้อง, ประมวลผล pose, ส่ง
  `POST /api/samples` ไป backend
- `requirements.txt` — OpenCV, MediaPipe (Python), requests
- `config.example.yaml` — backend URL, camera index, send interval, risk
  thresholds

## ติดตั้งแบบพร้อมใช้งานบน Pi 5

รองรับ **Raspberry Pi OS 64-bit Bookworm** และ Pi Camera ผ่าน CSI โดยตรง
หลังติดตั้ง Pi จะรันเว็บ, backend, ตรวจท่า และเสียงแจ้งเตือนเองหลัง reboot

```bash
git clone <repository-url> postureai
cd postureai
chmod +x raspberrypi/setup-pi5.sh
./raspberrypi/setup-pi5.sh
```

สคริปต์จะตรวจ MediaPipe, กล้อง และ backend ก่อนจบงาน แล้วแสดง URL สำหรับเปิด
จากอุปกรณ์ในเครือข่ายเดียวกัน เช่น `http://192.168.x.x:3000`

ตรวจสถานะหรือ log:

```bash
sudo systemctl status postureai-stack postureai-client
sudo journalctl -u postureai-client -f
```

หากต้องการติดตั้งเฉพาะกล้อง/เซนเซอร์ (ไม่ติดตั้ง Docker หรือหน้าเว็บ):

```bash
cd raspberrypi
./setup-sensor-pi5.sh
.venv/bin/python posture_client.py --config config.yaml --test-camera -v
```

ติดตั้งแบบ manual:

```bash
sudo apt-get install -y python3-picamera2 libatlas-base-dev
cd raspberrypi
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # แล้วแก้ค่าให้ตรงกับเครื่อง
```

ติดตั้งตัวเล่นเสียงของ Pi OS (สคริปต์ `setup-pi5.sh` ติดตั้งให้อัตโนมัติ):

```bash
sudo apt-get install -y alsa-utils
```

## ทดสอบเสียงก่อนเปิดกล้อง

ต่อ USB speaker / ลำโพง HDMI / ช่องเสียงที่ต้องการ แล้วรัน:

```bash
cd raspberrypi
source .venv/bin/activate
python posture_client.py --config config.yaml --test-sound
```

ถ้าไม่ได้ยินเสียง ให้ดูอุปกรณ์ด้วย `aplay -L` แล้วนำชื่อมาใส่ที่
`sound.device` ใน `config.yaml` จากนั้นเช็กระดับเสียงด้วย `alsamixer`.
หากมีไฟล์เสียงของตัวเอง ให้ใช้ไฟล์ WAV และกำหนด path ที่ `sound.file`;
เมื่อเว้นว่าง ระบบจะสร้างเสียง beep สองจังหวะให้เอง

## คำสั่งตรวจสอบแบบ manual

```bash
python posture_client.py --config config.yaml
```

ตรวจทั้ง MediaPipe, กล้อง และ backend โดยไม่ส่ง sample:

```bash
.venv/bin/python posture_client.py --config config.yaml --check
```

## โหมดทำงาน

1. **Local detection**: ทุก N วินาทีจับ frame → MediaPipe Pose Landmarker Full → คำนวณ score
   (คล้าย logic ใน `frontend/app.js`) → POST ไป backend
2. **Local sound + alert forwarding**: เมื่อ score ต่ำกว่า `risk.threshold`
   ต่อเนื่องเกิน `risk.seconds` จะเล่นเสียงและ POST `/api/alerts` โดยเว้นช่วง
   การแจ้งซ้ำตาม `risk.cooldown`
3. **Offline buffer**: ถ้า backend ไม่ตอบ จะเก็บ samples ใน
   `buffer.sqlite` แล้วยิงใหม่เมื่อกลับมา online

## หมายเหตุ

- `detection.mode` รองรับ `mediapipe` เท่านั้น และประมวลผลภาพบน Pi
- ถ้า MediaPipe เปิดไม่ได้ ระบบจะรายงาน error และไม่สร้างคะแนนจำลอง

## ดูภาพจาก Pi Camera บนอุปกรณ์อื่น

หลัง postureai-client ทำงาน ให้เปิด http://&lt;IP-Pi&gt;:3000 จากมือถือหรือคอมพิวเตอร์
ที่อยู่ในเครือข่ายเดียวกัน หน้าเว็บจะแสดงภาพล่าสุดจากกล้อง Pi อัตโนมัติ
โดยไม่ต้องอนุญาตกล้องของมือถือหรือคอมพิวเตอร์เครื่องนั้น

ภาพถูกส่งภายใน Pi ระหว่าง client และ backend และเก็บไว้ในหน่วยความจำเพียงภาพล่าสุด
เท่านั้น อย่าเปิดพอร์ต 3000 ออกสู่อินเทอร์เน็ตโดยไม่มี HTTPS และระบบยืนยันตัวตน
