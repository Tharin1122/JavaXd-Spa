import re
from collections import Counter

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import customer_or_ghost, iso, kv_get, log_event, next_receipt_no
from ..models import Booking, Customer, Payment, PaymentItem, Service, User, WalkIn
from ..security import current_user

router = APIRouter(prefix="/api/payment", tags=["payments"], dependencies=[Depends(current_user)])


# ---------- Thai QR PromptPay (EMVCo มาตรฐานธนาคารแห่งประเทศไทย) ----------
# สร้าง payload ในเครื่อง 100% — ฟรี ไม่ผูก gateway เงินเข้าบัญชี PromptPay ของร้านตรงๆ
# (gateway แบบมี API ยืนยันยอดอัตโนมัติ = ฟีเจอร์รออนุมัติ ดู wiki: payment-gateway-comparison)

def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def _crc16_ccitt(data: str) -> str:
    crc = 0xFFFF
    for ch in data.encode("ascii"):
        crc ^= ch << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def promptpay_payload(pp_id: str, amount: float) -> str:
    """สร้าง Thai QR (Tag 29) จากเบอร์มือถือ/เลขบัตรประชาชน + จำนวนเงิน"""
    digits = re.sub(r"\D", "", pp_id)
    if len(digits) == 10 and digits.startswith("0"):      # เบอร์มือถือ → 0066XXXXXXXXX
        acct = _tlv("01", "0066" + digits[1:])
    elif len(digits) == 13:                                # เลขบัตรประชาชน
        acct = _tlv("02", digits)
    else:
        raise HTTPException(status_code=422, detail="PromptPay ID ต้องเป็นเบอร์มือถือ 10 หลักหรือเลขบัตรประชาชน 13 หลัก")
    merchant = _tlv("00", "A000000677010111") + acct
    payload = (
        _tlv("00", "01")                 # payload format
        + _tlv("01", "12")               # dynamic QR (มียอดเงิน)
        + _tlv("29", merchant)           # merchant account (PromptPay AID)
        + _tlv("53", "764")              # สกุลเงิน THB
        + _tlv("54", f"{amount:.2f}")    # จำนวนเงิน
        + _tlv("58", "TH")               # ประเทศ
    )
    payload += "6304"
    return payload + _crc16_ccitt(payload)


@router.get("/qr")
def payment_qr(amount: float, db: Session = Depends(get_db)):
    if amount <= 0:
        raise HTTPException(status_code=422, detail="จำนวนเงินต้องมากกว่า 0")
    settings = kv_get(db, "settings", {})
    DEMO_PP = "0000000000"  # เลขที่เป็นไปไม่ได้ที่จะลงทะเบียนพร้อมเพย์ → สแกนได้แต่ธนาคารเด้ง = ไม่มีใครเสียเงินจริง
    raw = (settings.get("promptpayId") or "").strip()
    digits = re.sub(r"\D", "", raw)
    # ถ้าเบอร์ที่ตั้งไว้ผิดรูปแบบ (ไม่ใช่ 10/13 หลัก) → ใช้เลขเดโม่แทน ไม่ทำให้ POS พัง
    valid = (len(digits) == 10 and digits.startswith("0")) or len(digits) == 13
    pp_id = digits if valid else DEMO_PP
    return {"payload": promptpay_payload(pp_id, amount), "promptpayId": pp_id,
            "amount": amount, "isDemo": (not valid)}


def payment_out(db: Session, p: Payment) -> dict:
    return {
        "id": p.id, "receiptNo": p.receipt_no, "walkInId": p.walkin_id, "bookingId": p.booking_id,
        "customer": customer_or_ghost(db, p.customer_id), "paymentMethod": p.payment_method,
        "discountAmount": p.discount_amount, "totalAmount": p.total_amount,
        "paidAmount": p.paid_amount, "paidAt": iso(p.paid_at),
        "items": [{"serviceName": it.service_name, "quantity": it.quantity, "unitPrice": it.unit_price}
                  for it in p.items],
    }


