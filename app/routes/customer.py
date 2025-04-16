from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import and_, exists
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
from sqlalchemy.orm import joinedload

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

@router.delete(
    "/itinerary/room/cancel/{room_item_id}",
    response_model=schemas.ItineraryBookingCancellationResponse,
    responses={
        404: {"model": schemas.ErrorResponse, "description": "Not Found"},
        403: {"model": schemas.ErrorResponse, "description": "Access Denied"}
    }
)
async def cancel_room_booking_endpoint(
    room_item_id: int,
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
    
    # Get the room item first
    room_item = db.query(models.RoomItem).filter(models.RoomItem.id == room_item_id).first()
    if not room_item:
        raise HTTPException(
            status_code=404,
            detail="Room item not found"
        )
    
    # Check if the room item belongs to an itinerary owned by this customer
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == room_item.itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=403,
            detail="Access denied: This room item doesn't belong to your itinerary"
        )
    
    # Check if the room is actually booked
    if not room_item.roomBookingId:
        raise HTTPException(
            status_code=400,
            detail="This room is not currently booked"
        )
    
    # Call the service function to handle cancellation
    return cancel_room_booking(db, room_item.roomBookingId, customer.id)

@router.get("/all-hotels", response_model=List[schemas.CustomerHotelResponse])
def get_hotels(
    search: Optional[str] = None,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get a list of hotels with optional filtering.
    """
    # Join with the User table to efficiently access name/address data
    query = db.query(models.Hotel, models.User).join(
        models.User, models.Hotel.userId == models.User.id
    )
    
    # Apply search filter on the joined tables
    if search:
        query = query.filter(
            (models.User.name.ilike(f"%{search}%")) | 
            (models.Hotel.city.ilike(f"%{search}%")) |
            (models.User.address.ilike(f"%{search}%"))
        )
    
    # Apply city filter
    if city:
        query = query.filter(models.Hotel.city.ilike(f"%{city}%"))
    
    # Apply price filters based on the Room prices, not the hotel's basePrice.
    # This ensures that the hotel remains in the result if at least one room
    # has a price between the given min_price and max_price.
    if min_price is not None or max_price is not None:
        room_conditions = []
        if min_price is not None:
            room_conditions.append(models.Room.basePrice >= min_price)
        if max_price is not None:
            room_conditions.append(models.Room.basePrice <= max_price)
        
        # Use a subquery to check for existence of a room type in the hotel that meets the conditions.
        query = query.filter(
            db.query(models.Room)
              .filter(models.Room.hotelId == models.Hotel.id, *room_conditions)
              .exists()
        )
    
    # Apply rating filter
    if min_rating is not None:
        query = query.filter(models.Hotel.rating >= min_rating)
    
    # Get hotels with their associated users in a single query
    results = query.all()
    
    # Format the response data
    response_data = []
    for hotel, user in results:
        # Simulated amenity logic; replace with actual logic if needed.
        amenities = ["Free WiFi", "Parking"] if hotel.id % 2 == 0 else ["Pool", "Gym"]
        
        hotel_dict = {
            "id": hotel.id,
            "name": user.name,  # Name from User model
            "city": hotel.city,
            "address": user.address,  # Address from User model
            "description": hotel.description,
            # basePrice can still be set here if needed; otherwise, it might be omitted.
            "basePrice": None,
            "rating": float(hotel.rating) if hotel.rating else None,
            "imageUrl": hotel.imageUrl if hasattr(hotel, 'imageUrl') else None,
            "amenities": amenities
        }
        response_data.append(hotel_dict)
    
    return response_data

@router.get("/hotel/{hotel_id}", response_model=schemas.CustomerHotelByIdResponse)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific hotel including reviews.
    """
    # Get both the hotel and its associated user in a single query
    result = db.query(models.Hotel, models.User).join(
        models.User, models.Hotel.userId == models.User.id
    ).filter(models.Hotel.id == hotel_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    hotel, user = result
    
    # Get the hotel reviews with customer and user information
    reviews_query = db.query(
        models.HotelReview, 
        models.Customer, 
        models.User
    ).join(
        models.Customer, models.HotelReview.customerId == models.Customer.id
    ).join(
        models.User, models.Customer.userId == models.User.id
    ).filter(
        models.HotelReview.hotelId == hotel_id
    ).order_by(
        models.HotelReview.createdAt.desc()
    ).all()
    
    # Format the reviews
    reviews = []
    for review, customer, reviewer_user in reviews_query:
        reviews.append({
            "id": review.id,
            "customerId": customer.id,
            "customerName": reviewer_user.name,
            "rating": float(review.rating),
            "description": review.description,
            "createdAt": review.createdAt.isoformat() if review.createdAt else None
        })
    
    # Get all rooms for this hotel
    rooms = db.query(models.Room).filter(models.Room.hotelId == hotel_id).all()

    # Format the rooms
    rooms_list = []
    for room in rooms:
        # find number of rooms available on specified days
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=60)  # Example: next 60 days
        room_bookings = db.query(models.RoomBooking).filter(
            models.RoomBooking.roomId == room.id,
            models.RoomBooking.startDate <= end_date,
            models.RoomBooking.endDate > start_date
        ).all()
        
        # Calculate number of rooms booked for each day from start_date to end_date in a list
        booked_rooms = [0] * ((end_date - start_date).days + 1)
        for booking in room_bookings:
            start_index = max(0, (booking.startDate - start_date).days)
            end_index = min((end_date - start_date).days, (booking.endDate - start_date).days - 1)
            for i in range(start_index, end_index + 1):
                booked_rooms[i] += 1
        print("booked_rooms", booked_rooms)

        # calculate the number of available rooms list
        available_rooms_list = [room.totalNumber - booked for booked in booked_rooms]
        print("available_rooms_list", available_rooms_list)
        
        rooms_list.append({
            "id": room.id,
            "type": room.type,
            "basePrice": float(room.basePrice) if hasattr(room, 'basePrice') and room.basePrice else None,
            "roomCapacity": room.roomCapacity,
            "totalNumber": room.totalNumber,
            "availableRoomsList": available_rooms_list
        })
    
    # Simulated amenity logic; replace with actual logic if needed.
    
    # Format and return the hotel detail response with reviews
    hotel_dict = {
        "id": hotel.id,
        "name": user.name,  # Name from User model
        "city": hotel.city,
        "address": user.address,  # Address from User model
        "latitude": hotel.latitude,
        "longitude": hotel.longitude,
        "description": hotel.description,
        "basePrice": float(hotel.basePrice) if hasattr(hotel, 'basePrice') and hotel.basePrice else None,
        "rating": float(hotel.rating) if hotel.rating else None,
        "imageUrl": hotel.imageUrl if hasattr(hotel, 'imageUrl') else None,
        "rooms": rooms_list,
        # "amenities": amenities,
        "reviews": reviews  # Add the reviews to the response
    }
    
    return hotel_dict

# const response = await bookRoomByRoomId({
#         roomId: selectedRoom.id,
#         startDate: bookingDates.from.toISOString(),
#         endDate: bookingDates.to.toISOString(),
#         numberOfPersons: guests
#       })
# Book room by room id
# Book room by room id helper function
def book_room_by_room_id(db: Session, room_id: int, start_date: datetime, end_date: datetime, number_of_persons: int, customer_id: int):
    """
    Book a room with the specified details.
    """
    # First, ensure all datetime objects are timezone-consistent
    # Convert to timezone-naive if input dates have timezone info
    if start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    if end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)
    
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail="Room not found"
        )
    
    # Check room capacity
    if number_of_persons > room.roomCapacity:
        raise HTTPException(
            status_code=400,
            detail=f"Number of persons ({number_of_persons}) exceeds room capacity ({room.roomCapacity})"
        )
    
    # Check if the room is available for the specified dates
    existing_bookings = db.query(models.RoomBooking).filter(
        models.RoomBooking.roomId == room_id,
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
            # Make booking dates timezone-naive for comparison
            booking_start = booking.startDate
            booking_end = booking.endDate
            
            if booking_start.tzinfo is not None:
                booking_start = booking_start.replace(tzinfo=None)
            if booking_end.tzinfo is not None:
                booking_end = booking_end.replace(tzinfo=None)
                
            if booking_start <= current_date < booking_end:
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
    
    # All checks passed, create a new booking
    room_booking = models.RoomBooking(
        customerId=customer_id,
        roomId=room_id,
        startDate=start_date,
        endDate=end_date,
        numberOfPersons=number_of_persons,
    )
    
    db.add(room_booking)
    db.commit()
    db.refresh(room_booking)
    
    # Calculate price (basePrice * number of days)
    days = (end_date - start_date).days
    total_price = float(room.basePrice) * days
    
    # Get hotel name for response
    hotel = db.query(models.Hotel).join(models.User).filter(models.Hotel.id == room.hotelId).first()
    hotel_name = db.query(models.User).filter(models.User.id == hotel.userId).first().name
    
    # Return success response
    return {
        "booking_id": room_booking.id,
        "room_id": room_id,
        "start_date": start_date,
        "end_date": end_date,
        "room_type": room.type,
        "hotel_name": hotel_name,
        "number_of_persons": number_of_persons,
        "total_price": total_price
    }

@router.post("/book-room", response_model=schemas.RoomBookingByRoomIdResponse)
async def book_room_by_room_id_endpoint(booking_data: schemas.RoomBookingByRoomIdRequest, db: Session = Depends(get_db), current_user = Depends(is_customer)):
    """
    Book a room with the specified details.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer account not found"
        )
    
    return book_room_by_room_id(
        db, 
        booking_data.room_id, 
        booking_data.start_date, 
        booking_data.end_date, 
        booking_data.number_of_persons, 
        customer.id
    )

# # Cancel room booking by booking ID
# def cancel_room_booking_by_id(db: Session, booking_id: int, customer_id: int) -> dict:
#     """
#     Cancels an existing room booking by booking ID
    
#     Args:
#         db: Database session
#         booking_id: ID of the booking to cancel
#         customer_id: ID of the customer making the request
        
#     Returns:
#         dict: Confirmation of cancellation
        
#     Raises:
#         HTTPException: If booking doesn't exist or doesn't belong to the customer
#     """
#     # Find the booking
#     booking = db.query(models.RoomBooking).filter(models.RoomBooking.id == booking_id).first()
    
#     if not booking:
#         raise HTTPException(status_code=404, detail="Booking not found")
    
#     # Verify ownership
#     if booking.customerId != customer_id:
#         raise HTTPException(
#             status_code=403,
#             detail="Access denied: This booking doesn't belong to you"
#         )
    
#     # Find any room item associated with this booking (to clean up references)
#     room_item = db.query(models.RoomItem).filter(models.RoomItem.roomBookingId == booking_id).first()
    
#     if room_item:
#         # Remove the booking reference from the room item
#         room_item.roomBookingId = None
    
#     # Delete the booking
#     db.delete(booking)
#     db.commit()
    
#     return {"message": "Room booking cancelled successfully", "booking_id": booking_id}

# @router.delete(
#     "/cancel-booking/{booking_id}",
#     response_model=schemas.BookingCancellationByBookingIdResponse,
#     responses={
#         404: {"model": schemas.ErrorResponse, "description": "Not Found"},
#         403: {"model": schemas.ErrorResponse, "description": "Access Denied"}
#     }
# )
# async def cancel_room_booking_by_id_endpoint(
#     booking_id: int,
#     db: Session = Depends(get_db),
#     current_user = Depends(is_customer)
# ):
#     """
#     Cancel a room booking by booking ID.
    
#     This endpoint allows customers to cancel their existing room bookings.
#     The room will be freed up for other customers to book.
#     """
    
#     # Get the customer ID associated with the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     if not customer:
#         raise HTTPException(
#             status_code=404,
#             detail="Customer account not found"
#         )
    
#     return cancel_room_booking_by_id(db, booking_id, customer.id)

# Get all customer bookings
@router.get("/bookings", response_model=List[schemas.CustomerBookingResponse])
async def get_customer_bookings(
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Get all bookings for the currently logged in customer.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer account not found"
        )
    
    # Get all bookings for this customer
    bookings = db.query(models.RoomBooking).filter(
        models.RoomBooking.customerId == customer.id
    ).order_by(models.RoomBooking.startDate.desc()).all()
    
    result = []
    
    for booking in bookings:
        # Get room info
        room = db.query(models.Room).filter(models.Room.id == booking.roomId).first()
        if not room:
            raise HTTPException(
                status_code=404,
                detail="Room not found"
            )
        
        # Get hotel info
        hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
        if not hotel:
            raise HTTPException(
                status_code=404,
                detail="Hotel not found"
            )
        
        # Get hotel name from user table
        hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
        if not hotel_user:
            raise HTTPException(
                status_code=404,
                detail="Hotel user not found"
            )
        
        # Determine booking status
        status = "upcoming"
        now = datetime.utcnow()
        
        if booking.endDate < now:
            status = "completed"
        
        # Calculate total price
        days = (booking.endDate - booking.startDate).days
        total_price = float(room.basePrice) * days
        
        # Get the first hotel image if available
        image = hotel.imageUrl if hasattr(hotel, 'imageUrl') and hotel.imageUrl else None
        
        result.append({
            "id": booking.id,
            "hotelId": hotel.id,
            "hotelName": hotel_user.name,
            "roomName": room.type,
            "city": hotel.city,
            "startDate": booking.startDate,
            "endDate": booking.endDate,
            "guests": booking.numberOfPersons,
            "totalPrice": total_price,
            "status": status,
            "image": image
        })
    
    return result

# Cancel a booking
@router.post("/bookings/{booking_id}/cancel", response_model=schemas.CancelBookingResponse)
async def cancel_customer_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Cancel a specific booking.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer account not found"
        )
    
    # Find the booking
    booking = db.query(models.RoomBooking).filter(
        models.RoomBooking.id == booking_id,
        models.RoomBooking.customerId == customer.id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found or does not belong to this customer"
        )
    
    # Check if booking is already completed
    now = datetime.utcnow()
    if booking.endDate < now:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a completed booking"
        )
    
    # Check cancellation policy (24 hours before checkin)
    if (booking.startDate - now).total_seconds() < 24 * 60 * 60:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a booking within 24 hours of checkin"
        )
    
    db.delete(booking)
    
    # Find any room item associated with this booking (to clean up references)
    room_item = db.query(models.RoomItem).filter(models.RoomItem.roomBookingId == booking_id).first()
    if room_item:
        # Remove the booking reference from the room item
        room_item.roomBookingId = None
    
    db.commit()
    
    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking_id
    }

