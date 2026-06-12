"""เทสระบบ JavaXd MMS — ครอบคลุมวงจรจริง: login → จอง → คิว → เรียกคิว → จบงาน → ชำระ → รายงาน"""
import os
import sys
from datetime import datetime
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "test_mms.db"
os.environ["MMS_DB_URL"] = f"sqlite:///{TEST_DB}"
os.environ["MMS_OWNER_PASS"] = "Owner@2468"  # รหัสเฉพาะตอนเทส — ของจริงตั้งใน env ของเครื่อง/แพลตฟอร์ม
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.db import engine
from backend.main import app, init_db

TODAY = datetime.now().strftime("%Y-%m-%d")
from datetime import timedelta
TOMORROW = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


@pytest.fixture(scope="module")
def client():
    if TEST_DB.exists():
        TEST_DB.unlink()
    init_db()
    with TestClient(app) as c:
        yield c
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture(scope="module")
def H(client):
    r = client.post("/api/auth/login", data={"username": "owner", "password": "Owner@2468"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["roles"] == ["Owner"]
    return {"Authorization": "Bearer " + body["accessToken"]}


# ---------- auth ----------

def test_login_wrong(client):
    assert client.post("/api/auth/login", data={"username": "owner", "password": "bad"}).status_code == 401


def test_protected_requires_token(client):
    assert client.get("/api/dashboard").status_code == 401


def test_role_demo_users(client):
    for u in ["manager", "reception", "aom", "cashier"]:
        assert client.post("/api/auth/login", data={"username": u, "password": "demo1234"}).status_code == 200


# ---------- master data ----------

def test_seeded_services_categories(client, H):
    svcs = client.get("/api/services", headers=H).json()
    assert len(svcs) >= 7
    assert all(s["price"] > 0 and s["category"] for s in svcs)
    cats = client.get("/api/service-categories", headers=H).json()
    assert len(cats) >= 5


def test_seeded_therapists(client, H):
    th = client.get("/api/therapist", headers=H).json()
    assert len(th) >= 5
    assert any(t["userId"] for t in th)  # อ้อม ผูกบัญชี


def test_customer_crud_and_search(client, H):
    c = client.post("/api/customer", headers=H, json={"displayName": "คุณทดสอบ ระบบดี", "phone": "099-000-1111"}).json()
    r = client.get("/api/customer?search=ทดสอบ", headers=H).json()
    assert any(x["id"] == c["id"] for x in r["items"])
    upd = client.put(f"/api/customer/{c['id']}", headers=H, json={"displayName": "คุณทดสอบ แก้ไขแล้ว", "phone": None, "notes": "แพ้น้ำมัน"}).json()
    assert upd["displayName"] == "คุณทดสอบ แก้ไขแล้ว"
    assert client.delete(f"/api/customer/{c['id']}", headers=H).status_code == 204


# ---------- booking → check-in → queue → pay ----------

@pytest.fixture(scope="module")
def setup_ids(client, H):
    cust = client.get("/api/customer?pageSize=5", headers=H).json()["items"][0]
    svc = client.get("/api/services", headers=H).json()[0]
    ther = client.get("/api/therapist", headers=H).json()[0]
    return {"cust": cust, "svc": svc, "ther": ther}


def test_create_booking(client, H, setup_ids):
    r = client.post("/api/booking", headers=H, json={
        "customerId": setup_ids["cust"]["id"], "bookingDate": TODAY, "startTime": "14:00:00",
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": None, "therapistSelectionMode": 1, "sortOrder": 0}],
    })
    assert r.status_code == 201
    b = r.json()
    assert b["bookingNo"].startswith("B-")
    assert b["totalAmount"] == setup_ids["svc"]["price"]
    assert b["status"] == 0
    setup_ids["booking"] = b


def test_booking_in_list_and_confirm(client, H, setup_ids):
    r = client.get(f"/api/booking?date={TODAY}", headers=H).json()
    assert any(x["id"] == setup_ids["booking"]["id"] for x in r["items"])
    c = client.patch(f"/api/booking/{setup_ids['booking']['id']}/confirm", headers=H)
    assert c.json()["status"] == 1


def test_walkin_full_cycle(client, H, setup_ids):
    # เข้าคิว
    w = client.post("/api/walk-in", headers=H, json={
        "customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": None, "sortOrder": 0}],
    }).json()
    assert w["queueNo"].startswith("Q")
    assert w["walkInId"] == w["id"]
    # หาหมอนวดว่างที่ทำได้
    avail = client.get(f"/api/walk-in/available-therapists?serviceIds={setup_ids['svc']['id']}", headers=H).json()
    assert len(avail[setup_ids["svc"]["id"]]) >= 1
    tid = avail[setup_ids["svc"]["id"]][0]["id"]
    # assign + start → หมอนวดไม่ว่าง
    client.patch(f"/api/walk-in/{w['id']}/assign", headers=H, json={"therapistId": tid, "roomId": None})
    started = client.patch(f"/api/walk-in/{w['id']}/start", headers=H).json()
    assert started["status"] == 1
    th = client.get(f"/api/therapist/{tid}", headers=H).json()
    assert th["currentStatus"] == 1
    # complete → หมอนวดว่าง
    done = client.patch(f"/api/walk-in/{w['id']}/complete", headers=H).json()
    assert done["status"] == 2
    assert client.get(f"/api/therapist/{tid}", headers=H).json()["currentStatus"] == 0
    setup_ids["walkin"] = done


