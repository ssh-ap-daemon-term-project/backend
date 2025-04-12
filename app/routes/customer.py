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
from ..schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from ..models import User, RoomBooking, Hotel, Room, RoomItem, HotelReview, Customer, RideBooking, Itinerary, ScheduleItem, Driver

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