from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import log_event, next_receipt_no
from ..models import (Customer, CustomerPackage, Package, Payment, PaymentItem,
                      Promotion, User)
from ..security import current_user

router = APIRouter(prefix="/api", tags=["packages"], dependencies=[Depends(current_user)])

METHOD_CODE = {"Cash": 0, "Transfer": 1, "QR": 2, "Card": 3}


def package_out(p: Package) -> dict:
    return {"id": p.id, "name": p.name, "description": p.description, "totalSessions": p.total_sessions,
            "validityDays": p.validity_days, "price": p.price, "originalPrice": p.original_price,
            "isFeatured": p.is_featured, "soldCount": p.sold_count}


@router.get("/package")
def list_packages(db: Session = Depends(get_db)):
    return [package_out(p) for p in db.query(Package).all()]


@router.post("/package", status_code=201)
def create_package(body: dict = Body(...), db: Session = Depends(get_db)):
    if not (body.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="กรุณาระบุชื่อคอร์ส")
    p = Package(name=body["name"].strip(), description=body.get("description"),
                total_sessions=int(body.get("totalSessions") or 1), validity_days=body.get("validityDays"),
                price=float(body.get("price") or 0), original_price=body.get("originalPrice"),
                is_featured=bool(body.get("isFeatured")))
    db.add(p)
    db.commit()
    return package_out(p)


