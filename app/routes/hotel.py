from fastapi import APIRouter, Depends , HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import User, RoomBooking, Room
from ..database import SessionLocal
from ..middleware import is_hotel
from datetime import datetime, timedelta    
from sqlalchemy import func, cast, Numeric, Float
from .. import schemas, models
from typing import List, Optional
from ..schemas import (
    HotelRoomOverviewResponse,
    OccupancyRateResponse,
    RevenueResponse,
    ActiveBookingsResponse,
    RoomAvailabilityChartResponse,
    RoomTypeDistributionResponse,
    RecentBookingsResponse,
    RoomOverviewResponse
)

# Create router with prefix and tags
router = APIRouter(
    # dependencies=[Depends(is_hotel)]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Now your routes will automatically have /hotel prefix
@router.get("/hotelRoom", response_model=HotelRoomOverviewResponse)
def get_hotelRoom(db: Session = Depends(get_db)):
    """Get hotel Room"""
    today = datetime.utcnow()
    upcoming_30_days = today + timedelta(days=30)
    last_30_days = today - timedelta(days=30)

    # Get total rooms from the database
    total_rooms = db.query(func.sum(Room.totalNumber)).scalar() or 0

    # Get booked rooms in the last 30 days
    booked_rooms_last_30_days = db.query(RoomBooking).filter(
        RoomBooking.startDate <= today,
        RoomBooking.endDate >= last_30_days
    ).count()

    # Get booked rooms in the upcoming 30 days
    booked_rooms_upcoming_30_days = db.query(RoomBooking).filter(
        RoomBooking.startDate <= upcoming_30_days,
        RoomBooking.endDate >= today
    ).count()

    # Calculate available rooms
    available_rooms_last_30_days = total_rooms - booked_rooms_last_30_days
    available_rooms_upcoming_30_days = total_rooms - booked_rooms_upcoming_30_days

    # Difference in available rooms
    available_rooms_difference = available_rooms_upcoming_30_days - available_rooms_last_30_days

    overview_data = {
        "total_rooms": total_rooms,
        "available_rooms_last_30_days": available_rooms_last_30_days,
        "available_rooms_upcoming_30_days": available_rooms_upcoming_30_days,
        "available_rooms_difference": available_rooms_difference,
    }
    return overview_data

# Api for getting the Occupancy Rate...
@router.get("/occupancy-rate", response_model=OccupancyRateResponse)
def get_occupancy_rate(db: Session = Depends(get_db)):
    """Get occupancy rate for the upcoming 30 days and the last 30 days."""
    today = datetime.utcnow()
    upcoming_30_days = today + timedelta(days=30)
    last_30_days = today - timedelta(days=30)

    # Total room nights available in 30 days
    total_room_nights = db.query(func.sum(Room.totalNumber * 30)).scalar() or 1  # Avoid division by zero

    # Total booked room nights in the upcoming 30 days
    booked_nights_upcoming = db.query(func.sum(RoomBooking.numberOfPersons)).join(Room).filter(
        RoomBooking.startDate <= upcoming_30_days,
        RoomBooking.endDate >= today
    ).scalar() or 0

    # Total booked room nights in the last 30 days
    booked_nights_last = db.query(func.sum(RoomBooking.numberOfPersons)).join(Room).filter(
        RoomBooking.startDate <= today,
        RoomBooking.endDate >= last_30_days
    ).scalar() or 0

    # Calculate occupancy rates
    occupancy_rate_upcoming = (booked_nights_upcoming / total_room_nights) * 100
    occupancy_rate_last = (booked_nights_last / total_room_nights) * 100

    # Calculate the difference
    occupancy_rate_difference = occupancy_rate_upcoming - occupancy_rate_last

    return {
        "occupancy_rate_upcoming_30_days": round(occupancy_rate_upcoming, 2),
        "occupancy_rate_last_30_days": round(occupancy_rate_last, 2),
        "occupancy_rate_difference": round(occupancy_rate_difference, 2)
    }

@router.get("/revenue", response_model=RevenueResponse)
def get_revenue(user_id: int = 1, db: Session = Depends(get_db)):
    """Calculate total revenue for the last 30 days and upcoming 30 days"""

    today = datetime.utcnow()
    upcoming_30_days = today + timedelta(days=30)
    last_30_days = today - timedelta(days=30)
    
    # First get the hotel for this user
    hotel = db.query(models.Hotel).filter(models.Hotel.userId == user_id).first()
    
    if not hotel:
        return {
            "revenue_last_30_days": 0,
            "revenue_upcoming_30_days": 0,
            "revenue_difference": 0
        }
    
    # Revenue for the last 30 days (completed bookings)
    last_30_days_bookings = db.query(
        models.RoomBooking, models.Room
    ).join(
        models.Room, models.RoomBooking.roomId == models.Room.id
    ).filter(
        models.Room.hotelId == hotel.id,
        models.RoomBooking.startDate >= last_30_days,
        models.RoomBooking.startDate <= today
    ).all()
    
    revenue_last_30_days = 0
    for booking, room in last_30_days_bookings:
        # Calculate number of days in the booking
        start_date = max(booking.startDate, last_30_days)
        end_date = min(booking.endDate, today)
        days = (end_date - start_date).days + 1  # +1 because end day is inclusive
        revenue_last_30_days += room.basePrice * days
    
    # Revenue for the upcoming 30 days (future bookings)
    upcoming_30_days_bookings = db.query(
        models.RoomBooking, models.Room
    ).join(
        models.Room, models.RoomBooking.roomId == models.Room.id
    ).filter(
        models.Room.hotelId == hotel.id,
        models.RoomBooking.startDate >= today,
        models.RoomBooking.startDate <= upcoming_30_days
    ).all()
    
    revenue_upcoming_30_days = 0
    for booking, room in upcoming_30_days_bookings:
        # Calculate number of days in the booking
        start_date = max(booking.startDate, today)
        end_date = min(booking.endDate, upcoming_30_days)
        days = (end_date - start_date).days + 1  # +1 because end day is inclusive
        revenue_upcoming_30_days += room.basePrice * days
    
    # Calculate the difference
    revenue_difference = revenue_upcoming_30_days - revenue_last_30_days
    
    return {
        "revenue_last_30_days": revenue_last_30_days,
        "revenue_upcoming_30_days": revenue_upcoming_30_days,
        "revenue_difference": revenue_difference
    }
    
# Api for getting the Active Bookings
@router.get("/active-bookings", response_model=ActiveBookingsResponse)
def get_active_bookings(db: Session = Depends(get_db)):
    """Get active bookings for the last 30 days and upcoming 30 days"""
    today = datetime.utcnow()
    upcoming_30_days = today + timedelta(days=30)
    last_30_days = today - timedelta(days=30)
    
    # Get bookings from the last 30 days
    bookings_last_30_days = db.query(RoomBooking).filter(
        RoomBooking.startDate >= last_30_days,
        RoomBooking.startDate <= today,
    ).all()
    
    # Get bookings for the upcoming 30 days
    bookings_upcoming_30_days = db.query(RoomBooking).filter(
        RoomBooking.startDate >= today,
        RoomBooking.startDate <= upcoming_30_days,
    ).all()
    
    # Calculate the difference in booking count
    booking_count_last_30_days = len(bookings_last_30_days)
    booking_count_upcoming_30_days = len(bookings_upcoming_30_days)
    booking_count_difference = booking_count_upcoming_30_days - booking_count_last_30_days
    
    return {
        "bookings_last_30_days": bookings_last_30_days,
        "bookings_upcoming_30_days": bookings_upcoming_30_days,
        "booking_count_difference": booking_count_difference
    }
    
@router.get("/room-availability-chart", response_model=RoomAvailabilityChartResponse)
def get_room_availability_chart(days: int = 10, db: Session = Depends(get_db)):
    """
    Get daily room availability data for charting
    Returns data for the specified number of days (default: 10)
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get total rooms available
    total_rooms = db.query(func.sum(Room.totalNumber)).scalar() or 0
    
    # Prepare response data
    chart_data = []
    
    # Generate data for each day
    for day_offset in range(days):
        current_date = today + timedelta(days=day_offset)
        next_date = current_date + timedelta(days=1)
        
        # Count bookings for this day
        booked_rooms = db.query(func.sum(Room.totalNumber)).join(
            RoomBooking, Room.id == RoomBooking.roomId
        ).filter(
            RoomBooking.startDate <= current_date,
            RoomBooking.endDate >= next_date,
        ).scalar() or 0
        
        # Calculate available rooms
        available_rooms = total_rooms - booked_rooms
        
        # Format date as "MMM D" (e.g., "Jan 1")
        formatted_date = current_date.strftime("%b %d")
        
        # Add data point
        chart_data.append({
            "date": formatted_date,
            "available": available_rooms,
            "booked": booked_rooms
        })
    
    return chart_data

@router.get("/room-type-distribution", response_model=RoomTypeDistributionResponse)
def get_room_type_distribution(db: Session = Depends(get_db)):
    """
    Get distribution of room types
    Returns the count of each room type
    """
    # Get the count of each room type
    room_distribution = db.query(
        Room.type,
        func.count(Room.id).label("count")
    ).group_by(Room.type).all()
    
    # Convert to a list of dictionaries
    distribution_data = [{"room_type": room[0], "count": room[1]} for room in room_distribution]
    
    return distribution_data

@router.get("/recent-bookings", response_model=RecentBookingsResponse)
def get_recent_bookings(db: Session = Depends(get_db)):
    """
    Get recent bookings
    Returns the last 5 bookings
    """
    # Get the last 5 bookings
    recent_bookings = db.query(RoomBooking).order_by(RoomBooking.createdAt.desc()).limit(5).all()
    
    return recent_bookings

# API for adding the new Room-Type
def check_room_type_exists(db: Session, hotel_id: int, room_type: str):
    """Check if a room of this type already exists for the hotel"""
    return db.query(models.Room).filter(
        models.Room.hotelId == hotel_id,
        models.Room.type == room_type
    ).first()
    
def create_room(db: Session, room_data: schemas.RoomCreate):
    """Create a new room"""
    new_room = models.Room(
        type=room_data.type,
        roomCapacity=room_data.roomCapacity,
        totalNumber=room_data.totalNumber,
        hotelId=room_data.hotelId,
        basePrice=room_data.basePrice
    )
    
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


@router.post("/add-room", response_model=schemas.RoomResponse, status_code=200)
def create_hotel_room(room_data: schemas.RoomCreate, db: Session = Depends(get_db)):
    """Create a new room type for a hotel"""
    # Check if room type already exists for this hotel
    existing_room = check_room_type_exists(db, room_data.hotelId, room_data.type)
    if existing_room:
        raise HTTPException(
            status_code=403, 
            detail=f"Room of type {room_data.type} already exists for this hotel"
        )
    
    # Create new room
    return create_room(db, room_data)

@router.delete("/delete-room/{room_id}", response_model=schemas.MessageResponse)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    """Delete a room type"""
    # Find the room
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if room has bookings
    has_bookings = db.query(models.RoomBooking).filter(models.RoomBooking.roomId == room_id).first()
    if has_bookings:
        raise HTTPException(status_code=409, detail="Cannot delete room with active bookings")
    
    # Delete the room
    db.delete(room)
    db.commit()
    
    return {"detail": "Room deleted successfully"}


@router.get("/room-overview", response_model=List[schemas.RoomListResponse])
def get_room_overview(user_id: int = 1, db: Session = Depends(get_db)):
    """
    Get all rooms for a hotel associated with a user ID
    Returns rooms with arrays for booking, availability, and pricing data
    """
    # Step 1: Get the hotel ID associated with this user
    hotel = db.query(models.Hotel).filter(models.Hotel.userId == user_id).first()
    
    if not hotel:
        # If no hotel found for this user, return empty list
        return []
    
    # Step 2: Get all rooms for the hotel
    rooms = db.query(models.Room).filter(models.Room.hotelId == hotel.id).all()
    
    if not rooms:
        return []

    # count the number of rooms booked for each room type for each day till next 60 days
    today = datetime.utcnow().date()
    formatted_rooms = []
    
    # Process each room
    for room in rooms:
        # Initialize arrays for 60 days
        booked_count = [0] * 60
        
        # Get all bookings for this room
        bookings = db.query(models.RoomBooking).filter(models.RoomBooking.roomId == room.id).all()
        
        # Count bookings for each day in the next 60 days
        for booking in bookings:
            for day_offset in range(60):
                current_date = today + timedelta(days=day_offset)
                # Check if this date falls within the booking period
                if booking.startDate.date() <= current_date <= booking.endDate.date():
                    booked_count[day_offset] += 1
        
        # Calculate available rooms for each day
        available_count = [room.totalNumber - booked_count[i] for i in range(60)]
    
    
    # Step 3: Format response to match frontend expected structure
    formatted_rooms = []
    for room in rooms:
        formatted_room = {
            "id": room.id,
            "total_no": room.totalNumber,
            "type": room.type.capitalize(),  # Capitalize for display
            "room_capacity": room.roomCapacity,
            "no_available": available_count,
            "price": room.basePrice,
            "hotelfk": room.hotelId
        }
        formatted_rooms.append(formatted_room)
    
    return formatted_rooms


@router.patch("/rooms/{room_id}", response_model=schemas.RoomResponse)
def update_room_count(
    room_id: int, 
    room_update: schemas.RoomCountUpdate, 
    db: Session = Depends(get_db)
):
    """Update room total count"""
    # Find the room
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Update the room count
    old_count = room.totalNumber
    room.totalNumber = room_update.totalNumber
    
    # Calculate difference for availability updates
    difference = room_update.totalNumber - old_count
    
    # Update available numbers for future dates
    for i in range(len(room.availableNumber)):
        # Don't reduce availability below booked rooms
        room.availableNumber[i] = max(room.bookedNumber[i], room.availableNumber[i] + difference)
    
    db.commit()
    db.refresh(room)
    return room



@router.get("/hotel-bookings", response_model=List[schemas.BookingResponse])
def get_hotel_bookings(user_id: int = 1, db: Session = Depends(get_db)):
    """
    Get all bookings for a hotel associated with a user ID
    Returns bookings with customer and room information
    """
    # Step 1: Get the hotel ID associated with this user
    hotel = db.query(models.Hotel).filter(models.Hotel.userId == user_id).first()
    
    if not hotel:
        # If no hotel found for this user, return empty list
        return []
    
    # Step 2: Get all bookings for rooms in this hotel
    bookings = db.query(
        models.RoomBooking,
        models.Room.type.label("room_type"),
        models.User.name.label("customer_name")
    ).join(
        models.Room, models.RoomBooking.roomId == models.Room.id
    ).join(
        models.Customer, models.RoomBooking.customerId == models.Customer.id
    ).join(
        models.User, models.Customer.userId == models.User.id
    ).filter(
        models.Room.hotelId == hotel.id
    ).all()
    
    if not bookings:
        return []
    
    # Step 3: Format response
    today = datetime.utcnow().date()
    formatted_bookings = []
    
    for booking, room_type, customer_name in bookings:
        # Determine booking status based on dates
        if booking.startDate.date() > today:
            status = "pending"
        elif booking.endDate.date() < today:
            status = "completed"
        else:
            status = "confirmed"
        
        # Format the booking
        formatted_booking = {
            "id": booking.id,
            "no_persons": booking.numberOfPersons,
            "custfk": booking.customerId,
            "roomfk": booking.roomId,
            "start_date": booking.startDate.strftime("%Y-%m-%d"),
            "end_date": booking.endDate.strftime("%Y-%m-%d"),
            "customer_name": customer_name,
            "room_type": room_type.capitalize(),
            "status": status
        }
        
        formatted_bookings.append(formatted_booking)
    
    return formatted_bookings


@router.get("/hotel-reviews", response_model=List[schemas.ReviewResponse])
def get_hotel_reviews(user_id: int = 1, db: Session = Depends(get_db)):
    """
    Get all reviews for a hotel associated with a user ID
    Returns reviews with customer information
    """
    # Step 1: Get the hotel ID associated with this user
    hotel = db.query(models.Hotel).filter(models.Hotel.userId == user_id).first()
    
    if not hotel:
        # If no hotel found for this user, return empty list
        return []
    
    # Step 2: Get all reviews for this hotel
    reviews = db.query(
        models.HotelReview,
        models.User.name.label("customer_name")
    ).join(
        models.Customer, models.HotelReview.customerId == models.Customer.id
    ).join(
        models.User, models.Customer.userId == models.User.id
    ).filter(
        models.HotelReview.hotelId == hotel.id
    ).all()
    
    if not reviews:
        return []
    
    # Step 3: Format response
    formatted_reviews = []
    
    for review, customer_name in reviews:
        # Get customer initials
        initials = "".join([name[0].upper() for name in customer_name.split() if name])
        
        # Try to find the room type from customer's last booking
        room_type = "Various"  # Default if we can't find it
        last_booking = db.query(models.RoomBooking).join(
            models.Room
        ).filter(
            models.RoomBooking.customerId == review.customerId,
            models.Room.hotelId == hotel.id
        ).order_by(
            models.RoomBooking.createdAt.desc()
        ).first()
        
        if last_booking:
            room = db.query(models.Room).filter(models.Room.id == last_booking.roomId).first()
            if room:
                room_type = room.type.capitalize()
        
        # Format the review
        formatted_review = {
            "id": review.id,
            "customer_name": customer_name,
            "customer_initials": initials,
            "room_type": room_type,
            "rating": review.rating,
            "comment": review.description,
            "date": review.createdAt.strftime("%Y-%m-%d"),
            "status": "published",  # Default status since not in database
            "response": ""  # Default empty response since not in database
        }
        
        formatted_reviews.append(formatted_review)
    
    return formatted_reviews

@router.get("/profile/{user_id}", response_model=schemas.HotelProfileResponse)
def get_hotel_profile(user_id: int, db: Session = Depends(get_db)):
    """
    Get hotel profile information including rooms, ratings and stats
    """
    # First find the hotel with this user ID
    hotel = db.query(models.Hotel).filter(models.Hotel.userId == user_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found for this user"
        )
    
    # Get the user information
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get rooms for this hotel
    rooms = db.query(models.Room).filter(models.Room.hotelId == hotel.id).all()
    
    # Get reviews
    reviews = db.query(
        models.HotelReview,
        models.User.name.label("customerName")
    ).join(
        models.Customer, models.HotelReview.customerId == models.Customer.id
    ).join(
        models.User, models.Customer.userId == models.User.id
    ).filter(
        models.HotelReview.hotelId == hotel.id
    ).all()
    
    formatted_reviews = []
    for review, customer_name in reviews:
        formatted_reviews.append({
            "id": review.id,
            "rating": review.rating,
            "comment": review.description,
            "customerName": customer_name,
            "date": review.createdAt.isoformat()
        })
    
    # Calculate stats
    total_bookings = db.query(func.count(models.RoomBooking.id))\
        .join(models.Room, models.RoomBooking.roomId == models.Room.id)\
        .filter(models.Room.hotelId == hotel.id).scalar() or 0
    
    # Calculate occupancy rate - this is a simplified version
    total_rooms = len(rooms)
    occupancy_rate = 0
    if total_rooms > 0:
        booked_rooms = db.query(func.count(models.RoomBooking.id))\
            .join(models.Room, models.RoomBooking.roomId == models.Room.id)\
            .filter(
                models.Room.hotelId == hotel.id,
                models.RoomBooking.startDate <= datetime.now(),
                models.RoomBooking.endDate >= datetime.now()
            ).scalar() or 0
        occupancy_rate = round((booked_rooms / total_rooms) * 100)
    
    # Prepare room data
    formatted_rooms = []
    for room in rooms:
        formatted_rooms.append({
            "id": room.id,
            "type": room.type,
            "basePrice": float(room.basePrice),
            "roomCapacity": room.roomCapacity,
            "image": None  # You can add image URL later if available
        })
    
    # Construct the response
    response = {
        "id": hotel.id,
        "userId": user_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "address": user.address,
        "city": hotel.city,
        "description": hotel.description,
        "rating": hotel.rating,
        "totalRooms": total_rooms,
        "rooms": formatted_rooms,
        "reviews": formatted_reviews,
        "stats": {
            "totalBookings": total_bookings,
            "occupancyRate": occupancy_rate
        },
        "amenities": hotel.amenities.split(',') if hotel.amenities else []
    }
    
    return response

@router.put("/profile/{user_id}", response_model=schemas.HotelProfileResponse)
def update_hotel_profile(user_id: int, profile_data: schemas.HotelProfileUpdate, db: Session = Depends(get_db)):
    """
    Update hotel profile information
    """
    # First find the hotel with this user ID
    hotel = db.query(models.Hotel).filter(models.Hotel.userId == user_id).first()
    if not hotel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel not found for this user"
        )
    
    # Get the user information
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    if profile_data.name:
        user.name = profile_data.name
    if profile_data.email:
        user.email = profile_data.email
    if profile_data.phone:
        user.phone = profile_data.phone
    if profile_data.address:
        user.address = profile_data.address
    
    # Update hotel fields
    if profile_data.city:
        hotel.city = profile_data.city
    if profile_data.description:
        hotel.description = profile_data.description
    
    # Update amenities - convert from list to comma-separated string
    if profile_data.amenities is not None:
        hotel.amenities = ','.join(profile_data.amenities)
    
    db.commit()
    
    # Return the updated profile using the get_hotel_profile endpoint logic
    # Reload from database
    db.refresh(hotel)
    db.refresh(user)
    
    # Call the get function to return the updated profile with all associated data
    return get_hotel_profile(user_id, db)

