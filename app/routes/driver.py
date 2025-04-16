from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..middleware import is_driver
from typing import List, Optional
from datetime import datetime
from sqlalchemy import func
from .. import models, schemas
from fastapi.responses import JSONResponse
from ..middleware import is_auth

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

@router.get("/accepted-trips/{user_id}", response_model=List[schemas.RideBookingResponse])
def get_accepted_trips(user_id: int, db: Session = Depends(get_db)):
    """
    Get accepted trips for a driver identified by user_id.
    """
    # Find the driver associated with this user_id
    driver = db.query(models.Driver).filter(models.Driver.userId == user_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found for this user"
        )

    try:
        # Get all completed ride bookings for this driver
        accepted_rides = db.query(models.RideBooking).filter(
            models.RideBooking.driverId == driver.id,
            models.RideBooking.status == "confirmed"
        ).order_by(models.RideBooking.pickupDateTime.desc()).all()

        response_list = []
        for ride in accepted_rides:
            passenger_name = (
                ride.customer.user.name
                if ride.customer and ride.customer.user
                else "Unknown"
            )

            response = schemas.RideBookingResponse(
                id=ride.id,
                pickupLocation=ride.pickupLocation,
                dropoffLocation=ride.dropoffLocation,
                pickupDateTime=ride.pickupDateTime,
                numberOfPersons=ride.numberOfPersons,
                price=ride.price,
                status=ride.status,
                driverName=driver.user.name if driver.user else "Unknown"
            )
            response_list.append(response)

        return response_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve completed trips: {str(e)}"
        )       

@router.get("/pending-requests")
def get_pending_requests(db: Session = Depends(get_db)):
    """
    Get pending ride requests (unassigned) for the frontend to display to drivers
    """
    try:
        # Fetch pending ride requests (status = pending, driverId = None)
        pending_rides = db.query(models.RideBooking).join(
            models.Customer
        ).join(
            models.User, models.Customer.userId == models.User.id
        ).filter(
            models.RideBooking.status == "pending",
            models.RideBooking.driverId == None
        ).order_by(models.RideBooking.pickupDateTime.asc()).all()

        result = []
        for ride in pending_rides:
            passenger_name = ride.customer.user.name if ride.customer and ride.customer.user else "Unknown"
            trip_id = f"r-{ride.id:06d}"

            # Placeholder data — replace if you have actual logic
            distance = round(3 + ride.id % 4 + 0.5, 1)
            duration = int(distance * 4.5)
            estimated_fare = float(ride.price)
            passenger_rating = round(4.5 + ((ride.id % 5) * 0.1), 1)

            result.append({
                "id": trip_id,
                "passengerName": passenger_name,
                "passengerAvatar": "/placeholder.svg?height=40&width=40",
                "pickupLocation": ride.pickupLocation,
                "dropoffLocation": ride.dropoffLocation,
                "pickupTime": ride.pickupDateTime.isoformat(),
                "distance": distance,
                "duration": duration,
                "estimatedFare": estimated_fare,
                "passengerRating": passenger_rating
            })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pending requests: {str(e)}"
        )


@router.post("/accept-ride")
def accept_ride(ride_id: int, driver_id: int, db: Session = Depends(get_db)):
    """
    Assign a pending ride to a driver (accept the ride)
    """
    # First, find the driver record associated with the user ID
    driver = db.query(models.Driver).filter(models.Driver.userId == driver_id).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No driver found for user ID {driver_id}"
        )
    
    # Now find the ride
    ride = db.query(models.RideBooking).filter(
        models.RideBooking.id == ride_id,
        models.RideBooking.status == "pending",
        models.RideBooking.driverId == None  # unassigned
    ).first()

    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found or already accepted"
        )

    # Assign the actual driver ID, not the user ID
    ride.driverId = driver.id
    ride.status = "confirmed"
    db.commit()

    return {"message": "Ride accepted successfully"}

@router.post("/decline-ride/{ride_id}")
def decline_ride(ride_id: int, driver_id: int = None, db: Session = Depends(get_db)):
    """
    Decline a ride request
    """
    # Logic to update ride status to declined
    # ...
    return {"message": f"Ride {ride_id} declined successfully"}


@router.get("/profile")
def get_driver_profile(current_user: models.User = Depends(is_auth), db: Session = Depends(get_db)):
    """Get the profile for the currently logged-in driver"""
    # Get the driver profile for the current user
    driver = db.query(models.Driver).filter(models.Driver.userId == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Create a response that only includes fields that exist in the model
    # Start with basic user data we know exists
    response = {
        "id": driver.id,
        "userId": driver.userId,
        "name": current_user.name,
        "email": current_user.email,
        "phoneNumber": current_user.phone,
        "address": current_user.address,
        "carNumber": driver.carNumber,
        "carModel": driver.carModel,
        "carType": driver.carType,
        "seatingCapacity": driver.seatingCapacity,
        "createdAt": driver.createdAt,
        "isVerified": getattr(driver, "isVerified", False),
        "rating": 4.8,  # Placeholder
        "totalTrips": 120,  # Placeholder
    }
    
    # Safely add other fields if they exist in the model
    for field in ["licenseNumber", "vehicleType", "vehicleModel", "vehicleYear", 
                 "vehiclePlate"]:
        if hasattr(driver, field):
            response[field] = getattr(driver, field)
        else:
            # Add empty defaults for missing fields
            response[field] = "" if field not in ["vehicleYear"] else 0
    
    return response


# Add this to main.py:
# from .routes import driver
# app.include_router(driver.router, prefix="/api/driver", tags=["Driver"])
