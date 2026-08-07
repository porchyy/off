#!/usr/bin/env bash
# setup-max98357.sh — ตั้งค่า MAX98357 I2S DAC สำหรับ Raspberry Pi 5
set -euo pipefail

echo "============================================"
echo "  MAX98357 I2S DAC — Auto Setup Script"
echo "============================================"
echo ""

# 1. เพิ่ม I2S overlay ใน /boot/firmware/config.txt
CONFIG="/boot/firmware/config.txt"
if [ ! -f "$CONFIG" ]; then
    CONFIG="/boot/config.txt"
fi

if grep -q "hifiberry-dac" "$CONFIG" 2>/dev/null; then
    echo "[✓] I2S overlay (hifiberry-dac) มีอยู่แล้วใน $CONFIG"
else
    echo "[+] เพิ่ม dtoverlay=hifiberry-dac ลงใน $CONFIG ..."
    echo "" | sudo tee -a "$CONFIG" > /dev/null
    echo "# MAX98357 I2S DAC" | sudo tee -a "$CONFIG" > /dev/null
    echo "dtoverlay=hifiberry-dac" | sudo tee -a "$CONFIG" > /dev/null
    echo "[✓] เพิ่ม I2S overlay สำเร็จ"
fi

# 2. สร้างไฟล์ ALSA config
echo "[+] สร้าง /etc/asound.conf ..."
sudo tee /etc/asound.conf > /dev/null << 'ASOUND'
pcm.!default {
    type hw
    card 0
}
ctl.!default {
    type hw
    card 0
}
ASOUND
echo "[✓] สร้าง ALSA config สำเร็จ"

# 3. อัปเดต config.yaml ของ PostureAI
POSTURE_CONFIG="$HOME/off/raspberrypi/config.yaml"
if [ -f "$POSTURE_CONFIG" ]; then
    if grep -q "device:" "$POSTURE_CONFIG" 2>/dev/null; then
        sed -i 's/device: default/device: hw:0,0/' "$POSTURE_CONFIG"
        echo "[✓] อัปเดต sound.device เป็น hw:0,0 ใน config.yaml"
    else
        echo "[!] ไม่พบ device: ใน config.yaml — กรุณาแก้ด้วยตนเอง"
    fi
else
    echo "[!] ไม่พบไฟล์ $POSTURE_CONFIG"
fi

echo ""
echo "============================================"
echo "  ตั้งค่าเสร็จเรียบร้อย!"
echo "============================================"
echo ""
echo "  การต่อสาย MAX98357 กับ Pi 5:"
echo "  ┌────────────┬──────────────────────┐"
echo "  │ MAX98357   │ Raspberry Pi 5       │"
echo "  ├────────────┼──────────────────────┤"
echo "  │ VIN        │ Pin 2  (5V)          │"
echo "  │ GND        │ Pin 6  (GND)         │"
echo "  │ BCLK       │ Pin 12 (GPIO 18)     │"
echo "  │ LRC        │ Pin 35 (GPIO 19)     │"
echo "  │ DIN        │ Pin 40 (GPIO 21)     │"
echo "  └────────────┴──────────────────────┘"
echo ""
echo "  ⚠️  ต้อง REBOOT เครื่องก่อนถึงจะใช้งานได้!"
echo "  พิมพ์: sudo reboot"
echo ""
echo "  หลัง reboot ให้เทสเสียงด้วย:"
echo "  speaker-test -t sine -f 440 -c 1 -D hw:0,0"
echo "  (กด Ctrl+C เพื่อหยุด)"
echo ""
echo "  แล้วเทสเสียงเตือนของ PostureAI:"
echo "  cd ~/off/raspberrypi"
echo "  .venv/bin/python posture_client.py --config config.yaml --test-sound"
echo ""