def test_payment_from_walkin(client, H, setup_ids):
    w = setup_ids["walkin"]
    pay = client.post("/api/payment", headers=H, json={
        "walkInId": w["id"], "paymentMethod": 0, "paidAmount": w["totalAmount"], "discountAmount": 0,
    })
    assert pay.status_code == 201
    p = pay.json()
    assert p["receiptNo"].startswith("INV")
    assert p["totalAmount"] == w["totalAmount"]
    # จ่ายซ้ำต้องโดนกัน
    assert client.post("/api/payment", headers=H, json={"walkInId": w["id"], "paymentMethod": 0}).status_code == 400
    # ลูกค้าถูกอัปเดตยอดสะสม
    cust = client.get(f"/api/customer/{setup_ids['cust']['id']}", headers=H).json()
    assert cust["totalVisits"] >= 1 and cust["totalSpent"] >= w["totalAmount"]
    setup_ids["payment"] = p


def test_payment_reprint(client, H, setup_ids):
    p = client.get(f"/api/payment/{setup_ids['payment']['id']}", headers=H).json()
    assert p["items"][0]["serviceName"]


def test_walkin_cancel(client, H, setup_ids):
    w = client.post("/api/walk-in", headers=H, json={
        "customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "sortOrder": 0}],
    }).json()
    c = client.patch(f"/api/walk-in/{w['id']}/cancel", headers=H, json={"reason": "ทดสอบ"}).json()
    assert c["status"] == 3


# ---------- dashboard / queue display / reports ----------

def test_dashboard(client, H):
    d = client.get("/api/dashboard", headers=H).json()
    assert d["revenue"]["totalRevenue"] > 0
    assert d["queue"]["totalToday"] >= 2
    assert d["bookings"]["total"] >= 1
    assert isinstance(d["revenue"]["byMethod"], list)


def test_dashboard_schedule(client, H):
    s = client.get("/api/dashboard/schedule", headers=H).json()
    assert len(s["therapists"]) >= 5
    assert any(t["items"] for t in s["therapists"])  # มีงานที่มอบหมายแล้ว


def test_queue_display(client, H):
    q = client.get("/api/queue", headers=H).json()
    assert "waiting" in q and "inService" in q


def test_reports(client, H):
    rev = client.get("/api/report/revenue?groupBy=day", headers=H).json()
    assert rev["summary"]["totalRevenue"] > 0
    assert len(rev["series"]) == 365
    pop = client.get("/api/report/popular-services?top=10", headers=H).json()
    assert pop["popular"][0]["count"] >= 1
    perf = client.get("/api/report/therapist-performance", headers=H).json()
    assert any(p["totalCommission"] > 0 for p in perf["performance"])
    assert "comparison" in client.get("/api/report/summary", headers=H).json()


