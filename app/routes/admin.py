from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import User, RoomBooking, Hotel, Room
from ..database import SessionLocal
from ..middleware import is_admin
from ..schemas import HotelCreate, HotelUpdate, HotelResponse  # You'll need to create these schemas
from ..security import hash_password

# Create router with prefix and tags
router = APIRouter(
    # dependencies=[Depends(is_admin)]
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



# Hotel Management APIs
@router.get("/hotels", response_model=List[HotelResponse])
def get_all_hotels(db: Session = Depends(get_db)):
    """Get all hotels with user data"""
    hotels_with_users = []
    
    # Get all hotels
    hotels = db.query(Hotel).all()
    
    for hotel in hotels:
        # Get associated user
        user = db.query(User).filter(User.id == hotel.userId).first()
        
        if not user:
            continue  # Skip hotels with missing user data
        
        # Create a combined dictionary with fields from both models
        hotel_data = {
            "id": hotel.id,
            "userId": hotel.userId,
            "name": user.name,  # From User model
            "address": user.address,  # From User model
            "email": user.email,  # From User model
            "phone": user.phone,  # From User model
            "city": hotel.city,
            "latitude": hotel.latitude,
            "longitude": hotel.longitude,
            "rating": hotel.rating,
            "createdAt": hotel.createdAt
        }
        
        # Add description if your schema expects it
        if hasattr(hotel, "description"):
            hotel_data["description"] = hotel.description
        else:
            hotel_data["description"] = None
            
        hotels_with_users.append(hotel_data)
    
    return hotels_with_users

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
    new_hotel = Hotel(**hotel.dict())
    
@router.put("/hotels/{hotel_id}", response_model=HotelResponse)
def update_hotel(hotel_id: int, hotel_update: HotelUpdate, db: Session = Depends(get_db)):
    """Update an existing hotel and its associated user"""
    # Find the hotel
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    
    # Find the associated user
    user = db.query(User).filter(User.id == hotel.userId).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with hotel not found"
        )
    
    try:
        # Start a transaction for updating both records
        
        # Update User fields (if provided)

        if hasattr(hotel_update, "username") and hotel_update.username is not None:
            # see if the username is already taken
            existing_user = db.query(User).filter(User.username == hotel_update.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            user.username = hotel_update.username
        else:
            user.username = user.username  # Use the existing username if not provided

        if hasattr(hotel_update, "password") and hotel_update.password is not None:
            hashed = hash_password(hotel_update.password)
            user.hashedPassword = hashed
        else:
            user.hashedPassword = user.hashedPassword  # Use the existing password if not provided
        if hasattr(hotel_update, "name") and hotel_update.name is not None:
            user.name = hotel_update.name
        else:
            user.name = user.name  # Use the existing name if not provided
            
        if hasattr(hotel_update, "email") and hotel_update.email is not None:
            # Check if email already exists for another user
            existing_user = db.query(User).filter(
                User.email == hotel_update.email,
                User.id != user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered to another user"
                )
            user.email = hotel_update.email
        else:
            user.email = user.email  # Use the existing email if not provided
            
        if hasattr(hotel_update, "phone") and hotel_update.phone is not None:
            # Check if phone already exists for another user
            existing_user = db.query(User).filter(
                User.phone == hotel_update.phone,
                User.id != user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered to another user"
                )
            user.phone = hotel_update.phone
        else:
            user.phone = user.phone  # Use the existing phone if not provided
            
        if hasattr(hotel_update, "address") and hotel_update.address is not None:
            user.address = hotel_update.address
        else:
            user.address = user.address  # Use the existing address if not provided
            
        # Update Hotel fields (if provided)
        if hasattr(hotel_update, "city") and hotel_update.city is not None:
            hotel.city = hotel_update.city
        else:
            hotel.city = hotel.city  # Use the existing city if not provided
            
        if hasattr(hotel_update, "latitude") and hotel_update.latitude is not None:
            hotel.latitude = hotel_update.latitude
        else:
            hotel.latitude = hotel.latitude  # Use the existing latitude if not provided
            
        if hasattr(hotel_update, "longitude") and hotel_update.longitude is not None:
            hotel.longitude = hotel_update.longitude
        else:
            hotel.longitude = hotel.longitude  # Use the existing longitude if not provided
            
        if hasattr(hotel_update, "rating") and hotel_update.rating is not None:
            hotel.rating = hotel_update.rating
        else:
            hotel.rating = hotel.rating  # Use the existing rating if not provided
            
        if hasattr(hotel_update, "description") and hotel_update.description is not None:
            hotel.description = hotel_update.description
        else:
            hotel.description = hotel.description  # Use the existing description if not provided
        
        # Commit the changes
        db.commit()
        
        # Prepare response
        hotel_data = {
            "id": hotel.id,
            "userId": hotel.userId,
            "username": user.username,
            "name": user.name,
            "address": user.address,
            "email": user.email,
            "phone": user.phone,
            "city": hotel.city,
            "latitude": hotel.latitude,
            "longitude": hotel.longitude,
            "rating": hotel.rating,
            "description": hotel.description,
            "createdAt": hotel.createdAt
        }
        
        return hotel_data
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update hotel: {str(e)}"
        )

@router.delete("/hotels/{hotel_id}")
def delete_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """Delete a hotel"""
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found"
        )
    
    # delete the corresponding rooms
    rooms = db.query(Room).filter(Room.hotelId == hotel_id).all()
    for room in rooms:
        db.delete(room)

    # delete corresponding
    
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