# Database

SQLite file ใช้เก็บคะแนน posture, alerts, และ settings

## ตำแหน่ง

ตอนรัน backend จะสร้าง/ใช้ไฟล์ที่:

```
<POSTUREAI_DATA_DIR>/postureai.sqlite
```

`POSTUREAI_DATA_DIR` default คือ `./database` (เทียบกับ working dir ของ
backend container) ใน docker-compose จะ mount volume ไว้ที่ `./database/`
นี้แหละ — ไฟล์ sqlite จะอยู่ที่นี่

## Schema

| Table | Columns |
| --- | --- |
| `samples` | `id, score, neck, shoulders, torso, created_at` |
| `alerts` | `id, severity, message, created_at` |
| `settings` | `key, value` (JSON-encoded) |

## การย้ายข้อมูลเดิม

ไฟล์เก่าจากยุค Node.js (`server.mjs`) อยู่ที่:

- `postureai.sqlite.legacy` — SQLite file เดิมก่อน FastAPI port
- `server.mjs.legacy` — เก็บไว้เป็น historical reference เฉยๆ ไม่ได้รัน

ถ้ามี `postureai.sqlite` เดิมอยู่ที่อื่น แค่ copy มาทับในโฟลเดอร์นี้ —
schema เหมือนกัน 100%

## Backup

`postureai.sqlite` พร้อม WAL files (`-shm`, `-wal`) เก็บเป็น
`tar`/`zip` ได้ตรงๆ ขณะ server รัน เพราะใช้ WAL mode อยู่แล้ว