# ---------- inventory ----------

def test_inventory_movement(client, H):
    items = client.get("/api/inventory", headers=H).json()["items"]
    item = items[0]
    before = item["quantity"]
    r = client.post(f"/api/inventory/{item['id']}/movement", headers=H, json={"type": "in", "quantity": 10, "note": "PO ทดสอบ"}).json()
    assert r["quantity"] == before + 10
    bad = client.post(f"/api/inventory/{item['id']}/movement", headers=H, json={"type": "out", "quantity": 99999})
    assert bad.status_code == 400
    stats = client.get("/api/inventory/stats", headers=H).json()
    assert stats["totalItems"] >= 5


# ---------- package / coupon ----------

def test_package_sell_and_redeem(client, H, setup_ids):
    pkg = client.get("/api/package", headers=H).json()[0]
    sell = client.post(f"/api/package/{pkg['id']}/sell", headers=H,
                       json={"customerId": setup_ids["cust"]["id"], "paymentMethod": "Cash"}).json()
    assert sell["receiptNo"].startswith("INV")
    cps = client.get(f"/api/package/customer/{setup_ids['cust']['id']}", headers=H).json()
    assert cps and cps[0]["remainingSessions"] == cps[0]["totalSessions"]
    red = client.post(f"/api/package/redeem/{cps[0]['id']}", headers=H).json()
    assert red["remainingSessions"] == cps[0]["totalSessions"] - 1


def test_coupon_validate(client, H):
    ok = client.get("/api/promotion/validate/NEW15", headers=H).json()
    assert ok["discountPercent"] == 15
    assert client.get("/api/promotion/validate/NOPE99", headers=H).status_code == 404
    used = client.post("/api/promotion/redeem-coupon/NEW15", headers=H).json()
    assert used["usedCount"] == 1


# ---------- staff / leave / review ----------

def test_create_user_and_therapist_link(client, H):
    u = client.post("/api/user", headers=H, json={"displayName": "ส้ม หมอนวดใหม่", "username": "som01",
                                                  "password": "som123456", "roleId": "Therapist"}).json()
    t = client.post("/api/therapist/from-user", headers=H, json={"userId": u["id"], "code": "TH06"}).json()
    assert t["userId"] == u["id"]
    # ล็อกอินด้วยบัญชีใหม่ได้จริง
    assert client.post("/api/auth/login", data={"username": "som01", "password": "som123456"}).status_code == 200


def test_leave_flow(client, H):
    th = client.get("/api/therapist", headers=H).json()[0]
    lv = client.post(f"/api/therapist/{th['id']}/leaves", headers=H,
                     json={"leaveDate": TODAY, "leaveType": 0, "reason": "ลากิจ"}).json()
    assert lv["status"] == 0
    ap = client.patch(f"/api/therapist/{th['id']}/leaves/{lv['id']}/approve", headers=H).json()
    assert ap["status"] == 1


def test_review_and_rating(client, H, setup_ids):
    th = client.get("/api/therapist", headers=H).json()[0]
    client.post("/api/review", headers=H, json={"customerId": setup_ids["cust"]["id"],
                                                "therapistId": th["id"], "rating": 5, "comment": "ดีมาก"})
    rv = client.get("/api/review/therapists", headers=H).json()
    assert any(x["therapistId"] == th["id"] and x["average"] == 5 for x in rv)


# ---------- settings / matrix / timeline / expense ----------

def test_settings_roundtrip(client, H):
    client.put("/api/settings", headers=H, json={"shopName": "JavaXd Spa ทดสอบ", "vat": True})
    s = client.get("/api/settings", headers=H).json()
    assert s["shopName"] == "JavaXd Spa ทดสอบ"


