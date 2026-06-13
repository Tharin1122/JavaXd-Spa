"""ตัวกลางเช็คสิทธิ์ฝั่ง backend — อ่านจาก config 'role_caps' ตัวเดียวกับที่ Owner ตั้งในหน้า Roles
หลักการ: เปิด/ปิดสิทธิ์ที่หน้า Roles แล้ว backend ต้องเชื่อทันที ห้ามฮาร์ดโค้ด role ในแต่ละ endpoint
→ Owner กดอนุญาตอะไร backend อนุญาตตามทันที ไม่ต้องแก้โค้ด"""
from fastapi import HTTPException

from .helpers import kv_get

CAP_ALL = ["view", "cards", "table", "create", "edit", "pay", "money", "manage"]


def _role_caps(db, role: str):
    """caps ของบทบาทนี้จาก DB (ที่ Owner ตั้ง) — ถ้ายังไม่เคยตั้ง ใช้ค่าเริ่มต้น | Owner = None (ทุกสิทธิ์)"""
    if role == "Owner":
        return None
    from .routers.misc import _default_caps  # lazy import กัน circular
    saved = kv_get(db, "role_caps", None) or _default_caps()
    return saved.get(role) or {}


def has_cap(db, u, cap: str, pages) -> bool:
    """ผู้ใช้มีความสามารถ cap นี้ในหน้าใดหน้าหนึ่งใน pages ไหม (endpoint เดียวอาจถูกเรียกจากหลายหน้า)"""
    if getattr(u, "role", None) == "Owner":
        return True
    rc = _role_caps(db, getattr(u, "role", "") or "")
    if rc is None:
        return True
    if isinstance(pages, str):
        pages = [pages]
    return any(cap in (rc.get(p) or []) for p in pages)


def require(db, u, cap: str, pages, msg: str | None = None) -> None:
    if not has_cap(db, u, cap, pages):
        raise HTTPException(status_code=403,
                            detail=msg or "บัญชีนี้ไม่มีสิทธิ์ทำรายการนี้ — เจ้าของร้านเปิดสิทธิ์ได้ที่หน้า 'สิทธิ์การใช้งาน'")
