from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import customer_brief, iso, log_event
from ..models import Customer, Payment, PaymentItem, Therapist, User
from ..security import current_user

router = APIRouter(prefix="/api/customer", tags=["customers"], dependencies=[Depends(current_user)])


@router.get("")
def list_customers(search: str = "", pageSize: int = 50,
                   u: User = Depends(current_user), db: Session = Depends(get_db)):
    # ทุกบทบาทดูฐานลูกค้าได้ (หมอนวดจัดการลูกค้าได้ตามนโยบายร้าน) — ข้อมูลการเงินร้านยังกันไว้ที่หน้าอื่น
    q = db.query(Customer)
    if search:
        like = f"%{search}%"
        q = q.filter((Customer.display_name.ilike(like)) | (Customer.phone.ilike(like)))
    rows = q.order_by(Customer.created_at.desc()).limit(min(pageSize, 1000)).all()
    return {"items": [customer_brief(c) for c in rows], "total": q.count()}


@router.post("", status_code=201)
def create_customer(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..helpers import clean_name
    name = clean_name(body.get("displayName"))
    if not name:
        raise HTTPException(status_code=422, detail="กรุณาระบุชื่อลูกค้า")
    c = Customer(display_name=name, phone=body.get("phone"), notes=clean_name(body.get("notes")) or None, is_demo=u.is_demo)
    db.add(c)
    log_event(db, "CustomerCreated", "Customer", name, "เพิ่มลูกค้าใหม่", u.display_name)
    db.commit()
    return customer_brief(c)


def _get(db: Session, cid: str) -> Customer:
    c = db.get(Customer, cid)
    if c is None:
        raise HTTPException(status_code=404, detail="ไม่พบลูกค้า")
    return c


@router.get("/{cid}/history")
def history(cid: str, db: Session = Depends(get_db)):
    _get(db, cid)
    rows = (db.query(PaymentItem, Payment).join(Payment, Payment.id == PaymentItem.payment_id)
            .filter(Payment.customer_id == cid).order_by(Payment.paid_at.desc()).limit(50).all())
    out = []
    for it, p in rows:
        ther = db.get(Therapist, it.therapist_id) if it.therapist_id else None
        out.append({"serviceName": it.service_name, "therapistName": ther.display_name if ther else None,
                    "date": iso(p.paid_at), "receiptNo": p.receipt_no, "amount": it.unit_price * it.quantity})
    return out


@router.get("/{cid}")
def get_customer(cid: str, db: Session = Depends(get_db)):
    return customer_brief(_get(db, cid))


@router.put("/{cid}")
def update_customer(cid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    c = _get(db, cid)
    if body.get("displayName"):
        c.display_name = body["displayName"]
    c.phone = body.get("phone")
    c.notes = body.get("notes")
    db.commit()
    return customer_brief(c)


@router.delete("/{cid}", status_code=204)
def delete_customer(cid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    c = _get(db, cid)
    # ห้ามลบลูกค้าที่มีประวัติการเงิน/คิว — จะทำให้บิลเก่ากลายเป็นข้อมูลกำพร้า (ไม่มีชื่อ)
    from ..models import WalkIn
    has_history = (db.query(Payment).filter(Payment.customer_id == cid).count()
                   + db.query(WalkIn).filter(WalkIn.customer_id == cid).count()) > 0
    if has_history:
        raise HTTPException(status_code=400,
                            detail="ลบไม่ได้ — ลูกค้ารายนี้มีประวัติบิล/คิวอยู่ในระบบ (ลบแล้วรายงานการเงินจะเพี้ยน)")
    log_event(db, "CustomerDeleted", "Customer", c.display_name, "ลบลูกค้า", u.display_name)
    db.delete(c)
    db.commit()
