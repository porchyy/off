#!/usr/bin/env python3
"""Generate natural-sounding Thai voice alerts using Edge-TTS and convert to WAV."""

import argparse
import asyncio
import os
import subprocess
import tempfile
from pathlib import Path


VOICES = {
    "female": "th-TH-PremwadeeNeural",  # คุณเปรมวดี (เสียงผู้หญิง นุ่มนวล ชัดเจน)
    "male": "th-TH-NiwatNeural",        # คุณนิวัฒน์ (เสียงผู้ชาย สุภาพ)
}

DEFAULT_TEXT = "กรุณาปรับท่านั่งให้หลังตรงและคลายไหล่ค่ะ"


async def synthesize(text: str, voice_name: str, output_mp3: str) -> None:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_mp3)


def main() -> int:
    parser = argparse.ArgumentParser(description="สร้างไฟล์เสียงพูดภาษาไทยธรรมชาติ (AI Neural Voice)")
    parser.add_argument("--text", type=str, default=DEFAULT_TEXT, help="ข้อความที่ต้องการให้พูด")
    parser.add_argument("--voice", choices=["female", "male"], default="female", help="เลือกเสียงผู้หญิงหรือผู้ชาย")
    parser.add_argument("--output", type=str, default="alert_thai.wav", help="ไฟล์เสียง WAV ปลายทาง (default: alert_thai.wav)")
    args = parser.parse_args()

    voice_id = VOICES[args.voice]
    output_path = Path(args.output).resolve()

    print(f"🎙️ กำลังสังเคราะห์เสียง: \"{args.text}\"")
    print(f"👤 รูปแบบเสียง: {args.voice} ({voice_id})")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
        temp_mp3_path = temp_mp3.name

    try:
        asyncio.run(synthesize(args.text, voice_id, temp_mp3_path))

        # แปลงเป็น WAV 16-bit 44.1kHz สำหรับ ALSA aplay
        # ลองใช้ ffmpeg หรือ afconvert (macOS)
        converted = False
        for cmd in [
            ["ffmpeg", "-y", "-i", temp_mp3_path, "-ar", "44100", "-ac", "2", str(output_path)],
            ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", temp_mp3_path, str(output_path)],
        ]:
            try:
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if res.returncode == 0:
                    converted = True
                    break
            except FileNotFoundError:
                continue

        if not converted:
            print("⚠️ ไม่พบ ffmpeg หรือ afconvert กำลังบันทึกเป็น MP3 โดยตรง...")
            os.replace(temp_mp3_path, output_path.with_suffix(".mp3"))
            print(f"✅ บันทึกไฟล์เสียงสำเร็จ: {output_path.with_suffix('.mp3')}")
            return 0

        print(f"✅ สร้างไฟล์เสียงสำเร็จ: {output_path} (ขนาด {os.path.getsize(output_path)} bytes)")
        return 0
    finally:
        if os.path.exists(temp_mp3_path):
            os.remove(temp_mp3_path)


if __name__ == "__main__":
    raise SystemExit(main())
