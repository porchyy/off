# ไฟล์โมเดล AI (pose_landmarker_full.task)

โฟลเดอร์นี้ต้องมีไฟล์ `pose_landmarker_full.task` อยู่ก่อนใช้งานแอปได้
(ไฟล์นี้ **ไม่ commit เข้า git** เพราะขนาดใหญ่ ~5-7MB — CI ดึงเองอัตโนมัติ
ตาม `.github/workflows/pages.yml`, ส่วนเครื่อง dev/Pi ต้องดาวน์โหลดเองครั้งเดียว)

## วิธีดาวน์โหลด

### เบราว์เซอร์ (ง่ายสุด)
เปิดลิงก์นี้ แล้วเซฟไฟล์มาวางที่ `frontend/public/models/pose_landmarker_full.task`:
```
https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
```

### เทอร์มินัล
```bash
cd frontend/public/models
curl -fsSL -o pose_landmarker_full.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
```

## ทำครั้งเดียวพอ

ทำตอน setup โปรเจกต์ครั้งแรก (เครื่อง dev หรือ Pi) — หลังจากนั้น `npm run dev` /
`npm run build` จะเสิร์ฟไฟล์นี้เป็น static asset ที่ `/models/pose_landmarker_full.task`
ให้เอง แอปจะโหลด AI จากไฟล์นี้โดยตรง **ไม่ต้องพึ่งอินเทอร์เน็ตอีกเลย** หลัง build/deploy

ถ้าใช้ Docker: ไฟล์นี้ต้องอยู่ในตำแหน่งนี้ **ก่อน** รัน `docker compose up --build`
เพราะ Vite จะ copy โฟลเดอร์ `public/` ทั้งหมดเข้า `dist/` ตอน build image

---

## 🧠 โฟลเดอร์โมเดลที่เทรนเอง (`models/custom/`)

หากคุณเทรนโมเดลส่วนตัวในหน้าเว็บและกด **"บันทึกโมเดล"** คุณจะได้ไฟล์โมเดลมา 2 ไฟล์:
- `model.json`
- `model.weights.bin` (หรือ `custom-posture-model.weights.bin`)

หากต้องการให้โปรเจกต์โหลดโมเดลที่เทรนแล้วนี้ขึ้นมาใช้งานโดยอัตโนมัติเมื่อเปิดเว็บ/รันใน Docker โดยไม่ต้องกดโหลดไฟล์เองทุกครั้ง:
1. นำไฟล์ทั้งสองมาวางไว้ที่โฟลเดอร์ `frontend/public/models/custom/`
2. ตั้งชื่อไฟล์เป็น `model.json` และ `model.weights.bin`
3. หลังรัน `npm run build` / Docker Image ใหม่ แอปจะโหลดโมเดลนี้มาเป็นโมเดลส่วนตัวล่วงหน้าให้ทันที 100% Offline
