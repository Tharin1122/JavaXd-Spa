import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import (Booking, Customer, KeyValue, Payment, Service, Therapist,
                     TimelineEvent, WalkIn)

METHOD_NAMES = {0: "Cash", 1: "Transfer", 2: "QR", 3: "Card"}


def iso(dt) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def log_event(db: Session, event_type: str, entity_type: str, label: str | None = None,
              description: str | None = None, actor: str | None = None) -> None:
    db.add(TimelineEvent(event_type=event_type, entity_type=entity_type,
                         entity_label=label, description=description, actor_name=actor))


def kv_get(db: Session, key: str, default):
    row = db.get(KeyValue, key)
    if row is None:
        return default
    try:
        return json.loads(row.value)
    except Exception:
        return default


def kv_set(db: Session, key: str, value) -> None:
    row = db.get(KeyValue, key)
    if row is None:
        row = KeyValue(key=key, value=json.dumps(value, ensure_ascii=False))
        db.add(row)
    else:
        row.value = json.dumps(value, ensure_ascii=False)


def next_queue_no(db: Session) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    n = db.query(WalkIn).filter(WalkIn.arrival_time >= today + " 00:00:00").count()
    return f"Q{n + 1:03d}"


def next_booking_no(db: Session) -> str:
    return f"B-{db.query(Booking).count() + 2401}"


def next_receipt_no(db: Session) -> str:
    d = datetime.now().strftime("%y%m%d")
    n = db.query(Payment).filter(Payment.receipt_no.like(f"INV{d}%")).count()
    return f"INV{d}-{n + 1:03d}"


def customer_brief(c: Customer | None) -> dict | None:
    if c is None:
        return None
    return {"id": c.id, "displayName": c.display_name, "phone": c.phone,
            "notes": c.notes, "totalVisits": c.total_visits, "totalSpent": c.total_spent}


def customer_or_ghost(db: Session, cid: str | None) -> dict | None:
    """อ้างถึงลูกค้า — ถ้าถูกลบไปแล้ว (ข้อมูลเก่าก่อนมีตัวกัน) แสดงชื่อ fallback แทนช่องว่าง"""
    if not cid:
        return None
    c = db.get(Customer, cid)
    if c is None:
        return {"id": cid, "displayName": "ลูกค้าทั่วไป (ไม่ระบุ)", "phone": None,
                "notes": None, "totalVisits": 0, "totalSpent": 0}
    return customer_brief(c)


def service_brief(s: Service | None) -> dict | None:
    if s is None:
        return None
    return {"id": s.id, "name": s.name, "price": s.price, "durationMins": s.duration_mins}


def therapist_brief(t: Therapist | None) -> dict | None:
    if t is None:
        return None
    return {"id": t.id, "displayName": t.display_name, "code": t.code,
            "currentStatus": t.current_status, "userId": t.user_id}


def walkin_out(db: Session, w: WalkIn) -> dict:
    cust = db.get(Customer, w.customer_id)
    items = []
    for it in sorted(w.items, key=lambda x: x.sort_order):
        svc = db.get(Service, it.service_id)
        ther = db.get(Therapist, it.therapist_id) if it.therapist_id else None
        items.append({
            "id": it.id, "service": service_brief(svc), "serviceId": it.service_id,
            "serviceName": svc.name if svc else "", "therapist": therapist_brief(ther),
            "therapistId": it.therapist_id, "price": it.price,
            "durationMins": svc.duration_mins if svc else 0, "sortOrder": it.sort_order,
        })
    total = sum(i["price"] for i in items)
    # สถานะกลาง (ฟิลด์เดียว ใช้ตรงกันทุกหน้า): รวมทั้งขั้นบริการและการเงิน
    state = ("ยกเลิก" if w.status == 3 else
             "ชำระแล้ว" if (w.status == 2 and w.paid) else
             "เสร็จสิ้น · รอชำระ" if w.status == 2 else
             "กำลังให้บริการ" if w.status == 1 else "รอคิว")
    return {
        "id": w.id, "queueNo": w.queue_no, "queueNumber": w.queue_no, "status": w.status,
        "stateLabel": state,
        "customer": customer_brief(cust), "customerId": w.customer_id,
        "customerName": cust.display_name if cust else "",
        "bookingId": w.booking_id, "notes": w.notes, "cancelReason": w.cancel_reason,
        "arrivalTime": iso(w.arrival_time), "startTime": iso(w.start_time),
        "serviceStartTime": iso(w.start_time), "endTime": iso(w.end_time),
        "items": items, "itemCount": len(items), "totalAmount": total, "paid": w.paid,
    }


def booking_out(db: Session, b: Booking) -> dict:
    cust = db.get(Customer, b.customer_id)
    items, dur = [], 0
    for it in sorted(b.items, key=lambda x: x.sort_order):
        svc = db.get(Service, it.service_id)
        ther = db.get(Therapist, it.therapist_id) if it.therapist_id else None
        dur += (svc.duration_mins if svc else 0)
        items.append({
            "id": it.id, "service": service_brief(svc), "serviceId": it.service_id,
            "serviceName": svc.name if svc else "", "therapist": therapist_brief(ther),
            "therapistId": it.therapist_id, "price": it.price,
            "therapistSelectionMode": it.therapist_selection_mode, "sortOrder": it.sort_order,
        })
    total = sum(i["price"] for i in items)
    start = datetime.strptime(b.booking_date + " " + b.start_time[:8], "%Y-%m-%d %H:%M:%S")
    end = start + timedelta(minutes=dur or 60)
    # สถานะการชำระเงิน: ตามไปดูคิว walk-in ที่เกิดจากนัดนี้ (ตอนเช็คอิน) ว่าจ่ายหรือยัง
    wi = db.query(WalkIn).filter(WalkIn.booking_id == b.id).first()
    return {
        "id": b.id, "bookingNo": b.booking_no, "status": b.status, "checkedIn": b.checked_in,
        "paid": bool(wi.paid) if wi else False, "walkInId": wi.id if wi else None,
        "customer": customer_brief(cust), "customerId": b.customer_id,
        "bookingDate": b.booking_date, "startTime": b.start_time,
        "endTime": end.strftime("%H:%M:%S"), "totalDurationMins": dur,
        "items": items, "itemCount": len(items), "totalAmount": total,
        "createdAt": iso(b.created_at),
    }
