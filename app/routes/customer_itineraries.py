from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from ..middleware import is_customer
from .. import models, schemas
from ..database import SessionLocal
from sqlalchemy.orm import joinedload

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
        
    # Process the itineraries to set the start and end dates based on room items
    for itinerary in itineraries:
        if itinerary.roomItems:
            # Extract start date from earliest room booking
            start_dates = [item.startDate for item in itinerary.roomItems]
            if start_dates:
                itinerary.startDate = min(start_dates)
                
            # Extract end date from latest room booking
            end_dates = [item.endDate for item in itinerary.roomItems]
            if end_dates:
                itinerary.endDate = max(end_dates)
                
            # Calculate destinations from room items
            destinations = set()
            for item in itinerary.roomItems:
                if item.room and item.room.hotel:
                    destinations.add(item.room.hotel.city)
            itinerary.destinations = list(destinations)
    
    return itineraries

@router.get("/{id}", response_model=schemas.ItineraryResponse)
def get_itinerary(
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
    
    # Get the itinerary with room items and schedule items
    itinerary = db.query(models.Itinerary)\
        .filter(
            models.Itinerary.id == id,
            models.Itinerary.customerId == customer.id
        )\
        .options(
            joinedload(models.Itinerary.roomItems),
            joinedload(models.Itinerary.scheduleItems)
        )\
        .first()
        
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {id} not found"
        )
    
    # Calculate start and end dates
    if itinerary.roomItems:
        start_dates = [item.startDate for item in itinerary.roomItems]
        if start_dates:
            itinerary.startDate = min(start_dates)
            
        end_dates = [item.endDate for item in itinerary.roomItems]
        if end_dates:
            itinerary.endDate = max(end_dates)
    
    # Calculate destinations
    destinations = set()
    for item in itinerary.roomItems:
        if item.room and item.room.hotel:
            destinations.add(item.room.hotel.city)
    itinerary.destinations = list(destinations)
    
    return itinerary

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

# @router.get("/{itinerary_id}/items", response_model=schemas.ItineraryItemsResponse)
# def get_itinerary_items(
#     itinerary_id: int,
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
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get schedule items and room items
#     schedule_items = db.query(models.ScheduleItem).filter(
#         models.ScheduleItem.itineraryId == itinerary_id
#     ).all()
    
#     room_items = db.query(models.RoomItem).filter(
#         models.RoomItem.itineraryId == itinerary_id
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
@router.post("/{itinerary_id}/schedule", response_model=schemas.ScheduleItemResponse)
async def add_schedule_item(
    itinerary_id: int,
    schedule_item: schemas.ScheduleItemCreate,
    current_user: models.User = Depends(is_customer),
    db: Session = Depends(get_db)
):
    # Verify itinerary belongs to the current user
    customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
    itinerary = db.query(models.Itinerary).filter(
        models.Itinerary.id == itinerary_id,
        models.Itinerary.customerId == customer.id
    ).first()
    
    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itinerary_id} not found"
        )
    
    # Create the schedule item
    new_schedule_item = models.ScheduleItem(
        itineraryId=itinerary_id,
        startTime=schedule_item.startTime,
        endTime=schedule_item.endTime,
        location=schedule_item.location,
        description=schedule_item.description
    )
    
    db.add(new_schedule_item)
    db.commit()
    db.refresh(new_schedule_item)
    
    return new_schedule_item

# @router.put("/{itinerary_id}/schedule/{item_id}", response_model=schemas.ScheduleItemResponse)
# async def update_schedule_item(
#     itinerary_id: int,
#     item_id: int,
#     schedule_item: schemas.ScheduleItemUpdate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get the schedule item
#     item_query = db.query(models.ScheduleItem).filter(
#         models.ScheduleItem.id == item_id,
#         models.ScheduleItem.itinerary_id == itinerary_id
#     )
    
#     item = item_query.first()
#     if not item:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Schedule item with ID {item_id} not found"
#         )
    
#     # Update the schedule item
#     update_data = schedule_item.dict(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(item, key, value)
    