def test_role_matrix_roundtrip(client, H):
    m = [[1, 1, 1, 2, 0]] * 10
    client.put("/api/role/matrix", headers=H, json=m)
    assert client.get("/api/role/matrix", headers=H).json() == m


def test_expense_and_timeline(client, H):
    client.post("/api/expense", headers=H, json={"category": "ค่าเช่า / สาธารณูปโภค", "amount": 1500, "note": "ค่าน้ำ"})
    ex = client.get("/api/expense", headers=H).json()
    assert ex["total"] >= 1500
    tl = client.get("/api/timeline?pageSize=50", headers=H).json()
    assert len(tl["items"]) >= 5  # กิจกรรมถูกบันทึกตลอดทาง


def test_subscription_select_no_money(client, H):
    r = client.post("/api/subscription/select", headers=H, json={"planType": "Professional", "trial": True}).json()
    assert r["planType"] == "Professional"
    assert client.get("/api/subscription", headers=H).json()["planType"] == "Professional"


# ---------- PromptPay QR ----------

def test_promptpay_qr_payload(client, H):
    r = client.get("/api/payment/qr?amount=550.00", headers=H)
    assert r.status_code == 200
    d = r.json()
    p = d["payload"]
    assert p.startswith("000201")            # EMVCo format
    assert "A000000677010111" in p           # PromptPay AID
    assert "5303764" in p                    # THB
    assert "5406550.00" in p                 # amount
    assert "5802TH" in p
    # CRC ตรวจซ้ำได้: คำนวณใหม่ต้องตรงกับ 4 ตัวท้าย
    from backend.routers.payments import _crc16_ccitt
    assert p[-4:] == _crc16_ccitt(p[:-4])


def test_promptpay_qr_validation(client, H):
    assert client.get("/api/payment/qr?amount=0", headers=H).status_code == 422
    assert client.get("/api/payment/qr?amount=-5", headers=H).status_code == 422


def test_promptpay_uses_settings_id(client, H):
    client.put("/api/settings", headers=H, json={"promptpayId": "0899999999"})
    d = client.get("/api/payment/qr?amount=100", headers=H).json()
    assert d["promptpayId"] == "0899999999"
    assert d["isDemo"] is False
    assert "0066899999999" in d["payload"]


# ---------- login rate limit ----------

def test_login_rate_limit(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "ratelimit-x", "password": "bad"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "ratelimit-x", "password": "bad"}).status_code == 429
    # username อื่นไม่โดนหางเลข
    assert client.post("/api/auth/login", json={"username": "manager", "password": "demo1234"}).status_code == 200


# ---------- public booking (หน้าจองออนไลน์ ไม่ต้อง login) ----------

def test_public_services_no_auth(client):
    r = client.get("/api/public/services")
    assert r.status_code == 200
    assert len(r.json()) >= 7


def test_public_booking_flow(client, H):
    r = client.post("/api/public/booking", json={
        "name": "คุณออนไลน์ ทดสอบจริง", "phone": "0861112222",
        "serviceId": client.get("/api/public/services").json()[0]["id"],
        "date": TOMORROW, "time": "19:00",
    })
    assert r.status_code == 201
    out = r.json()
    assert out["bookingNo"].startswith("B-")
    # ต้องโผล่ในระบบหลังบ้านจริง
    bk = client.get(f"/api/booking?date={TOMORROW}", headers=H).json()["items"]
    assert any(x["bookingNo"] == out["bookingNo"] and x["customer"]["displayName"] == "คุณออนไลน์ ทดสอบจริง" for x in bk)
    # จองซ้ำเบอร์เดิม → ใช้ลูกค้าเดิม ไม่สร้างซ้ำ
    client.post("/api/public/booking", json={"name": "คุณออนไลน์ ทดสอบจริง", "phone": "0861112222",
                "serviceId": client.get("/api/public/services").json()[1]["id"], "date": TOMORROW, "time": "20:00"})
    custs = client.get("/api/customer?search=ออนไลน์", headers=H).json()["items"]
    assert len(custs) == 1


