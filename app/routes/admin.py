from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased
from typing import List, Optional, Dict, Any
from ..models import User, RoomBooking, Hotel, Room, Driver, RideBooking, Customer
from ..database import SessionLocal
from ..middleware import is_admin
from ..schemas import HotelCreate, HotelUpdate, HotelResponse  
from ..security import hash_password
from datetime import datetime, timedelta
from sqlalchemy import func
from .. import schemas

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

# Driver Management APIs
@router.get("/drivers")
def get_all_drivers(db: Session = Depends(get_db)):
    """Get all drivers with user data"""
    drivers_with_users = []
    
    # Get all drivers
    drivers = db.query(Driver).all()
    
    for driver in drivers:
        # Get associated user
        user = db.query(User).filter(User.id == driver.userId).first()
        
        if not user:
            continue  # Skip drivers with missing user data
        
        # Create a combined dictionary with fields from both models
        driver_data = {
            "id": driver.id,
            "userId": driver.userId,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "carModel": driver.carModel,
            "carNumber": driver.carNumber,
            "carType": driver.carType,
            "seatingCapacity": driver.seatingCapacity,
            "rating": driver.rating if hasattr(driver, "rating") else None,
            "status": driver.status if hasattr(driver, "status") else "active",
            "joinedDate": user.createdAt.strftime("%Y-%m-%d")
        }
        
        drivers_with_users.append(driver_data)
    
    return drivers_with_users

@router.get("/drivers/{driver_id}")
def get_driver_by_id(driver_id: int, db: Session = Depends(get_db)):
    """Get a specific driver by ID"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    user = db.query(User).filter(User.id == driver.userId).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User associated with driver not found"
        )
    
    # Create a response that combines both driver and user data
    driver_data = {
        "id": driver.id,
        "userId": driver.userId,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "carModel": driver.carModel,
        "carNumber": driver.carNumber,
        "carType": driver.carType,
        "seatingCapacity": driver.seatingCapacity,
        "rating": driver.rating if hasattr(driver, "rating") else None,
        "status": driver.status if hasattr(driver, "status") else "active",
        "joinedDate": user.createdAt.strftime("%Y-%m-%d")
    }
    
    return driver_data

@router.post("/drivers")
def create_driver(driver_data: schemas.DriverCreate, db: Session = Depends(get_db)):
    """Create a new driver"""
    try:
        print(f"Received driver data: {driver_data}")
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == driver_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # First create a user account
        try:
            # Hash the password with our updated function
            hashed_password = hash_password(driver_data.password)
            
            user = User(
                username=driver_data.email,  # Use email as username
                email=driver_data.email,
                hashedPassword=hashed_password,
                name=driver_data.name,
                phone=driver_data.phone,
                userType="driver",
                address=driver_data.address
            )
            db.add(user)
            db.flush()
            print(f"Created user with ID: {user.id}")
        except Exception as e:
            print(f"Error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create user: {str(e)}"
            )
        
        # Now create the driver record
        try:
            driver = Driver(
                userId=user.id,
                carModel=driver_data.carModel,
                carNumber=driver_data.carNumber,
                carType=driver_data.carType,
                seatingCapacity=driver_data.seatingCapacity,
            )
            
            db.add(driver)
            db.commit()
            db.refresh(driver)
            print(f"Created driver with ID: {driver.id}")
        except Exception as e:
            print(f"Error creating driver: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create driver record: {str(e)}"
            )
        
        # Return the combined data
        return {
            "id": driver.id,
            "userId": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "carModel": driver.carModel,
            "carNumber": driver.carNumber,
            "carType": driver.carType,
            "seatingCapacity": driver.seatingCapacity,
            "rating": 0.0,
            "joinedDate": user.createdAt.strftime("%Y-%m-%d")
        }
        
    except HTTPException as e:
        db.rollback()
        print(f"HTTP Exception: {e.detail}")
        raise e
    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create driver: {str(e)}"
        )

@router.put("/drivers/{driver_id}")
def update_driver(driver_id: int, driver_data: dict, db: Session = Depends(get_db)):
    """Update an existing driver"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    
    user = db.query(User).filter(User.id == driver.userId).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with driver not found"
        )
    
    try:
        # Update user fields if provided
        if "name" in driver_data:
            user.name = driver_data["name"]
        if "email" in driver_data:
            user.email = driver_data["email"]
        if "phone" in driver_data:
            user.phone = driver_data["phone"]
        if "password" in driver_data:
            user.hashedPassword = hash_password(driver_data["password"])
        
        # Update driver fields if provided
        if "carModel" in driver_data:
            driver.carModel = driver_data["carModel"]
        if "carNumber" in driver_data:
            driver.carNumber = driver_data["carNumber"]
        if "carType" in driver_data:
            driver.carType = driver_data["carType"]
        if "seatingCapacity" in driver_data:
            driver.seatingCapacity = driver_data["seatingCapacity"]
        if "status" in driver_data and hasattr(driver, "status"):
            driver.status = driver_data["status"]
        
        db.commit()
        
        # Return the updated data
        return {
            "id": driver.id,
            "userId": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "carModel": driver.carModel,
            "carNumber": driver.carNumber,
            "carType": driver.carType,
            "seatingCapacity": driver.seatingCapacity,
            "status": driver.status if hasattr(driver, "status") else "active",
            "rating": driver.rating if hasattr(driver, "rating") else 0.0,
            "joinedDate": user.createdAt.strftime("%Y-%m-%d")
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update driver: {str(e)}"
        )

