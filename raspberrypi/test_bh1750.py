#!/usr/bin/env python3
"""ทดสอบเซนเซอร์วัดแสง BH1750FVI ผ่าน I2C."""

import struct
import time

# BH1750 I2C Address (ADDR pin ต่อ GND = 0x23, ต่อ VCC = 0x5C)
BH1750_ADDR = 0x23

# Commands
POWER_ON = 0x01
CONTINUOUS_HIGH_RES = 0x10  # 1 lux resolution, 120ms


def read_light(addr):
    """อ่านค่าแสงจาก BH1750 คืนค่าเป็น Lux."""
    import smbus2  # type: ignore

    bus = smbus2.SMBus(1)
    try:
        # เปิดเซนเซอร์
        bus.write_byte(addr, POWER_ON)
        time.sleep(0.01)

        # สั่งวัดแบบ Continuous High Resolution
        bus.write_byte(addr, CONTINUOUS_HIGH_RES)
        time.sleep(0.18)  # รอเซนเซอร์วัดค่า (~120-180ms)

        # อ่านค่า 2 bytes
        data = bus.read_i2c_block_data(addr, CONTINUOUS_HIGH_RES, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return round(lux, 1)
    finally:
        bus.close()


def main():
    print("=" * 44)
    print("  BH1750FVI Light Sensor Test")
    print("=" * 44)
    print()
    print("  การต่อสาย BH1750 กับ Pi 5:")
    print("  ┌────────────┬──────────────────────┐")
    print("  │ BH1750     │ Raspberry Pi 5       │")
    print("  ├────────────┼──────────────────────┤")
    print("  │ VCC        │ Pin 1  (3.3V)        │")
    print("  │ GND        │ Pin 9  (GND)         │")
    print("  │ SDA        │ Pin 3  (GPIO 2/SDA)  │")
    print("  │ SCL        │ Pin 5  (GPIO 3/SCL)  │")
    print("  │ ADDR       │ (ไม่ต่อ หรือ GND)    │")
    print("  └────────────┴──────────────────────┘")
    print()

    # เช็กว่าเจอเซนเซอร์ไหม
    print("[1/3] ตรวจหาเซนเซอร์บน I2C bus...")
    active_addr = BH1750_ADDR
    try:
        import smbus2  # type: ignore
        bus = smbus2.SMBus(1)
        try:
            bus.read_byte(BH1750_ADDR)
            print(f"[✓] พบ BH1750 ที่ address 0x{BH1750_ADDR:02X}")
        except OSError:
            # ลองอีก address
            alt_addr = 0x5C
            try:
                bus.read_byte(alt_addr)
                print(f"[✓] พบ BH1750 ที่ address 0x{alt_addr:02X} (ADDR=VCC)")
                active_addr = alt_addr
            except OSError:
                print("[✗] ไม่พบเซนเซอร์ BH1750!")
                print("    ลอง: sudo i2cdetect -y 1")
                return 1
        finally:
            bus.close()
    except ImportError:
        print("[!] ไม่พบ smbus2 — กำลังติดตั้ง...")
        import subprocess
        subprocess.run(["pip", "install", "smbus2"], check=True)
        print("[✓] ติดตั้ง smbus2 สำเร็จ")

    # อ่านค่าแสง 1 ครั้ง
    print("[2/3] อ่านค่าแสงครั้งแรก...")
    lux = read_light(active_addr)
    print(f"[✓] ค่าแสง: {lux} lux")
    print()

    # อ่านค่าแสงต่อเนื่อง 10 วินาที
    print("[3/3] อ่านค่าแสงต่อเนื่อง 10 วินาที (กด Ctrl+C เพื่อหยุด)")
    print("-" * 44)
    try:
        for i in range(20):
            lux = read_light(active_addr)
            bar_len = min(30, int(lux / 50))
            bar = "█" * bar_len + "░" * (30 - bar_len)
            level = "มืด" if lux < 50 else "สลัว" if lux < 200 else "ปกติ" if lux < 500 else "สว่าง" if lux < 1000 else "สว่างมาก"
            print(f"  {lux:>8.1f} lux  |{bar}|  {level}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()

    print()
    print("[✓] ทดสอบเสร็จสิ้น!")
    print()
    print("  ระดับแสงอ้างอิง:")
    print("  • < 50 lux     = มืด (ห้องปิดไฟ)")
    print("  • 50-200 lux   = สลัว (ทางเดิน)")
    print("  • 200-500 lux  = ปกติ (ออฟฟิศ)")
    print("  • 500-1000 lux = สว่าง (ใกล้หน้าต่าง)")
    print("  • > 1000 lux   = สว่างมาก (แสงแดด)")
    return 0


if __name__ == "__main__":
    exit(main())
