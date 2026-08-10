# OfficeGuardian AI: BH1750

คู่มือนี้ครอบคลุมเซนเซอร์ I2C BH1750 สำหรับวัดความสว่างเป็น Lux ไม่มีการเปิดใช้กล้อง, AI, เว็บ, database หรือระบบแจ้งเตือน

## Wiring

ใช้ I2C bus 1 ของ Raspberry Pi 5 และไฟเลี้ยง 3.3V:

| Signal | Raspberry Pi 5 |
| --- | --- |
| VCC | Pin 1 (3.3V) |
| GND | Pin 6 หรือ Pin 9 (GND) |
| SDA | Pin 3 (GPIO 2 / SDA1) |
| SCL | Pin 5 (GPIO 3 / SCL1) |

โดยปกติ BH1750 อยู่ที่ I2C address `0x23` หรือ `0x5C`

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

ตาราง I2C ควรแสดง `23` หรือ `5c` สำหรับ BH1750

## Run

~~~bash
cd ~/off/raspberrypi
.venv/bin/python test_bh1750.py
.venv/bin/python test_sensors.py
~~~

ทุก script อ่านค่าทุก 1 วินาทีและหยุดด้วย Ctrl+C. หากใช้ address อื่น:

~~~bash
.venv/bin/python test_bh1750.py --address 0x5c
.venv/bin/python test_sensors.py --bh1750-address 0x5c
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

หน้า dashboard จะแสดงค่า BH1750 จาก endpoint `/api/sensors/latest` โดยข้อมูลอยู่ใน memory
ของ backend เท่านั้นและไม่บันทึกลง database. หาก backend อยู่คนละเครื่อง ให้เปลี่ยน backend URL เป็น
`http://IP-ของ-backend:8000`

## Expected output

~~~text
[14:20:01]
Lux: 423.5
Status: OK
~~~

ถ้าถอดสายหรือ I2C อ่านไม่ได้ script จะไม่หยุดทำงาน และรายงาน `BH1750: SENSOR ERROR`
ก่อนพยายามเชื่อมต่อใหม่ในรอบถัดไป

## Hardware validation

1. บัง/ส่องไฟที่ BH1750; ค่า Lux ต้องเปลี่ยนในรอบถัดไป
2. ถอด sensor ระหว่างที่ script ทำงาน; script ต้องแสดง error ต่อเนื่องโดยไม่ crash
3. ต่อ sensor กลับ; ค่าอ่านต้องกลับมาเองโดยไม่ต้อง restart script

หากไม่พบ sensor ให้ตรวจสาย VCC/GND/SDA/SCL และ output ของ `sudo i2cdetect -y 1`.
หากไม่พบ `/dev/i2c-1` ให้ตรวจว่าเปิด I2C แล้วและ reboot เรียบร้อย
