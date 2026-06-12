"""ข้อมูลเริ่มต้น — รันครั้งแรกครั้งเดียว (เช็คจากจำนวน user)"""
import os

from sqlalchemy.orm import Session

from .models import (Customer, InventoryItem, Promotion, Service,
                     ServiceCategory, Therapist, TherapistSchedule, User, Package)
from .security import hash_password


def seed(db: Session) -> None:
    if db.query(User).count() > 0:
        return

    # ---- ผู้ใช้ตามบทบาท (ตรงกับปุ่มเดโม่หน้า login) ----
    users = [
        ("owner", os.environ.get("MMS_OWNER_PASS", "changeme-owner"), "เจ้าของร้าน", "Owner"),
        ("manager", "demo1234", "มะปราง ผู้จัดการ", "Manager"),
        ("reception", "demo1234", "บัว รีเซปชั่น", "Reception"),
        ("aom", "demo1234", "อ้อม หมอนวด", "Therapist"),
        ("cashier", "demo1234", "ฝน แคชเชียร์", "Cashier"),
    ]
    objs = {}
    for uname, pw, name, role in users:
        u = User(username=uname, password_hash=hash_password(pw), display_name=name, role=role)
        db.add(u)
        objs[uname] = u
    db.flush()

    # ---- หมวดหมู่ + บริการ ----
    cats = {}
    for cn in ["นวดไทย", "นวดน้ำมัน", "ประคบ", "นวดเท้า", "คอบ่าไหล่"]:
        c = ServiceCategory(name=cn)
        db.add(c)
        cats[cn] = c
    db.flush()
    services = [
        ("นวดไทย 60 นาที", "นวดไทย", 60, 350, 30), ("นวดไทย 90 นาที", "นวดไทย", 90, 500, 30),
        ("นวดน้ำมันอโรมา 60 นาที", "นวดน้ำมัน", 60, 550, 30), ("นวดน้ำมันอโรมา 90 นาที", "นวดน้ำมัน", 90, 750, 30),
        ("ประคบสมุนไพร 60 นาที", "ประคบ", 60, 450, 30), ("นวดเท้า 45 นาที", "นวดเท้า", 45, 300, 30),
        ("คอบ่าไหล่ 45 นาที", "คอบ่าไหล่", 45, 320, 30),
    ]
    for name, cat, dur, price, comm in services:
        db.add(Service(name=name, category_id=cats[cat].id, duration_mins=dur, price=price, commission_rate=comm))

    # ---- หมอนวด ----
    ths = [("อ้อม", "TH01", 8, 2, objs["aom"].id), ("นุ่น", "TH02", 5, 1, None),
           ("ใบเตย", "TH03", 4, 1, None), ("ปลา", "TH04", 3, 1, None), ("ฟ้า", "TH05", 1, 0, None)]
    for name, code, exp, skill, uid_ in ths:
        t = Therapist(display_name=name, code=code, experience_years=exp, skill_level=skill, user_id=uid_)
        db.add(t)
        db.flush()
        for dow in range(7):
            db.add(TherapistSchedule(therapist_id=t.id, day_of_week=dow,
                                     is_workday=(dow != 0), start_time="10:00:00", end_time="22:00:00"))

    # ---- ลูกค้า ----
    for name, phone, notes in [
        ("คุณเมย์ ลีลาวดี", "091-222-3344", None), ("คุณวิภา ทองคำ", "087-111-2233", "ชอบน้ำหนักมือเบา"),
        ("คุณริรินทร์ ศรีสุข", "081-234-5678", None), ("คุณดารา แสงทอง", "083-101-2020", "แพ้น้ำมันหอมระเหย"),
        ("คุณวรพล ธนะวัฒน์", "089-555-7788", None), ("คุณณัฐชา พึ่งพร", "086-909-1122", None),
    ]:
        db.add(Customer(display_name=name, phone=phone, notes=notes))

    # ---- สต็อก ----
    for name, sku, cat, unit, qty, cost, rop in [
        ("น้ำมันนวดอโรมา ลาเวนเดอร์", "OIL-001", "น้ำมัน", "ขวด", 12, 180, 6),
        ("น้ำมันนวดสมุนไพรไทย", "OIL-002", "น้ำมัน", "ขวด", 4, 150, 6),
        ("ลูกประคบสมุนไพร", "HERB-001", "สมุนไพร", "ลูก", 25, 45, 10),
        ("ผ้าขนหนูใหญ่", "SUP-001", "ของใช้", "ผืน", 40, 90, 15),
        ("ชาสมุนไพรต้อนรับ", "SUP-002", "ของใช้", "กล่อง", 8, 120, 5),
    ]:
        db.add(InventoryItem(name=name, sku=sku, category=cat, unit=unit, quantity=qty,
                             cost_per_unit=cost, reorder_point=rop))

    # ---- คอร์ส + คูปอง ----
    db.add(Package(name="คอร์สนวดน้ำมัน 10 ครั้ง", description="ใช้ได้ทุกสาขา",
                   total_sessions=10, validity_days=180, price=4950, original_price=5500, is_featured=True))
    db.add(Package(name="คอร์สนวดไทย 5 ครั้ง", total_sessions=5, validity_days=90, price=1590, original_price=1750))
    db.add(Promotion(kind="coupon", code="NEW15", campaign="ลูกค้าใหม่ -15%", discount_percent=15, quota=100))

    db.commit()
    seed_showcase(db)