def test_public_booking_validation(client):
    svc = client.get("/api/public/services").json()[0]["id"]
    assert client.post("/api/public/booking", json={"name": "0812345678", "phone": "0861112222",
                       "serviceId": svc, "date": TOMORROW, "time": "19:00"}).status_code == 422  # ชื่อเป็นเบอร์
    assert client.post("/api/public/booking", json={"name": "คุณดี", "phone": "12345",
                       "serviceId": svc, "date": TOMORROW, "time": "19:00"}).status_code == 422  # เบอร์ผิด
    assert client.post("/api/public/booking", json={"name": "คุณดี", "phone": "0861112223",
                       "serviceId": "nope", "date": TODAY, "time": "19:00"}).status_code == 404


# ---------- daily close (Z-Report) ----------

def test_daily_close(client, H):
    d = client.get(f"/api/report/daily-close?date={TODAY}", headers=H).json()
    assert d["date"] == TODAY
    assert d["billCount"] >= 2
    assert d["totalRevenue"] > 0
    assert abs(sum(m["amount"] for m in d["byMethod"]) - d["totalRevenue"]) < 0.01  # ยอดแยกช่องทางรวมต้องเท่ายอดรวม
    assert d["netCash"] == round(d["totalRevenue"] - d["expenseTotal"], 2)
    assert d["topItems"][0]["qty"] >= 1


# ---------- backup ----------

def test_backup_owner_only(client, H):
    r = client.get("/api/backup", headers=H)
    assert r.status_code == 200
    assert len(r.content) > 1000  # ได้ไฟล์ DB จริง
    # role อื่นห้าม
    tok = client.post("/api/auth/login", json={"username": "aom", "password": "demo1234"}).json()["accessToken"]
    assert client.get("/api/backup", headers={"Authorization": "Bearer " + tok}).status_code == 403


# ---------- demo mode: บัญชีแยก + ติดธง + ล้างเฉพาะของเดโม่ ----------

def test_demo_accounts_exist_and_flagged(client):
    r = client.post("/api/auth/login", json={"username": "demo_owner", "password": "demo1234"})
    assert r.status_code == 200
    assert r.json()["user"]["isDemo"] is True
    # บัญชีจริงต้องไม่ใช่ demo
    r2 = client.post("/api/auth/login", json={"username": "owner", "password": "Owner@2468"})
    assert r2.json()["user"]["isDemo"] is False


def test_demo_data_tagged_in_db_and_purged_selectively(client, H):
    from backend.db import SessionLocal
    from backend.main import purge_demo_data
    from backend.models import Customer
    # demo สร้างลูกค้า
    tok = client.post("/api/auth/login", json={"username": "demo_owner", "password": "demo1234"}).json()["accessToken"]
    DH = {"Authorization": "Bearer " + tok}
    demo_c = client.post("/api/customer", headers=DH, json={"displayName": "ลูกค้าเดโม่ ทดลอง", "phone": "0800000001"}).json()
    # ของจริงสร้างลูกค้า
    real_c = client.post("/api/customer", headers=H, json={"displayName": "ลูกค้าจริง ถาวร", "phone": "0800000002"}).json()
    # เช็คใน DB จริง (กฎ JavaXd: จออย่างเดียวไม่พอ)
    db = SessionLocal()
    try:
        assert db.get(Customer, demo_c["id"]).is_demo is True
        assert db.get(Customer, real_c["id"]).is_demo is False
        # ล้างทันที (อายุ 0 นาที) → เดโม่หาย ของจริงอยู่
        n = purge_demo_data(db, older_than_minutes=0)
        assert n >= 1
        assert db.get(Customer, demo_c["id"]) is None
        assert db.get(Customer, real_c["id"]) is not None
    finally:
        db.close()


