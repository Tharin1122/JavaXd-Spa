from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..helpers import log_event
from ..models import InventoryItem, InventoryMovement, User
from ..security import current_user

router = APIRouter(prefix="/api/inventory", tags=["inventory"], dependencies=[Depends(current_user)])


def item_out(x: InventoryItem) -> dict:
    return {"id": x.id, "name": x.name, "sku": x.sku, "category": x.category, "unit": x.unit,
            "quantity": x.quantity, "costPerUnit": x.cost_per_unit,
            "reorderPoint": x.reorder_point, "minQuantity": x.reorder_point}


@router.get("")
def list_items(db: Session = Depends(get_db)):
    rows = db.query(InventoryItem).order_by(InventoryItem.name).all()
    return {"items": [item_out(x) for x in rows], "total": len(rows)}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    from datetime import datetime
    rows = db.query(InventoryItem).all()
    low = [x for x in rows if x.quantity <= x.reorder_point]
    cost = {x.id: x.cost_per_unit for x in rows}
    month_start = datetime.now().strftime("%Y-%m-01 00:00:00")
    outs = db.query(InventoryMovement).filter(InventoryMovement.type == "out",
                                              InventoryMovement.created_at >= month_start).all()
    return {"totalItems": len(rows), "lowStock": len(low),
            "totalValue": sum(x.quantity * x.cost_per_unit for x in rows),
            "outOfStock": len([x for x in rows if x.quantity <= 0]),
            "monthlyOutQty": sum(m.quantity for m in outs),
            "monthlyOutValue": round(sum(m.quantity * cost.get(m.item_id, 0) for m in outs), 2)}


@router.post("", status_code=201)
def create_item(body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not (body.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="กรุณาระบุชื่อสินค้า")
    x = InventoryItem(name=body["name"].strip(), sku=body.get("sku"), category=body.get("category") or "ของใช้",
                      unit=body.get("unit") or "ชิ้น", quantity=int(body.get("quantity") or 0),
                      cost_per_unit=float(body.get("costPerUnit") or 0),
                      reorder_point=int(body.get("reorderPoint") or body.get("minQuantity") or 5))
    db.add(x)
    log_event(db, "InventoryCreated", "Inventory", x.name, "เพิ่มสินค้าเข้าคลัง", u.display_name)
    db.commit()
    return item_out(x)


def _get(db: Session, iid: str) -> InventoryItem:
    x = db.get(InventoryItem, iid)
    if x is None:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return x


@router.put("/{iid}")
def update_item(iid: str, body: dict = Body(...), db: Session = Depends(get_db)):
    x = _get(db, iid)
    x.name = body.get("name") or x.name
    x.sku = body.get("sku")
    x.category = body.get("category") or x.category
    x.unit = body.get("unit") or x.unit
    if body.get("quantity") is not None:
        x.quantity = int(body["quantity"])
    if body.get("costPerUnit") is not None:
        x.cost_per_unit = float(body["costPerUnit"])
    if body.get("reorderPoint") is not None:
        x.reorder_point = int(body["reorderPoint"])
    db.commit()
    return item_out(x)


@router.post("/{iid}/movement")
def movement(iid: str, body: dict = Body(...), u: User = Depends(current_user), db: Session = Depends(get_db)):
    x = _get(db, iid)
    mtype = body.get("type")
    qty = int(body.get("quantity") or 0)
    if mtype not in ("in", "out") or qty <= 0:
        raise HTTPException(status_code=422, detail="ระบุ type=in/out และจำนวนมากกว่า 0")
    if mtype == "out" and qty > x.quantity:
        raise HTTPException(status_code=400, detail=f"สต็อกไม่พอ (เหลือ {x.quantity} {x.unit})")
    x.quantity += qty if mtype == "in" else -qty
    db.add(InventoryMovement(item_id=iid, type=mtype, quantity=qty, note=body.get("note")))
    log_event(db, "InventoryMoved", "Inventory", x.name,
              ("รับเข้า " if mtype == "in" else "เบิกออก ") + f"{qty} {x.unit}", u.display_name)
    db.commit()
    return item_out(x)


@router.delete("/{iid}", status_code=204)
def delete_item(iid: str, db: Session = Depends(get_db)):
    db.delete(_get(db, iid))
    db.commit()
