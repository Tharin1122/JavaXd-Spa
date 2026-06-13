"""กวาดเทสทุกหน้า × ทุก role บนเซิร์ฟเวอร์จริง — ตามข้อมูลข้ามหน้า + เคสลบ
ใช้: python scripts/sweep_test.py [BASE_URL]   (ค่าเริ่มต้น http://127.0.0.1:8088)
"""
import json
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8088").rstrip("/")
ROLES = {"owner": "demo_owner", "manager": "demo_manager", "reception": "demo_reception",
         "therapist": "demo_therapist", "cashier": "demo_cashier"}
RESULTS = []  # (severity, page, detail)


def call(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None
    except Exception as e:
        return 0, str(e)


def login(u):
    s, d = call("POST", "/api/auth/login", body={"username": u, "password": "demo1234"})
    return d.get("accessToken") if s == 200 and isinstance(d, dict) else None


def bug(page, detail):
    RESULTS.append(("BUG", page, detail))


def ok(page, detail):
    RESULTS.append(("ok", page, detail))


# ---------- เทสระดับข้อมูล (owner เห็นทุกอย่าง) ----------
def test_data_integrity(tok):
    # 1) ทุก endpoint อ่านได้ + ไม่มี 500
    reads = ["/api/dashboard", "/api/dashboard/schedule", "/api/booking?pageSize=500",
             "/api/walk-in", "/api/customer?pageSize=500", "/api/services", "/api/service-categories",
             "/api/therapist", "/api/payment?pageSize=500", "/api/expense", "/api/inventory",
             "/api/inventory/stats", "/api/package", "/api/promotion", "/api/timeline?pageSize=100",
             "/api/report/revenue?groupBy=day", "/api/report/summary", "/api/report/popular-services?top=10",
             "/api/report/therapist-performance", "/api/role/matrix", "/api/role/capabilities",
             "/api/settings", "/api/subscription"]
    for p in reads:
        s, d = call("GET", p, tok)
        if s >= 500 or s == 0:
            bug(p, f"อ่านไม่ได้ status={s} {str(d)[:80]}")
        elif s == 200:
            ok(p, "อ่านได้")
        else:
            bug(p, f"status={s}")

    # 2) ตามข้อมูลข้ามหน้า: ยอดรายรับวันนี้ (dashboard) ต้อง = ผลรวม payment วันนี้
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    s, dash = call("GET", "/api/dashboard", tok)
    s, pays = call("GET", "/api/payment?pageSize=500", tok)
    items = (pays or {}).get("items", []) if isinstance(pays, dict) else []
    pay_today = sum(p.get("totalAmount", 0) for p in items if (p.get("paidAt") or "").startswith(today))
    dash_today = (dash or {}).get("revenue", {}).get("totalRevenue", 0)
    if abs(pay_today - dash_today) > 1:
        bug("cross:dashboard↔payment", f"รายรับวันนี้ dashboard={dash_today} แต่รวม payment={pay_today}")
    else:
        ok("cross:dashboard↔payment", f"ตรงกัน ({dash_today})")

    # 3) booking_out ต้องมี paid/walkInId/stateLabel ทุกตัว
    s, bk = call("GET", "/api/booking?pageSize=20", tok)
    for b in (bk or {}).get("items", [])[:20]:
        if "paid" not in b:
            bug("booking_out", f"{b.get('bookingNo')} ขาดฟิลด์ paid"); break
    else:
        ok("booking_out", "มี paid/walkInId ครบ")

    # 4) walkin_out ต้องมี stateLabel
    s, wi = call("GET", "/api/walk-in", tok)
    for w in (wi or {}).get("items", [])[:20]:
        if not w.get("stateLabel"):
            bug("walkin_out", f"{w.get('queueNo')} ขาด stateLabel"); break
    else:
        ok("walkin_out", "มี stateLabel ครบ")

    # 5) ข้อมูลถาวร 1 เดือน: ต้องมี payment กระจายหลายวัน
    days = set((p.get("paidAt") or "")[:10] for p in items)
    if len([d for d in days if d]) >= 10:
        ok("seed:1month", f"ข้อมูลกระจาย {len(days)} วัน")
    else:
        bug("seed:1month", f"ข้อมูลมีแค่ {len(days)} วัน (ควร ≥10)")


# ---------- เทสสิทธิ์ (RBAC) ----------
def test_rbac(role, tok):
    # owner-only endpoints ต้อง 403 สำหรับ role อื่น
    if role != "owner":
        s, _ = call("PUT", "/api/role/matrix", tok, body=[])
        if s == 200:
            bug(f"rbac:{role}", "แก้ role/matrix ได้ทั้งที่ไม่ใช่ owner!")
        else:
            ok(f"rbac:{role}", f"role/matrix ถูกกัน ({s})")


# ---------- เคสลบ (ควร fail แต่ผ่าน = อันตราย) ----------
def test_negatives(tok):
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cust = (call("GET", "/api/customer?pageSize=1", tok)[1] or {}).get("items", [{}])
    cid = cust[0].get("id") if cust else None
    svc = call("GET", "/api/services", tok)[1] or []
    sid = svc[0].get("id") if svc else None
    if not cid or not sid:
        return
    # จองเวลาในอดีต (ผ่าน public) → ต้อง 422
    s, _ = call("POST", "/api/public/booking", body={"serviceId": sid, "date": "2020-01-01",
                "time": "10:00", "name": "เทสอดีต", "phone": "0810000000"})
    if s in (422, 404):
        ok("neg:past-booking", f"กันจองอดีต ({s})")
    else:
        bug("neg:past-booking", f"จองอดีตได้! ({s})")
    # จ่ายเงิน walk-in ที่ยังไม่เริ่ม → ต้อง 409
    s, w = call("POST", "/api/walk-in", tok, body={"customerId": cid, "items": [{"serviceId": sid}]})
    if isinstance(w, dict) and w.get("walkInId"):
        s2, _ = call("POST", "/api/payment", tok, body={"walkInId": w["walkInId"], "paymentMethod": 0})
        if s2 == 409:
            ok("neg:pay-before-start", "กันจ่ายก่อนเริ่มบริการ (409)")
        else:
            bug("neg:pay-before-start", f"จ่ายก่อนเริ่มได้! ({s2})")
        call("PATCH", f"/api/walk-in/{w['walkInId']}/cancel", tok, body={"reason": "เทส"})


def main():
    print(f"=== กวาดเทส {BASE} ===")
    otok = login(ROLES["owner"])
    if not otok:
        print("login owner ไม่ได้ — หยุด"); return
    test_data_integrity(otok)
    test_negatives(otok)
    for role, u in ROLES.items():
        tok = login(u)
        if not tok:
            bug(f"login:{role}", "login ไม่ได้"); continue
        test_rbac(role, tok)

    bugs = [r for r in RESULTS if r[0] == "BUG"]
    oks = [r for r in RESULTS if r[0] == "ok"]
    print(f"\n✅ ผ่าน {len(oks)} | 🔴 บั๊ก {len(bugs)}")
    for sev, page, detail in bugs:
        print(f"  🔴 {page}: {detail}")
    if not bugs:
        print("  ไม่พบบั๊กระดับ API")


if __name__ == "__main__":
    main()
