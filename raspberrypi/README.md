# PostureAI — Raspberry Pi Client

Lightweight Python client ที่รันบน Raspberry Pi เพื่อตรวจจับท่านั่งด้วย
**YOLOv5** ผ่านกล้อง USB หรือ Pi Camera แล้วส่งผล `sitting_good` / `sitting_bad` ไปยัง backend

## โครงสร้าง

- `posture_client.py` — main loop: เปิดกล้อง, ประมวลผล pose, ส่ง
  `POST /api/samples` ไป backend
- `requirements.txt` — OpenCV, requests และ dependencies พื้นฐาน
- `requirements-yolov5.txt` — PyTorch และ YOLOv5 runtime
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

สคริปต์จะติดตั้ง YOLOv5, ดาวน์โหลดโมเดล, ตรวจกล้อง และ backend ก่อนจบงาน แล้วแสดง URL สำหรับเปิด
จากอุปกรณ์ในเครือข่ายเดียวกัน เช่น `http://192.168.x.x:3000` พร้อมสร้างรหัสผู้ดูแล
แบบสุ่มไว้ที่ `<project>/.env` (permission `600`) สำหรับใช้เมื่อบันทึกการตั้งค่าหรือลบข้อมูล
บน dashboard; ดูค่าเมื่อต้องใช้ด้วย `grep POSTUREAI_ADMIN_TOKEN ../.env` จากโฟลเดอร์ `raspberrypi/`

ตรวจสถานะหรือ log:

```bash
sudo systemctl status postureai-stack postureai-client postureai-sensors
sudo journalctl -u postureai-client -f
sudo journalctl -u postureai-sensors -f
```

ตัวติดตั้งจะเปิด I2C และสร้าง `postureai-sensors` service สำหรับอ่าน BH1750
แล้วส่งค่าล่าสุดไปยัง dashboard ทุก 0.5 วินาทีโดยอัตโนมัติ รวมถึงหลัง reboot.
หากตัวติดตั้งหลักหยุดก่อนขั้นสร้าง service (เช่น Docker หรือกล้องยังไม่พร้อม)
สามารถติดตั้งเฉพาะ service เซนเซอร์ได้ด้วย:

```bash
chmod +x raspberrypi/install-sensor-service.sh
./raspberrypi/install-sensor-service.sh
sudo reboot
```

ค่าเกณฑ์ความเสี่ยงและเสียงที่บันทึกจาก dashboard จะถูก client ดึงมาใช้ภายใน 30 วินาที
หาก backend หลุด client จะใช้ค่าล่าสุด/ค่าจาก `config.yaml` ต่อไป และ dashboard จะแสดง
สถานะการ sync ของ Pi ในหน้า Settings

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

## เสียงแจ้งเตือนผ่าน MAX98357A I2S เท่านั้น

ระบบชุดนี้ใช้โมดูล **MAX98357A I2S 3W Class-D amplifier พร้อมลำโพง** เป็นเสียงจาก Pi
โดยไม่ใช้ GPIO buzzer, USB audio หรือ HDMI audio. ปิด Raspberry Pi และถอดไฟก่อนต่อสาย:

| MAX98357A | Raspberry Pi 5 |
|---|---|
| VIN | Pin 2 (5V) |
| GND | Pin 6 (GND) |
| BCLK | Pin 12 (GPIO18) |
| LRC | Pin 35 (GPIO19) |
| DIN | Pin 40 (GPIO21) |
| SD | Pin 7 (GPIO4) |

ต่อลำโพงเข้าขั้ว `SPK+` และ `SPK-` ของโมดูลเท่านั้น ห้ามต่อขั้วลำโพงข้างใดข้างหนึ่ง
ลง GND จากนั้นติดตั้ง I2S overlay และตั้ง MAX98357A เป็น ALSA output หลัก:

```bash
cd ~/off
chmod +x raspberrypi/setup-max98357.sh
./raspberrypi/setup-max98357.sh
sudo reboot
```

หลัง reboot ตรวจว่าระบบพบการ์ด `MAX98357A` แล้วทดสอบเสียง:

```bash
aplay -l | grep -i MAX98357A
speaker-test -D plughw:CARD=MAX98357A,DEV=0 -c 2 -t sine -f 880 -l 1
cd ~/off/raspberrypi
.venv/bin/python posture_client.py --config config.yaml --test-sound
```

ปล่อยขา `GAIN` ว่างเพื่อใช้ค่า gain เริ่มต้นของบอร์ด สคริปต์ใช้ overlay ทางการ
`dtoverlay=max98357a,sdmode-pin=4` และกำหนด
`sound.device` เป็น `plughw:CARD=MAX98357A,DEV=0` จึงไม่อ้างอิงหมายเลข card
ที่อาจเปลี่ยนหลัง reboot. เมื่อ `sound.file` ว่าง ระบบจะสร้างเสียง beep สองจังหวะให้เอง.

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
  # เว้นว่างเพื่อให้ตรวจหา GPIO ของ Pi 5 อัตโนมัติ
  chip:
  active_high: true
  threshold: 50