def test_demo_full_cycle_purged(client):
    """เดโม่ทำครบวงจร จอง→คิว→จ่าย แล้วล้างต้องหายหมดทุกตาราง"""
    from backend.db import SessionLocal
    from backend.main import purge_demo_data
    from backend.models import Payment, WalkIn
    tok = client.post("/api/auth/login", json={"username": "demo_reception", "password": "demo1234"}).json()["accessToken"]
    DH = {"Authorization": "Bearer " + tok}
    c = client.post("/api/customer", headers=DH, json={"displayName": "เดโม่ ครบวงจร"}).json()
    svc = client.get("/api/services", headers=DH).json()[0]
    w = client.post("/api/walk-in", headers=DH, json={"customerId": c["id"], "items": [{"serviceId": svc["id"]}]}).json()
    client.patch(f"/api/walk-in/{w['id']}/start", headers=DH)
    client.patch(f"/api/walk-in/{w['id']}/complete", headers=DH)
    pay = client.post("/api/payment", headers=DH, json={"walkInId": w["id"], "paymentMethod": 0}).json()
    db = SessionLocal()
    try:
        assert db.get(WalkIn, w["id"]).is_demo is True
        assert db.get(Payment, pay["id"]).is_demo is True
        purge_demo_data(db, older_than_minutes=0)
        assert db.get(WalkIn, w["id"]) is None
        assert db.get(Payment, pay["id"]) is None
    finally:
        db.close()


# ---------- state machine: ทำนอกขั้นตอนต้องโดน 409 ทุกทาง ----------

def test_booking_state_machine(client, H, setup_ids):
    b = client.post("/api/booking", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "bookingDate": TOMORROW, "startTime": "10:00:00",
        "items": [{"serviceId": setup_ids["svc"]["id"]}]}).json()
    assert client.patch(f"/api/booking/{b['id']}/complete", headers=H).status_code == 409  # ข้ามขั้น
    client.patch(f"/api/booking/{b['id']}/cancel", headers=H)
    assert client.patch(f"/api/booking/{b['id']}/confirm", headers=H).status_code == 409  # จบทางแล้ว
    assert client.patch(f"/api/booking/{b['id']}/cancel", headers=H).status_code == 409


def test_walkin_state_machine(client, H, setup_ids):
    w = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"]}]}).json()
    assert client.patch(f"/api/walk-in/{w['id']}/complete", headers=H).status_code == 409  # จบงานโดยไม่เริ่ม
    assert client.post("/api/payment", headers=H, json={"walkInId": w["id"], "paymentMethod": 0}).status_code == 409  # จ่ายก่อนจบงาน
    client.patch(f"/api/walk-in/{w['id']}/start", headers=H)
    client.patch(f"/api/walk-in/{w['id']}/complete", headers=H)
    assert client.patch(f"/api/walk-in/{w['id']}/cancel", headers=H).status_code == 409  # จบงานแล้วยกเลิกไม่ได้
    client.post("/api/payment", headers=H, json={"walkInId": w["id"], "paymentMethod": 0})
    assert client.patch(f"/api/walk-in/{w['id']}/cancel", headers=H).status_code == 409  # จ่ายแล้วยิ่งห้าม


def test_start_blocked_when_therapist_busy(client, H, setup_ids):
    """รูรั่วที่ Tharin เจอ: หมอกำลังนวดคนอื่น — ตอนนี้บล็อกตั้งแต่ 'สร้างคิวพร้อมระบุหมอ' เลย (เข้มกว่าเดิม)"""
    tid = client.get("/api/therapist", headers=H).json()[1]["id"]
    w1 = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": tid}]}).json()
    client.patch(f"/api/walk-in/{w1['id']}/start", headers=H)
    # สร้างคิวใหม่ระบุหมอคนเดิมที่กำลังนวดอยู่ → 409 ตั้งแต่ตอนสร้าง
    r2 = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": tid}]})
    assert r2.status_code == 409
    # ไม่ระบุหมอ สร้างได้ แต่ assign หมอที่ติดอยู่ → 409 / start คิวที่ไม่มีหมอชน → ผ่าน
    w2 = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"]}]}).json()
    assert client.patch(f"/api/walk-in/{w2['id']}/assign", headers=H,
                        json={"therapistId": tid}).status_code == 409
    client.patch(f"/api/walk-in/{w1['id']}/complete", headers=H)
    client.patch(f"/api/walk-in/{w2['id']}/cancel", headers=H)


