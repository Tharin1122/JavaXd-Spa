import os
import time as _time
from contextlib import asynccontextmanager
from pathlib import Path

# เซิร์ฟเวอร์ cloud (Render ฯลฯ) เป็น UTC — ร้านอยู่ไทย: บังคับโซนเวลาไทยทั้งโปรเซส
# ไม่งั้น "วันนี้" ของ backend ช้ากว่าหน้าร้าน 7 ชม. (การ์ดนับ 0 ทั้งที่มีนัด ฯลฯ)
os.environ.setdefault("TZ", "Asia/Bangkok")
try:
    _time.tzset()  # มีผลบน Linux — Windows (เครื่อง dev) ไม่มีฟังก์ชันนี้ แต่เวลา local ถูกอยู่แล้ว
except AttributeError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, SessionLocal, engine
from .routers import (auth, bookings, customers, dashboard, inventory, misc,
                      packages, payments, public, reports, services, therapists,
                      walkins)
from .seed import seed


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # migration: เติมคอลัมน์ is_demo ให้ DB เก่า (SQLite ADD COLUMN ปลอดภัย)
    from sqlalchemy import text
    with engine.connect() as conn:
        for tbl in ("users", "customers", "bookings", "walkins", "payments", "expenses"):
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN is_demo BOOLEAN DEFAULT 0"))
                conn.commit()
            except Exception:
                pass  # มีอยู่แล้ว
    db = SessionLocal()
    try:
        seed(db)
        ensure_demo_users(db)
    finally:
        db.close()


def ensure_demo_users(db) -> None:
    """บัญชีเดโม่แยกจากของจริง — ข้อมูลที่สร้างติดธง is_demo และถูกล้างทุก 1 ชม."""
    from .models import Therapist, User
    from .security import hash_password
    demos = [("demo_owner", "เจ้าของร้าน (เดโม่)", "Owner"),
             ("demo_manager", "ผู้จัดการ (เดโม่)", "Manager"),
             ("demo_reception", "รีเซปชั่น (เดโม่)", "Reception"),
             ("demo_therapist", "หมอนวด (เดโม่)", "Therapist"),
             ("demo_cashier", "แคชเชียร์ (เดโม่)", "Cashier")]
    for uname, name, role in demos:
        if not db.query(User).filter(User.username == uname).first():
            u = User(username=uname, password_hash=hash_password("demo1234"),
                     display_name=name, role=role, is_demo=True)
            db.add(u)
            db.flush()
            if role == "Therapist" and not db.query(Therapist).filter(Therapist.user_id == u.id).first():
                db.add(Therapist(display_name=name, code="DEMO", user_id=u.id))
    db.commit()


def purge_demo_data(db, older_than_minutes: int = 60) -> int:
    """ล้างเฉพาะข้อมูลที่บัญชีเดโม่สร้าง อายุเกินกำหนด — ของจริงไม่โดนแตะเด็ดขาด"""
    from datetime import datetime, timedelta

    from .models import (Booking, Customer, Expense, Payment, WalkIn)
    cutoff = datetime.now() - timedelta(minutes=older_than_minutes)
    n = 0
    for p in db.query(Payment).filter(Payment.is_demo == True, Payment.paid_at < cutoff).all():  # noqa: E712
        db.delete(p); n += 1
    for w in db.query(WalkIn).filter(WalkIn.is_demo == True, WalkIn.arrival_time < cutoff).all():  # noqa: E712
        db.delete(w); n += 1
    for b in db.query(Booking).filter(Booking.is_demo == True, Booking.created_at < cutoff).all():  # noqa: E712
        db.delete(b); n += 1
    for c in db.query(Customer).filter(Customer.is_demo == True, Customer.created_at < cutoff).all():  # noqa: E712
        db.delete(c); n += 1
    for e in db.query(Expense).filter(Expense.is_demo == True, Expense.spent_at < cutoff).all():  # noqa: E712
        db.delete(e); n += 1
    db.commit()
    return n


async def _demo_cleaner():
    import asyncio
    while True:
        await asyncio.sleep(600)  # เช็คทุก 10 นาที ล้างของที่อายุเกิน 60 นาที
        db = SessionLocal()
        try:
            purge_demo_data(db)
        except Exception:
            pass
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    import asyncio
    init_db()
    task = asyncio.create_task(_demo_cleaner())
    yield
    task.cancel()


app = FastAPI(title="JavaXd Massage & Spa Suite (Local)", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for r in (auth, customers, services, therapists, bookings, walkins, payments,
          inventory, packages, dashboard, reports, misc, public):
    app.include_router(r.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}


# ---------- เสิร์ฟ frontend ----------
FRONT = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/assets", StaticFiles(directory=FRONT / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONT / "index.html")


@app.get("/{page}.html", include_in_schema=False)
def root_page(page: str):
    f = FRONT / f"{page}.html"
    if f.is_file():
        return FileResponse(f)
    return FileResponse(FRONT / "index.html")


@app.get("/pages/{page}", include_in_schema=False)
def sub_page(page: str):
    f = (FRONT / "pages" / page).resolve()
    if f.is_file() and f.parent == (FRONT / "pages").resolve():
        return FileResponse(f)
    return FileResponse(FRONT / "index.html")