# Write a review for a booking
@router.post("/bookings/review", response_model=schemas.HotelReviewResponse)
async def create_booking_review(
    review_data: schemas.BookingReviewRequest,
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Create a review for a completed booking.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer account not found"
        )
    
    # Find the booking
    booking = db.query(models.RoomBooking).filter(
        models.RoomBooking.id == review_data.booking_id,
        models.RoomBooking.customerId == customer.id
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found or does not belong to this customer"
        )
    
    # Check if booking is completed
    now = datetime.utcnow()
    if booking.endDate > now:
        raise HTTPException(
            status_code=400,
            detail="Cannot review a booking that hasn't been completed yet"
        )
    
    # Check if a review already exists for this hotel by this customer
    existing_review = db.query(models.HotelReview).filter(
        models.HotelReview.customerId == customer.id,
        models.HotelReview.hotelId == booking.room.hotelId
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this hotel"
        )
    
    # Get room and hotel for this booking
    room = db.query(models.Room).filter(models.Room.id == booking.roomId).first()
    if not room:
        raise HTTPException(
            status_code=404,
            detail="Room information not found"
        )
    
    # Create the review
    new_review = models.HotelReview(
        customerId=customer.id,
        hotelId=room.hotelId,
        rating=review_data.rating,
        description=review_data.comment
    )
    
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    
    return {
        "id": new_review.id,
        "customerId": customer.id,
        "customerName": current_user.name,
        "rating": float(new_review.rating),
        "description": new_review.description,
        "createdAt": new_review.createdAt.isoformat()
    }

