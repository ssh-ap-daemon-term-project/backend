from fastapi import APIRouter, Depends , HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import User, RoomBooking, Room
from ..database import SessionLocal
from ..middleware import is_hotel
from datetime import datetime, timedelta    
from sqlalchemy import func, cast, Numeric, Float
from .. import schemas, models
from typing import List
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
def get_revenue(db: Session = Depends(get_db)):
    """Calculate total revenue for the last 30 days and upcoming 30 days"""

    today = datetime.utcnow()
    upcoming_30_days = today + timedelta(days=30)
    last_30_days = today - timedelta(days=30)

    # Revenue for the last 30 days (sum of booked room prices)
    revenue_last_30_days = db.query(
        func.sum(cast(func.coalesce(Room.price[1], 0), Float))  # First price in the price array
    ).select_from(RoomBooking).join(Room, RoomBooking.roomId == Room.id).filter(
        RoomBooking.startDate >= last_30_days,
        RoomBooking.endDate <= today
    ).scalar() or 0

    # Revenue for the upcoming 30 days (sum of booked room prices)
    revenue_upcoming_30_days = db.query(
        func.sum(cast(func.coalesce(Room.price[1], 0), Float))
    ).select_from(RoomBooking).join(Room, RoomBooking.roomId == Room.id).filter(
        RoomBooking.startDate >= today,
        RoomBooking.endDate <= upcoming_30_days
    ).scalar() or 0

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

# @router.get("/room-overview", response_model=RoomOverviewResponse , status_code= 200)
# def get_room_overview(db: Session = Depends(get_db)):
#     """
#     Get a comprehensive overview of the hotel's key metrics
#     Returns a summary of various dashboard elements
#     """
#     today = datetime.utcnow()
    
#     # Get room overview data
#     room_overview = get_hotelRoom(db)
    
#     # Get occupancy rate data
#     occupancy_rate = get_occupancy_rate(db)
    
#     # Get revenue data
#     revenue = get_revenue(db)
    
#     # Count of active bookings
#     active_bookings_count = db.query(RoomBooking).filter(
#         RoomBooking.endDate >= today
#     ).count()
    
#     # Count of recent bookings (last 7 days)
#     week_ago = today - timedelta(days=7)
#     recent_bookings_count = db.query(RoomBooking).filter(
#         RoomBooking.createdAt >= week_ago
#     ).count()
    
#     return {
#         "room_overview": room_overview,
#         "occupancy_rate": occupancy_rate,
#         "revenue": revenue,
#         "recent_bookings_count": recent_bookings_count,
#         "active_bookings_count": active_bookings_count
#     }
    
    
    
# API for adding the new Room-Type
def check_room_type_exists(db: Session, hotel_id: int, room_type: str):
    """Check if a room of this type already exists for the hotel"""
    return db.query(models.Room).filter(
        models.Room.hotelId == hotel_id,
        models.Room.type == room_type
    ).first()
    
def create_room(db: Session, room_data: schemas.RoomCreate):
    """Create a new room"""
    # Create arrays for the room data - 60 days
    price_array = [room_data.basePrice] * 60
    available_array = [room_data.totalNumber] * 60
    booked_array = [0] * 60
    
    new_room = models.Room(
        type=room_data.type,
        roomCapacity=room_data.roomCapacity,
        totalNumber=room_data.totalNumber,
        availableNumber=available_array,
        bookedNumber=booked_array,
        price=price_array,
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
    
    # Step 3: Format response to match frontend expected structure
    formatted_rooms = []
    for room in rooms:
        formatted_room = {
            "id": room.id,
            "total_no": room.totalNumber,
            "type": room.type.capitalize(),  # Capitalize for display
            "room_capacity": room.roomCapacity,
            "no_booked": room.bookedNumber,
            "no_available": room.availableNumber,
            "price": room.price,
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