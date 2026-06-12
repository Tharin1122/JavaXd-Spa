import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uid() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now()  # เวลาท้องถิ่นเครื่องร้าน (ไทย)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200), default="")
    display_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="Reception")  # Owner/Manager/Reception/Therapist/Cashier
    line_user_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Therapist(Base):
    __tablename__ = "therapists"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    display_name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    skill_level: Mapped[int] = mapped_column(Integer, default=0)
    current_status: Mapped[int] = mapped_column(Integer, default=0)  # 0ว่าง 1ไม่ว่าง 2พัก 3ลา 4เลิกงาน 5ยังไม่เข้า
    avatar_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class TherapistService(Base):
    __tablename__ = "therapist_services"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    therapist_id: Mapped[str] = mapped_column(String(32), index=True)
    service_id: Mapped[str] = mapped_column(String(32), index=True)


class TherapistSchedule(Base):
    __tablename__ = "therapist_schedules"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    therapist_id: Mapped[str] = mapped_column(String(32), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(8), default="10:00:00")
    end_time: Mapped[str] = mapped_column(String(8), default="22:00:00")
    is_workday: Mapped[bool] = mapped_column(Boolean, default=True)


class TherapistLeave(Base):
    __tablename__ = "therapist_leaves"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    therapist_id: Mapped[str] = mapped_column(String(32), index=True)
    leave_date: Mapped[str] = mapped_column(String(10))
    leave_type: Mapped[int] = mapped_column(Integer, default=0)  # 0 ทั้งวัน 1 บางช่วง
    start_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0 รอ 1 อนุมัติ 2 ไม่อนุมัติ
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    display_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_visits: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80))


class Service(Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    category_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    duration_mins: Mapped[int] = mapped_column(Integer, default=60)
    buffer_mins: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    commission_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # % ของราคา
    commission_fixed: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    booking_no: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[str] = mapped_column(String(32), index=True)
    booking_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(8))  # HH:MM:SS
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0รอ 1ยืนยัน 2กำลังบริการ 3เสร็จ 4ยกเลิก 5ไม่มา
    checked_in: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    items: Mapped[list["BookingItem"]] = relationship(cascade="all, delete-orphan")


class BookingItem(Base):
    __tablename__ = "booking_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(32))
    therapist_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    therapist_selection_mode: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, default=0.0)


class WalkIn(Base):
    __tablename__ = "walkins"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    queue_no: Mapped[str] = mapped_column(String(12))
    customer_id: Mapped[str] = mapped_column(String(32), index=True)
    booking_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0รอ 1กำลังบริการ 2เสร็จ 3ยกเลิก
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrival_time: Mapped[datetime] = mapped_column(DateTime, default=now)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    items: Mapped[list["WalkInItem"]] = relationship(cascade="all, delete-orphan")


class WalkInItem(Base):
    __tablename__ = "walkin_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    walkin_id: Mapped[str] = mapped_column(ForeignKey("walkins.id"), index=True)
    service_id: Mapped[str] = mapped_column(String(32))
    therapist_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, default=0.0)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    receipt_no: Mapped[str] = mapped_column(String(24))
    walkin_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    booking_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_method: Mapped[int] = mapped_column(Integer, default=0)  # 0เงินสด 1โอน 2QR 3บัตร
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    items: Mapped[list["PaymentItem"]] = relationship(cascade="all, delete-orphan")


class PaymentItem(Base):
    __tablename__ = "payment_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), index=True)
    service_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    service_name: Mapped[str] = mapped_column(String(160))
    therapist_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    category: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    spent_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    sku: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="ของใช้")
    unit: Mapped[str] = mapped_column(String(30), default="ชิ้น")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    cost_per_unit: Mapped[float] = mapped_column(Float, default=0.0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=5)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    item_id: Mapped[str] = mapped_column(String(32), index=True)
    type: Mapped[str] = mapped_column(String(8))  # in / out
    quantity: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Package(Base):
    __tablename__ = "packages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_sessions: Mapped[int] = mapped_column(Integer, default=10)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sold_count: Mapped[int] = mapped_column(Integer, default=0)


class CustomerPackage(Base):
    __tablename__ = "customer_packages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    customer_id: Mapped[str] = mapped_column(String(32), index=True)
    package_id: Mapped[str] = mapped_column(String(32))
    package_name: Mapped[str] = mapped_column(String(160))
    total_sessions: Mapped[int] = mapped_column(Integer, default=10)
    remaining_sessions: Mapped[int] = mapped_column(Integer, default=10)
    expires_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Promotion(Base):
    __tablename__ = "promotions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(10), default="promo")  # promo / coupon
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    campaign: Mapped[str | None] = mapped_column(String(160), nullable=True)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quota: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    therapist_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    event_type: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class KeyValue(Base):
    """เก็บ settings / role matrix / subscription เป็น JSON"""
    __tablename__ = "key_values"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="{}")
