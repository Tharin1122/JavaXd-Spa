from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import iso, log_event, therapist_brief
from ..models import (Service, Therapist, TherapistLeave, TherapistSchedule,
                      TherapistService, User)
from ..security import current_user, hash_password, user_payload

router = APIRouter(prefix="/api", tags=["therapists"], dependencies=[Depends(current_user)])


def therapist_out(db: Session, t: Therapist) -> dict:
    links = db.query(TherapistService).filter(TherapistService.therapist_id == t.id).all()
    tsv = []
    for ln in links:
        svc = db.get(Service, ln.service_id)
        if svc:
            tsv.append({"service": {"id": svc.id, "name": svc.name}})
    return {
        "id": t.id, "displayName": t.display_name, "code": t.code, "phone": t.phone,
        "userId": t.user_id, "experienceYears": t.experience_years, "skillLevel": t.skill_level,
        "currentStatus": t.current_status, "avatarUrl": t.avatar_url, "therapistServices": tsv,
    }


def _get(db: Session, tid: str) -> Therapist:
    t = db.get(Therapist, tid)
    if t is None:
        raise HTTPException(status_code=404, detail="ไม่พบหมอนวด")
    return t


@router.get("/therapist")
def list_therapists(db: Session = Depends(get_db)):
    return [therapist_out(db, t) for t in db.query(Therapist).order_by(Therapist.created_at).all()]


