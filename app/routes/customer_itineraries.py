from fastapi import APIRouter, Depends, HTTPException, status , Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from ..middleware import is_customer
from .. import models, schemas
from ..database import SessionLocal
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import and_
from ..models import Customer , Itinerary, RoomItem, ScheduleItem, RideBooking

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.ItineraryResponse)
def create_itinerary(
    itinerary: schemas.ItineraryCreate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Get the customer profile
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Create new itinerary
    new_itinerary = models.Itinerary(
        customerId=customer.id,
        name=itinerary.name,
        numberOfPersons=itinerary.numberOfPersons
    )
    
    db.add(new_itinerary)
    db.commit()
    db.refresh(new_itinerary)
    
    return new_itinerary

@router.get("/", response_model=List[schemas.ItineraryResponse])
def get_itineraries(
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Get the customer profile
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Get all itineraries for the customer with room items and schedule items
    itineraries = db.query(models.Itinerary)\
        .filter(models.Itinerary.customerId == customer.id)\
        .options(
            joinedload(models.Itinerary.roomItems),
            joinedload(models.Itinerary.scheduleItems)
        )\
        .all()
        
    # Process the itineraries to set the start and end dates based on schedule items
    for itinerary in itineraries:
        if itinerary.scheduleItems:
            # Extract start date from earliest schedule item
            start_dates = [item.startTime for item in itinerary.scheduleItems]
            # print all start dates
            if start_dates:
                itinerary.startDate = min(start_dates)
                
            # Extract end date from latest schedule item
            end_dates = [item.endTime for item in itinerary.scheduleItems]
            if end_dates:
                itinerary.endDate = max(end_dates)
                
        if itinerary.roomItems:
            # Calculate destinations from room items
            destinations = set()
            for item in itinerary.roomItems:
                if item.room and item.room.hotel:
                    destinations.add(item.room.hotel.city)
            itinerary.destinations = list(destinations)
    
    return itineraries

# Available rooms endpoint
@router.get("/available-rooms", response_model=List[schemas.CustomerAvailableRoomResponse])
async def get_available_rooms(
    start_date: datetime,
    end_date: datetime,
    city: Optional[str] = None,
    guests: int = 1,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Base query for rooms
    query = db.query(models.Room).join(
        models.Hotel,
        models.Room.hotelId == models.Hotel.id
    )
    
    # Apply filters
    if city:
        query = query.filter(models.Hotel.city == city)
    
    # Get all matching rooms
    rooms = query.all()

    available_rooms = []
    
    for room in rooms:
        hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
        hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()

        # find number of rooms available on specified days
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

        # calculate the number of available rooms list
        available_rooms_list = [room.totalNumber - booked for booked in booked_rooms]
        
        # Create response
        room_data = {
            "id": room.id,
            "hotelId": room.hotelId,
            "type": room.type,
            "roomCapacity": room.roomCapacity,
            "basePrice": room.basePrice,
            "totalNumber": room.totalNumber,
            "hotelName": hotel_user.name,
            "city": hotel.city,
            "availableRoomsList": available_rooms_list,
            "image": "/placeholder.svg?height=300&width=500",  # This would come from an assets table
            "amenities": ["Free WiFi", "TV", "Air Conditioning"]  # This would come from a room_amenities table
        }
        
        available_rooms.append(room_data)
    
    return available_rooms

@router.get("/{id}", response_model=schemas.GetItineraryResponse)
def get_itinerary(
    id: int,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer profile not found")

    itinerary = db.query(models.Itinerary)\
        .filter(models.Itinerary.id == id, models.Itinerary.customerId == customer.id)\
        .options(
            joinedload(models.Itinerary.roomItems)
                .joinedload(models.RoomItem.room)
                .joinedload(models.Room.hotel)
                .joinedload(models.Hotel.user),
            joinedload(models.Itinerary.scheduleItems),
            joinedload(models.Itinerary.rideBookings)
        )\
        .first()

    if not itinerary:
        raise HTTPException(status_code=404, detail=f"Itinerary with ID {id} not found")

    # Prepare response manually
    start_dates = []
    end_dates = []
    destinations = set()

    room_items = []
    for item in itinerary.scheduleItems:
        if item.startTime:
            start_dates.append(item.startTime)
        if item.endTime:
            end_dates.append(item.endTime)

    for item in itinerary.roomItems:
        hotel_user_name = (
            item.room.hotel.user.name if item.room.hotel and item.room.hotel.user else "Unknown Hotel"
        )

        # check if the roomBookkingId is null or not
        isPaid = item.roomBookingId is not None

        room_items.append({
            "id": item.id,
            "itineraryId": item.itineraryId,
            "roomId": item.roomId,
            "startDate": item.startDate,
            "endDate": item.endDate,
            "isPaid": isPaid,
            "room": {
                "id": item.room.id,
                "hotelId": item.room.hotelId,
                "type": item.room.type,
                "roomCapacity": item.room.roomCapacity,
                "basePrice": item.room.basePrice,
                "totalNumber": item.room.totalNumber,
                "hotel": {
                    "id": item.room.hotel.id,
                    "userId": item.room.hotel.userId,
                    "name": hotel_user_name,
                    "city": item.room.hotel.city,
                    "address": item.room.hotel.user.address if hasattr(item.room.hotel.user, "address") else None,
                    "description": item.room.hotel.description,
                    "stars": item.room.hotel.rating  # Set to None since your model has no 'stars' field
                } 
            }
        })

        destinations.add(item.room.hotel.city)
        
    # Add ride bookings - using a list for consistency even though model has uselist=False
    ride_bookings = []
    # Query directly instead of using relationship
    db_ride_bookings = db.query(models.RideBooking).filter(models.RideBooking.itineraryId == itinerary.id).all()

    for booking in db_ride_bookings:
        driver_name = "Pending..."
        
        # If there's a driver assigned, get their name
        if booking.driverId:
            driver = db.query(models.Driver).filter(models.Driver.id == booking.driverId).first()
            if driver:
                driver_user = db.query(models.User).filter(models.User.id == driver.userId).first()
                if driver_user:
                    driver_name = driver_user.name
        
        ride_bookings.append({
            "id": booking.id,
            "pickupLocation": booking.pickupLocation,
            "dropoffLocation": booking.dropoffLocation,
            "pickupDateTime": booking.pickupDateTime,
            "numberOfPersons": booking.numberOfPersons,
            "price": float(booking.price),
            "status": booking.status,
            "driverName": driver_name,
            "isReviewed": False  # You can add logic to check if reviewed
        })

    # Build final response
    response_data = {
        "id": itinerary.id,
        "customerId": itinerary.customerId,
        "name": itinerary.name,
        "numberOfPersons": itinerary.numberOfPersons,
        "createdAt": itinerary.createdAt,
        "startDate": min(start_dates) if start_dates else None,
        "endDate": max(end_dates) if end_dates else None,
        "destinations": list(destinations),
        "roomItems": room_items,
        "scheduleItems": [
            {
                "id": item.id,
                "itineraryId": item.itineraryId,
                "startTime": item.startTime,
                "endTime": item.endTime,
                "location": item.location,
                "description": item.description,
                "createdAt": item.createdAt
            }
            for item in itinerary.scheduleItems
        ],
        "rideBookings": ride_bookings  # TODO: Add ride booking
    }
    
    print("+++++++++++++++++++++++++++++++++")
    print(f"Ride-Bookings is {response_data["rideBookings"]}")

    return response_data

@router.put("/{id}", response_model=schemas.ItineraryResponse)
def update_itinerary(
    id: int,
    itinerary_data: schemas.ItineraryUpdate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Get the customer profile
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Get the existing itinerary
    db_itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == id,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not db_itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {id} not found"
        )
    
    # Update fields
    if itinerary_data.name is not None:
        db_itinerary.name = itinerary_data.name
        
    if itinerary_data.numberOfPersons is not None:
        db_itinerary.numberOfPersons = itinerary_data.numberOfPersons
    
    db.commit()
    db.refresh(db_itinerary)
    
    return db_itinerary

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(
    id: int,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Get the customer profile
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Get the itinerary
    itinerary_query = db.query(models.Itinerary).filter(
        models.Itinerary.id == id,
        models.Itinerary.customerId == customer.id
    )
    
    itinerary = itinerary_query.first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {id} not found"
        )

    # check if the corresponding ride booking has status completed or confirmed, if so, raise an error that it cannot be deleted
    ride_booking = db.query(models.RideBooking).filter(models.RideBooking.itineraryId == id).first()
    if ride_booking and ride_booking.status in ["completed", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete itinerary with confirmed or completed ride booking"
        )

    # delete the corresponding schedule items and room items
    schedule_items_query = db.query(models.ScheduleItem).filter(models.ScheduleItem.itineraryId == id)
    room_items_query = db.query(models.RoomItem).filter(models.RoomItem.itineraryId == id)
    schedule_items_query.delete(synchronize_session=False)
    room_items_query.delete(synchronize_session=False)
    
    # Delete the itinerary
    itinerary_query.delete(synchronize_session=False)
    db.commit()
    
    return None

# @router.get("/{itineraryId}/items", response_model=schemas.ItineraryItemsResponse)
# def get_itinerary_items(
#     itineraryId: int,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Get the customer profile
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     if not customer:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Customer profile not found"
#         )
    
#     # Get the itinerary
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itineraryId,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itineraryId} not found"
#         )
    
#     # Get schedule items and room items
#     schedule_items = db.query(models.ScheduleItem).filter(
#         models.ScheduleItem.itineraryId == itineraryId
#     ).all()
    
#     room_items = db.query(models.RoomItem).filter(
#         models.RoomItem.itineraryId == itineraryId
#     ).all()
    
#     # Return the combined response
#     return {
#         "schedule_items": schedule_items,
#         "room_items": room_items
#     }

# router = APIRouter(
#     prefix="/api/itineraries",
#     tags=["Itinerary Items"]
# )

# # Schedule Items
@router.post("/{itineraryId}/schedule", response_model=schemas.ScheduleItemResponse)
async def add_schedule_item(
    itineraryId: int,
    schedule_item: schemas.ScheduleItemCreate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Create the schedule item
    new_schedule_item = models.ScheduleItem(
        itineraryId=itineraryId,
        startTime=schedule_item.startTime,
        endTime=schedule_item.endTime,
        location=schedule_item.location,
        description=schedule_item.description
    )
    
    db.add(new_schedule_item)
    db.commit()
    db.refresh(new_schedule_item)
    
    return new_schedule_item

@router.put("/{itineraryId}/schedule/{item_id}", response_model=schemas.ScheduleItemResponse)
async def update_schedule_item(
    itineraryId: int,
    item_id: int,
    schedule_item: schemas.ScheduleItemUpdate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Get the schedule item
    item_query = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.id == item_id,
        models.ScheduleItem.itineraryId == itineraryId
    )
    
    item = item_query.first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule item with ID {item_id} not found"
        )
    
    # Update the schedule item
    update_data = schedule_item.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    
    return item

@router.delete("/{itineraryId}/schedule/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_item(
    itineraryId: int,
    item_id: int,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Get the schedule item
    item_query = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.id == item_id,
        models.ScheduleItem.itineraryId == itineraryId
    )
    
    if not item_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule item with ID {item_id} not found"
        )
    
    # Delete the schedule item
    item_query.delete(synchronize_session=False)
    db.commit()
    
    return None

# Room Items
@router.post("/{itineraryId}/rooms", response_model=schemas.RoomItemResponse)
async def add_room_to_itinerary(
    itineraryId: int,
    room_item: schemas.RoomItemCreate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Verify room exists
    room = db.query(models.Room).filter(models.Room.id == room_item.roomId).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_item.roomId} not found"
        )
    
    # Check room availability
    # This would require checking against existing bookings
    
    # Create the room item
    new_room_item = models.RoomItem(
        itineraryId=itineraryId,
        roomId=room_item.roomId,
        roomBookingId=None,
        startDate=room_item.startDate,
        endDate=room_item.endDate
    )
    
    db.add(new_room_item)
    db.commit()
    db.refresh(new_room_item)
    
    # Fetch additional information
    hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
    hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
    
    # Create response with extended information
    response = {
        "id": new_room_item.id,
        "itineraryId": new_room_item.itineraryId,
        "roomId": new_room_item.roomId,
        "startDate": new_room_item.startDate,
        "endDate": new_room_item.endDate,
        "createdAt": new_room_item.createdAt,
        "hotelName": hotel_user.name if hotel_user else "Unknown Hotel",
        "roomName": f"{room.type.capitalize()} Room",
        "roomType": room.type,
        "city": hotel.city,
        "pricePerNight": room.basePrice,
        "capacity": room.roomCapacity,
        "isPaid": False
    }
    
    return response

@router.put("/{itineraryId}/rooms/{item_id}", response_model=schemas.UpdateItineraryRoomItemResponse)
async def update_room_dates(
    itineraryId: int,
    item_id: int,
    room_update: schemas.RoomItemUpdate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Get the room item
    room_item_query = db.query(models.RoomItem).filter(
        models.RoomItem.id == item_id,
        models.RoomItem.itineraryId == itineraryId
    )
    
    room_item = room_item_query.first()
    if not room_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room item with ID {item_id} not found"
        )
    
    # Update the dates
    update_data = room_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(room_item, key, value)
    
    db.commit()
    db.refresh(room_item)
    
    # Get additional information for the response
    room = db.query(models.Room).filter(models.Room.id == room_item.roomId).first()
    hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
    hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
    
    # Create response with extended information
    response = {
        "id": room_item.id,
        "itineraryId": room_item.itineraryId,
        "roomId": room_item.roomId,
        "startDate": room_item.startDate,
        "endDate": room_item.endDate,
        "createdAt": room_item.createdAt,
        "hotelName": hotel_user.name if hotel_user else "Unknown Hotel",
        "roomName": f"{room.type.capitalize()} Room",
        "roomType": room.type,
        "city": hotel.city,
        "pricePerNight": room.basePrice,
        "capacity": room.roomCapacity,
        "isPaid": False
    }
    
    return response

@router.delete("/{itineraryId}/rooms/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_room_from_itinerary(
    itineraryId: int,
    item_id: int,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Get the room item
    room_item_query = db.query(models.RoomItem).filter(
        models.RoomItem.id == item_id,
        models.RoomItem.itineraryId == itineraryId
    )
    
    if not room_item_query.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room item with ID {item_id} not found"
        )
    
    # Delete the room item
    room_item_query.delete(synchronize_session=False)
    db.commit()
    
    return None


@router.post("/{itinerary_id}/rides", response_model=schemas.RideBookingResponse)
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
            dropoffLocation=ride_data.dropoffLocation,
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
            "dropoffLocation": new_ride.dropoffLocation,
            "pickupDateTime": new_ride.pickupDateTime,
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


# # Transportation (Ride Bookings)
# @router.post("/{itineraryId}/rides", response_model=schemas.RideBookingResponse)
# async def book_ride(
#     itineraryId: int,
#     ride_booking: schemas.RideBookingCreate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itineraryId,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itineraryId} not found"
#         )
    
#     # Find an available driver (in a real app, this would be more sophisticated)
#     driver = db.query(models.Driver).filter(
#         models.Driver.carType == "sedan"  # This should match the requested type
#     ).first()
    
#     if not driver and ride_booking.driverId is None:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="No available drivers found"
#         )
    
#     # Set the drop time based on pickup time (could be more sophisticated)
#     drop_time = ride_booking.pickupTime + timedelta(hours=1)
    
#     # Create the ride booking
#     new_ride = models.RideBooking(
#         customerId=customer.id,
#         driverId=ride_booking.driverId if ride_booking.driverId else driver.id,
#         itineraryId=itineraryId,
#         pickupLocation=ride_booking.pickupLocation,
#         dropLocation=ride_booking.dropLocation,
#         pickupTime=ride_booking.pickupTime,
#         dropTime=drop_time,
#         numberOfPersons=ride_booking.numberOfPersons,
#         price=ride_booking.price,
#         status="confirmed"
#     )
    
#     db.add(new_ride)
#     db.commit()
#     db.refresh(new_ride)
    
#     # Get driver details for the response
#     driver_info = db.query(models.Driver).filter(models.Driver.id == new_ride.driverId).first()
#     driver_user = None
#     if driver_info:
#         driver_user = db.query(models.User).filter(models.User.id == driver_info.userId).first()
    
#     # Create response with extended information
#     response = {
#         "id": new_ride.id,
#         "customerId": new_ride.customerId,
#         "itineraryId": new_ride.itineraryId,
#         "driverId": new_ride.driverId,
#         "pickupLocation": new_ride.pickupLocation,
#         "dropLocation": new_ride.dropLocation,
#         "pickupTime": new_ride.pickupTime,
#         "dropTime": new_ride.dropTime,
#         "numberOfPersons": new_ride.numberOfPersons,
#         "price": new_ride.price,
#         "status": new_ride.status,
#         "createdAt": new_ride.createdAt,
#         "driverName": driver_user.name if driver_user else "To be assigned",
#         "driverPhone": driver_user.phone if driver_user else "",
#         "vehicleInfo": f"{driver_info.carModel}, {driver_info.carNumber}" if driver_info else "",
#         "withDriverService": ride_booking.withDriverService,
#         "type": ride_booking.type
#     }
    
#     return response

# @router.put("/{itineraryId}/rides/{ride_id}", response_model=schemas.RideBookingResponse)
# async def update_ride_booking(
#     itineraryId: int,
#     ride_id: int,
#     ride_update: schemas.RideBookingUpdate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itineraryId,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itineraryId} not found"
#         )
    
#     # Get the ride booking
#     ride_query = db.query(models.RideBooking).filter(
#         models.RideBooking.id == ride_id,
#         models.RideBooking.itineraryId == itineraryId,
#         models.RideBooking.customerId == customer.id
#     )
    
#     ride = ride_query.first()
#     if not ride:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Ride with ID {ride_id} not found"
#         )
    
#     # Update the ride
#     update_data = ride_update.dict(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(ride, key, value)
    
#     # If pickup time is updated, also update drop time
#     if ride_update.pickupTime:
#         ride.dropTime = ride_update.pickupTime + timedelta(hours=1)
    
#     db.commit()
#     db.refresh(ride)
    
#     # Get driver details for the response
#     driver_info = db.query(models.Driver).filter(models.Driver.id == ride.driverId).first()
#     driver_user = None
#     if driver_info:
#         driver_user = db.query(models.User).filter(models.User.id == driver_info.userId).first()
    
#     # Create response with extended information
#     response = {
#         "id": ride.id,
#         "customerId": ride.customerId,
#         "itineraryId": ride.itineraryId,
#         "driverId": ride.driverId,
#         "pickupLocation": ride.pickupLocation,
#         "dropLocation": ride.dropLocation,
#         "pickupTime": ride.pickupTime,
#         "dropTime": ride.dropTime,
#         "numberOfPersons": ride.numberOfPersons,
#         "price": ride.price,
#         "status": ride.status,
#         "createdAt": ride.createdAt,
#         "driverName": driver_user.name if driver_user else "To be assigned",
#         "driverPhone": driver_user.phone if driver_user else "",
#         "vehicleInfo": f"{driver_info.carModel}, {driver_info.carNumber}" if driver_info else "",
#         "withDriverService": getattr(ride, "withDriverService", False),  # This would need to be added to the model
#         "type": getattr(ride, "type", "taxi")  # This would need to be added to the model
#     }
    
#     return response

@router.delete("/{itineraryId}/rides/{ride_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_ride(
    itineraryId: int,
    ride_id: int,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itineraryId,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itineraryId} not found"
        )
    
    # Get the ride
    ride_query = db.query(models.RideBooking).filter(
        models.RideBooking.id == ride_id,
        models.RideBooking.itineraryId == itineraryId,
        models.RideBooking.customerId == customer.id
    )
    
    ride = ride_query.first()
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride with ID {ride_id} not found"
        )
    
    # Update status to cancelled instead of deleting
    ride.status = "cancelled"
    db.commit()
    
    return None

# # Driver service endpoint
# @router.put("/{itineraryId}/driver-service", response_model=schemas.ItineraryResponse)
# async def toggle_driver_service(
#     itineraryId: int,
#     driver_service: bool,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itineraryId,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itineraryId} not found"
#         )
    
#     # Update the driver service flag
#     # Note: You would need to add this field to the Itinerary model
#     itinerary.driverServiceRequested = driver_service
#     db.commit()
#     db.refresh(itinerary)
    
#     return itinerary