@router.delete("/drivers/{driver_id}")
def delete_driver(driver_id: int, db: Session = Depends(get_db)):
    """Delete a driver"""
    # First get the driver record
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Check if the driver has any associated ride bookings
    # TODO: Add check for ride bookings if that table exists in your model
    
    try:
        # Delete the driver record - but keep the user record for audit purposes
        db.delete(driver)
        db.commit()
        return {"message": "Driver deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete driver: {str(e)}"
        )

@router.get("/dashboard-data")
def get_dashboard_data(db: Session = Depends(get_db)):
    """
    Get comprehensive dashboard data for admin frontend
    Returns structured data for various dashboard components
    """
    # Calculate basic counts
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_hotels = db.query(func.count(Hotel.id)).scalar() or 0
    total_drivers = db.query(func.count(Driver.id)).scalar() or 0
    total_bookings = db.query(func.count(RoomBooking.id)).scalar() or 0
    
    # Calculate admin users
    total_admins = db.query(func.count(User.id)).filter(User.userType == "admin").scalar() or 0
    total_customers = db.query(func.count(User.id)).filter(User.userType == "customer").scalar() or 0
    
    # Calculate total revenue from room bookings
    total_revenue = db.query(
        func.sum(Room.basePrice)
    ).join(
        RoomBooking, Room.id == RoomBooking.roomId
    ).scalar() or 0
    
    # Get breakdown of user types
    user_types = [
        {"name": "Customers", "value": total_customers},
        {"name": "Hotels", "value": total_hotels},
        {"name": "Drivers", "value": total_drivers},
        {"name": "Admins", "value": total_admins}
    ]
    
    # Create aliases for the User model to avoid table name conflicts
    HotelUser = aliased(User, name="hotel_user")
    CustomerUser = aliased(User, name="customer_user")
    
    # Get recent bookings with detailed info - fetch hotel name from User model using aliases
    recent_bookings_data = db.query(
        RoomBooking, 
        CustomerUser.name.label("customer_name"),
        HotelUser.name.label("hotel_name"),  # Get hotel name from hotel user
        Room.type.label("room_type"),
        Room.basePrice.label("room_price")
    ).join(
        Room, RoomBooking.roomId == Room.id
    ).join(
        Hotel, Room.hotelId == Hotel.id
    ).join(
        HotelUser, Hotel.userId == HotelUser.id  # Join using hotel user alias
    ).join(
        Customer, RoomBooking.customerId == Customer.id, isouter=True
    ).join(
        CustomerUser, Customer.userId == CustomerUser.id, isouter=True  # Join using customer user alias
    ).order_by(
        RoomBooking.createdAt.desc()
    ).limit(4).all()
    
    recent_bookings = []
    for booking, customer_name, hotel_name, room_type, room_price in recent_bookings_data:
        # Calculate amount based on booking duration and room price
        days = (booking.endDate - booking.startDate).days
        amount = days * room_price if days > 0 else room_price
        
        recent_bookings.append({
            "id": booking.id,
            "customer": customer_name,
            "hotel": hotel_name,
            "room": room_type.capitalize(),
            "startDate": booking.startDate.strftime("%Y-%m-%d"),
            "endDate": booking.endDate.strftime("%Y-%m-%d"),
            "amount": amount
        })
    
    # Get recent users
    recent_users_data = db.query(User).order_by(User.createdAt.desc()).limit(4).all()
    recent_users = []
    for user in recent_users_data:
        recent_users.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "type": user.userType,
            "joined": user.createdAt.strftime("%Y-%m-%d")
        })
    
    # Generate monthly booking data (rooms and rides)
    # This would typically come from a query grouping by month, but we'll simulate it here
    current_month = datetime.now().month
    bookings_by_month = []
    
    # Get the last 6 months of data
    for i in range(6):
        month_num = ((current_month - i - 1) % 12) + 1  # Go back i months
        month_name = datetime(2000, month_num, 1).strftime("%b")
        
        # Count room bookings for this month
        month_start = datetime(datetime.now().year, month_num, 1)
        if month_num == 12:
            month_end = datetime(datetime.now().year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = datetime(datetime.now().year, month_num + 1, 1) - timedelta(days=1)
            
        # Get room bookings count
        room_bookings = db.query(func.count(RoomBooking.id)).filter(
            func.extract('month', RoomBooking.startDate) == month_num,
            func.extract('year', RoomBooking.startDate) == datetime.now().year
        ).scalar() or 0
        
        # Get ride bookings count (if you have RideBooking table)
        ride_bookings = 0
        try:
            ride_bookings = db.query(func.count(RideBooking.id)).filter(
                func.extract('month', RideBooking.startDate) == month_num,
                func.extract('year', RideBooking.startDate) == datetime.now().year
            ).scalar() or 0
        except:
            # Fallback if no ride bookings table exists
            ride_bookings = int(room_bookings * 0.6)  # Just an estimate for demo purposes
            
        bookings_by_month.append({
            "name": month_name,
            "rooms": room_bookings,
            "rides": ride_bookings
        })
    
    # Sort months chronologically
    bookings_by_month.reverse()
    
    # Get popular hotels - fetch hotel name from User model using alias
    popular_hotels_data = db.query(
        HotelUser.name.label("hotel_name"),  # Get hotel name from User table with alias
        func.count(RoomBooking.id).label("booking_count"),
        func.avg(Hotel.rating).label("avg_rating")
    ).join(
        Hotel, HotelUser.id == Hotel.userId  # Join using hotel user alias
    ).join(
        Room, Hotel.id == Room.hotelId
    ).join(
        RoomBooking, Room.id == RoomBooking.roomId
    ).group_by(
        Hotel.id, HotelUser.name  # Group by both Hotel.id and User.name
    ).order_by(
        func.count(RoomBooking.id).desc()
    ).limit(5).all()
    
    popular_hotels = []
    for hotel_name, bookings, rating in popular_hotels_data:
        popular_hotels.append({
            "name": hotel_name,  # This now comes from the User model
            "bookings": bookings,
            "rating": round(rating, 1) if rating else 0
        })
    
    # Compile all data
    dashboard_data = {
        "totalUsers": total_users,
        "totalHotels": total_hotels,
        "totalDrivers": total_drivers,
        "totalBookings": total_bookings,
        "totalRevenue": float(total_revenue),
        "userTypes": user_types,
        "recentBookings": recent_bookings,
        "recentUsers": recent_users,
        "bookingsByMonth": bookings_by_month,
        "popularHotels": popular_hotels
    }
    
    return dashboard_data