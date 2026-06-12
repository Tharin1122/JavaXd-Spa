# เติมข้อมูลจริง (is_demo=False) ทั้งเดือน มิ.ย. 2026 (1-30)
# - วันที่ผ่านมาแล้ว: คิวจบงาน + ใบเสร็จชำระจริง (ธุรกรรมครบ)
# - วันนี้เป็นต้นไป: นัดจองยืนยันแล้ว ระบุหมอแบบไม่ชนกัน (เห็นในตารางคิว/gantt)
# กันรันซ้ำด้วย marker ใน key-value
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from backend.db import SessionLocal
from backend.helpers import kv_get, kv_set, next_booking_no, next_queue_no, next_receipt_no
from backend.models import (Booking, BookingItem, Customer, Payment, PaymentItem,
                            Service, Therapist, WalkIn, WalkInItem)

random.seed(26)
db = SessionLocal()

if kv_get(db, "seed_june_2026", False):
    print("เคยเติมแล้ว — ข้าม (ลบ key 'seed_june_2026' ถ้าจะรันใหม่)")
    sys.exit(0)

today = datetime.now().strftime("%Y-%m-%d")
custs = [c for c in db.query(Customer).all() if not c.is_demo and not (c.notes or "").startswith("seed")]
ths = db.query(Therapist).all()
svcs = [s for s in db.query(Service).all() if s.is_active and "ทดสอบ" not in s.name]
if not custs or not ths or not svcs:
    print("ข้อมูลพื้นฐานไม่พอ")
    sys.exit(1)

METHODS = [0, 0, 0, 2, 2, 3, 1]  # เงินสดเยอะสุด รองลงมา QR
made_w = made_b = made_p = 0

for d in range(1, 31):
    day = f"2026-06-{d:02d}"
    # ตารางว่างต่อหมอ: ช่องชั่วโมง 10:00-20:00 — กันชนกันเองในข้อมูลที่เติม
    free_slots = {t.id: list(range(10, 21)) for t in ths}

    def take_slot(tid, need_h):
        slots = free_slots[tid]
        for i in range(len(slots) - need_h + 1):
            if all(slots[i] + k == slots[i + k] for k in range(need_h)):
                got = slots[i]
                for k in range(need_h):
                    slots.remove(got + k)
                return got
        return None

    if day < today:
        # ประวัติ: 3-6 คิวจบ+จ่ายจริงต่อวัน
        for _ in range(random.randint(3, 6)):
            c = random.choice(custs)
            s = random.choice(svcs)
            t = random.choice(ths)
            need = max(1, round(s.duration_mins / 60))
            h = take_slot(t.id, need)
            if h is None:
                continue
            start = datetime.strptime(f"{day} {h:02d}:00:00", "%Y-%m-%d %H:%M:%S")
            w = WalkIn(queue_no=f"M{d:02d}{random.randint(10,99)}", customer_id=c.id, status=2,
                       is_demo=False, paid=True, arrival_time=start - timedelta(minutes=10),
                       start_time=start, end_time=start + timedelta(minutes=s.duration_mins))
            w.items.append(WalkInItem(service_id=s.id, therapist_id=t.id, sort_order=0, price=s.price))
            db.add(w)
            db.flush()
            p = Payment(receipt_no=next_receipt_no(db), walkin_id=w.id, customer_id=c.id,
                        payment_method=random.choice(METHODS), total_amount=s.price,
                        paid_amount=s.price, is_demo=False,
                        paid_at=start + timedelta(minutes=s.duration_mins + 5))
            p.items.append(PaymentItem(service_id=s.id, service_name=s.name, quantity=1,
                                       unit_price=s.price, therapist_id=t.id))
            db.add(p)
            c.total_visits = (c.total_visits or 0) + 1
            c.total_spent = (c.total_spent or 0) + s.price
            c.last_visit_at = p.paid_at
            made_w += 1
            made_p += 1
    else:
        # อนาคต: 2-4 นัดยืนยันต่อวัน ระบุหมอ ไม่ชนกัน
        for _ in range(random.randint(2, 4)):
            c = random.choice(custs)
            s = random.choice(svcs)
            t = random.choice(ths)
            need = max(1, round(s.duration_mins / 60))
            h = take_slot(t.id, need)
            if h is None:
                continue
            b = Booking(booking_no=next_booking_no(db), customer_id=c.id, status=1,
                        is_demo=False, booking_date=day, start_time=f"{h:02d}:00:00")
            b.items.append(BookingItem(service_id=s.id, therapist_id=t.id,
                                       therapist_selection_mode=0, sort_order=0, price=s.price))
            db.add(b)
            made_b += 1

kv_set(db, "seed_june_2026", True)
db.commit()
print(f"เติมแล้ว: คิวจบ+จ่าย {made_w} | ใบเสร็จ {made_p} | นัดล่วงหน้า {made_b} (1-30 มิ.ย. 2026, is_demo=False)")