@router.get("")
def list_payments(pageSize: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    rows = (db.query(Payment).order_by(Payment.paid_at.desc())
            .offset(max(offset, 0)).limit(min(pageSize, 500)).all())
    return {"items": [payment_out(db, p) for p in rows], "total": db.query(Payment).count()}


@router.post("", status_code=201)
def create_payment(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    # รับเงิน/ออกบิล = เจ้าของ/ผู้จัดการ/รีเซป/แคชเชียร์ — หมอนวดไม่แตะเงิน
    if u.role == "Therapist":
        raise HTTPException(status_code=403, detail="หมอนวดไม่มีสิทธิ์รับชำระเงิน")
    p = Payment(receipt_no=next_receipt_no(db), is_demo=u.is_demo, payment_method=int(body.get("paymentMethod") or 0),
                discount_amount=float(body.get("discountAmount") or 0),
                paid_amount=float(body.get("paidAmount") or 0))
    gross = 0.0
    cust = None
    if body.get("walkInId"):
        w = db.get(WalkIn, body["walkInId"])
        if w is None:
            raise HTTPException(status_code=404, detail="ไม่พบคิวที่จะชำระ")
        if w.paid:
            raise HTTPException(status_code=400, detail="คิวนี้ชำระเงินแล้ว")
        if w.status == 1:
            # กฎ Tharin: ต้อง "กำลังให้บริการ" ก่อนแล้วค่อยจ่าย → จ่ายระหว่างบริการ = จบงานอัตโนมัติ
            from datetime import datetime as _dt

            from ..models import Therapist
            w.status = 2
            w.end_time = _dt.now()
            for it in w.items:
                if it.therapist_id:
                    t = db.get(Therapist, it.therapist_id)
                    if t:
                        t.current_status = 0  # หมอเคลียร์คิว ว่างรับงานต่อ
            log_event(db, "QueueUpdated", "WalkIn", w.queue_no, "จบงานอัตโนมัติเมื่อรับชำระ", u.display_name)
        elif w.status != 2:
            raise HTTPException(status_code=409,
                                detail="คิวนี้ยังไม่เริ่มบริการ — ต้องเริ่มบริการก่อนถึงเก็บเงินได้ (ห้ามจ่ายก่อนขึ้นเตียง)")
        p.walkin_id = w.id
        p.customer_id = w.customer_id
        cust = db.get(Customer, w.customer_id)
        counted = Counter()
        for it in w.items:
            counted[(it.service_id, it.price, it.therapist_id)] += 1
        for (sid, price, tid), qty in counted.items():
            svc = db.get(Service, sid)
            p.items.append(PaymentItem(service_id=sid, service_name=svc.name if svc else "บริการ",
                                       therapist_id=tid, quantity=qty, unit_price=price))
            gross += price * qty
        w.paid = True
    elif body.get("bookingId"):
        b = db.get(Booking, body["bookingId"])
        if b is None:
            raise HTTPException(status_code=404, detail="ไม่พบการจองที่จะชำระ")
        p.booking_id = b.id
        p.customer_id = b.customer_id
        cust = db.get(Customer, b.customer_id)
        for it in b.items:
            svc = db.get(Service, it.service_id)
            p.items.append(PaymentItem(service_id=it.service_id, service_name=svc.name if svc else "บริการ",
                                       therapist_id=it.therapist_id, quantity=1, unit_price=it.price))
            gross += it.price
        b.status = 3
    else:
        raise HTTPException(status_code=422, detail="ต้องระบุ walkInId หรือ bookingId")

    p.total_amount = max(0.0, gross - p.discount_amount)
    if p.paid_amount <= 0:
        p.paid_amount = p.total_amount
    if cust:
        cust.total_visits += 1
        cust.total_spent += p.total_amount
    db.add(p)
    log_event(db, "PaymentCreated", "Payment", p.receipt_no,
              f"รับชำระ {p.total_amount:,.0f} บาท", u.display_name)
    db.commit()
    return payment_out(db, p)


@router.get("/{pid}")
def get_payment(pid: str, db: Session = Depends(get_db)):
    p = db.get(Payment, pid)
    if p is None:
        raise HTTPException(status_code=404, detail="ไม่พบใบเสร็จ")
    return payment_out(db, p)
