"""Public API — หน้าจองออนไลน์สำหรับลูกค้าร้าน (ไม่ต้อง login)
ขอบเขตจำกัด: ดูบริการ + สร้างการจองเท่านั้น มี rate limit กัน spam"""
import os
import re
import time

# บนเว็บเดโม่ตั้ง DEMO_MODE=1 → จองออนไลน์/ลูกค้าที่ไม่มี login ติดธง is_demo (ถูกล้างทุกชั่วโมง)
# บนร้านจริง (ไม่ตั้ง) → เป็นข้อมูลถาวรตามปกติ
DEMO_MODE = bool(os.environ.get("DEMO_MODE"))

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import clean_name, kv_get, log_event, next_booking_no
from ..models import Booking, BookingItem, Customer, Service, ServiceCategory

router = APIRouter(prefix="/api/public", tags=["public"])

_HITS: dict[str, list[float]] = {}


def _rate(ip: str, limit: int = 10, window: float = 3600.0) -> None:
    now = time.time()
    hits = [t for t in _HITS.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="จองถี่เกินไป — ลองใหม่ภายหลังหรือโทรหาร้านโดยตรง")
    hits.append(now)
    _HITS[ip] = hits


@router.get("/shop-info")
def shop_info(db: Session = Depends(get_db)):
    s = kv_get(db, "settings", {})
    return {"shopName": s.get("shopName") or "JavaXd Massage & Spa",
            "phone": s.get("shopPhone") or "02-123-4567",
            "openHours": s.get("openHours") or "เปิดทุกวัน 10:00 - 22:00",
            "address": s.get("shopAddress") or "123/45 ถนนสุขุมวิท คลองเตย กรุงเทพฯ"}


@router.get("/services")
def public_services(db: Session = Depends(get_db)):
    cats = {c.id: c.name for c in db.query(ServiceCategory).all()}
    rows = db.query(Service).filter(Service.is_active == True).order_by(Service.price).all()  # noqa: E712
    return [{"id": s.id, "name": s.name, "durationMins": s.duration_mins,
             "price": s.price, "category": cats.get(s.category_id, "")} for s in rows]


@router.post("/booking", status_code=201)
def public_booking(request: Request, body: dict = Body(...), db: Session = Depends(get_db)):
    _rate(request.client.host if request.client else "?")
    name = (body.get("name") or "").strip()
    phone = re.sub(r"\D", "", body.get("phone") or "")
    date = body.get("date") or ""
    t = body.get("time") or ""
    svc = db.get(Service, body.get("serviceId") or "")
    if len(name) < 2 or re.fullmatch(r"[\d\s\-+().]+", name):
        raise HTTPException(status_code=422, detail="กรุณากรอกชื่อ-นามสกุลจริง")
    if len(phone) != 10 or not phone.startswith("0"):
        raise HTTPException(status_code=422, detail="กรุณากรอกเบอร์มือถือ 10 หลัก (ใช้ยืนยันการจอง)")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not re.fullmatch(r"\d{2}:\d{2}", t):
        raise HTTPException(status_code=422, detail="กรุณาเลือกวันและเวลา")
    if svc is None:
        raise HTTPException(status_code=404, detail="ไม่พบบริการที่เลือก")
    # ห้ามจองเวลาที่ผ่านไปแล้ว (เผื่อเดินทาง 30 นาที)
    from datetime import datetime, timedelta
    try:
        when = datetime.strptime(f"{date} {t}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=422, detail="วันหรือเวลาไม่ถูกต้อง")
    if when < datetime.now() + timedelta(minutes=30):
        raise HTTPException(status_code=422, detail="เวลานี้ผ่านไปแล้วหรือกระชั้นเกินไป — เลือกเวลาล่วงหน้าอย่างน้อย 30 นาที")

    name = clean_name(name)
    cust = db.query(Customer).filter(Customer.phone.like(f"%{phone[-9:]}")).first()
    if cust is None:
        cust = Customer(display_name=name, phone=phone, notes="สมัครผ่านจองผ่านเว็บ", is_demo=DEMO_MODE)
        db.add(cust)
        db.flush()
    # หน้าเว็บสัญญาว่า "ยืนยันทันที" → สถานะเป็นยืนยันแล้ว (1) ไม่ใช่รอดำเนินการ
    b = Booking(booking_no=next_booking_no(db), customer_id=cust.id, is_demo=DEMO_MODE,
                booking_date=date, start_time=t + ":00", status=1)
    b.items.append(BookingItem(service_id=svc.id, therapist_selection_mode=1, price=svc.price))
    db.add(b)
    log_event(db, "BookingCreated", "Booking", b.booking_no,
              f"จองออนไลน์: {cust.display_name} · {svc.name}", "ลูกค้า (เว็บ)")
    db.commit()
    return {"bookingNo": b.booking_no, "customerName": cust.display_name,
            "serviceName": svc.name, "date": date, "time": t, "price": svc.price}
