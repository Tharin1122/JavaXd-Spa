from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import METHOD_NAMES, booking_out, iso, walkin_out
from ..models import (Booking, Customer, Payment, Service, ServiceCategory,
                      Therapist, WalkIn)
from ..security import current_user

router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[Depends(current_user)])


def _day(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _pct(cur: float, prev: float):
    if prev <= 0:
        return None
    return round((cur - prev) / prev * 100)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.now()
    today = _day(now)
    yesterday = _day(now - timedelta(days=1))
    month_start = today[:8] + "01"
    prev_month_end = datetime.strptime(month_start, "%Y-%m-%d") - timedelta(days=1)
    prev_month_start = _day(prev_month_end)[:8] + "01"

    def pay_sum(d1: str, d2: str):
        rows = db.query(Payment).filter(Payment.paid_at >= d1 + " 00:00:00",
                                        Payment.paid_at <= d2 + " 23:59:59").all()
        return sum(p.total_amount for p in rows), len(rows), rows

    rev_today, bills_today, pays_today = pay_sum(today, today)
    rev_yda, _, _ = pay_sum(yesterday, yesterday)
    rev_month, bills_month, _ = pay_sum(month_start, today)
    rev_prev_month, _, _ = pay_sum(prev_month_start, _day(prev_month_end))

    by_method: dict[str, float] = {}
    for p in pays_today:
        name = METHOD_NAMES.get(p.payment_method, "Cash")
        by_method[name] = by_method.get(name, 0) + p.total_amount

    wi = (db.query(WalkIn).filter(WalkIn.arrival_time >= today + " 00:00:00").all())
    waiting = [w for w in wi if w.status == 0]
    in_service = [w for w in wi if w.status == 1]
    completed = [w for w in wi if w.status == 2]
    cancelled = [w for w in wi if w.status == 3]
    wi_yda = db.query(WalkIn).filter(WalkIn.arrival_time >= yesterday + " 00:00:00",
                                     WalkIn.arrival_time <= yesterday + " 23:59:59").count()

    bks = db.query(Booking).filter(Booking.booking_date == today).all()
    bks_yda = db.query(Booking).filter(Booking.booking_date == yesterday).count()

    def bcount(*sts):
        return len([b for b in bks if b.status in sts])

    return {
        "revenue": {"totalRevenue": rev_today, "totalReceipts": bills_today,
                    "byMethod": [{"method": m, "amount": a} for m, a in by_method.items()]},
        "monthlyRevenue": {"totalRevenue": rev_month, "totalReceipts": bills_month},
        "queue": {"totalToday": len(wi), "waiting": len(waiting), "inService": len(in_service),
                  "completed": len(completed), "cancelled": len(cancelled),
                  "waitingList": [walkin_out(db, w) for w in waiting[:10]],
                  "inServiceList": [walkin_out(db, w) for w in in_service[:10]]},
        "bookings": {"total": len(bks), "pending": bcount(0), "confirmed": bcount(1),
                     "inProgress": bcount(2), "completed": bcount(3), "cancelled": bcount(4),
                     "noShow": bcount(5),
                     "upcomingList": [booking_out(db, b) for b in bks if b.status in (0, 1)][:10]},
        "trends": {"revenueDay": _pct(rev_today, rev_yda), "revenueMonth": _pct(rev_month, rev_prev_month),
                   "customers": _pct(len(wi), wi_yda), "bookings": _pct(len(bks), bks_yda)},
    }


@router.get("/dashboard/schedule")
def schedule(date: str = "", db: Session = Depends(get_db)):
    day = date or datetime.now().strftime("%Y-%m-%d")
    cats = {c.id: c.name for c in db.query(ServiceCategory).all()}
    services = {s.id: s for s in db.query(Service).all()}
    custs = {c.id: c for c in db.query(Customer).all()}
    out = []
    for t in db.query(Therapist).all():
        items = []
        # คิว walk-in ที่มอบหมายหมอนวดคนนี้
        wis = db.query(WalkIn).filter(WalkIn.arrival_time >= day + " 00:00:00",
                                      WalkIn.arrival_time <= day + " 23:59:59",
                                      WalkIn.status.in_([0, 1, 2])).all()
        for w in wis:
            cur = w.start_time or w.arrival_time
            for it in sorted(w.items, key=lambda x: x.sort_order):
                if it.therapist_id != t.id:
                    continue
                svc = services.get(it.service_id)
                dur = svc.duration_mins if svc else 60
                end = cur + timedelta(minutes=dur)
                cust = custs.get(w.customer_id)
                items.append({
                    "id": it.id, "walkInId": w.id, "queueId": w.id,
                    "startTime": iso(cur), "endTime": iso(end),
                    "serviceName": svc.name if svc else "",
                    "serviceCategory": cats.get(svc.category_id, "") if svc else "",
                    "customerName": cust.display_name if cust else "",
                    "customerNotes": cust.notes if cust else "",
                    "source": "walkin", "status": w.status,
                })
                cur = end
        # การจองที่ระบุหมอนวด (ยังไม่เช็คอิน)
        for b in db.query(Booking).filter(Booking.booking_date == day, Booking.status.in_([0, 1])).all():
            start = datetime.strptime(day + " " + b.start_time[:8], "%Y-%m-%d %H:%M:%S")
            for it in sorted(b.items, key=lambda x: x.sort_order):
                svc = services.get(it.service_id)
                dur = svc.duration_mins if svc else 60
                if it.therapist_id == t.id:
                    cust = custs.get(b.customer_id)
                    items.append({
                        "id": it.id, "bookingId": b.id, "queueId": b.id,
                        "startTime": iso(start), "endTime": iso(start + timedelta(minutes=dur)),
                        "serviceName": svc.name if svc else "",
                        "serviceCategory": cats.get(svc.category_id, "") if svc else "",
                        "customerName": cust.display_name if cust else "",
                        "customerNotes": cust.notes if cust else "",
                        "source": "booking", "status": 0,
                    })
                start += timedelta(minutes=dur)
        out.append({"id": t.id, "displayName": t.display_name, "currentStatus": t.current_status,
                    "items": items})
    return {"date": day, "therapists": out}


@router.patch("/dashboard/schedule/reschedule")
def reschedule(body: dict = Body(...), db: Session = Depends(get_db)):
    """gantt ลากย้ายคิว — บันทึกจริง: เปลี่ยนเวลา + ย้ายหมอนวด / งานที่จบหรือจ่ายแล้วห้ามย้าย"""
    from fastapi import HTTPException

    from ..models import BookingItem, WalkInItem
    from ..models import Service
    from .walkins import therapist_conflict
    src, item_id = body.get("source"), body.get("itemId")
    new_time = (body.get("startTime") or "")[:5]
    tid = body.get("therapistId")
    if src == "walkin":
        it = db.get(WalkInItem, item_id or "")
        if it is None:
            raise HTTPException(status_code=404, detail="ไม่พบคิวนี้ในระบบ")
        w = db.get(WalkIn, it.walkin_id)
        if w.status >= 2 or w.paid:
            raise HTTPException(status_code=400, detail="คิวนี้จบงาน/ชำระแล้ว ย้ายไม่ได้")
        base = (w.start_time or w.arrival_time)
        new_start = base.replace(hour=int(new_time[:2]), minute=int(new_time[3:5])) if new_time else base
        # 🚪 ตัวตรวจกลาง: ย้ายเวลา/ย้ายหมอ ต้องไม่ชนทั้งคิวอื่นและนัดจอง
        chk_tid = tid or it.therapist_id
        if chk_tid:
            svc = db.get(Service, it.service_id)
            reason = therapist_conflict(db, chk_tid, new_start,
                                        svc.duration_mins if svc else 60, exclude_walkin=w.id)
            if reason:
                raise HTTPException(status_code=409, detail=f"ย้ายไม่ได้ — หมอนวด{reason}")
        if new_time:
            w.start_time = new_start
        if tid:
            it.therapist_id = tid
    elif src == "booking":
        it = db.get(BookingItem, item_id or "")
        if it is None:
            raise HTTPException(status_code=404, detail="ไม่พบการจองนี้ในระบบ")
        b = db.get(Booking, it.booking_id)
        if b.status >= 3:
            raise HTTPException(status_code=400, detail="การจองนี้จบ/ยกเลิกแล้ว ย้ายไม่ได้")
        new_start = datetime.strptime(
            b.booking_date + " " + ((new_time + ":00") if new_time else b.start_time[:8]),
            "%Y-%m-%d %H:%M:%S")
        chk_tid = tid or it.therapist_id
        if chk_tid:
            svc = db.get(Service, it.service_id)
            reason = therapist_conflict(db, chk_tid, new_start,
                                        svc.duration_mins if svc else 60, exclude_booking=b.id)
            if reason:
                raise HTTPException(status_code=409, detail=f"ย้ายไม่ได้ — หมอนวด{reason}")
        if new_time:
            b.start_time = new_time + ":00"
        if tid:
            it.therapist_id = tid
    else:
        raise HTTPException(status_code=422, detail="ไม่รู้จักชนิดคิวนี้")
    db.commit()
    return {"ok": True}


@router.get("/queue")
def queue_display(db: Session = Depends(get_db)):
    today = datetime.now().strftime("%Y-%m-%d")
    wi = db.query(WalkIn).filter(WalkIn.arrival_time >= today + " 00:00:00").order_by(WalkIn.arrival_time).all()
    return {"waiting": [walkin_out(db, w) for w in wi if w.status == 0],
            "inService": [walkin_out(db, w) for w in wi if w.status == 1],
            "completed": [walkin_out(db, w) for w in wi if w.status == 2]}