@router.put("/package/{pid}")
def update_package(pid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    p = db.get(Package, pid)
    if p is None:
        raise HTTPException(status_code=404, detail="ไม่พบคอร์ส")
    p.name = body.get("name") or p.name
    p.description = body.get("description")
    p.total_sessions = int(body.get("totalSessions") or p.total_sessions)
    p.validity_days = body.get("validityDays")
    p.price = float(body.get("price") or p.price)
    p.original_price = body.get("originalPrice")
    p.is_featured = bool(body.get("isFeatured"))
    db.commit()
    return package_out(p)


@router.delete("/package/{pid}", status_code=204)
def delete_package(pid: str, db: Session = Depends(get_db)):
    p = db.get(Package, pid)
    if p is None:
        raise HTTPException(status_code=404, detail="ไม่พบคอร์ส")
    db.delete(p)
    db.commit()


@router.get("/package/customer/{cid}")
def customer_packages(cid: str, db: Session = Depends(get_db)):
    rows = db.query(CustomerPackage).filter(CustomerPackage.customer_id == cid).all()
    return [{"id": r.id, "packageId": r.package_id, "packageName": r.package_name,
             "totalSessions": r.total_sessions, "remainingSessions": r.remaining_sessions,
             "expiresAt": r.expires_at} for r in rows]


@router.post("/package/{pid}/sell", status_code=201)
def sell_package(pid: str, body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Package, pid)
    cust = db.get(Customer, body.get("customerId") or "")
    if p is None or cust is None:
        raise HTTPException(status_code=404, detail="ไม่พบคอร์สหรือลูกค้า")
    expires = (datetime.now() + timedelta(days=p.validity_days)).strftime("%Y-%m-%d") if p.validity_days else None
    db.add(CustomerPackage(customer_id=cust.id, package_id=p.id, package_name=p.name,
                           total_sessions=p.total_sessions, remaining_sessions=p.total_sessions,
                           expires_at=expires))
    pay = Payment(receipt_no=next_receipt_no(db), customer_id=cust.id,
                  payment_method=METHOD_CODE.get(body.get("paymentMethod"), 0),
                  total_amount=p.price, paid_amount=p.price)
    pay.items.append(PaymentItem(service_name=f"คอร์ส {p.name}", quantity=1, unit_price=p.price))
    db.add(pay)
    p.sold_count += 1
    cust.total_spent += p.price
    log_event(db, "PaymentCreated", "Payment", pay.receipt_no, f"ขายคอร์ส {p.name} ให้ {cust.display_name}", u.display_name)
    db.commit()
    return {"receiptNo": pay.receipt_no, "customerPackage": True}


@router.post("/package/redeem/{cpid}")
def redeem(cpid: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    cp = db.get(CustomerPackage, cpid)
    if cp is None:
        raise HTTPException(status_code=404, detail="ไม่พบคอร์สของลูกค้า")
    if cp.remaining_sessions <= 0:
        raise HTTPException(status_code=400, detail="คอร์สนี้ใช้ครบแล้ว")
    cp.remaining_sessions -= 1
    log_event(db, "PackageRedeemed", "Package", cp.package_name,
              f"ตัดคอร์ส เหลือ {cp.remaining_sessions} ครั้ง", u.display_name)
    db.commit()
    return {"remainingSessions": cp.remaining_sessions}


# ---------- โปรโมชัน & คูปอง ----------

def promo_out(x: Promotion) -> dict:
    return {"id": x.id, "title": x.title, "campaign": x.campaign, "code": x.code,
            "discountPercent": x.discount_percent, "discountAmount": x.discount_amount,
            "description": x.description, "quota": x.quota, "usedCount": x.used_count,
            "expiresAt": x.expires_at, "isActive": x.is_active,
            "label": x.title or x.campaign or x.code}


@router.get("/promotion")
def list_promotions(db: Session = Depends(get_db)):
    promos = db.query(Promotion).filter(Promotion.kind == "promo").all()
    coupons = db.query(Promotion).filter(Promotion.kind == "coupon").all()
    sold = db.query(Package).with_entities(Package.sold_count).all()
    return {
        "promos": [promo_out(x) for x in promos],
        "coupons": [promo_out(x) for x in coupons],
        "summary": {"activePromos": len([x for x in promos if x.is_active]),
                    "totalSold": sum(s[0] for s in sold),
                    "couponsUsed": sum(x.used_count for x in coupons)},
    }


def _fill(x: Promotion, body: dict) -> None:
    x.title = body.get("title") or x.title
    x.campaign = body.get("campaign") or x.campaign
    x.code = (body.get("code") or "").upper() or x.code
    x.discount_percent = body.get("discountPercent")
    x.discount_amount = body.get("discountAmount")
    x.description = body.get("description")
    x.quota = int(body.get("quota") or 0)
    x.expires_at = body.get("expiresAt")


@router.post("/promotion", status_code=201)
def create_promo(body: dict = Body(...), db: Session = Depends(get_db)):
    x = Promotion(kind="promo")
    _fill(x, body)
    db.add(x)
    db.commit()
    return promo_out(x)


@router.post("/promotion/coupon", status_code=201)
def create_coupon(body: dict = Body(...), db: Session = Depends(get_db)):
    x = Promotion(kind="coupon")
    _fill(x, body)
    if not x.code:
        raise HTTPException(status_code=422, detail="กรุณาระบุรหัสคูปอง")
    db.add(x)
    db.commit()
    return promo_out(x)


@router.put("/promotion/coupon/{xid}")
def update_coupon(xid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    return _update(xid, body, db)


@router.put("/promotion/{xid}")
def update_promo(xid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    return _update(xid, body, db)


def _update(xid: str, body: dict, db: Session):
    x = db.get(Promotion, xid)
    if x is None:
        raise HTTPException(status_code=404, detail="ไม่พบโปรโมชัน")
    _fill(x, body)
    db.commit()
    return promo_out(x)


@router.delete("/promotion/{xid}", status_code=204)
def delete_promo(xid: str, db: Session = Depends(get_db)):
    x = db.get(Promotion, xid)
    if x is None:
        raise HTTPException(status_code=404, detail="ไม่พบโปรโมชัน")
    db.delete(x)
    db.commit()


@router.get("/promotion/validate/{code}")
def validate_coupon(code: str, db: Session = Depends(get_db)):
    x = db.query(Promotion).filter(Promotion.code == code.upper(), Promotion.is_active == True).first()  # noqa: E712
    if x is None:
        raise HTTPException(status_code=404, detail="ไม่พบรหัสคูปองนี้")
    if x.expires_at and x.expires_at < datetime.now().strftime("%Y-%m-%d"):
        raise HTTPException(status_code=400, detail="คูปองหมดอายุแล้ว")
    if x.quota and x.used_count >= x.quota:
        raise HTTPException(status_code=400, detail="คูปองถูกใช้ครบโควต้าแล้ว")
    return promo_out(x)


@router.post("/promotion/redeem-coupon/{code}")
def redeem_coupon(code: str, db: Session = Depends(get_db)):
    x = db.query(Promotion).filter(Promotion.code == code.upper()).first()
    if x is None:
        raise HTTPException(status_code=404, detail="ไม่พบรหัสคูปองนี้")
    x.used_count += 1
    db.commit()
    return {"usedCount": x.used_count}
