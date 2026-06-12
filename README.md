# 🌿 JavaXd Massage & Spa Suite

ระบบบริหารร้านนวด-สปาครบวงจร — จองออนไลน์ 24 ชม. · คิวเรียลไทม์ · POS + Thai QR PromptPay · ใบกำกับภาษี · Z-Report · สิทธิ์ 5 บทบาท
**FastAPI + SQLAlchemy + SQLite** (รองรับ DB อื่นผ่าน `MMS_DB_URL`) · frontend 18 หน้า · 85+ API · pytest 45 ตัว

## รัน local

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
copy .env.example .env        # แล้วแก้ค่า (ไม่มีไฟล์นี้ก็รันได้ — ใช้ค่า default สำหรับ dev)
.venv/Scripts/python -m uvicorn backend.main:app --port 8088
```

เปิด http://127.0.0.1:8088/login.html — มีปุ่มบัญชีเดโม่ 5 บทบาทที่หน้า login
(ข้อมูลที่สร้างด้วยบัญชีเดโม่ถูกล้างอัตโนมัติทุก 1 ชั่วโมง)
หน้า public จองออนไลน์: `/book.html` · จอเรียกคิว TV: `/pages/queue-display.html`

## Environment Variables

| ตัวแปร | ความหมาย |
|---|---|
| `MMS_DB_URL` | DB connection string (เว้นว่าง = SQLite `mms.db`) |
| `MMS_OWNER_PASS` | รหัสบัญชี `owner` — ต้องตั้งใหม่ใน production เสมอ |
| `MMS_SECRET_KEY` | JWT secret — สุ่มยาวๆ |

## Deploy (Render)

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Branch: **master** = production · **UAT** = ทดสอบ (merge เข้า master เมื่อเทสผ่านเท่านั้น)
- ⚠ Free tier ดิสก์ไม่ถาวร: SQLite รีเซ็ตเมื่อ service restart — เหมาะกับโหมดเดโม่ (ระบบ seed ข้อมูลตั้งต้นใหม่เองอัตโนมัติ)

## Tests

```bash
.venv/Scripts/python -m pytest tests -q
```