def test_pay_during_service_autocompletes(client, H, setup_ids):
    """กฎ Tharin: ต้อง 'กำลังบริการ' ก่อนแล้วจ่าย → จ่ายระหว่างบริการ = จบงาน+หมอว่างอัตโนมัติ / จ่ายก่อนเริ่ม = 409"""
    tid = client.get("/api/therapist", headers=H).json()[4]["id"]
    w = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": tid}]}).json()
    # จ่ายตอนยังรอคิว (status 0) → ห้าม
    assert client.post("/api/payment", headers=H,
                       json={"walkInId": w["id"], "paymentMethod": 0}).status_code == 409
    client.patch(f"/api/walk-in/{w['id']}/start", headers=H)
    # จ่ายตอนกำลังบริการ → สำเร็จ + จบงานอัตโนมัติ + หมอว่าง
    r = client.post("/api/payment", headers=H, json={"walkInId": w["id"], "paymentMethod": 0})
    assert r.status_code == 201
    w2 = client.get(f"/api/walk-in/{w['id']}", headers=H).json()
    assert w2["status"] == 2 and w2["paid"] is True
    t = next(x for x in client.get("/api/therapist", headers=H).json() if x["id"] == tid)
    assert t["currentStatus"] == 0  # หมอเคลียร์คิวแล้ว


def test_reschedule_blocked_on_conflict(client, H, setup_ids):
    """ประตูที่เคยรั่วจริง: gantt ย้ายคิว/ย้ายหมอ ต้องผ่านตัวตรวจกลาง — ย้ายไปทับหมอที่กำลังนวด → 409"""
    tid = client.get("/api/therapist", headers=H).json()[2]["id"]
    w1 = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": tid}]}).json()
    client.patch(f"/api/walk-in/{w1['id']}/start", headers=H)
    w2 = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"]}]}).json()
    item_id = client.get(f"/api/walk-in/{w2['id']}", headers=H).json()["items"][0]["id"]
    from datetime import datetime as _dt
    now_hm = _dt.now().strftime("%H:%M")
    r = client.patch("/api/dashboard/schedule/reschedule", headers=H,
                     json={"source": "walkin", "itemId": item_id, "startTime": now_hm, "therapistId": tid})
    assert r.status_code == 409  # ย้ายไปทับหมอที่กำลังนวด ต้องโดนปฏิเสธ
    client.patch(f"/api/walk-in/{w1['id']}/complete", headers=H)
    client.patch(f"/api/walk-in/{w2['id']}/cancel", headers=H)


def test_booking_create_blocked_by_active_walkin(client, H, setup_ids):
    """จองวันนี้ระบุหมอที่กำลังนวดช่วงเดียวกัน → 409 (เดิมเช็คแค่จองชนจอง ไม่เห็น walk-in)"""
    from datetime import datetime as _dt
    tid = client.get("/api/therapist", headers=H).json()[3]["id"]
    w1 = client.post("/api/walk-in", headers=H, json={"customerId": setup_ids["cust"]["id"],
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": tid}]}).json()
    client.patch(f"/api/walk-in/{w1['id']}/start", headers=H)
    r = client.post("/api/booking", headers=H, json={
        "customerId": setup_ids["cust"]["id"],
        "bookingDate": _dt.now().strftime("%Y-%m-%d"),
        "startTime": _dt.now().strftime("%H:%M:00"),
        "items": [{"serviceId": setup_ids["svc"]["id"], "therapistId": tid}]})
    assert r.status_code == 409
    client.patch(f"/api/walk-in/{w1['id']}/complete", headers=H)


# ---------- frontend serving ----------

def test_frontend_served(client):
    assert "JavaXd" in client.get("/login.html").text
    assert client.get("/pages/pos.html").status_code == 200
    assert "location.origin" in client.get("/assets/api.js").text  # ชี้ backend local แล้ว