def seed_showcase(db: Session) -> None:
    """ข้อมูลโชว์สำหรับเดโม่ — คิววันนี้ + ประวัติ 7 วัน ให้แดชบอร์ด/ตาราง/การเงินมีตัวเลขทันที
    (รันเฉพาะตอน DB ยังไม่มีคิวเลย — บน Render ดิสก์รีเซ็ตแล้ว seed ใหม่เองทุกครั้ง)"""
    import random
    from datetime import datetime, timedelta

    from .models import Booking, BookingItem, Payment, PaymentItem, WalkIn, WalkInItem

    if os.environ.get("MMS_SEED_SHOWCASE", "1") == "0":  # ปิดตอนรันเทส
        return
    if db.query(WalkIn).count() > 0:
        return
    random.seed(11)
    custs = db.query(Customer).all()
    ths = db.query(Therapist).all()
    svcs = db.query(Service).all()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    rcpt = 1

    # ---- ประวัติ 7 วันก่อนหน้า: คิวจบ+ชำระจริง (การเงิน/รายงานมียอด) ----
    for back in range(7, 0, -1):
        day = now - timedelta(days=back)
        hours = random.sample(range(10, 20), 4)
        for i, h in enumerate(hours):
            c, s, t = random.choice(custs), random.choice(svcs), ths[(back + i) % len(ths)]
            start = day.replace(hour=h, minute=0, second=0, microsecond=0)
            w = WalkIn(queue_no=f"H{back}{i:02d}", customer_id=c.id, status=2, paid=True,
                       arrival_time=start - timedelta(minutes=10), start_time=start,
                       end_time=start + timedelta(minutes=s.duration_mins))
            w.items.append(WalkInItem(service_id=s.id, therapist_id=t.id, sort_order=0, price=s.price))
            db.add(w)
            db.flush()
            p = Payment(receipt_no=f"INV{day:%y%m%d}-{rcpt:03d}", walkin_id=w.id, customer_id=c.id,
                        payment_method=random.choice([0, 0, 2, 3]), total_amount=s.price,
                        paid_amount=s.price, paid_at=start + timedelta(minutes=s.duration_mins + 5))
            p.items.append(PaymentItem(service_id=s.id, service_name=s.name, quantity=1,
                                       unit_price=s.price, therapist_id=t.id))
            db.add(p)
            rcpt += 1
            c.total_visits = (c.total_visits or 0) + 1
            c.total_spent = (c.total_spent or 0) + s.price

    # ---- วันนี้: จบแล้ว 2 / กำลังบริการ 1 / รอคิว 2 (กระดานคิวมีของให้เล่น) ----
    base = now.replace(minute=0, second=0, microsecond=0)
    plan = [(2, -3, True), (2, -2, True), (1, 0, False), (0, 0, False), (0, 0, False)]
    for i, (st, off, paid) in enumerate(plan):
        c, s = custs[i % len(custs)], svcs[i % len(svcs)]
        t = ths[i % len(ths)] if st > 0 else None
        start = base + timedelta(hours=off)
        w = WalkIn(queue_no=f"Q{i+1:03d}", customer_id=c.id, status=st, paid=paid,
                   arrival_time=start - timedelta(minutes=8),
                   start_time=start if st > 0 else None,
                   end_time=start + timedelta(minutes=s.duration_mins) if st == 2 else None)
        w.items.append(WalkInItem(service_id=s.id, therapist_id=t.id if t else None,
                                  sort_order=0, price=s.price))
        db.add(w)
        db.flush()
        if st == 1 and t:
            t.current_status = 1
        if paid:
            p = Payment(receipt_no=f"INV{now:%y%m%d}-{rcpt:03d}", walkin_id=w.id, customer_id=c.id,
                        payment_method=0, total_amount=s.price, paid_amount=s.price,
                        paid_at=start + timedelta(minutes=s.duration_mins + 5))
            p.items.append(PaymentItem(service_id=s.id, service_name=s.name, quantity=1,
                                       unit_price=s.price, therapist_id=t.id if t else None))
            db.add(p)
            rcpt += 1

    # ---- นัดล่วงหน้า วันนี้+พรุ่งนี้ (ตาราง gantt/การจองมีบล็อก) ----
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    bk_plan = [(today, 18), (today, 19), (tomorrow, 11), (tomorrow, 14), (tomorrow, 16)]
    for i, (d, h) in enumerate(bk_plan):
        c, s, t = custs[(i + 2) % len(custs)], svcs[(i + 1) % len(svcs)], ths[(i + 1) % len(ths)]
        b = Booking(booking_no=f"B-{2401 + i}", customer_id=c.id, status=1,
                    booking_date=d, start_time=f"{h:02d}:00:00")
        b.items.append(BookingItem(service_id=s.id, therapist_id=t.id,
                                   therapist_selection_mode=0, sort_order=0, price=s.price))
        db.add(b)

    db.commit()
