from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import booking_out, log_event, next_booking_no
from ..models import Booking, BookingItem, Customer, Service, User
from ..security import current_user

router = APIRouter(prefix="/api/booking", tags=["bookings"], dependencies=[Depends(current_user)])


@router.get("")
def list_bookings(date: str = "", pageSize: int = 100, db: Session = Depends(get_db)):
    q = db.query(Booking)
    if date:
        q = q.filter(Booking.booking_date == date)
    rows = q.order_by(Booking.booking_date.desc(), Booking.start_time).limit(min(pageSize, 1000)).all()
    return {"items": [booking_out(db, b) for b in rows], "total": q.count()}


@router.post("", status_code=201)
def create_booking(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    cust = db.get(Customer, body.get("customerId") or "")
    if cust is None:
        raise HTTPException(status_code=404, detail="ไม่พบลูกค้า")
    items = body.get("items") or []
    if not items:
        raise HTTPException(status_code=422, detail="ต้องมีอย่างน้อย 1 บริการ")
    b = Booking(booking_no=next_booking_no(db), customer_id=cust.id, is_demo=u.is_demo,
                booking_date=body.get("bookingDate") or "", start_time=body.get("startTime") or "12:00:00")
    for i, it in enumerate(items):
        svc = db.get(Service, it.get("serviceId") or "")
        if svc is None:
            raise HTTPException(status_code=404, detail="ไม่พบบริการที่เลือก")
        # 🚪 กันจองชนผ่านตัวตรวจกลาง: เช็คทั้งนัดจองอื่นและคิว walk-in ของหมอคนนั้น
        tid = it.get("therapistId")
        if tid:
            from datetime import datetime as _dt

            from .walkins import therapist_conflict
            try:
                new_start = _dt.strptime(b.booking_date + " " + b.start_time[:8], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise HTTPException(status_code=422, detail="รูปแบบวันที่/เวลาไม่ถูกต้อง")
            reason = therapist_conflict(db, tid, new_start, svc.duration_mins)
            if reason:
                raise HTTPException(status_code=409,
                                    detail=f"หมอนวดคนนี้{reason} — เลือกเวลาอื่นหรือให้ระบบจัดอัตโนมัติ")
        b.items.append(BookingItem(service_id=svc.id, therapist_id=it.get("therapistId"),
                                   therapist_selection_mode=int(it.get("therapistSelectionMode") or 0),
                                   sort_order=int(it.get("sortOrder") or i), price=svc.price))
    db.add(b)
    log_event(db, "BookingCreated", "Booking", b.booking_no, f"สร้างการจองให้ {cust.display_name}", u.display_name)
    db.commit()
    return booking_out(db, b)


def _get(db: Session, bid: str) -> Booking:
    b = db.get(Booking, bid)
    if b is None:
        raise HTTPException(status_code=404, detail="ไม่พบการจอง")
    return b


@router.get("/{bid}")
def get_booking(bid: str, db: Session = Depends(get_db)):
    return booking_out(db, _get(db, bid))


_ACTIONS = {"confirm": 1, "start": 2, "complete": 3, "cancel": 4, "no-show": 5}
# state machine: สถานะปัจจุบัน → action ที่อนุญาตเท่านั้น (ดู wiki/spa-mms-state-machine)
_ALLOWED = {0: {"confirm", "cancel", "no-show"},
            1: {"start", "cancel", "no-show"},
            2: {"complete"},
            3: set(), 4: set(), 5: set()}  # จบทาง — ห้ามทุก action
_STATE_TH = {0: "รอดำเนินการ", 1: "ยืนยันแล้ว", 2: "เช็คอินแล้ว", 3: "เสร็จสิ้น", 4: "ยกเลิกแล้ว", 5: "ไม่มาตามนัด"}


@router.patch("/{bid}/{action}")
def booking_action(bid: str, action: str, body: dict | None = Body(default=None),
                   u: User = Depends(current_user), db: Session = Depends(get_db)):
    if action not in _ACTIONS:
        raise HTTPException(status_code=404, detail="ไม่รู้จักคำสั่งนี้")
    b = _get(db, bid)
    if action not in _ALLOWED.get(b.status, set()):
        raise HTTPException(status_code=409,
                            detail=f"การจองอยู่สถานะ '{_STATE_TH.get(b.status)}' — ทำ '{action}' ไม่ได้ตามขั้นตอน")
    b.status = _ACTIONS[action]
    log_event(db, "BookingUpdated", "Booking", b.booking_no, f"อัปเดตสถานะ → {action}", u.display_name)
    db.commit()
    return booking_out(db, b)
