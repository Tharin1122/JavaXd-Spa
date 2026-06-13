from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import iso, kv_get, kv_set, log_event
from ..models import Expense, Review, TimelineEvent, User
from ..security import current_user

router = APIRouter(prefix="/api", tags=["misc"], dependencies=[Depends(current_user)])


# ---------- สำรองข้อมูล (Owner เท่านั้น) ----------

@router.get("/backup")
def download_backup(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """ดาวน์โหลดไฟล์ฐานข้อมูลทั้งหมด — กดเก็บทุกสัปดาห์ = ประกันชีวิตของร้าน"""
    if u.role != "Owner":
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของร้านเท่านั้นที่สำรองข้อมูลได้")
    import shutil
    import tempfile
    from pathlib import Path

    from fastapi.responses import FileResponse
    src = Path("mms.db").resolve()
    if not src.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ฐานข้อมูล")
    tmp = Path(tempfile.gettempdir()) / f"mms-backup-{datetime.now():%Y%m%d-%H%M}.db"
    shutil.copy2(src, tmp)  # copy ก่อนส่ง กันไฟล์ล็อกระหว่างเขียน
    log_event(db, "BackupDownloaded", "System", None, "ดาวน์โหลดสำรองข้อมูล", u.display_name)
    db.commit()
    return FileResponse(tmp, filename=tmp.name, media_type="application/octet-stream")


# ---------- timeline / logs ----------

@router.get("/timeline")
def timeline(pageSize: int = 20, offset: int = 0, dateFrom: str = "", dateTo: str = "",
             db: Session = Depends(get_db)):
    q = db.query(TimelineEvent)
    # กรองช่วงเวลา: รับ "YYYY-MM-DDTHH:MM" (datetime-local) หรือ "YYYY-MM-DD"
    if dateFrom:
        q = q.filter(TimelineEvent.created_at >= dateFrom.replace("T", " "))
    if dateTo:
        to_s = dateTo.replace("T", " ")
        q = q.filter(TimelineEvent.created_at <= (to_s + " 23:59:59" if len(to_s) == 10 else to_s))
    q = q.order_by(TimelineEvent.created_at.desc())
    rows = q.offset(max(offset, 0)).limit(min(pageSize, 500)).all()
    return {"total": q.count(),
            "items": [{"id": e.id, "eventType": e.event_type, "entityType": e.entity_type,
                       "entityLabel": e.entity_label, "description": e.description,
                       "actorName": e.actor_name, "createdAt": iso(e.created_at)} for e in rows]}


# ---------- expense ----------

@router.get("/expense")
def expenses(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของ/ผู้จัดการดูรายจ่ายได้")
    month_start = datetime.now().strftime("%Y-%m-01")
    rows = db.query(Expense).filter(Expense.spent_at >= month_start + " 00:00:00").order_by(Expense.spent_at.desc()).all()
    by_cat: dict[str, float] = {}
    for e in rows:
        by_cat[e.category] = by_cat.get(e.category, 0) + e.amount
    return {"total": sum(e.amount for e in rows),
            "byCategory": [{"category": c, "amount": a} for c, a in by_cat.items()],
            "items": [{"id": e.id, "category": e.category, "amount": e.amount,
                       "note": e.note, "spentAt": iso(e.spent_at)} for e in rows]}


@router.post("/expense", status_code=201)
def create_expense(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของ/ผู้จัดการบันทึกรายจ่ายได้")
    amt = float(body.get("amount") or 0)
    if amt <= 0:
        raise HTTPException(status_code=422, detail="จำนวนเงินต้องมากกว่า 0")
    spent = body.get("spentAt")
    e = Expense(category=body.get("category") or "อื่นๆ", amount=amt, note=body.get("note"), is_demo=u.is_demo,
                spent_at=datetime.fromisoformat(spent) if spent else datetime.now())
    db.add(e)
    log_event(db, "ExpenseCreated", "Expense", e.category, f"บันทึกรายจ่าย {amt:,.0f} บาท", u.display_name)
    db.commit()
    return {"id": e.id, "amount": e.amount}


# ---------- reviews ----------

@router.post("/review", status_code=201)
def create_review(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = Review(customer_id=body.get("customerId"), therapist_id=body.get("therapistId"),
               payment_id=body.get("paymentId"), rating=int(body.get("rating") or 5),
               comment=body.get("comment"))
    db.add(r)
    log_event(db, "ReviewCreated", "Review", None, f"รีวิว {r.rating} ดาว", u.display_name)
    db.commit()
    return {"id": r.id, "rating": r.rating}


# ---------- settings / role matrix / subscription ----------

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return kv_get(db, "settings", {})


@router.put("/settings")
def put_settings(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของ/ผู้จัดการแก้ตั้งค่าร้านได้")
    kv_set(db, "settings", body)
    log_event(db, "SettingsUpdated", "Settings", None, "บันทึกการตั้งค่าร้าน", u.display_name)
    db.commit()
    return body


@router.get("/role/matrix")
def get_matrix(db: Session = Depends(get_db)):
    return kv_get(db, "role_matrix", [])


@router.put("/role/matrix")
def put_matrix(body: list = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role != "Owner":
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของร้านตั้งสิทธิ์ได้")
    kv_set(db, "role_matrix", body)
    log_event(db, "RoleMatrixUpdated", "Settings", None, "บันทึกสิทธิ์การใช้งาน", u.display_name)
    db.commit()
    return body


@router.get("/subscription")
def get_subscription(db: Session = Depends(get_db)):
    return kv_get(db, "subscription", {"planType": "Free", "trialEndsAt": None})


@router.post("/subscription/select")
def select_subscription(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    # ⚠ เวอร์ชัน local: เปลี่ยนแพ็กเกจเป็นการบันทึกสถานะเท่านั้น ไม่มีการเรียกเก็บเงินจริง
    sub = {"planType": body.get("planType") or "Starter", "trial": bool(body.get("trial")),
           "trialEndsAt": None, "selectedAt": datetime.now().isoformat(timespec="seconds")}
    kv_set(db, "subscription", sub)
    log_event(db, "SubscriptionChanged", "Subscription", sub["planType"], "เปลี่ยนแพ็กเกจ (โหมดทดลอง ไม่มีค่าใช้จ่าย)", u.display_name)
    db.commit()
    return sub
