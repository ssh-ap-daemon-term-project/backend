from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, aliased
from typing import List, Optional, Dict, Any
from ..database import SessionLocal
from ..middleware import is_customer
from ..schemas import HotelCreate, HotelUpdate, HotelResponse  
from ..security import hash_password
from datetime import datetime, timedelta
from sqlalchemy import func
from .. import schemas
from ..schemas import CustomerCreate, CustomerUpdate, CustomerResponse , RideBookingBase , RideBookingResponse
from ..models import User, RoomBooking, Hotel, Room, RoomItem, HotelReview, Customer, RideBooking, Itinerary, ScheduleItem, Driver
from datetime import timedelta



# Create router with prefix and tags
router = APIRouter(
    dependencies=[Depends(is_customer)]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Itinerary functions
@router.post("/create-itinerary", response_model=schemas.ItineraryResponse)
def create_itinerary(itinerary: schemas.ItineraryCreate, request: Request, db: Session = Depends(get_db)):
    # Check if the user is a customer
    current_user = is_customer(request)
    
    # Get the customer profile
    customer = db.query(Customer).filter(Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Check if the itinerary name already exists for the customer
    existing_itinerary = db.query(Itinerary).filter(
        Itinerary.customerId == customer.id,
        Itinerary.name == itinerary.name
    ).first()
    
    if existing_itinerary:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Itinerary name already exists for this customer"
        )
    
    # Create the itinerary
    new_itinerary = Itinerary(
        customerId=customer.id,
        name=itinerary.name,
        numberOfPersons=itinerary.numberOfPersons
    )
    
    db.add(new_itinerary)
    db.commit()
    db.refresh(new_itinerary)
    
    return new_itinerary

@router.get("/get-itineraries", response_model=List[schemas.ItineraryResponse])
def get_itineraries(current_user: User = Depends(is_customer), db: Session = Depends(get_db)):
    
    # Get the customer profile
    customer = db.query(Customer).filter(Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Get all itineraries for the customer
    itineraries = db.query(Itinerary).filter(Itinerary.customerId == customer.id).all()

    # Get all room items for the itineraries
    room_items = db.query(RoomItem).filter(RoomItem.itinerary_id.in_([itinerary.id for itinerary in itineraries])).all()

    # Get all schedule items for the itineraries
    schedule_items = db.query(ScheduleItem).filter(ScheduleItem.itinerary_id.in_([itinerary.id for itinerary in itineraries])).all()

    # Add room items to the itineraries
    for itinerary in itineraries:
        # Add room items to the itinerary
        itinerary.room_items = [item for item in room_items if item.itinerary_id == itinerary.id]
        # Add schedule items to the itinerary
        itinerary.schedule_items = [item for item in schedule_items if item.itinerary_id == itinerary.id]
        # set itinerary.startDate and itinerary.endDate to the scheduleItem lowest startTime and highest endTime
        if itinerary.schedule_items:
            itinerary.startDate = min(item.startTime for item in itinerary.schedule_items)
            itinerary.endDate = max(item.endTime for item in itinerary.schedule_items)
        else:
            itinerary.startDate = None
            itinerary.endDate = None
    
    # Return the itineraries
    return itineraries


def calculate_ride_price(ride_type: str, with_driver_service: bool) -> float:
    """Calculate ride price based on type and driver service"""
    # Base price by ride type
    base_prices = {
        "taxi": 65.0,
        "premium": 85.0,
        "shuttle": 45.0
    }
    
    # Get base price or default to 50.0 if type not recognized
    base_price = base_prices.get(ride_type.lower(), 50.0)
    
    # Add driver service fee if requested
    if with_driver_service:
        base_price += 120.0  # Daily fee for driver service
        
    return base_price


@router.post("/customer_itineraries/{itinerary_id}/rides", response_model=schemas.RideBookingResponse)
def book_ride_for_itinerary(
    itinerary_id: int,
    ride_data: schemas.RideBookingCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Book a ride for an itinerary with pending status"""
    # Get the current user and their customer profile
    current_user = is_customer(request)
    customer = db.query(Customer).filter(Customer.userId == current_user.id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Check if the itinerary exists and belongs to this customer
    itinerary = db.query(Itinerary).filter(
        Itinerary.id == itinerary_id,
        Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found or you don't have access"
        )
    
    try:
                
        # Create the ride booking - note driverId is NULL initially
        new_ride = RideBooking(
            pickupLocation=ride_data.pickupLocation,
            dropLocation=ride_data.dropoffLocation,
            pickupDateTime=ride_data.pickupDateTime,
            numberOfPersons=ride_data.numberOfPersons if ride_data.numberOfPersons else itinerary.numberOfPersons,
            price=100,                                  #by default 100
            status="pending",  # Set initial status as pending
            customerId=customer.id,
            itineraryId=itinerary_id
        )
        
        db.add(new_ride)
        db.commit()
        db.refresh(new_ride)
        
        # Format the response
        return {
            "id": new_ride.id,
            "pickupLocation": new_ride.pickupLocation,
            "dropLocation": new_ride.dropLocation,
            "pickupTime": new_ride.pickupTime,
            "dropTime": new_ride.dropTime,
            "numberOfPersons": new_ride.numberOfPersons,
            "price": float(new_ride.price),  # Convert Decimal to float if needed
            "status": new_ride.status,
            "driverName": "Pending...",
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to book ride: {str(e)}"
        )

# @router.get("/{id}", response_model=schemas.FullItineraryResponse)
# def get_itinerary(
#     id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(is_customer)
# ):
#     # Get the itinerary
#     itinerary = db.query(Itinerary).filter(Itinerary.id == id).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {id} not found"
#         )
    
#     # Check if the user is authorized to view this itinerary
#     if current_user.userType == "customer":
#         customer = db.query(Customer).filter(Customer.userId == current_user.id).first()
#         if not customer or itinerary.customerId != customer.id:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Not authorized to access this itinerary"
#             )
#     elif current_user.userType != "admin":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this itinerary"
#         )
    
#     return itinerary