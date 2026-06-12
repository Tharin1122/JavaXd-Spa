from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import log_event, next_queue_no, walkin_out
from ..models import (Booking, Customer, Service, Therapist, TherapistService,
                      User, WalkIn, WalkInItem)
from ..security import current_user

router = APIRouter(prefix="/api/walk-in", tags=["walk-in"], dependencies=[Depends(current_user)])


def _suggest_therapist(db: Session, w: WalkIn) -> dict | None:
    """คิวรอ: หาหมอที่ทำบริการนี้ได้ — ว่างตอนนี้ (callable) หรือใกล้ว่างที่สุด (nextFree)"""
    svc_dur = {s.id: s.duration_mins for s in db.query(Service).all()}
    sids = [it.service_id for it in w.items]
    total_mins = sum(svc_dur.get(s, 60) for s in sids) or 60
    links: dict[str, set] = {}
    for l in db.query(TherapistService).all():
        links.setdefault(l.therapist_id, set()).add(l.service_id)
    out = {"callable": False, "suggested": None, "nextFree": None}
    soonest = None
    for t in db.query(Therapist).all():
        skills = links.get(t.id)
        if skills and not all(s in skills for s in sids):
            continue  # ทำบริการนี้ไม่ได้
        if t.current_status == 0 and therapist_conflict(db, t.id, datetime.now(), total_mins,
                                                        exclude_walkin=w.id, exclude_booking=w.booking_id) is None:
            out["callable"] = True
            out["suggested"] = {"id": t.id, "displayName": t.display_name}
            return out
        # กำลังบริการ → คำนวณเวลาว่างโดยประมาณจากคิวที่ทำอยู่
        busy = (db.query(WalkIn).join(WalkInItem, WalkInItem.walkin_id == WalkIn.id)
                .filter(WalkInItem.therapist_id == t.id, WalkIn.status == 1).first())
        if busy:
            cur = busy.start_time or busy.arrival_time
            end = cur + timedelta(minutes=sum(svc_dur.get(i.service_id, 60) for i in busy.items))
            end = max(end, datetime.now())
            if soonest is None or end < soonest[1]:
                soonest = (t, end)
    if soonest:
        out["nextFree"] = {"id": soonest[0].id, "displayName": soonest[0].display_name,
                           "freeAt": soonest[1].strftime("%H:%M")}
    return out


@router.get("")
def list_walkins(date: str = "", pageSize: int = 100, db: Session = Depends(get_db)):
    day = date or datetime.now().strftime("%Y-%m-%d")
    q = (db.query(WalkIn).filter(WalkIn.arrival_time >= day + " 00:00:00",
                                 WalkIn.arrival_time <= day + " 23:59:59")
         .order_by(WalkIn.arrival_time))
    rows = q.limit(min(pageSize, 500)).all()
    items = []
    for w in rows:
        o = walkin_out(db, w)
        if w.status == 0:  # คิวรอ → แนบคำแนะนำหมอ (เรียกได้เลย / ใครใกล้ว่าง)
            o["assign"] = _suggest_therapist(db, w)
        items.append(o)
    return {"items": items, "total": q.count()}


