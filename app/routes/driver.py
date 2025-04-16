from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..middleware import is_driver
from typing import List, Optional
from datetime import datetime
from sqlalchemy import func
from .. import models, schemas
from fastapi.responses import JSONResponse

# Create router with prefix and tags
router = APIRouter(
    # dependencies=[Depends(is_driver)]  # Uncomment to enforce driver authentication
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Define a Pydantic schema to match the frontend expected format
class CompletedTripResponse(schemas.BaseModel):
    id: str
    passengerName: str
    passengerAvatar: str
    pickupLocation: str
    dropoffLocation: str
    date: str
    distance: float
    duration: int
    fare: float
    status: str
    paymentMethod: str
    tip: float

    class Config:
        from_attributes = True

@router.get("/completed-trips/{user_id}", response_model=List[CompletedTripResponse])
def get_completed_trips(user_id: int, db: Session = Depends(get_db)):
    """
    Get completed trips for a driver identified by user_id
    """
    # Find the driver associated with this user_id
    driver = db.query(models.Driver).filter(models.Driver.userId == user_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found for this user"
        )
    
    driver_id = driver.id
    
    # Get completed ride bookings for this driver
    try:
        # Query the database for completed rides
        completed_rides = db.query(
            models.RideBooking,
            models.User.name.label("passenger_name"),
        ).join(
            models.Customer, models.RideBooking.customerId == models.Customer.id
        ).join(
            models.User, models.Customer.userId == models.User.id
        ).filter(
            models.RideBooking.driverId == driver_id,
            models.RideBooking.status == "completed"
        ).order_by(
            models.RideBooking.dropTime.desc()
        ).all()
        
        # Format response to match frontend expectations
        formatted_trips = []
        for ride, passenger_name in completed_rides:
            # Calculate duration in minutes
            if ride.pickupTime and ride.dropTime:
                duration_seconds = (ride.dropTime - ride.pickupTime).total_seconds()
                duration_minutes = int(duration_seconds / 60)
            else:
                duration_minutes = 0
                
            # Generate trip ID with "t-" prefix and padding
            trip_id = f"t-{ride.id:06d}"
            
            # Determine payment method - simplify to avoid hasattr checks
            payment_method = "Credit Card"  # Default
            
            # Calculate tip (simplified)
            tip = 0.0
                
            # Format in the expected structure
            formatted_trip = {
                "id": trip_id,
                "passengerName": passenger_name,
                "passengerAvatar": "/placeholder.svg?height=40&width=40",
                "pickupLocation": ride.pickupLocation,
                "dropoffLocation": ride.dropLocation,
                "date": ride.pickupTime.isoformat(),
                "distance": 0.0,  # Default if not available in your model
                "duration": duration_minutes,
                "fare": float(ride.price),
                "status": "completed",
                "paymentMethod": payment_method,
                "tip": tip
            }
            formatted_trips.append(formatted_trip)
            
        return formatted_trips
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve completed trips: {str(e)}"
        )
        

@router.get("/pending-requests")
def get_pending_requests(driver_id: int = None, db: Session = Depends(get_db)):
    """
    Get pending ride requests for a specific driver
    """
    # Implementation similar to completed-trips but for pending rides
    # This would filter for ride status = "pending" or similar
    # ...
    
    # For now, return mock data
    mock_pending_requests = [
        {
            "id": "r-123456",
            "passengerName": "Michael Johnson",
            "passengerAvatar": "/placeholder.svg?height=40&width=40",
            "pickupLocation": "123 Main St, Downtown",
            "dropoffLocation": "456 Park Ave, Uptown",
            "pickupTime": "2023-12-05T14:30:00",
            "distance": 5.2,
            "duration": 18,
            "estimatedFare": 15.75,
            "passengerRating": 4.7,
        }
    ]
    return mock_pending_requests

@router.post("/accept-ride/{ride_id}")
def accept_ride(ride_id: int, driver_id: int = None, db: Session = Depends(get_db)):
    """
    Accept a ride request
    """
    # Logic to update ride status to accepted/confirmed
    # ...
    return {"message": f"Ride {ride_id} accepted successfully"}

@router.post("/decline-ride/{ride_id}")
def decline_ride(ride_id: int, driver_id: int = None, db: Session = Depends(get_db)):
    """
    Decline a ride request
    """
    # Logic to update ride status to declined
    # ...
    return {"message": f"Ride {ride_id} declined successfully"}




# Add this to main.py:
# from .routes import driver
# app.include_router(driver.router, prefix="/api/driver", tags=["Driver"])
