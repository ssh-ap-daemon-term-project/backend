from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import User, RoomBooking , Room
from ..database import SessionLocal
from ..middleware import is_hotel
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Numeric , Float

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
@router.get("/hotelRoom")
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
@router.get("/occupancy-rate")
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


@router.get("/revenue")
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
# Api for getting the Active Bookings
@router.get("/active-bookings")
def get_active_bookings(db: Session = Depends(get_db)):
    """Get active bookings for the last 30 days and upcoming 30 days"""
    today = datetime.utcnow()
    upcoming_30_days = today + timedelta(days=30)
    last_30_days = today - timedelta(days=30)
    
    # Get bookings from the last 30 days
    bookings_last_30_days = db.query(RoomBooking).filter(
        RoomBooking.startDate >= last_30_days,
        RoomBooking.startDate <= today,
        RoomBooking.status == "active"
    ).all()
    
    # Get bookings for the upcoming 30 days
    bookings_upcoming_30_days = db.query(RoomBooking).filter(
        RoomBooking.startDate >= today,
        RoomBooking.startDate <= upcoming_30_days,
        RoomBooking.status == "active"
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
    

@router.get("/room-availability-chart")
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

@router.get("/room-type-distribution")
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

@router.get("/recent-bookings")
def get_recent_bookings(db: Session = Depends(get_db)):
    """
    Get recent bookings
    Returns the last 5 bookings
    """
    # Get the last 5 bookings
    recent_bookings = db.query(RoomBooking).order_by(RoomBooking.createdAt.desc()).limit(5).all()
    
    return recent_bookings