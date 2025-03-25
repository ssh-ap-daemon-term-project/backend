from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models import User, RoomBooking
from ..database import SessionLocal
from ..middleware import is_admin

# Create router with prefix and tags
router = APIRouter(
    dependencies=[Depends(is_admin)]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Now your routes will automatically have /admin prefix
@router.get("/customers")
def get_all_customers(db: Session = Depends(get_db)):
    """Get all customers"""
    customers = db.query(User).filter(User.userType == "customer").all()
    return customers

@router.delete("/customer/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Delete a customer"""
    customer = db.query(User).filter(User.id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}
    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted"}

@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db)):
    """Admin dashboard statistics"""
    # Count of different user types
    stats = {
        "customers": db.query(User).filter(User.userType == "customer").count(),
        "hotels": db.query(User).filter(User.userType == "hotel").count(),
        "drivers": db.query(User).filter(User.userType == "driver").count(),
        "admins": db.query(User).filter(User.userType == "admin"),
        "room_bookings": db.query(RoomBooking).count(),
    }
    return stats

