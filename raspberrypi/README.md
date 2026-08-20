# OffSyn Tech — Raspberry Pi Client

Lightweight Python client ที่รันบน Raspberry Pi เพื่อตรวจจับท่านั่งผ่านกล้อง USB หรือ Pi Camera
โดยใช้ **MediaPipe Pose Landmarker Full** วาด skeleton และประเมินคอ ไหล่ และการค่อม/บิดของช่วงบน
โดยไม่ใช้สะโพกหรือขาในการให้คะแนน ก่อนส่งผลไปเก็บที่ backend

## โครงสร้าง

- `posture_client.py` — main loop: เปิดกล้อง, ประมวลผล pose, ส่ง
  `POST /api/samples` ไป backend
- `requirements.txt` — OpenCV, MediaPipe, ONNX Runtime และ requests
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

สคริปต์จะดาวน์โหลด MediaPipe model (และ Kanden ONNX ตัวเลือกเสริม),
ตรวจ MediaPipe, กล้อง และ backend ก่อนจบงาน แล้วแสดง URL สำหรับเปิด
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

ติดตั้งตัวเล่นเสียงและเสียงพูดภาษาไทยของ Pi OS (สคริปต์ `setup-pi5.sh` ติดตั้งให้อัตโนมัติ):

```bash
sudo apt-get install -y alsa-utils espeak-ng
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
เมื่อเปิด **เสียงพูดภาษาไทย** จาก dashboard ระบบใช้ `espeak-ng` พูดว่า
“กรุณาปรับท่านั่งให้หลังตรงและคลายไหล่” ผ่านลำโพงเดียวกันหลังเสียง beep. ทดสอบได้ด้วย:

```bash
cd ~/off/raspberrypi
.venv/bin/python posture_client.py --config config.yaml --test-voice
```

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
  active_high: false
  threshold: 50
```

ทดสอบก่อนใช้งานจริงด้วย `python posture_client.py --config config.yaml --test-led`.
LED ที่ physical Pin 11 (BCM GPIO17) จะเป็น LOW และติดค้างทันทีเมื่อคะแนนต่ำกว่า **50** จากนั้น
เป็น HIGH และดับทันทีเมื่อคะแนนตั้งแต่ 50 หรือไม่พบ pose โดยไม่ต้องรอเสียงแจ้งเตือน.

## คำสั่งตรวจสอบแบบ manual

```bash
python posture_client.py --config config.yaml
```

ตรวจทั้ง MediaPipe, กล้อง และ backend โดยไม่ส่ง sample:

```bash
.venv/bin/python posture_client.py --config config.yaml --check
```

## คะแนนจากช่วงบนของร่างกาย

ค่าเริ่มต้น `detection.score_source: upper_body` ใช้เพียงจมูก/หู/ไหล่: คอที่โน้มหรือเอียง,
ไหล่สูงต่ำ และแนวโน้มโน้มหน้า/เอนหลังจากการเปลี่ยนความลึกเทียบกับท่านั่งตรงของคนเดิม จึงยังทำงานได้
เมื่อโต๊ะบังสะโพกและขา. หลังเริ่ม service ให้นั่งตรงและนิ่งราว 2 วินาทีเพื่อให้ระบบสร้างค่า
อ้างอิงส่วนตัว. กล้อง RGB ด้านหน้าไม่สามารถวัดความโค้งกระดูกสันหลังจริงได้ ค่านี้จึงใช้ช่วย
ปรับพฤติกรรม ไม่ใช่การวินิจฉัย. การหักคะแนนไหล่มีเพดาน เพื่อไม่ให้กล้องเอียงหรือ landmark
แกว่งเพียงค่าเดียวทำให้คะแนนเป็นศูนย์ตลอด.

Kanden ONNX ยังคงเป็นทางเลือกสำหรับทดลองจำแนกภาพทั้งเฟรม แต่ไม่เปิดใช้และไม่ทับคะแนน
ตามค่าเริ่มต้น. หากต้องการใช้เอง ให้เปิดทั้งสองค่า:

```yaml
detection:
  score_source: image_classifier
posture_classifier:
  enabled: true
```

## โหมดทำงาน

1. **Live camera pipeline**: Pi Camera จับภาพต่อเนื่องหนึ่งชุดที่ 640×360 / 12 FPS
   ในหน่วยความจำเท่านั้น แล้วส่งเป็น WebRTC ไปยัง dashboard ใน LAN (ไม่มีการบันทึกภาพลงดิสก์)
   Pi client ขอภาพใน byte order `RGB` จาก Picamera2 แล้วส่งต่อเป็น `RGB3`
   (24-bit RGB) เข้า MediaPipe และหน้าเว็บตั้งแต่ต้นทาง จึงไม่สลับสีแดง/น้ำเงิน.
2. **Local detection**: MediaPipe Pose Landmarker Full วิเคราะห์ frame ล่าสุดทุก 0.1 วินาที
   (10 FPS) เพื่อหา skeleton แล้วคำนวณจากศีรษะและไหล่เท่านั้น → POST เฉพาะคะแนนไป backend
   และส่งเฉพาะพิกัด landmark สำคัญไปวาด
   เส้นทับบน dashboard (ไม่ส่งหรือบันทึกภาพเพิ่ม)
3. **Local sound, Thai voice + alert forwarding**: เมื่อ score ต่ำกว่า `risk.threshold`
   จะเล่นเสียง beep ตามด้วยเสียงพูดไทย และ POST `/api/alerts` ทันทีเมื่อ `risk.seconds` เป็น `0` โดยเว้นช่วง
   การแจ้งซ้ำตาม `risk.cooldown` (ตั้งค่าเวลาหน่วงได้จากหน้าเว็บ)
4. **Offline buffer**: ถ้า backend ไม่ตอบ จะเก็บ samples ใน
   `buffer.sqlite` แล้วยิงใหม่เมื่อกลับมา online

บริการ `postureai-sensors.service` ถูก enable ให้เริ่มพร้อมระบบทุกครั้งที่เปิด Pi,
ใช้ HTTP connection pool เดิมและปิด response ทุกครั้งเพื่อไม่ให้ socket สะสม หาก backend
ยังเริ่มไม่เสร็จ client จะ retry แบบหน่วงสูงสุด 10 วินาที และ systemd จะ restart ให้อัตโนมัติ
หากโปรเซสหยุดทำงาน.

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