#     db.commit()
#     db.refresh(item)
    
#     return item

# @router.delete("/{itinerary_id}/schedule/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_schedule_item(
#     itinerary_id: int,
#     item_id: int,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get the schedule item
#     item_query = db.query(models.ScheduleItem).filter(
#         models.ScheduleItem.id == item_id,
#         models.ScheduleItem.itinerary_id == itinerary_id
#     )
    
#     if not item_query.first():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Schedule item with ID {item_id} not found"
#         )
    
#     # Delete the schedule item
#     item_query.delete(synchronize_session=False)
#     db.commit()
    
#     return None

# # Room Items
# @router.post("/{itinerary_id}/rooms", response_model=schemas.RoomItemResponse)
# async def add_room_to_itinerary(
#     itinerary_id: int,
#     room_item: schemas.RoomItemCreate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Verify room exists
#     room = db.query(models.Room).filter(models.Room.id == room_item.roomId).first()
#     if not room:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Room with ID {room_item.roomId} not found"
#         )
    
#     # Check room availability
#     # This would require checking against existing bookings
    
#     # Create the room item
#     new_room_item = models.RoomItem(
#         itinerary_id=itinerary_id,
#         roomId=room_item.roomId,
#         startDate=room_item.startDate,
#         endDate=room_item.endDate
#     )
    
#     db.add(new_room_item)
#     db.commit()
#     db.refresh(new_room_item)
    
#     # Fetch additional information
#     hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
#     hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
    
#     # Create response with extended information
#     response = {
#         "id": new_room_item.id,
#         "itinerary_id": new_room_item.itinerary_id,
#         "roomId": new_room_item.roomId,
#         "startDate": new_room_item.startDate,
#         "endDate": new_room_item.endDate,
#         "createdAt": new_room_item.createdAt,
#         "hotelName": hotel_user.name if hotel_user else "Unknown Hotel",
#         "roomName": f"{room.type.capitalize()} Room",
#         "roomType": room.type,
#         "city": hotel.city,
#         "pricePerNight": room.basePrice,
#         "capacity": room.roomCapacity,
#         "isPaid": False
#     }
    
#     return response

# @router.put("/{itinerary_id}/rooms/{item_id}", response_model=schemas.RoomItemResponse)
# async def update_room_dates(
#     itinerary_id: int,
#     item_id: int,
#     room_update: schemas.RoomItemUpdate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get the room item
#     room_item_query = db.query(models.RoomItem).filter(
#         models.RoomItem.id == item_id,
#         models.RoomItem.itinerary_id == itinerary_id
#     )
    
#     room_item = room_item_query.first()
#     if not room_item:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Room item with ID {item_id} not found"
#         )
    
#     # Update the dates
#     update_data = room_update.dict(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(room_item, key, value)
    
#     db.commit()
#     db.refresh(room_item)
    
#     # Get additional information for the response
#     room = db.query(models.Room).filter(models.Room.id == room_item.roomId).first()
#     hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
#     hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
    
#     # Create response with extended information
#     response = {
#         "id": room_item.id,
#         "itinerary_id": room_item.itinerary_id,
#         "roomId": room_item.roomId,
#         "startDate": room_item.startDate,
#         "endDate": room_item.endDate,
#         "createdAt": room_item.createdAt,
#         "hotelName": hotel_user.name if hotel_user else "Unknown Hotel",
#         "roomName": f"{room.type.capitalize()} Room",
#         "roomType": room.type,
#         "city": hotel.city,
#         "pricePerNight": room.basePrice,
#         "capacity": room.roomCapacity,
#         "isPaid": False
#     }
    
#     return response

# @router.delete("/{itinerary_id}/rooms/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def remove_room_from_itinerary(
#     itinerary_id: int,
#     item_id: int,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get the room item
#     room_item_query = db.query(models.RoomItem).filter(
#         models.RoomItem.id == item_id,
#         models.RoomItem.itinerary_id == itinerary_id
#     )
    
#     if not room_item_query.first():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Room item with ID {item_id} not found"
#         )
    
