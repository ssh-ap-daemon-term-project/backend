from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import User, RoomBooking, Hotel, Room
from ..database import SessionLocal
from ..middleware import is_admin
from ..schemas import HotelCreate, HotelUpdate, HotelResponse  # You'll need to create these schemas

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


# Hotel Management APIs
@router.get("/hotels", response_model=List[HotelResponse])
def get_all_hotels(db: Session = Depends(get_db)):
    """Get all hotels"""
    hotels = db.query(Hotel).all()
    return hotels

@router.get("/hotels/{hotel_id}", response_model=HotelResponse)
def get_hotel_by_id(hotel_id: int, db: Session = Depends(get_db)):
    """Get a specific hotel by ID"""
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    return hotel

@router.post("/hotels", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
def create_hotel(hotel: HotelCreate, db: Session = Depends(get_db)):
    """Create a new hotel"""
    # Check if a hotel with the same email already exists
    existing_hotel = db.query(Hotel).filter(Hotel.email == hotel.email).first()
    if existing_hotel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A hotel with this email already exists"
        )
    
    # Create a new Hotel instance
    new_hotel = Hotel(
        name=hotel.name,
        address=hotel.address,
        city=hotel.city,
        email=hotel.email,
        phone=hotel.phone,
        description=hotel.description if hasattr(hotel, "description") else None
    )
    
    db.add(new_hotel)
    db.commit()
    db.refresh(new_hotel)
    return new_hotel

@router.put("/hotels/{hotel_id}", response_model=HotelResponse)
def update_hotel(hotel_id: int, hotel_update: HotelUpdate, db: Session = Depends(get_db)):
    """Update an existing hotel"""
    # Find the hotel
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    
    # Check if updating to an email that already exists for another hotel
    if hasattr(hotel_update, "email") and hotel_update.email:
        existing_hotel = db.query(Hotel).filter(
            Hotel.email == hotel_update.email,
            Hotel.id != hotel_id
        ).first()
        if existing_hotel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A hotel with this email already exists"
            )
    
    # Update the hotel attributes
    for key, value in hotel_update.dict(exclude_unset=True).items():
        setattr(hotel, key, value)
    
    db.commit()
    db.refresh(hotel)
    return hotel

@router.delete("/hotels/{hotel_id}")
def delete_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """Delete a hotel"""
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    
    db.delete(hotel)
    db.commit()
    return {"message": "Hotel deleted successfully"}

# Add endpoint to get hotel rooms
@router.get("/hotels/{hotel_id}/rooms")
def get_hotel_rooms(hotel_id: int, db: Session = Depends(get_db)):
    """Get all rooms for a specific hotel"""
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    
    rooms = db.query(Room).filter(Room.hotelId == hotel_id).all()
    return rooms