```

ทดสอบก่อนใช้งานจริงด้วย `python posture_client.py --config config.yaml --test-led`.
LED จะติดทันทีเมื่อคะแนนต่ำกว่า `indicator.threshold` และจะปิดทันทีเมื่อคะแนนกลับมาถึงเกณฑ์
โดยไม่ต้องรอเวลาการแจ้งเตือนเสียง. หากไฟทำงานกลับด้าน ให้ตั้ง `active_high: false`.

## คำสั่งตรวจสอบแบบ manual

```bash
python posture_client.py --config config.yaml
```

ตรวจทั้ง YOLOv5, กล้อง และ backend โดยไม่ส่ง sample:

```bash
.venv/bin/python posture_client.py --config config.yaml --check
```

## โหมดทำงาน

1. **Live camera pipeline**: Pi Camera จับภาพต่อเนื่องหนึ่งชุดที่ 640×360 / 12 FPS
   ในหน่วยความจำเท่านั้น แล้วส่งเป็น WebRTC ไปยัง dashboard ใน LAN (ไม่มีการบันทึกภาพลงดิสก์)
   Pi client ขอภาพใน byte order `RGB` จาก Picamera2 แล้วส่งต่อเป็น `RGB3`
   (24-bit RGB) เข้า YOLOv5 โดยไม่สลับสีแดง/น้ำเงิน.
2. **Local detection**: YOLOv5s `small640.pt` จากโปรเจกต์
   `itakurah/Sitting-Posture-Detection-YOLOv5` วิเคราะห์ frame ล่าสุดทุก 0.5 วินาที
   และจำแนก `sitting_good` หรือ `sitting_bad` บน Pi (ไม่ส่งภาพออกอินเทอร์เน็ต).
3. **Local sound + alert forwarding**: เมื่อ score ต่ำกว่า `risk.threshold`
   จะเล่นเสียงและ POST `/api/alerts` ทันทีเมื่อ `risk.seconds` เป็น `0` โดยเว้นช่วง
   การแจ้งซ้ำตาม `risk.cooldown` (ตั้งค่าเวลาหน่วงได้จากหน้าเว็บ)
4. **Offline buffer**: ถ้า backend ไม่ตอบ จะเก็บ samples ใน
   `buffer.sqlite` แล้วยิงใหม่เมื่อกลับมา online

บริการ `postureai-sensors.service` ถูก enable ให้เริ่มพร้อมระบบทุกครั้งที่เปิด Pi,
ใช้ HTTP connection pool เดิมและปิด response ทุกครั้งเพื่อไม่ให้ socket สะสม หาก backend
ยังเริ่มไม่เสร็จ client จะ retry แบบหน่วงสูงสุด 10 วินาที และ systemd จะ restart ให้อัตโนมัติ
หากโปรเซสหยุดทำงาน.

## AI เสริมจาก Roboflow (ทางเลือก)

ระบบหลักใช้ **YOLOv5 sitting-posture model บน Pi** เพื่อจำแนกท่านั่งและแจ้งเตือน
โดยไม่ต้องใช้อินเทอร์เน็ต. หากต้องการให้หน้าเว็บแสดง
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

- `detection.mode` รองรับ `yolov5` เท่านั้น และประมวลผลภาพบน Pi
- WebRTC รองรับ dashboard หนึ่งเครื่องใน LAN พร้อมกัน; หากสตรีมขาด หน้าเว็บจะเชื่อมต่อใหม่อัตโนมัติ
- ถ้า YOLOv5 เปิดไม่ได้ ระบบจะรายงาน error และไม่สร้างคะแนนจำลอง

## ดูภาพจาก Pi Camera บนอุปกรณ์อื่น

หลัง postureai-client ทำงาน ให้เปิด http://&lt;IP-Pi&gt;:3000 จากมือถือหรือคอมพิวเตอร์
ที่อยู่ในเครือข่ายเดียวกัน หน้าเว็บจะแสดงภาพล่าสุดจากกล้อง Pi อัตโนมัติ
โดยไม่ต้องอนุญาตกล้องของมือถือหรือคอมพิวเตอร์เครื่องนั้น

ภาพถูกส่งภายใน Pi ระหว่าง client และ backend และเก็บไว้ในหน่วยความจำเพียงภาพล่าสุด
เท่านั้น อย่าเปิดพอร์ต 3000 ออกสู่อินเทอร์เน็ตโดยไม่มี HTTPS และระบบยืนยันตัวตน