def therapist_conflict(db: Session, tid: str, start_dt: datetime, duration_mins: int = 60,
                       exclude_walkin: str | None = None, exclude_booking: str | None = None) -> str | None:
    """🚪 ตัวตรวจกลางตัวเดียว — ทุกประตูที่ผูกหมอนวดกับเวลา (สร้างคิว/assign/start/ย้ายคิว/สร้างจอง/เช็คอิน)
    ต้องเรียกผ่านนี่เท่านั้น คืน None=ว่าง หรือข้อความเหตุผลที่ชน"""
    end_dt = start_dt + timedelta(minutes=duration_mins)
    svc_dur = {s.id: s.duration_mins for s in db.query(Service).all()}
    # 1) ชนกับคิว walk-in ที่ยังมีชีวิตของหมอคนนี้
    #    - กำลังบริการ (status 1): นับทุกใบไม่จำกัดวัน — คิวค้างข้ามคืนที่ยังไม่กดจบ = หมอยังไม่ว่าง
    #    - รอคิว (status 0): เฉพาะของวันเดียวกับเวลาที่เช็ค
    day_s = start_dt.strftime("%Y-%m-%d")
    live = (db.query(WalkIn).filter(WalkIn.status == 1).all() +
            db.query(WalkIn).filter(WalkIn.arrival_time >= day_s + " 00:00:00",
                                    WalkIn.arrival_time <= day_s + " 23:59:59",
                                    WalkIn.status == 0).all())
    for w in live:
        if w.id == exclude_walkin:
            continue
        cur = w.start_time or w.arrival_time
        for it in sorted(w.items, key=lambda x: x.sort_order):
            dur = svc_dur.get(it.service_id, 60)
            item_end = cur + timedelta(minutes=dur)
            # คิวที่กำลังบริการแต่ยังไม่กด 'จบงาน' = หมอยังอยู่บนเตียงจริง แม้เลย/ชนเวลาตามตารางพอดี
            if w.status == 1:
                item_end = max(item_end, datetime.now() + timedelta(minutes=1))
            if it.therapist_id == tid and start_dt < item_end and cur < end_dt:
                return f"ติดคิว {w.queue_no} ช่วง {cur:%H:%M}"
            cur += timedelta(minutes=dur)
    # 2) ชนกับนัดจอง (รอ/ยืนยัน ยังไม่เช็คอิน) ของหมอคนนี้
    for b in db.query(Booking).filter(Booking.booking_date == day_s,
                                      Booking.status.in_([0, 1]), Booking.checked_in == False).all():  # noqa: E712
        if b.id == exclude_booking:
            continue
        try:
            b_start = datetime.strptime(day_s + " " + b.start_time[:8], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        for it in sorted(b.items, key=lambda x: x.sort_order):
            dur = svc_dur.get(it.service_id, 60)
            if it.therapist_id == tid and start_dt < b_start + timedelta(minutes=dur) and b_start < end_dt:
                return f"มีนัดจอง {b.booking_no} เวลา {b.start_time[:5]} น."
            b_start += timedelta(minutes=dur)
    return None


def _therapist_conflict(db: Session, tid: str, duration_mins: int = 60) -> str | None:
    """เช็คจาก 'ตอนนี้' (ใช้ตอน assign/start)"""
    return therapist_conflict(db, tid, datetime.now(), duration_mins)


@router.get("/available-therapists")
def available_therapists(request: Request, db: Session = Depends(get_db)):
    service_ids = request.query_params.getlist("serviceIds")
    free = db.query(Therapist).filter(Therapist.current_status == 0).all()
    durations = {s.id: s.duration_mins for s in db.query(Service).all()}
    out = {}
    for sid in service_ids:
        lst = []
        for t in free:
            links = db.query(TherapistService).filter(TherapistService.therapist_id == t.id).all()
            # ไม่ได้กำหนดทักษะ = ทำได้ทุกบริการ + ต้องไม่ติดคิว/นัดในช่วงเวลาบริการนี้
            if (not links or any(l.service_id == sid for l in links)) \
                    and _therapist_conflict(db, t.id, durations.get(sid, 60)) is None:
                lst.append({"id": t.id, "displayName": t.display_name, "code": t.code})
        out[sid] = lst
    return out


@router.get("/therapist-availability")
def therapist_availability(date: str = "", time: str = "", serviceId: str = "",
                           db: Session = Depends(get_db)):
    """หมอแต่ละคน ว่าง/ไม่ว่างเพราะอะไร ถึงเมื่อไหร่ — สำหรับ dropdown จอง/เข้าคิว"""
    svc = db.get(Service, serviceId) if serviceId else None
    dur = svc.duration_mins if svc else 60
    try:
        start_dt = (datetime.strptime(f"{date} {time[:5]}", "%Y-%m-%d %H:%M")
                    if date and time else datetime.now())
    except ValueError:
        start_dt = datetime.now()
    svc_dur = {s.id: s.duration_mins for s in db.query(Service).all()}
    links: dict[str, set] = {}
    for l in db.query(TherapistService).all():
        links.setdefault(l.therapist_id, set()).add(l.service_id)
    out = []
    for t in db.query(Therapist).all():
        skills = links.get(t.id)
        if serviceId and skills and serviceId not in skills:
            out.append({"id": t.id, "displayName": t.display_name, "free": False,
                        "reason": "ไม่ได้ทำบริการนี้", "freeAt": None})
            continue
        reason = therapist_conflict(db, t.id, start_dt, dur)
        free_at = None
        if reason:
            # ประมาณเวลาว่าง: จากคิวที่ทำค้างอยู่ของหมอคนนี้
            busy = (db.query(WalkIn).join(WalkInItem, WalkInItem.walkin_id == WalkIn.id)
                    .filter(WalkInItem.therapist_id == t.id, WalkIn.status == 1).first())
            if busy:
                cur = busy.start_time or busy.arrival_time
                end = max(cur + timedelta(minutes=sum(svc_dur.get(i.service_id, 60) for i in busy.items)),
                          datetime.now())
                free_at = end.strftime("%H:%M")
        out.append({"id": t.id, "displayName": t.display_name, "free": reason is None,
                    "reason": reason, "freeAt": free_at})
    return out


@router.post("", status_code=201)
def create_walkin(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    cust = db.get(Customer, body.get("customerId") or "")
    if cust is None:
        raise HTTPException(status_code=404, detail="ไม่พบลูกค้า")
    items = body.get("items") or []
    if not items:
        raise HTTPException(status_code=422, detail="ต้องมีอย่างน้อย 1 บริการ")
    w = WalkIn(queue_no=next_queue_no(db), customer_id=cust.id, is_demo=u.is_demo,
               booking_id=body.get("bookingId"), notes=body.get("notes"))
    for i, it in enumerate(items):
        svc = db.get(Service, it.get("serviceId") or "")
        if svc is None:
            raise HTTPException(status_code=404, detail="ไม่พบบริการที่เลือก")
        # 🚪 ประตูที่เคยรั่ว: สร้างคิวพร้อมระบุหมอ (รวมเช็คอินจากนัด) ต้องผ่านตัวตรวจกลาง
        tid = it.get("therapistId")
        if tid:
            t = db.get(Therapist, tid)
            reason = therapist_conflict(db, tid, datetime.now(), svc.duration_mins,
                                        exclude_booking=body.get("bookingId"))
            if reason:
                raise HTTPException(status_code=409,
                                    detail=f"{t.display_name if t else 'หมอนวด'} {reason} — เลือกคนอื่นหรือปล่อยให้ระบบจัด")
        w.items.append(WalkInItem(service_id=svc.id, therapist_id=tid,
                                  sort_order=int(it.get("sortOrder") or i), price=svc.price))
    db.add(w)
    # เช็คอินจากนัด → ทำเครื่องหมายการจอง
    if body.get("bookingId"):
        bk = db.get(Booking, body["bookingId"])
        if bk:
            bk.checked_in = True
            if bk.status in (0, 1):
                bk.status = 2
    log_event(db, "QueueUpdated", "WalkIn", w.queue_no, f"{cust.display_name} เข้าคิว", u.display_name)
    db.commit()
    out = walkin_out(db, w)
    out["walkInId"] = w.id
    return out


def _get(db: Session, wid: str) -> WalkIn:
    w = db.get(WalkIn, wid)
    if w is None:
        raise HTTPException(status_code=404, detail="ไม่พบคิวนี้")
    return w


@router.get("/{wid}")
def get_walkin(wid: str, db: Session = Depends(get_db)):
    return walkin_out(db, _get(db, wid))


@router.patch("/{wid}/assign")
def assign(wid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    w = _get(db, wid)
    tid = body.get("therapistId")
    t = db.get(Therapist, tid or "")
    if t is None:
        raise HTTPException(status_code=404, detail="ไม่พบหมอนวด")
    # 🚪 กันคิวซ้อนผ่านตัวตรวจกลาง: ทั้งคิวที่ทำอยู่และนัดจองที่จะทับ
    svc_dur = {s.id: s.duration_mins for s in db.query(Service).all()}
    total_mins = sum(svc_dur.get(it.service_id, 60) for it in w.items if it.therapist_id is None) or 60
    reason = therapist_conflict(db, tid, datetime.now(), total_mins,
                                exclude_walkin=wid, exclude_booking=w.booking_id)
    if t.current_status != 0 or reason:
        raise HTTPException(status_code=409,
                            detail=f"{t.display_name} {reason or 'กำลังให้บริการคิวอื่นอยู่'} — เลือกหมอนวดที่ว่าง")
    for it in w.items:
        if it.therapist_id is None:
            it.therapist_id = tid
    db.commit()
    return walkin_out(db, w)


@router.patch("/{wid}/start")
def start(wid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    w = _get(db, wid)
    if w.status == 3:
        raise HTTPException(status_code=400, detail="คิวนี้ถูกยกเลิกแล้ว")
    if w.status == 0:
        # ปิดรูรั่ว: คิวที่มีหมอนวดติดมาแล้ว (เช่นเช็คอินจากนัด) กด start ตรงๆ ต้องเช็คว่าหมอว่างจริง
        svc_dur = {s.id: s.duration_mins for s in db.query(Service).all()}
        for it in w.items:
            if it.therapist_id:
                t = db.get(Therapist, it.therapist_id)
                reason = therapist_conflict(db, it.therapist_id, datetime.now(),
                                            svc_dur.get(it.service_id, 60), exclude_walkin=w.id)
                if t and (t.current_status != 0 or reason):
                    raise HTTPException(status_code=409,
                                        detail=f"{t.display_name} {reason or 'ไม่ว่างขณะนี้'} — เปลี่ยนหมอนวดหรือรอก่อน")
        w.status = 1
        w.start_time = datetime.now()
        for it in w.items:
            if it.therapist_id:
                t = db.get(Therapist, it.therapist_id)
                if t:
                    t.current_status = 1  # ไม่ว่าง
        log_event(db, "QueueUpdated", "WalkIn", w.queue_no, "เริ่มให้บริการ", u.display_name)
        db.commit()
    return walkin_out(db, w)


@router.patch("/{wid}/complete")
def complete(wid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    w = _get(db, wid)
    if w.status == 3:
        raise HTTPException(status_code=400, detail="คิวนี้ถูกยกเลิกแล้ว")
    if w.status == 0:
        raise HTTPException(status_code=409, detail="คิวนี้ยังไม่เริ่มบริการ — ต้องกด 'เริ่ม' ก่อนถึงจบงานได้ (ตามขั้นตอน)")
    if w.status == 1:
        w.status = 2
        w.end_time = datetime.now()
        for it in w.items:
            if it.therapist_id:
                t = db.get(Therapist, it.therapist_id)
                if t:
                    t.current_status = 0  # ว่าง
        log_event(db, "QueueUpdated", "WalkIn", w.queue_no, "จบงานบริการ", u.display_name)
        db.commit()
    return walkin_out(db, w)


@router.patch("/{wid}/cancel")
def cancel(wid: str, body: dict | None = Body(default=None), u: User = Depends(current_user),
           db: Session = Depends(get_db)):
    w = _get(db, wid)
    # state machine: ยกเลิกได้เฉพาะ รอคิว(0)/กำลังบริการ(1) — งานที่จบ/จ่ายแล้วยกเลิกไม่ได้
    if w.status == 2 or w.paid:
        raise HTTPException(status_code=409, detail="คิวนี้จบงานแล้ว ยกเลิกไม่ได้ — ถ้าเงินผิดให้แก้ที่บิล")
    if w.status == 3:
        raise HTTPException(status_code=409, detail="คิวนี้ถูกยกเลิกไปแล้ว")
    # ถ้ายกเลิกตอนกำลังบริการ → คืนหมอนวดเป็นว่าง
    if w.status == 1:
        for it in w.items:
            if it.therapist_id:
                t = db.get(Therapist, it.therapist_id)
                if t:
                    t.current_status = 0
    w.status = 3
    w.cancel_reason = (body or {}).get("reason")
    log_event(db, "QueueUpdated", "WalkIn", w.queue_no, "ยกเลิกคิว", u.display_name)
    db.commit()
    return walkin_out(db, w)