# Get all reviews by the current customer
@router.get("/reviews", response_model=List[schemas.CustomerReviewResponse])
async def get_customer_reviews(
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Get all reviews written by the currently logged in customer.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer account not found")
    
    # Get all reviews by this customer
    reviews = db.query(models.HotelReview).filter(
        models.HotelReview.customerId == customer.id
    ).all()
    
    result = []
    
    for review in reviews:
        # Get hotel info
        hotel = db.query(models.Hotel).filter(models.Hotel.id == review.hotelId).first()
        if not hotel:
            continue  # Skip if hotel not found
        
        # Get hotel name from user table
        hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
        if not hotel_user:
            continue  # Skip if user not found
        
        result.append({
            "id": review.id,
            "hotelId": hotel.id,
            "hotelName": hotel_user.name,
            "city": hotel.city,
            "rating": int(review.rating),
            "comment": review.description,
            "date": review.createdAt.strftime('%Y-%m-%d'),
            "image": hotel.imageUrl if hasattr(hotel, 'imageUrl') and hotel.imageUrl else None
        })
    
    return result

# Update a review
@router.put("/reviews/{review_id}", response_model=schemas.HotelReviewResponse)
async def update_review(
    review_id: int,
    review_data: schemas.HotelReviewUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Update a review written by the current customer.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer account not found")
    
    # Get the review
    review = db.query(models.HotelReview).filter(
        models.HotelReview.id == review_id,
        models.HotelReview.customerId == customer.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or does not belong to this customer")
    
    # Update fields
    if review_data.rating is not None:
        review.rating = review_data.rating
    
    if review_data.comment is not None:
        review.description = review_data.comment
    
    # review.updatedAt = datetime.utcnow()
    
    db.commit()
    db.refresh(review)
    
    return {
        "id": review.id,
        "customerId": review.customerId,
        "customerName": current_user.name,
        "rating": float(review.rating),
        "description": review.description,
        "createdAt": review.createdAt
    }

# Delete a review
@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(is_customer)
):
    """
    Delete a review written by the current customer.
    """
    # Get the customer ID associated with the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer account not found")
    
    # Get the review
    review = db.query(models.HotelReview).filter(
        models.HotelReview.id == review_id,
        models.HotelReview.customerId == customer.id
    ).first()
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or does not belong to this customer")
    
    # Store the hotel ID to update its rating later
    hotel_id = review.hotelId
    
    # Delete the review
    db.delete(review)
    db.commit()
    
    return {"message": "Review deleted successfully", "review_id": review_id}