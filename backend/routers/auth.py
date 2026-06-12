import secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import log_event
from ..models import User
from ..security import (current_user, hash_password, make_token, user_payload,
                        verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# token ผูก LINE จำลอง (in-memory) — LINE จริงต้องตั้ง LIFF เอง
_LINK_TOKENS: dict[str, dict] = {}


# rate limit หน้า login: กัน brute force (5 ครั้งผิด / 60 วิ ต่อ username) — in-memory พอสำหรับ single server
import time as _time

_FAILED: dict[str, list[float]] = {}
_MAX_FAILS, _WINDOW = 5, 60.0


def _check_rate(key: str) -> None:
    now = _time.time()
    fails = [t for t in _FAILED.get(key, []) if now - t < _WINDOW]
    _FAILED[key] = fails
    if len(fails) >= _MAX_FAILS:
        raise HTTPException(status_code=429,
                            detail="พยายามเข้าสู่ระบบผิดหลายครั้งเกินไป — รอ 1 นาทีแล้วลองใหม่")


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    # หน้าเว็บส่ง JSON {username,password} / เครื่องมืออื่นอาจส่ง form — รับทั้งคู่
    ctype = request.headers.get("content-type", "")
    if "json" in ctype:
        body = await request.json()
        username, password = body.get("username", ""), body.get("password", "")
    else:
        form = await request.form()
        username, password = form.get("username", ""), form.get("password", "")
    _check_rate(username)
    u = db.query(User).filter(User.username == username).first()
    if u is None or not verify_password(password, u.password_hash):
        _FAILED.setdefault(username, []).append(_time.time())
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    _FAILED.pop(username, None)
    log_event(db, "Login", "User", u.display_name, "เข้าสู่ระบบ", u.display_name)
    db.commit()
    return {"accessToken": make_token(u), "refreshToken": "", "user": user_payload(u)}


@router.get("/line-config")
def line_config():
    return {"liffId": None}  # ไม่ใช้ LINE login ในเวอร์ชัน local


@router.post("/line-login")
def line_login():
    raise HTTPException(status_code=400, detail="เวอร์ชัน local ยังไม่เปิดใช้ LINE Login — ใช้ username/password")


@router.put("/me")
def update_me(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(User, u.id)
    if body.get("displayName"):
        u.display_name = body["displayName"]
    u.phone = body.get("phone")
    db.commit()
    return user_payload(u)


@router.post("/change-password")
def change_password(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    u = db.get(User, u.id)
    if u.password_hash and not verify_password(body.get("currentPassword") or "", u.password_hash):
        raise HTTPException(status_code=400, detail="รหัสผ่านเดิมไม่ถูกต้อง")
    new = body.get("newPassword") or ""
    if len(new) < 6:
        raise HTTPException(status_code=422, detail="รหัสผ่านใหม่ต้องยาวอย่างน้อย 6 ตัว")
    u.password_hash = hash_password(new)
    db.commit()
    return {"ok": True}


@router.post("/link-token")
def link_token(body: dict = Body(...), _: User = Depends(current_user)):
    token = secrets.token_urlsafe(16)
    _LINK_TOKENS[token] = {"userId": body.get("userId"), "status": "pending"}
    return {"token": token, "liffUrl": f"http://127.0.0.1:8088/link-line/{token}"}


@router.get("/link-status/{token}")
def link_status(token: str, _: User = Depends(current_user)):
    info = _LINK_TOKENS.get(token)
    return {"status": (info or {}).get("status", "expired")}
