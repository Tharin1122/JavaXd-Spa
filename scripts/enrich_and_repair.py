"""ซ่อมคิวซ้อน + เติมข้อมูลหลากหลาย (รัน: .venv\\Scripts\\python scripts\\enrich_and_repair.py)
1) repair: หมอนวดคนเดียวกันมีช่วงเวลาทับกัน → เลื่อนคิวหลังให้ต่อท้ายคิวก่อน
2) enrich: เพิ่มลูกค้า/คิวจบ+จ่าย หลายช่องทาง/การจองบ่าย+พรุ่งนี้/รายจ่าย แบบไม่ชนกัน
3) verify: สแกนซ้ำทั้งระบบ ต้องเหลือ overlap = 0
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.db import SessionLocal
from backend.models import (Booking, BookingItem, Customer, Expense, Payment,
                            PaymentItem, Service, Therapist, WalkIn, WalkInItem)
from backend.helpers import next_booking_no, next_queue_no, next_receipt_no

db = SessionLocal()
now = datetime.now()
today = now.strftime("%Y-%m-%d")


def blocks_for(therapist_id, day):
    """ทุกช่วงเวลา (start,end,obj,kind) ของหมอนวดในวันนั้น จาก walk-in + booking"""
    out = []
    svc = {s.id: s for s in db.query(Service).all()}
    for w in db.query(WalkIn).filter(WalkIn.arrival_time >= day + " 00:00:00",
                                     WalkIn.arrival_time <= day + " 23:59:59",
                                     WalkIn.status.in_([0, 1, 2])).all():
        cur = w.start_time or w.arrival_time
        for it in sorted(w.items, key=lambda x: x.sort_order):
            dur = svc[it.service_id].duration_mins if it.service_id in svc else 60
            if it.therapist_id == therapist_id:
                out.append([cur, cur + timedelta(minutes=dur), w, "walkin"])
            cur = cur + timedelta(minutes=dur)
    for b in db.query(Booking).filter(Booking.booking_date == day, Booking.status.in_([0, 1, 2])).all():
        start = datetime.strptime(day + " " + b.start_time[:8], "%Y-%m-%d %H:%M:%S")
        for it in sorted(b.items, key=lambda x: x.sort_order):
            dur = svc[it.service_id].duration_mins if it.service_id in svc else 60
            if it.therapist_id == therapist_id:
                out.append([start, start + timedelta(minutes=dur), b, "booking"])
            start += timedelta(minutes=dur)
    return sorted(out, key=lambda x: x[0])


def find_overlaps(day):
    bad = []
    for t in db.query(Therapist).all():
        bl = blocks_for(t.id, day)
        for i in range(1, len(bl)):
            if bl[i][0] < bl[i - 1][1]:
                bad.append((t.display_name, bl[i - 1], bl[i]))
    return bad


# ---------- 1) REPAIR ----------
print("== ตรวจคิวซ้อนก่อนซ่อม ==")
overlaps = find_overlaps(today)
for name, a, b in overlaps:
    print(f"  ซ้อน: {name} | {a[0]:%H:%M}-{a[1]:%H:%M} ทับ {b[0]:%H:%M}-{b[1]:%H:%M} ({b[3]})")
fixed = 0
guard = 0
while overlaps and guard < 20:
    name, a, b = overlaps[0]
    new_start = a[1] + timedelta(minutes=5)  # เลื่อนคิวหลังไปต่อท้าย + buffer 5 นาที
    if b[3] == "walkin":
        b[2].start_time = new_start
    else:
        b[2].start_time = new_start.strftime("%H:%M:%S")
    db.commit()
    print(f"  ✔ เลื่อนคิว {name} ไปเริ่ม {new_start:%H:%M}")
    fixed += 1
    guard += 1
    overlaps = find_overlaps(today)

# ---------- 2) ENRICH (idempotent — เช็คจาก marker customer) ----------
if not db.query(Customer).filter(Customer.display_name == "คุณพิมพ์ชนก วงศ์สว่าง").first():
    svcs = db.query(Service).order_by(Service.price).all()
    ths = db.query(Therapist).filter(Therapist.code != "DEMO").all()
    new_custs = []
    for nm, ph, note in [("คุณพิมพ์ชนก วงศ์สว่าง", "081-777-2211", None),
                         ("คุณอรรถพล คงมั่น", "089-432-1100", "ปวดหลังเรื้อรัง ชอบนวดแรง"),
                         ("คุณสุภาพร แก้วใส", "086-345-9988", None),
                         ("คุณเจมส์ มิลเลอร์", "082-111-4455", "ลูกค้าต่างชาติ พูดอังกฤษ"),
                         ("คุณกมลทิพย์ บัวบาน", "084-606-7733", "ตั้งครรภ์ 5 เดือน — เลี่ยงน้ำมันหอม")]:
        c = Customer(display_name=nm, phone=ph, notes=note)
        db.add(c)
        new_custs.append(c)
    db.flush()

    # คิวที่จบ+จ่ายแล้วเมื่อเช้า — หมอนวดคนละคน เวลาเหลื่อมกัน หลายช่องทางจ่าย
    plans = [(new_custs[0], ths[1], svcs[3], 9, 30, 2),   # นุ่น 09:30 QR
             (new_custs[1], ths[2], svcs[6], 10, 0, 0),   # ใบเตย 10:00 เงินสด
             (new_custs[2], ths[3], svcs[1], 11, 15, 3),  # ปลา 11:15 บัตร
             (new_custs[3], ths[4], svcs[5], 12, 30, 2)]  # ฟ้า 12:30 QR
    for cust, th, sv, hh, mm, method in plans:
        start = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if start > now:  # ถ้ายังไม่ถึงเวลา ใช้เมื่อเช้าถอยหลังแทน
            start -= timedelta(hours=6)
        w = WalkIn(queue_no=next_queue_no(db), customer_id=cust.id, status=2, paid=True,
                   arrival_time=start - timedelta(minutes=10), start_time=start,
                   end_time=start + timedelta(minutes=sv.duration_mins))
        w.items.append(WalkInItem(service_id=sv.id, therapist_id=th.id, price=sv.price))
        db.add(w)
        db.flush()
        p = Payment(receipt_no=next_receipt_no(db), walkin_id=w.id, customer_id=cust.id,
                    payment_method=method, total_amount=sv.price, paid_amount=sv.price,
                    paid_at=start + timedelta(minutes=sv.duration_mins + 5))
        p.items.append(PaymentItem(service_id=sv.id, service_name=sv.name,
                                   therapist_id=th.id, quantity=1, unit_price=sv.price))
        db.add(p)
        cust.total_visits += 1
        cust.total_spent += sv.price
    # การจองบ่ายนี้ + พรุ่งนี้ — เวลาห่างกัน ไม่ชนใคร
    tmr = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    bks = [(new_custs[4], ths[1], svcs[4], today, "17:00:00", 1),
           (new_custs[0], ths[2], svcs[2], today, "18:30:00", 1),
           (new_custs[2], ths[0], svcs[3], tmr, "11:00:00", 1),
           (new_custs[1], ths[3], svcs[6], tmr, "14:00:00", 0)]
    for cust, th, sv, d, t, st in bks:
        b = Booking(booking_no=next_booking_no(db), customer_id=cust.id,
                    booking_date=d, start_time=t, status=st)
        b.items.append(BookingItem(service_id=sv.id, therapist_id=th.id, price=sv.price))
        db.add(b)
    # รายจ่ายหลากหมวด
    for cat, amt, note_, hrs in [("ของใช้ / วัตถุดิบ", 1240, "น้ำมันนวด+ผ้า", 5),
                                 ("ค่าเช่า / สาธารณูปโภค", 850, "ค่าไฟ", 3),
                                 ("การตลาด", 300, "บูสต์โพสต์", 1)]:
        db.add(Expense(category=cat, amount=amt, note=note_, spent_at=now - timedelta(hours=hrs)))
    db.commit()
    print("== เติมข้อมูล: ลูกค้า 5, คิวจบ+จ่าย 4 (3 ช่องทาง), จอง 4 (วันนี้+พรุ่งนี้), รายจ่าย 3 ==")
else:
    print("== ข้อมูล enrich มีแล้ว ข้าม ==")

# ---------- 3) VERIFY ----------
left_today = find_overlaps(today)
left_tmr = find_overlaps((now + timedelta(days=1)).strftime("%Y-%m-%d"))
print(f"== ผลตรวจสุดท้าย: ซ่อม {fixed} จุด | overlap วันนี้={len(left_today)} พรุ่งนี้={len(left_tmr)} ==")
assert not left_today and not left_tmr, "ยังมีคิวซ้อน!"
print("✅ ไม่มีหมอนวดคิวซ้อนทั้งระบบ")
db.close()
