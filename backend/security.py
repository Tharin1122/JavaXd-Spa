import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

SECRET = os.environ.get("MMS_SECRET_KEY", "dev-secret-change-me")
ALG = "HS256"
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
_ITER = 150_000


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), _ITER).hex()


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, dig = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), _ITER).hex(), dig)


def user_payload(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "displayName": u.display_name,
        "phone": u.phone, "roles": [u.role], "avatarUrl": u.avatar_url,
        "hasLine": bool(u.line_user_id), "hasPassword": bool(u.password_hash), "isDemo": bool(getattr(u, "is_demo", False)),
    }


def make_token(u: User) -> str:
    return jwt.encode(
        {"sub": u.id, "roles": [u.role], "exp": datetime.now(timezone.utc) + timedelta(hours=12)},
        SECRET, algorithm=ALG,
    )


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    err = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token ไม่ถูกต้องหรือหมดอายุ")
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALG])
    except jwt.PyJWTError:
        raise err
    u = db.get(User, payload.get("sub", ""))
    if u is None:
        raise err
    return u


def require_roles(*allowed: str):
    """ด่านบังคับสิทธิ์ฝั่ง backend — เดิม API เปิดโล่งทุก role (Broken Access Control)
    หมอนวด/แคชเชียร์ยิงตรงดึงเงินเดือน/บิล/รายชื่อพนักงานได้ → ปิดที่นี่ ไม่ใช่แค่ซ่อนเมนู"""
    def _guard(u: User = Depends(current_user)) -> User:
        if u.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="บัญชีของคุณไม่มีสิทธิ์เข้าถึงข้อมูลส่วนนี้")
        return u
    return _guard
