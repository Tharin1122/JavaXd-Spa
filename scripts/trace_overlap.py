import sys
sys.path.insert(0, '.')
from backend.db import SessionLocal
from backend.models import WalkIn, WalkInItem, Booking, BookingItem, Therapist, Customer

db = SessionLocal()
t = db.query(Therapist).filter(Therapist.display_name == 'ใบเตย').first()
print('--- walk-in items ของใบเตย ---')
for it in db.query(WalkInItem).filter(WalkInItem.therapist_id == t.id).all():
    w = db.get(WalkIn, it.walkin_id)
    c = db.get(Customer, w.customer_id)
    nm = c.display_name if c else '?'
    print(f'WI {w.queue_no} st={w.status} start={w.start_time} arr={w.arrival_time} {nm}')
print('--- booking items ของใบเตย ---')
for it in db.query(BookingItem).filter(BookingItem.therapist_id == t.id).all():
    b = db.get(Booking, it.booking_id)
    c = db.get(Customer, b.customer_id)
    nm = c.display_name if c else '?'
    print(f'BK {b.booking_no} st={b.status} {b.booking_date} {b.start_time} ci={b.checked_in} {nm}')
