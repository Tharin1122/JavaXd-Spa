from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Payment, PaymentItem, Review, Service, Therapist, User
from fastapi import HTTPException

from ..security import current_user

router = APIRouter(prefix="/api", tags=["reports"], dependencies=[Depends(current_user)])


def _mgr(u: User):
    """รายงานเชิงลึก = เจ้าของ+ผู้จัดการเท่านั้น"""
    if u.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์เข้าถึงรายงานนี้")


def _fin(u: User):
    """ตัวเลขการเงิน (หน้าการเงิน/ปิดยอด) = เจ้าของ+ผู้จัดการ+รีเซป(ดู)+แคชเชียร์ — หมอนวดห้าม"""
    if u.role not in ("Owner", "Manager", "Reception", "Cashier"):
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์เข้าถึงข้อมูลการเงิน")


@router.get("/report/revenue")
def revenue(groupBy: str = "day", u: User = Depends(current_user), db: Session = Depends(get_db)):
    _fin(u)
    now = datetime.now()
    start = now - timedelta(days=365)
    pays = db.query(Payment).filter(Payment.paid_at >= start).all()
    by_day: dict[str, float] = defaultdict(float)
    for p in pays:
        by_day[p.paid_at.strftime("%Y-%m-%d")] += p.total_amount
    series = []
    for i in range(364, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        series.append({"date": d, "revenue": round(by_day.get(d, 0.0), 2)})
    total = sum(p.total_amount for p in pays)
    n = len(pays)
    return {"summary": {"totalRevenue": round(total, 2), "totalReceipts": n,
                        "avgPerReceipt": round(total / n, 2) if n else 0},
            "series": series}


@router.get("/report/summary")
def summary(u: User = Depends(current_user), db: Session = Depends(get_db)):
    _mgr(u)
    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")
    prev_end = datetime.strptime(month_start, "%Y-%m-%d") - timedelta(days=1)
    prev_start = prev_end.strftime("%Y-%m-01")

    def total(d1, d2):
        rows = db.query(Payment).filter(Payment.paid_at >= d1 + " 00:00:00",
                                        Payment.paid_at <= d2 + " 23:59:59").all()
        return sum(p.total_amount for p in rows)

    cur = total(month_start, now.strftime("%Y-%m-%d"))
    prev = total(prev_start, prev_end.strftime("%Y-%m-%d"))
    growth = round((cur - prev) / prev * 100) if prev > 0 else 0
    return {"comparison": {"revenueGrowth": growth, "currentMonth": cur, "previousMonth": prev}}


@router.get("/report/popular-services")
def popular(top: int = 10, u: User = Depends(current_user), db: Session = Depends(get_db)):
    _mgr(u)
    rows = db.query(PaymentItem).all()
    cnt: dict[str, int] = defaultdict(int)
    for it in rows:
        cnt[it.service_name] += it.quantity
    ranked = sorted(cnt.items(), key=lambda x: -x[1])[:top]
    return {"popular": [{"name": n, "count": c} for n, c in ranked]}


# หมอนวดเข้าได้ แต่กรองให้เห็นเฉพาะค่ามือของตัวเอง (เจ้าของ/ผู้จัดการเห็นทุกคน)
@router.get("/report/therapist-performance")
def therapist_performance(u: User = Depends(current_user), db: Session = Depends(get_db)):
    if u.role not in ("Owner", "Manager", "Therapist"):
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์เข้าถึงข้อมูลส่วนนี้")
    month_start = datetime.now().strftime("%Y-%m-01")
    services = {s.id: s for s in db.query(Service).all()}
    perf = []
    ther_list = db.query(Therapist).all()
    if u.role == "Therapist":  # หมอนวดเห็นค่ามือของตัวเองเท่านั้น
        ther_list = [t for t in ther_list if getattr(t, "user_id", None) == u.id]
    for t in ther_list:
        items = (db.query(PaymentItem).join(Payment, Payment.id == PaymentItem.payment_id)
                 .filter(PaymentItem.therapist_id == t.id, Payment.paid_at >= month_start + " 00:00:00").all())
        comm, jobs, revenue = 0.0, 0, 0.0
        for it in items:
            jobs += it.quantity
            revenue += it.unit_price * it.quantity
            svc = services.get(it.service_id)
            if svc and svc.commission_fixed:
                comm += svc.commission_fixed * it.quantity
            elif svc and svc.commission_rate:
                comm += it.unit_price * it.quantity * svc.commission_rate / 100
            else:
                comm += it.unit_price * it.quantity * 0.30  # ค่ามือเริ่มต้น 30%
        perf.append({"therapistId": t.id, "therapistName": t.display_name,
                     "totalJobs": jobs, "totalRevenue": round(revenue, 2),
                     "totalCommission": round(comm, 2)})
    perf.sort(key=lambda x: -x["totalCommission"])
    return {"performance": perf}


@router.get("/report/daily-close")
def daily_close(date: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """ปิดยอดสิ้นวัน (Z-Report): รายรับแยกช่องทาง + รายจ่าย + กำไรสุทธิของวัน"""
    _fin(u)
    from ..helpers import METHOD_NAMES
    from ..models import Expense, WalkIn
    day = date or datetime.now().strftime("%Y-%m-%d")
    pays = db.query(Payment).filter(Payment.paid_at >= day + " 00:00:00",
                                    Payment.paid_at <= day + " 23:59:59").all()
    by_method: dict[str, float] = {}
    for p in pays:
        m = METHOD_NAMES.get(p.payment_method, "Cash")
        by_method[m] = by_method.get(m, 0) + p.total_amount
    exps = db.query(Expense).filter(Expense.spent_at >= day + " 00:00:00",
                                    Expense.spent_at <= day + " 23:59:59").all()
    items: dict[str, dict] = {}
    for p in pays:
        for it in p.items:
            row = items.setdefault(it.service_name, {"name": it.service_name, "qty": 0, "amount": 0.0})
            row["qty"] += it.quantity
            row["amount"] += it.unit_price * it.quantity
    wi = db.query(WalkIn).filter(WalkIn.arrival_time >= day + " 00:00:00",
                                 WalkIn.arrival_time <= day + " 23:59:59").count()
    total = sum(p.total_amount for p in pays)
    discount = sum(p.discount_amount for p in pays)
    exp_total = sum(e.amount for e in exps)
    return {
        "date": day, "billCount": len(pays), "queueCount": wi,
        "totalRevenue": round(total, 2), "totalDiscount": round(discount, 2),
        "byMethod": [{"method": m, "amount": round(a, 2)} for m, a in by_method.items()],
        "topItems": sorted(items.values(), key=lambda x: -x["amount"])[:10],
        "expenses": [{"category": e.category, "amount": e.amount, "note": e.note} for e in exps],
        "expenseTotal": round(exp_total, 2), "netCash": round(total - exp_total, 2),
    }


@router.get("/review/therapists")
def review_therapists(db: Session = Depends(get_db)):
    out = []
    for t in db.query(Therapist).all():
        rows = db.query(Review).filter(Review.therapist_id == t.id).all()
        if rows:
            out.append({"therapistId": t.id, "therapistName": t.display_name,
                        "average": sum(r.rating for r in rows) / len(rows), "count": len(rows)})
    return out
