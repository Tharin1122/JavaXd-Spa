from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import log_event
from ..models import Service, ServiceCategory, User
from ..security import current_user

router = APIRouter(prefix="/api", tags=["services"], dependencies=[Depends(current_user)])


def _mgr(u: User):
    """แก้ไขบริการ/คอร์ส = เจ้าของ+ผู้จัดการเท่านั้น (คนอื่นดูได้)"""
    if u.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="เฉพาะเจ้าของ/ผู้จัดการแก้ไขบริการได้")


def service_out(db: Session, s: Service) -> dict:
    cat = db.get(ServiceCategory, s.category_id) if s.category_id else None
    return {
        "id": s.id, "name": s.name, "durationMins": s.duration_mins, "bufferMins": s.buffer_mins,
        "price": s.price, "commissionRate": s.commission_rate, "commissionFixed": s.commission_fixed,
        "isActive": s.is_active, "category": {"id": cat.id, "name": cat.name} if cat else None,
    }


@router.get("/service-categories")
def categories(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name} for c in db.query(ServiceCategory).all()]


@router.get("/services")
def list_services(db: Session = Depends(get_db)):
    return [service_out(db, s) for s in db.query(Service).order_by(Service.created_at).all()]


@router.post("/services", status_code=201)
def create_service(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    _mgr(u)
    if not (body.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="กรุณาระบุชื่อบริการ")
    s = Service(
        name=body["name"].strip(), category_id=body.get("categoryId"),
        duration_mins=int(body.get("durationMins") or 60), buffer_mins=int(body.get("bufferMins") or 0),
        price=float(body.get("price") or 0), commission_rate=body.get("commissionRate"),
        commission_fixed=body.get("commissionFixed"), is_active=bool(body.get("isActive", True)),
    )
    db.add(s)
    log_event(db, "ServiceCreated", "Service", s.name, "เพิ่มบริการใหม่", u.display_name)
    db.commit()
    return service_out(db, s)


@router.put("/services/{sid}")
def update_service(sid: str, body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    _mgr(u)
    s = db.get(Service, sid)
    if s is None:
        raise HTTPException(status_code=404, detail="ไม่พบบริการ")
    s.name = body.get("name") or s.name
    s.category_id = body.get("categoryId") or s.category_id
    s.duration_mins = int(body.get("durationMins") or s.duration_mins)
    s.price = float(body.get("price") if body.get("price") is not None else s.price)
    s.commission_rate = body.get("commissionRate")
    s.commission_fixed = body.get("commissionFixed")
    if body.get("isActive") is not None:
        s.is_active = bool(body["isActive"])
    db.commit()
    return service_out(db, s)


@router.delete("/services/{sid}", status_code=204)
def delete_service(sid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    _mgr(u)
    s = db.get(Service, sid)
    if s is None:
        raise HTTPException(status_code=404, detail="ไม่พบบริการ")
    db.delete(s)
    db.commit()