#     # Delete the room item
#     room_item_query.delete(synchronize_session=False)
#     db.commit()
    
#     return None

# # Transportation (Ride Bookings)
# @router.post("/{itinerary_id}/rides", response_model=schemas.RideBookingResponse)
# async def book_ride(
#     itinerary_id: int,
#     ride_booking: schemas.RideBookingCreate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
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
#         itineraryId=itinerary_id,
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

# @router.put("/{itinerary_id}/rides/{ride_id}", response_model=schemas.RideBookingResponse)
# async def update_ride_booking(
#     itinerary_id: int,
#     ride_id: int,
#     ride_update: schemas.RideBookingUpdate,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get the ride booking
#     ride_query = db.query(models.RideBooking).filter(
#         models.RideBooking.id == ride_id,
#         models.RideBooking.itineraryId == itinerary_id,
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

# @router.delete("/{itinerary_id}/rides/{ride_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def cancel_ride(
#     itinerary_id: int,
#     ride_id: int,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Get the ride
#     ride_query = db.query(models.RideBooking).filter(
#         models.RideBooking.id == ride_id,
#         models.RideBooking.itineraryId == itinerary_id,
#         models.RideBooking.customerId == customer.id
#     )
    
#     ride = ride_query.first()
#     if not ride:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Ride with ID {ride_id} not found"
#         )
    
#     # Update status to cancelled instead of deleting
#     ride.status = "cancelled"
#     db.commit()
    
#     return None

# # Available rooms endpoint
# @router.get("/available-rooms", response_model=List[schemas.AvailableRoomResponse])
# async def get_available_rooms(
#     start_date: datetime,
#     end_date: datetime,
#     city: Optional[str] = None,
#     guests: int = 1,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Base query for rooms
#     query = db.query(models.Room).join(
#         models.Hotel,
#         models.Room.hotelId == models.Hotel.id
#     )
    
#     # Apply filters
#     if city:
#         query = query.filter(models.Hotel.city == city)
    
#     # Filter by capacity
#     query = query.filter(models.Room.roomCapacity >= guests)
    
#     # Get all matching rooms
#     rooms = query.all()
    
#     # For each room, check if it's available during the specified dates
#     # This would require checking bookings and room items
    
#     # For this example, we'll return all rooms as available
#     available_rooms = []
    
#     for room in rooms:
#         hotel = db.query(models.Hotel).filter(models.Hotel.id == room.hotelId).first()
#         hotel_user = db.query(models.User).filter(models.User.id == hotel.userId).first()
        
#         # Create response
#         room_data = {
#             "id": room.id,
#             "hotelId": room.hotelId,
#             "type": room.type,
#             "roomCapacity": room.roomCapacity,
#             "basePrice": room.basePrice,
#             "totalNumber": room.totalNumber,
#             "hotelName": hotel_user.name,
#             "city": hotel.city,
#             "image": "/placeholder.svg?height=300&width=500",  # This would come from an assets table
#             "amenities": ["Free WiFi", "TV", "Air Conditioning"]  # This would come from a room_amenities table
#         }
        
#         available_rooms.append(room_data)
    
#     return available_rooms

# # Driver service endpoint
# @router.put("/{itinerary_id}/driver-service", response_model=schemas.ItineraryResponse)
# async def toggle_driver_service(
#     itinerary_id: int,
#     driver_service: bool,
#     current_user: models.User = Depends(is_customer),
#     db: Session = Depends(get_db)
# ):
#     # Verify itinerary belongs to the current user
#     customer = db.query(models.Customer).filter(models.Customer.userId == current_user.id).first()
#     itinerary = db.query(models.Itinerary).filter(
#         models.Itinerary.id == itinerary_id,
#         models.Itinerary.customerId == customer.id
#     ).first()
    
#     if not itinerary:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Itinerary with ID {itinerary_id} not found"
#         )
    
#     # Update the driver service flag
#     # Note: You would need to add this field to the Itinerary model
#     itinerary.driverServiceRequested = driver_service
#     db.commit()
#     db.refresh(itinerary)
    
#     return itinerary