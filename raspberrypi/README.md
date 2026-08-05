# PostureAI — Raspberry Pi Client

Lightweight Python client ที่รันบน Raspberry Pi เพื่อตรวจจับท่านั่ง (pose)
ด้วย **MediaPipe Pose Landmarker Full** ผ่านกล้อง USB หรือ Pi Camera แล้วส่งคะแนนไปเก็บที่ backend

## โครงสร้าง

- `posture_client.py` — main loop: เปิดกล้อง, ประมวลผล pose, ส่ง
  `POST /api/samples` ไป backend
- `requirements.txt` — OpenCV, MediaPipe (Python), requests
- `config.example.yaml` — backend URL, camera/video settings, AI rate, risk
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

## ไฟ LED สีแดงแจ้งเตือน

โมดูลในรูปเป็น LED module ไม่ใช่เซนเซอร์เสียง ใช้เป็นไฟเตือนเมื่อท่านั่งเสี่ยง
ต่อไฟเลี้ยงของโมดูลตามสกรีนบนบอร์ด และต่อขาสัญญาณ `IN` กับ **BCM GPIO17**
(physical pin 11) ของ Pi; ใช้ระดับสัญญาณ 3.3V เท่านั้น ห้ามป้อนไฟ 5V เข้าขา GPIO ของ Pi
หากบอร์ดมีขา `GND` ให้ต่อกับ GND ของ Pi ด้วย

เมื่อต่อสายแล้ว ตั้งค่าใน `config.yaml`:

```yaml
indicator:
  enabled: true
  pin: 17
  active_high: true
```

ทดสอบก่อนใช้งานจริงด้วย `python posture_client.py --config config.yaml --test-led`.
ระบบจะเปิด LED เมื่อคะแนนต่ำกว่าค่า `risk.threshold` ต่อเนื่องครบ `risk.seconds`
และจะปิดทันทีเมื่อคะแนนกลับมาปกติ. หากไฟทำงานกลับด้าน ให้ตั้ง `active_high: false`.

## คำสั่งตรวจสอบแบบ manual

```bash
python posture_client.py --config config.yaml
```

ตรวจทั้ง MediaPipe, กล้อง และ backend โดยไม่ส่ง sample:

```bash
.venv/bin/python posture_client.py --config config.yaml --check
```

## โหมดทำงาน

1. **Live camera pipeline**: Pi Camera จับภาพต่อเนื่องหนึ่งชุดที่ 640×360 / 12 FPS
   ในหน่วยความจำเท่านั้น แล้วส่งเป็น WebRTC ไปยัง dashboard ใน LAN (ไม่มีการบันทึกภาพลงดิสก์)
   Pi client ขอภาพใน byte order `RGB` จาก Picamera2 แล้วส่งต่อเป็น `RGB3`
   (24-bit RGB) เข้า MediaPipe และหน้าเว็บตั้งแต่ต้นทาง จึงไม่สลับสีแดง/น้ำเงิน.
2. **Local detection**: MediaPipe Pose Landmarker Full วิเคราะห์ frame ล่าสุดทุก 0.1 วินาที
   (10 FPS) → POST เฉพาะคะแนนไป backend และส่งเฉพาะพิกัด landmark สำคัญไปวาด
   เส้นทับบน dashboard (ไม่ส่งหรือบันทึกภาพเพิ่ม)
3. **Local sound + alert forwarding**: เมื่อ score ต่ำกว่า `risk.threshold`
   ต่อเนื่องเกิน `risk.seconds` จะเล่นเสียงและ POST `/api/alerts` โดยเว้นช่วง
   การแจ้งซ้ำตาม `risk.cooldown`
4. **Offline buffer**: ถ้า backend ไม่ตอบ จะเก็บ samples ใน
   `buffer.sqlite` แล้วยิงใหม่เมื่อกลับมา online

## AI เสริมจาก Roboflow (ทางเลือก)

ระบบหลักยังคงใช้ **MediaPipe Pose Landmarker Full บน Pi** เพื่อวาด skeleton,
คำนวณคะแนน และแจ้งเตือนโดยไม่ต้องใช้อินเทอร์เน็ต. หากต้องการให้หน้าเว็บแสดง
ผลจำแนกท่านั่งจากโมเดล Roboflow เพิ่มเติม ให้เปิด `roboflow.enabled: true` ใน
`config.yaml` และเก็บ API key ไว้นอก repository:

```bash
sudo install -d -m 700 /etc/postureai
sudo nano /etc/postureai/roboflow.env
```

ใส่เพียงบรรทัดนี้ในไฟล์ (แทนที่ด้วย key ของตนเอง):

```text
ROBOFLOW_API_KEY=your-key-here
```

จากนั้นจำกัดสิทธิ์และเพิ่ม environment ให้ service:

```bash
sudo chmod 600 /etc/postureai/roboflow.env
sudo systemctl edit postureai-client
```

ใส่:

```ini
[Service]
EnvironmentFile=/etc/postureai/roboflow.env
```

แล้วสั่ง `sudo systemctl daemon-reload` และ `sudo systemctl restart postureai-client`.
ผล Roboflow เป็นการส่งภาพตัวอย่างออกไปประมวลผลที่ cloud ทุก 1 วินาที จึงต้องให้
Pi ออกอินเทอร์เน็ตได้ และไม่ควรเปิดใช้หากนโยบายความเป็นส่วนตัวไม่อนุญาต.

## หมายเหตุ

- `detection.mode` รองรับ `mediapipe` เท่านั้น และประมวลผลภาพบน Pi
- WebRTC รองรับ dashboard หนึ่งเครื่องใน LAN พร้อมกัน; หากสตรีมขาด หน้าเว็บจะเชื่อมต่อใหม่อัตโนมัติ
- ถ้า MediaPipe เปิดไม่ได้ ระบบจะรายงาน error และไม่สร้างคะแนนจำลอง

## ดูภาพจาก Pi Camera บนอุปกรณ์อื่น

หลัง postureai-client ทำงาน ให้เปิด http://&lt;IP-Pi&gt;:3000 จากมือถือหรือคอมพิวเตอร์
ที่อยู่ในเครือข่ายเดียวกัน หน้าเว็บจะแสดงภาพล่าสุดจากกล้อง Pi อัตโนมัติ
โดยไม่ต้องอนุญาตกล้องของมือถือหรือคอมพิวเตอร์เครื่องนั้น

ภาพถูกส่งภายใน Pi ระหว่าง client และ backend และเก็บไว้ในหน่วยความจำเพียงภาพล่าสุด
เท่านั้น อย่าเปิดพอร์ต 3000 ออกสู่อินเทอร์เน็ตโดยไม่มี HTTPS และระบบยืนยันตัวตน