@router.post("/therapist", status_code=201)
def create_therapist(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not (body.get("displayName") or "").strip():
        raise HTTPException(status_code=422, detail="กรุณาระบุชื่อ")
    t = Therapist(display_name=body["displayName"].strip(), code=body.get("code"), phone=body.get("phone"),
                  experience_years=int(body.get("experienceYears") or 0), skill_level=int(body.get("skillLevel") or 0))
    db.add(t)
    log_event(db, "TherapistCreated", "Therapist", t.display_name, "เพิ่มพนักงานใหม่", u.display_name)
    db.commit()
    return therapist_out(db, t)


@router.post("/therapist/from-user", status_code=201)
def therapist_from_user(body: dict = Body(...), db: Session = Depends(get_db)):
    usr = db.get(User, body.get("userId") or "")
    if usr is None:
        raise HTTPException(status_code=404, detail="ไม่พบบัญชีผู้ใช้")
    t = Therapist(display_name=usr.display_name, code=body.get("code"), phone=usr.phone, user_id=usr.id,
                  experience_years=int(body.get("experienceYears") or 0), skill_level=int(body.get("skillLevel") or 0))
    db.add(t)
    db.commit()
    return therapist_out(db, t)


@router.get("/therapist/{tid}")
def get_therapist(tid: str, db: Session = Depends(get_db)):
    return therapist_out(db, _get(db, tid))


@router.put("/therapist/{tid}")
def update_therapist(tid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    t = _get(db, tid)
    t.display_name = body.get("displayName") or t.display_name
    t.code = body.get("code")
    t.phone = body.get("phone")
    t.experience_years = int(body.get("experienceYears") or 0)
    t.skill_level = int(body.get("skillLevel") or 0)
    db.commit()
    return therapist_out(db, t)


@router.patch("/therapist/{tid}/status")
def set_status(tid: str, body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _get(db, tid)
    t.current_status = int(body.get("status") or 0)
    log_event(db, "TherapistStatusChanged", "Therapist", t.display_name, "เปลี่ยนสถานะ", u.display_name)
    db.commit()
    return therapist_out(db, t)


@router.delete("/therapist/{tid}", status_code=204)
def delete_therapist(tid: str, db: Session = Depends(get_db)):
    t = _get(db, tid)
    db.query(TherapistService).filter(TherapistService.therapist_id == tid).delete()
    db.delete(t)
    db.commit()


# ---------- กะการทำงาน ----------

@router.get("/therapist/{tid}/schedules")
def schedules(tid: str, db: Session = Depends(get_db)):
    rows = db.query(TherapistSchedule).filter(TherapistSchedule.therapist_id == tid).all()
    return [{"id": s.id, "dayOfWeek": s.day_of_week, "startTime": s.start_time,
             "endTime": s.end_time, "isWorkday": s.is_workday} for s in rows]


@router.post("/therapist/{tid}/schedules", status_code=201)
def save_schedule(tid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    _get(db, tid)
    dow = int(body.get("dayOfWeek") or 0)
    s = (db.query(TherapistSchedule)
         .filter(TherapistSchedule.therapist_id == tid, TherapistSchedule.day_of_week == dow).first())
    if s is None:
        s = TherapistSchedule(therapist_id=tid, day_of_week=dow)
        db.add(s)
    s.start_time = body.get("startTime") or "10:00:00"
    s.end_time = body.get("endTime") or "22:00:00"
    s.is_workday = bool(body.get("isWorkday", True))
    db.commit()
    return {"id": s.id, "dayOfWeek": dow}


# ---------- การลา ----------

@router.get("/therapist/{tid}/leaves")
def leaves(tid: str, db: Session = Depends(get_db)):
    rows = (db.query(TherapistLeave).filter(TherapistLeave.therapist_id == tid)
            .order_by(TherapistLeave.created_at.desc()).all())
    return [{"id": l.id, "leaveDate": l.leave_date, "leaveType": l.leave_type, "startTime": l.start_time,
             "endTime": l.end_time, "reason": l.reason, "status": l.status, "createdAt": iso(l.created_at)} for l in rows]


@router.post("/therapist/{tid}/leaves", status_code=201)
def create_leave(tid: str, body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _get(db, tid)
    l = TherapistLeave(therapist_id=tid, leave_date=body.get("leaveDate") or "",
                       leave_type=int(body.get("leaveType") or 0), start_time=body.get("startTime"),
                       end_time=body.get("endTime"), reason=body.get("reason"))
    db.add(l)
    log_event(db, "LeaveRequested", "Therapist", t.display_name, "ขอลางาน " + l.leave_date, u.display_name)
    db.commit()
    return {"id": l.id, "status": l.status}


@router.patch("/therapist/{tid}/leaves/{lid}/approve")
def approve_leave(tid: str, lid: str, db: Session = Depends(get_db)):
    l = db.get(TherapistLeave, lid)
    if l is None:
        raise HTTPException(status_code=404, detail="ไม่พบคำขอลา")
    l.status = 1
    db.commit()
    return {"id": l.id, "status": 1}


# ---------- บัญชีผู้ใช้ (หน้า staff/roles) ----------

ROLE_LIST = [
    {"id": "Owner", "name": "Owner", "description": "เจ้าของร้าน เข้าถึงทุกอย่าง"},
    {"id": "Manager", "name": "Manager", "description": "ผู้จัดการ จัดการร้านยกเว้นสิทธิ์/แพ็กเกจ"},
    {"id": "Reception", "name": "Reception", "description": "งานต้อนรับ คิว และการจอง"},
    {"id": "Therapist", "name": "Therapist", "description": "หมอนวด เห็นเฉพาะงานตัวเอง"},
    {"id": "Cashier", "name": "Cashier", "description": "แคชเชียร์ POS และคิวรอชำระ"},
]


@router.get("/user/roles")
def user_roles():
    return ROLE_LIST


@router.get("/user")
def list_users(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของ/ผู้จัดการดูรายชื่อผู้ใช้ได้")
    return [user_payload(x) for x in db.query(User).all()]


@router.post("/user", status_code=201)
def create_user(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role != "Owner":
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของร้านเพิ่มผู้ใช้ได้")
    uname = (body.get("username") or "").strip()
    if len(uname) < 3:
        raise HTTPException(status_code=422, detail="username อย่างน้อย 3 ตัว")
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(status_code=409, detail="username นี้ถูกใช้แล้ว")
    if len(body.get("password") or "") < 6:
        raise HTTPException(status_code=422, detail="รหัสผ่านอย่างน้อย 6 ตัว")
    usr = User(username=uname, password_hash=hash_password(body["password"]),
               display_name=body.get("displayName") or uname, phone=body.get("phone"),
               role=body.get("roleId") or body.get("role") or "Reception")
    db.add(usr)
    db.commit()
    return user_payload(usr)


@router.post("/user/{uid}/set-password")
def set_password(uid: str, body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    # เจ้าของตั้งรหัสให้ใครก็ได้ / คนอื่นตั้งได้เฉพาะของตัวเอง
    if u.role != "Owner" and u.id != uid:
        raise HTTPException(status_code=403, detail="ตั้งรหัสผ่านได้เฉพาะของบัญชีตัวเอง")
    usr = db.get(User, uid)
    if usr is None:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")
    if len(body.get("newPassword") or "") < 6:
        raise HTTPException(status_code=422, detail="รหัสผ่านอย่างน้อย 6 ตัว")
    usr.password_hash = hash_password(body["newPassword"])
    db.commit()
    return {"ok": True}
