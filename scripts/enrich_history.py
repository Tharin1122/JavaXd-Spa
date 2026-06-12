"""เติมข้อมูลย้อนหลัง 14 วัน (ข้อมูลถาวร is_demo=False — ตัวล้าง demo ไม่แตะ)
ลูกค้า 24 คน + บิลย้อนหลัง ~3-6 บิล/วัน หลายช่องทาง + รายจ่ายรายวัน — idempotent"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.db import SessionLocal
from backend.models import (Customer, Expense, Payment, PaymentItem, Service,
                            Therapist, WalkIn, WalkInItem)

random.seed(20260612)  # ผลคงที่ รันซ้ำได้ผลเดิม
db = SessionLocal()
if db.query(Customer).filter(Customer.display_name == "คุณธนา ภูมิใจ").first():
    print("ข้อมูลย้อนหลังมีแล้ว ข้าม")
    sys.exit(0)

first = ["ธนา", "มาลี", "ประยุทธ", "สมศรี", "วีระ", "นภา", "เกรียงไกร", "จิราพร", "อนันต์", "รัตนา",
         "ชาญชัย", "พิมพา", "สุรชัย", "อมรา", "ปกรณ์", "ดวงใจ", "ศักดิ์ชัย", "เพ็ญศรี", "ภาคิน", "ชลธิชา",
         "กิตติ", "วันดี", "ธีรพล", "บุษบา"]
last = ["ภูมิใจ", "ทองดี", "ศรีสุข", "มั่งมี", "ใจเย็น", "แก้วมณี", "พูลสวัสดิ์", "บุญมา", "วัฒนกุล", "จันทร์เพ็ญ"]
custs = []
for i, fn in enumerate(first):
    c = Customer(display_name=f"คุณ{fn} {last[i % len(last)]}",
                 phone=f"08{random.randint(1,9)}-{random.randint(100,999)}-{random.randint(1000,9999)}",
                 notes=random.choice([None, None, None, "ชอบนวดแรง", "ขอผู้หญิงนวด", "มาประจำทุกสัปดาห์"]))
    db.add(c)
    custs.append(c)
db.flush()

svcs = db.query(Service).all()
ths = [t for t in db.query(Therapist).all() if t.code != "DEMO"]
now = datetime.now()
made = 0
for d in range(14, 0, -1):
    day = now - timedelta(days=d)
    for slot in range(random.randint(3, 6)):
        cust = random.choice(custs)
        sv = random.choice(svcs)
        th = random.choice(ths)
        hh = random.choice([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        start = day.replace(hour=hh, minute=random.choice([0, 30]), second=0, microsecond=0)
        w = WalkIn(queue_no=f"H{d:02d}{slot}", customer_id=cust.id, status=2, paid=True,
                   arrival_time=start - timedelta(minutes=10), start_time=start,
                   end_time=start + timedelta(minutes=sv.duration_mins))
        w.items.append(WalkInItem(service_id=sv.id, therapist_id=th.id, price=sv.price))
        db.add(w)
        db.flush()
        p = Payment(receipt_no=f"INV{day:%y%m%d}-H{slot:02d}", walkin_id=w.id, customer_id=cust.id,
                    payment_method=random.choice([0, 0, 2, 2, 3]), total_amount=sv.price,
                    paid_amount=sv.price, paid_at=start + timedelta(minutes=sv.duration_mins + 5))
        p.items.append(PaymentItem(service_id=sv.id, service_name=sv.name,
                                   therapist_id=th.id, quantity=1, unit_price=sv.price))
        db.add(p)
        cust.total_visits += 1
        cust.total_spent += sv.price
        made += 1
    if d % 3 == 0:
        db.add(Expense(category=random.choice(["ของใช้ / วัตถุดิบ", "ค่าเช่า / สาธารณูปโภค", "การตลาด"]),
                       amount=random.choice([350, 600, 850, 1200]), note="รายจ่ายประจำ",
                       spent_at=day.replace(hour=18)))
db.commit()
print(f"เพิ่ม: ลูกค้า 24, บิลย้อนหลัง {made} ใบ (14 วัน), รายจ่าย ~5 รายการ — ทั้งหมด is_demo=False")
db.close()
