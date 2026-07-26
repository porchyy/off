# 🧘 PostureAI (OfficeGuardian) — Project Roadmap & Task List

> 📌 **สถานะปัจจุบัน**: ปรับปรุง UI หน้าเว็บใหม่สวยงาม, เคลียร์ไฟล์ซ้ำซ้อน, และเขียนระบบ Raspberry Pi Client สมบูรณ์ 100% (ผ่าน 23/23 Unit Tests)

---

## 🏷️ Overview & Task Summary

| หมวดหมู่ | งานทั้งหมด | สำเร็จแล้ว | คงเหลือ | สถานะ |
| :--- | :---: | :---: | :---: | :---: |
| 🍓 Hardware & Pi Deployment | 4 | 1 | **3** | 🟡 In Progress |
| 💻 Frontend & UI/UX | 4 | 2 | **2** | 🟡 In Progress |
| ⚙️ Backend & Data Management | 4 | 3 | **1** | 🟢 Almost Done |
| 🎤 Presentation & Demo Prep | 3 | 0 | **3** | 🔴 Pending |

---

## 🍓 Phase 1: Hardware & Raspberry Pi Deployment (งานฝั่งฮาร์ดแวร์)

> [!NOTE]
> โค้ด MediaPipe Pose + Offline Buffer บน Pi เขียนเสร็จสมบูรณ์แล้ว เหลือขั้นตอนติดตั้งลงบอร์ดจริง

- [x] **[Dev]** เขียนระบบ MediaPipe Pose Scoring + Offline Buffer SQLite บน Raspberry Pi Client (`raspberrypi/client/detect.py`)
- [ ] **[Setup]** คัดลอกโปรเจกต์ลง Raspberry Pi และติดตั้ง dependencies (`python3 -m venv .venv`, `pip install -r requirements.txt`)
- [ ] **[Config]** ปรับแก้ IP ใน `raspberrypi/config.yaml` ให้ชี้ไปที่ IP ของเครื่อง Server
- [ ] **[Service]** ตั้งค่า `systemd` (`postureai-client.service`) เพื่อให้ Raspberry Pi เริ่มทำงานทันทีเมื่อเปิดเครื่อง/เสียบปลั๊ก
- [ ] **[Testing]** ทดสอบถอดสาย LAN/WiFi บน Pi แล้วเสียบใหม่ เพื่อลองระบบ Offline Buffer ชดเชยข้อมูลย้อนหลัง

---

## 💻 Phase 2: Frontend & UX Enhancements (ฟีเจอร์หน้าเว็บเพิ่มเติม)

> [!TIP]
> หน้าเว็บปัจจุบันเปลี่ยนเป็นดีไซน์เข้ม (Deep Navy) อ่านง่ายระดับกรรมการประเมินแล้ว สามารถเพิ่มฟีเจอร์เสริมความประทับใจได้ดังนี้

- [x] **[UI Redesign]** ปรับปรุง UI ใหม่ทั้งหมด (IBM Plex Sans Thai + Inter, Responsive layout, Status Card ชัดเจน)
- [x] **[Clean Code]** ย้ายและลบไฟล์ซ้ำซ้อนใน Root directory ให้เหลือเฉพาะใน `frontend/`
- [ ] **[Feature] Calibration Mode (โหมดตั้งค่าท่ามาตรฐาน)**: เพิ่มปุ่ม "เซ็ตท่านั่งมาตรฐานของคุณ" ให้ผู้ใช้กดเซ็ตจุดอ้างอิงของตัวเองก่อนเริ่มใช้งาน
- [ ] **[Feature] Sound Customization**: เพิ่มตัวเลือกเสียงแจ้งเตือน (Beep สั้น / เสียงเตือนความถี่สูง / เปิด-ปิดเสียงเตือน)
- [ ] **[Feature] Dark / Light Mode Toggle**: (Optional) ปุ่มสลับธีมสีสว่างสำหรับใช้งานกลางวัน

---

## ⚙️ Phase 3: Backend & Data Management (ระบบหลังบ้าน)

- [x] **[API]** FastAPI routes ครอบคลุม `/api/samples`, `/api/alerts`, `/api/summary`, `/api/export`
- [x] **[Database]** SQLite Local Storage ประมวลผลและเก็บข้อมูลแบบ Privacy-First บนเครื่อง
- [x] **[Tests]** 15 Pytest integration tests สำหรับตรวจสอบความถูกต้องของ API
- [ ] **[Report Export]** เพิ่มปุ่ม Export รายงานฉบับสรุปประจำสัปดาห์ (PDF หรือภาพกราฟสรุปพฤติกรรม)

---

## 🎤 Phase 4: Presentation & Demonstration Prep (เตรียมนำเสนอกรรมการ)

> [!IMPORTANT]
> จุดขายหลักสำหรับนำเสนอกรรมการคือ **"Privacy-First"** (วิดีโอไม่หลุดออกจากเครื่อง) + **"Edge AI"** (ประมวลผลบน Raspberry Pi / Browser โดยตรง)

- [ ] **[Slide]** จัดทำสไลด์นำเสนอ 8-10 สไลด์:
  1. *Problem*: ปัญหา Office Syndrome และโรคจากท่านั่งทำงาน
  2. *Solution*: ระบบ PostureAI ตรวจจับและเตือนท่านั่งแบบ Real-time
  3. *Architecture*: โครงสร้าง Edge AI (Raspberry Pi + MediaPipe + Local SQLite)
  4. *Privacy Highlight*: เน้นย้ำความปลอดภัย ไม่มีการบันทึกภาพวิดีโอลง Server
  5. *Demo Screenshots & Results*: ผลการทดสอบ 23/23 Pass และหน้าตา UI ใหม่
- [ ] **[Video Demo]** อัดคลิปวิดีโอสาธิตการใช้งานความยาว 1-2 นาที (แสดงการนั่งผิดท่า -> ไฟเตือนแดง -> กราฟสรุปผล)
- [ ] **[User Manual]** จัดทำเอกสารคู่มือการใช้งานฉบับสรุป 1 หน้า (Quick Start Guide)

---

## 📅 Action Plan Timeline (ตารางเวลาสรุป)

```
[ระยะที่ 1] ──> ติดตั้งโค้ดลง Raspberry Pi + ทดสอบการส่งข้อมูลจริง
[ระยะที่ 2] ──> เพิ่มระบบ Calibration Mode บน Frontend & ทดลองระบบ offline
[ระยะที่ 3] ──> ถ่ายวิดีโอ Demo + ทำสไลด์นำเสนอกรรมการ
```
