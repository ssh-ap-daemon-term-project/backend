from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import and_
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
from .. import models


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

# room booking
# room booking helper function
def book_room(db: Session, request: schemas.ItineraryRoomBookingRequest) -> schemas.ItineraryRoomBookingResponse:
    """
    Books a room based on a room item in an itinerary
    
    Args:
        db: Database session
        request: Room booking request containing room_item_id, number_of_persons, and customer_id
        
    Returns:
        RoomBookingResponse: Details of the successful booking
        
    Raises:
        HTTPException: If validation fails or room is unavailable
    """
    # Step 1: Check if the room item exists and belongs to the customer's itinerary
    room_item = db.query(models.RoomItem).filter(models.RoomItem.id == request.room_item_id).first()
    
    if not room_item:
        raise HTTPException(status_code=404, detail="Room item not found")
    
    # Verify customer owns the itinerary
    itinerary = db.query(models.Itinerary).filter(
        and_(
            models.Itinerary.id == room_item.itineraryId,
            models.Itinerary.customerId == request.customer_id
        )
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: This room item doesn't belong to your itinerary"
        )
    
    # Step 2: Check if the room is already booked
    if room_item.roomBookingId is not None:
        raise HTTPException(
            status_code=400,
            detail="This room is already booked"
        )
    
    room = db.query(models.Room).filter(models.Room.id == room_item.roomId).first()
    # # Step 3: Check room capacity
    # if request.number_of_persons > room.roomCapacity:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Number of persons ({request.number_of_persons}) exceeds room capacity ({room.roomCapacity})"
    #     )
    
    # Step 3: Check room availability for each day in the date range
    start_date = room_item.startDate
    end_date = room_item.endDate
    
    # Get all bookings for this room type in the hotel during the date range
    existing_bookings = db.query(models.RoomBooking).join(
        models.Room, models.Room.id == models.RoomBooking.roomId
    ).filter(
        models.RoomBooking.startDate < end_date,
        models.RoomBooking.endDate > start_date
    ).all()
    
    # Calculate availability for each day
    current_date = start_date
    unavailable_dates = []
    
    while current_date < end_date:
        # Count bookings that include this day
        bookings_count = 0
        for booking in existing_bookings:
            if booking.startDate <= current_date < booking.endDate:
                bookings_count += 1
        
        # Check if there's at least one room available
        if bookings_count >= room.totalNumber:
            unavailable_dates.append(current_date.strftime("%Y-%m-%d"))
        
        current_date += timedelta(days=1)
    
    # If any days are unavailable, return an error
    if unavailable_dates:
        raise HTTPException(
            status_code=409,
            detail=f"Room not available for the following dates: {', '.join(unavailable_dates)}"
        )
    
    # Step 4: All checks passed, create a new booking
    room_booking = models.RoomBooking(
        customerId=request.customer_id,
        roomId=room_item.roomId,
        startDate=start_date,
        endDate=end_date,
        numberOfPersons=request.number_of_persons,
    )
    
    db.add(room_booking)
    db.flush()  # Get the ID of the new booking
    
    # Update the room item with the booking ID
    room_item.roomBookingId = room_booking.id
    
    db.commit()
    
    # Calculate price (basePrice * number of days)
    days = (end_date - start_date).days
    total_price = room.basePrice * days
    
    # Get hotel name for response
    hotel_name = room.hotel.user.name
    
    # Return success response
    return schemas.ItineraryRoomBookingResponse(
        booking_id=room_booking.id,
        room_item_id=room_item.id,
        start_date=start_date,
        end_date=end_date,
        room_type=room.type,
        hotel_name=hotel_name,
        number_of_persons=request.number_of_persons,
        total_price=total_price
    )

@router.post(
    "/itinerary/room/book", 
    response_model=schemas.ItineraryRoomBookingResponse, 
    responses={
        400: {"model": schemas.ErrorResponse, "description": "Bad Request"},
        403: {"model": schemas.ErrorResponse, "description": "Access Denied"},
        404: {"model": schemas.ErrorResponse, "description": "Not Found"},
        409: {"model": schemas.ErrorResponse, "description": "Conflict - Room Unavailable"}
    }
)
async def create_room_booking(
    request: schemas.ItineraryRoomBookingRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Book a room from an itinerary's room item.
    
    This endpoint allows a customer to book a room that was previously added to their itinerary.
    It checks for room availability and creates a booking if the room is available.
    """
    
    # Verify the customer ID in the request matches the authenticated user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if customer.id != request.customer_id:
        raise HTTPException(
            status_code=403,
            detail="You can only book rooms for your own itineraries"
        )
    
    # Call the service function to handle booking
    return book_room(db, request)

# cancel room booking
# cancel room booking helper function
def cancel_room_booking(db: Session, booking_id: int, customer_id: int) -> dict:
    """
    Cancels an existing room booking
    
    Args:
        db: Database session
        booking_id: ID of the booking to cancel
        customer_id: ID of the customer making the request
        
    Returns:
        dict: Confirmation of cancellation
        
    Raises:
        HTTPException: If booking doesn't exist or doesn't belong to the customer
    """
    # Find the booking
    booking = db.query(models.RoomBooking).filter(models.RoomBooking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify ownership
    if booking.customerId != customer_id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: This booking doesn't belong to you"
        )
    
    # Find the room item associated with this booking
    room_item = db.query(models.RoomItem).filter(models.RoomItem.roomBookingId == booking_id).first()
    
    if room_item:
        # Remove the booking reference from the room item
        room_item.roomBookingId = None
    
    # Delete the booking
    db.delete(booking)
    db.commit()
    
    return {"message": "Room booking cancelled successfully", "booking_id": booking_id}

# Add this route after your book-room endpoint
@router.delete(
    "/itinerary/room/cancel/{booking_id}",
    response_model=schemas.ItineraryBookingCancellationResponse,
    responses={
        404: {"model": schemas.ErrorResponse, "description": "Not Found"},
        403: {"model": schemas.ErrorResponse, "description": "Access Denied"}
    }
)
async def cancel_room_booking_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Cancel a room booking.
    
    This endpoint allows customers to cancel their existing room bookings.
    The room will be freed up for other customers to book.
    """
    
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer account not found"
        )
    
    # Call the service function to handle cancellation
    return cancel_room_booking(db, booking_id, customer.id)


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
