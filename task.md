# Task: Fix all issues from project_review.md

## Critical Fixes
- [x] C5 — เพิ่ม `voiceEnabled` ใน `settings_store.py` + `schemas.py`
- [x] C6 — แก้ CORS `"*"` ใน `docker-compose.yml`
- [x] M1 — เปลี่ยน Node 20 → 22 ใน `Dockerfile.frontend`
- [x] M2 — ย้าย `import json` + `json_dumps()` ใน `routes.py`
- [x] M3 — แก้ `test_update_settings_clamping` ให้ทดสอบ out-of-range จริง
- [x] M7 — ลบ TODO comment ล้าสมัยใน `posture_client.py`

## Tests
- [x] รัน backend tests (pytest) — **16/16 PASSED** ✅
- [x] รัน frontend tests (node --test) — **13/13 PASSED** ✅
