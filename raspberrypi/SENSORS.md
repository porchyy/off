# OfficeGuardian AI: BH1750 + TOF400C

คู่มือนี้ครอบคลุม BH1750 สำหรับวัดความสว่างเป็น Lux และ TOF400C สำหรับวัดระยะเป็นเซนติเมตร ทั้งสองใช้ I2C bus 1 ของ Pi 5

## Wiring

ใช้ I2C bus 1 ของ Raspberry Pi 5 และไฟเลี้ยง 3.3V:

| Signal | Raspberry Pi 5 |
| --- | --- |
| VCC | Pin 1 (3.3V) |
| GND | Pin 6 หรือ Pin 9 (GND) |
| SDA | Pin 3 (GPIO 2 / SDA1) |
| SCL | Pin 5 (GPIO 3 / SCL1) |

โดยปกติ BH1750 อยู่ที่ I2C address `0x23` หรือ `0x5C`

TOF400C ใช้สายเดียวกัน: VCC ไป Pin 1 (3.3V), GND ไป Pin 6, SDA ไป Pin 3 และ SCL ไป Pin 5 โดยปกติอยู่ที่ I2C address `0x29`.

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
และ `29` สำหรับ TOF400C

## Run

~~~bash
cd ~/off/raspberrypi
.venv/bin/python test_bh1750.py
.venv/bin/python test_sensors.py
.venv/bin/python test_vl53l1x.py
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
และจะแสดงระยะของ TOF400C เป็นเซนติเมตรในกล่องเดียวกัน

## TOF400C ร่วมกับการประเมินท่านั่ง

ยึด TOF400C ไว้ใกล้ Pi Camera ในกล่องเดียวกัน แล้วหันหัวเซนเซอร์ไปที่หน้าอกหรือ
ลำตัวส่วนบนของผู้ใช้ ระบบจะเก็บระยะช่วงนั่งตรงโดยอัตโนมัติ 6 ค่าเป็นค่าอ้างอิง
จากนั้นระยะที่ลดลงอย่างต่อเนื่องหมายถึงลำตัวขยับเข้าใกล้กล้อง และระยะที่เพิ่มขึ้นหมายถึง
เอนออกจากกล้อง ค่า TOF จะลดคะแนนได้เท่านั้น จึงไม่สามารถเพิ่มคะแนนที่กล้องประเมินต่ำอยู่แล้ว

ไม่ควรให้มือ คีย์บอร์ด หรือวัตถุอื่นอยู่ในแนวลำแสง และต้องทำให้ `i2cdetect` พบ address `29`
ก่อนใช้งานจริง
ของ backend เท่านั้นและไม่บันทึกลง database. หาก backend อยู่คนละเครื่อง ให้เปลี่ยน backend URL เป็น
`http://IP-ของ-backend:8000`

## ปรับเทียบค่า Lux

ค่า BH1750 ขึ้นกับตำแหน่งและแสงรอบตัว หากต้องการปรับให้ค่าที่อ่านได้ตรงกับค่าอ้างอิง
ให้ใช้ตัวคูณ `ค่าอ้างอิง ÷ ค่าเฉลี่ยที่อ่านได้` เช่น อ่านได้เฉลี่ย 192.5 Lux แต่ค่าอ้างอิงคือ
300 Lux จะได้ตัวคูณ `1.56`.

ทดสอบแบบปรับเทียบชั่วคราว:

~~~bash
.venv/bin/python test_bh1750.py --lux-scale 1.56
~~~

สำหรับ service ถาวร ให้สร้าง systemd override:

~~~bash
sudo systemctl edit postureai-sensors
# เพิ่มสองบรรทัดนี้:
[Service]
Environment=POSTUREAI_BH1750_LUX_SCALE=1.56

sudo systemctl daemon-reload
sudo systemctl restart postureai-sensors
~~~

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
