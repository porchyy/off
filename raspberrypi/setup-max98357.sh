#!/usr/bin/env bash
# Configure the MAX98357A I2S DAC/amplifier as OffSyn Tech's only Pi audio output.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POSTURE_CONFIG="$SCRIPT_DIR/config.yaml"
BOOT_CONFIG="/boot/firmware/config.txt"
ALSA_CONFIG="/etc/asound.conf"
MAX98357_DEVICE="plughw:CARD=MAX98357A,DEV=0"

fail() { echo "ERROR: $*" >&2; exit 1; }

if [ "$EUID" -eq 0 ]; then
    fail "Run this script as your normal Pi user, without sudo."
fi
if [ ! -f "$BOOT_CONFIG" ]; then
    BOOT_CONFIG="/boot/config.txt"
fi
[ -f "$BOOT_CONFIG" ] || fail "Raspberry Pi boot config was not found."

MODEL="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
if [[ "$MODEL" != *"Raspberry Pi 5"* ]]; then
    echo "WARNING: Expected Raspberry Pi 5, found: ${MODEL:-unknown model}"
fi

echo "[1/4] Installing ALSA playback and Thai speech tools..."
sudo apt-get update
sudo apt-get install -y alsa-utils espeak-ng

echo "[2/4] Enabling the official MAX98357A I2S overlay..."
BOOT_BACKUP="${BOOT_CONFIG}.postureai-before-max98357"
if [ ! -f "$BOOT_BACKUP" ]; then
    sudo cp "$BOOT_CONFIG" "$BOOT_BACKUP"
fi

TEMP_BOOT="$(mktemp)"
trap 'rm -f "$TEMP_BOOT"' EXIT
awk '
    /^[[:space:]]*dtoverlay=hifiberry-dac([,[:space:]].*)?$/ {
        print "# Disabled by OffSyn Tech MAX98357A setup: " $0
        next
    }
    /^[[:space:]]*dtoverlay=max98357a([,[:space:]].*)?$/ { next }
    { print }
    END {
        print ""
        print "# OffSyn Tech MAX98357A I2S DAC/amplifier"
        print "dtoverlay=max98357a,sdmode-pin=4"
    }
' "$BOOT_CONFIG" > "$TEMP_BOOT"
sudo install -m 644 "$TEMP_BOOT" "$BOOT_CONFIG"

echo "[3/4] Making MAX98357A the default ALSA output..."
if [ -f "$ALSA_CONFIG" ] && [ ! -f "${ALSA_CONFIG}.postureai-backup" ]; then
    sudo cp "$ALSA_CONFIG" "${ALSA_CONFIG}.postureai-backup"
fi
sudo tee "$ALSA_CONFIG" >/dev/null <<'ASOUND'
pcm.!default {
    type plug
    slave.pcm "hw:MAX98357A,0"
}

ctl.!default {
    type hw
    card MAX98357A
}
ASOUND

echo "[4/4] Pointing OffSyn Tech directly at MAX98357A..."
if [ -f "$POSTURE_CONFIG" ]; then
    sed -i -E 's|^([[:space:]]*)device:[[:space:]].*$|\1device: "plughw:CARD=MAX98357A,DEV=0"|' "$POSTURE_CONFIG"
    sed -i -E '/^buzzer:/,/^[^[:space:]#]/{s/^([[:space:]]*)enabled:[[:space:]].*$/\1enabled: false/}' "$POSTURE_CONFIG"
else
    echo "WARNING: $POSTURE_CONFIG does not exist yet; copy config.example.yaml after reboot."
fi

echo
echo "MAX98357A setup is ready. Wiring (power the Pi off first):"
echo "  VIN  -> physical pin 2  (5V)"
echo "  GND  -> physical pin 6  (GND)"
echo "  BCLK -> physical pin 12 (GPIO18)"
echo "  LRC  -> physical pin 35 (GPIO19)"
echo "  DIN  -> physical pin 40 (GPIO21)"
echo "  SD   -> physical pin 7  (GPIO4)"
echo "  Speaker -> MAX98357A SPK+ and SPK- only"
echo "  GAIN -> leave unconnected"
echo
echo "Reboot is required: sudo reboot"
echo "After reboot, verify with:"
echo "  aplay -l | grep -i MAX98357A"
echo "  speaker-test -D $MAX98357_DEVICE -c 2 -t sine -f 880 -l 1"
echo "  cd $SCRIPT_DIR"
echo "  .venv/bin/python posture_client.py --config config.yaml --test-sound"
