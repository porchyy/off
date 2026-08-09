# OfficeGuardian AI: BH1750 and TOF200C

คู่มือนี้ครอบคลุมเฉพาะเซนเซอร์ I2C สองตัว: BH1750 (Lux) และ TOF200C
(Distance เป็น cm) ไม่มีการเปิดใช้กล้อง, AI, เว็บ, database หรือระบบแจ้งเตือน

## Wiring

ใช้ I2C bus 1 ของ Raspberry Pi 5 และไฟเลี้ยง 3.3V:

| Signal | Raspberry Pi 5 |
| --- | --- |
| VCC | Pin 1 (3.3V) |
| GND | Pin 6 หรือ Pin 9 (GND) |
| SDA | Pin 3 (GPIO 2 / SDA1) |
| SCL | Pin 5 (GPIO 3 / SCL1) |

ต่อ BH1750 และ TOF200C บน SDA/SCL ชุดเดียวกันได้ เพราะใช้อุปกรณ์คนละ I2C address
โดยปกติ BH1750 อยู่ที่ 0x23 (หรือ 0x5C) และ TOF200C อยู่ที่ 0x29

## Setup

เปิด I2C จากนั้น reboot หนึ่งครั้ง:

~~~bash
sudo raspi-config
# Interface Options -> I2C -> Enable
sudo reboot
~~~

ติดตั้งเครื่องมือและ dependency เฉพาะ sensor:

~~~bash
sudo apt update
sudo apt install -y i2c-tools python3-venv
cd ~/off/raspberrypi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-sensors.txt
sudo i2cdetect -y 1
~~~

ตาราง I2C ควรแสดง 23 หรือ 5c สำหรับ BH1750 และ 29 สำหรับ TOF200C

## Run

~~~bash
cd ~/off/raspberrypi
.venv/bin/python test_bh1750.py
.venv/bin/python test_tof200c.py
.venv/bin/python test_sensors.py
~~~

ทุก script อ่านค่าทุก 1 วินาทีและหยุดด้วย Ctrl+C. หากใช้ address อื่น:

~~~bash
.venv/bin/python test_bh1750.py --address 0x5c
.venv/bin/python test_tof200c.py --address 0x30
.venv/bin/python test_sensors.py --bh1750-address 0x5c --tof200c-address 0x30
~~~

## Show values on the dashboard

เมื่อใช้ `setup-pi5.sh` ระบบจะสร้าง `postureai-sensors` service เพื่ออ่านและส่งค่า
ขึ้น dashboard ทุก 0.5 วินาทีโดยอัตโนมัติ รวมถึงหลัง reboot. ตรวจสถานะและ log ด้วย:

~~~bash
sudo systemctl status postureai-sensors
sudo journalctl -u postureai-sensors -f
~~~

หากติดตั้งแบบ manual และ backend/dashboard ทำงานอยู่บน Pi ให้รัน client นี้ใน terminal แยก:

~~~bash
cd ~/off/raspberrypi
.venv/bin/python sensor_web_client.py --backend-url http://localhost:8000 --interval 0.5
~~~

หน้า dashboard จะแสดงค่า BH1750 และ TOF200C พร้อมกันจาก endpoint
/api/sensors/latest โดยข้อมูลอยู่ใน memory ของ backend เท่านั้น
และไม่บันทึกลง database. หาก backend อยู่คนละเครื่อง ให้เปลี่ยน backend URL เป็น
http://IP-ของ-backend:8000

## Calibrate ค่า Lux

วาง BH1750 และเครื่องวัดอ้างอิงที่ตำแหน่ง/ทิศทางเดียวกัน แล้วหาค่าตัวคูณจาก
`ค่าอ้างอิง ÷ ค่า BH1750`. ตัวอย่าง เครื่องอ้างอิงอ่าน 400 Lux แต่ BH1750 อ่าน 100 Lux
ให้ใช้ calibration `4.0`. แก้ไฟล์บน Pi:

~~~bash
sudo nano /etc/default/postureai-sensors
~~~

กำหนดค่าและ restart service:

~~~text
POSTUREAI_LUX_CALIBRATION=4.0
~~~

~~~bash
sudo systemctl restart postureai-sensors
sudo journalctl -u postureai-sensors -f
~~~

ตัวติดตั้งจะเก็บค่า calibration เดิมไว้เมื่อรันซ้ำ และค่า Lux ที่ส่งขึ้น dashboard
จะเป็นค่าหลังคูณ calibration แล้ว.

## Expected output

~~~text
[14:20:01]
Lux: 423.5
Distance: 62.4 cm
Status: OK
~~~

ถ้าถอดสายหรือ I2C อ่านไม่ได้ script จะไม่หยุดทำงาน และรายงาน
BH1750: SENSOR ERROR, TOF200C: SENSOR ERROR, หรือค่า sensor error ใน test รวม
ก่อนพยายามเชื่อมต่อใหม่ในรอบถัดไป

## Hardware validation

1. บัง/ส่องไฟที่ BH1750; ค่า Lux ต้องเปลี่ยนในรอบถัดไป
2. ขยับวัตถุเข้า/ออกจาก TOF200C; ค่า Distance ต้องเปลี่ยนตามเป็น cm
3. ถอด sensor ทีละตัวระหว่างที่ script ทำงาน; script ต้องแสดง error ต่อเนื่องโดยไม่ crash
4. ต่อ sensor กลับ; ค่าอ่านต้องกลับมาเองโดยไม่ต้อง restart script

หากไม่พบ sensor ให้ตรวจสาย VCC/GND/SDA/SCL และ output ของ
sudo i2cdetect -y 1. หากไม่พบ /dev/i2c-1 ให้ตรวจว่าเปิด I2C แล้วและ reboot เรียบร้อย
