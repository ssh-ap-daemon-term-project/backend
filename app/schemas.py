from pydantic import BaseModel, EmailStr, Field, RootModel
from typing import Optional, List, Literal, Dict, Any, Union
from datetime import date, datetime
from enum import Enum

class UserCreate(BaseModel):
    username: str = Field(..., max_length=50, description="Max 50 characters")
    email: EmailStr = Field(..., max_length=100, description="User's email address")
    password: str = Field(..., min_length=8, max_length=32, description="Password must be at least 8 characters and at most 32 characters")
    phone: str = Field(..., max_length=15, description="Max 15 characters")
    userType: Literal["customer", "hotel", "driver"] = "customer"
    name: str = Field(..., max_length=100, description="Max 100 characters")
    address: str = Field(..., max_length=200, description="Max 200 characters")
    
    # Fields specific to customer
    dob: Optional[date] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    
    # Fields specific to hotel
    city: Optional[str] = Field(None, max_length=100, description="Max 100 characters")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    description: Optional[str] = None
    
    # Fields specific to driver
    carModel: Optional[str] = Field(None, max_length=50, description="Max 50 characters")
    carNumber: Optional[str] = Field(None, max_length=20, description="Max 20 characters")
    carType: Optional[Literal["sedan", "suv", "hatchback", "luxury"]] = None
    seatingCapacity: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    phone: str
    userType: str
    name: str
    address: str

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Hotel Schemas
class HotelBase(BaseModel):
    name: str
    address: str
    city: str
    email: EmailStr
    phone: str
    description: Optional[str] = None

class HotelCreate(HotelBase):
    pass

class HotelUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    description: Optional[str] = None

class HotelResponse(BaseModel):
    id: int
    userId: int
    username: str
    name: str
    address: str
    email: EmailStr
    phone: str
    city: str
    latitude: float
    longitude: float
    rating: float
    description: Optional[str] = None
    createdAt: datetime
    
    class Config:
        from_attributes = True

# Room Booking Schemas
class RoomBookingBase(BaseModel):
    id: int
    roomId: int
    userId: int
    startDate: datetime
    endDate: datetime
    status: str
    numberOfPersons: int
    
    class Config:
        from_attributes = True

# Hotel Room Overview Schemas
class HotelRoomOverviewResponse(BaseModel):
    total_rooms: int
    available_rooms_last_30_days: int
    available_rooms_upcoming_30_days: int
    available_rooms_difference: int

# Occupancy Rate Schemas
class OccupancyRateResponse(BaseModel):
    occupancy_rate_upcoming_30_days: float
    occupancy_rate_last_30_days: float
    occupancy_rate_difference: float

# Revenue Schemas
class RevenueResponse(BaseModel):
    revenue_last_30_days: float
    revenue_upcoming_30_days: float
    revenue_difference: float

# Active Bookings Schemas
class ActiveBookingsResponse(BaseModel):
    bookings_last_30_days: List[RoomBookingBase]
    bookings_upcoming_30_days: List[RoomBookingBase]
    booking_count_difference: int

# Room Availability Chart Schemas
class RoomAvailabilityDataPoint(BaseModel):
    date: str
    available: int
    booked: int

class RoomAvailabilityChartResponse(RootModel):
    root: List[RoomAvailabilityDataPoint]

# Room Type Distribution Schemas
class RoomTypeDistribution(BaseModel):
    room_type: str
    count: int

class RoomTypeDistributionResponse(RootModel):
    root: List[RoomTypeDistribution]

# Recent Bookings Schema
class RecentBookingsResponse(RootModel):
    root: List[RoomBookingBase]

# Room Overview Schema
class RoomOverviewResponse(BaseModel):
    room_overview: HotelRoomOverviewResponse
    occupancy_rate: OccupancyRateResponse
    revenue: RevenueResponse
    recent_bookings_count: int
    active_bookings_count: int
    
    
class RoomTypeEnum(str, Enum):
    basic = "basic"
    luxury = "luxury" 
    suite = "suite"

class RoomCreate(BaseModel):
    type: RoomTypeEnum
    roomCapacity: int
    totalNumber: int
    hotelId: int
    basePrice: float  # Initial price for all days

class RoomResponse(RoomCreate):
    id: int
    roomCapacity: int
    totalNumber: int
    basePrice: float
    
    class Config:
        from_attributes = True
        
        
class MessageResponse(BaseModel):
    detail: str
    
    
class RoomListResponse(BaseModel):
    id: int
    total_no: int
    type: str
    room_capacity: int
    # no_booked: List[int]
    no_available: List[int]
    price: float
    hotelfk: int

    class Config:
        from_attributes = True
        
# Add this schema
class RoomCountUpdate(BaseModel):
    totalNumber: int

class CustomerBase(BaseModel):
    name: str
    address: str
    email: EmailStr
    phone: str
    dob: date
    gender: str

class CustomerCreate(CustomerBase):
    username: str
    password: str

class CustomerUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    userId: int
    username: str
    createdAt: datetime
    
    class Config:
        from_attributes = True
    
    
    
class BookingResponse(BaseModel):
    id: int
    no_persons: int
    custfk: int
    roomfk: int
    start_date: str
    end_date: str
    customer_name: str
    room_type: str
    status: str

    class Config:
        from_attributes = True
        
        
class ReviewResponse(BaseModel):
    id: int
    customer_name: str
    customer_initials: str
    room_type: str
    rating: float
    comment: str
    date: str
    status: str
    response: str

    class Config:
        from_attributes = True

class DriverCreate(BaseModel):
    username : str
    name: str
    email: EmailStr
    password: str
    phone: str
    carModel: str
    carNumber: str
    carType: Literal["sedan", "suv", "hatchback", "luxury"]
    seatingCapacity: int
    address: Optional[str] = ""

# Base schemas
class ItineraryBase(BaseModel):
    name: str
    numberOfPersons: int = Field(gt=0)

class ItineraryCreate(ItineraryBase):
    pass

class ItineraryUpdate(BaseModel):
    name: Optional[str] = None
    numberOfPersons: Optional[int] = None

class ScheduleItemBase(BaseModel):
    startTime: datetime
    endTime: datetime
    location: str
    description: Optional[str] = None

class ScheduleItemCreate(ScheduleItemBase):
    pass

class ScheduleItemResponse(ScheduleItemBase):
    id: int
    itineraryId: int
    createdAt: datetime

    class Config:
        from_attributes = True

class RoomItemBase(BaseModel):
    roomId: int
    startDate: datetime
    endDate: datetime

class RoomItemCreate(RoomItemBase):
    pass

class RoomItemResponse(RoomItemBase):
    id: int
    itineraryId: int
    createdAt: datetime

    class Config:
        from_attributes = True

class ItineraryResponse(ItineraryBase):
    id: int
    customerId: int
    createdAt: datetime
    roomItems: List[RoomItemResponse] = []
    scheduleItems: List[ScheduleItemResponse] = []
    # rideBookings: List[RideBookingResponse] = []
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    destinations: List[str] = []

    class Config:
        from_attributes = True

# Hotel Schema
class GetItineraryHotelResponse(BaseModel):
    id: int
    name: str
    city: str
    address: Optional[str] = None
    description: Optional[str] = None
    stars: Optional[int] = None
    
    class Config:
        from_attributes = True

# Room Schema
class GetItineraryRoomResponse(BaseModel):
    id: int
    hotelId: int
    type: str
    roomCapacity: int
    basePrice: float
    totalNumber: int
    hotel: Optional[GetItineraryHotelResponse] = None
    
    class Config:
        from_attributes = True
        
class GetItineraryRoomItemResponse(BaseModel):
    id: int
    itineraryId: int
    roomId: int
    startDate: datetime
    endDate: datetime
    isPaid: bool = False
    room: Optional[GetItineraryRoomResponse] = None
    
    class Config:
        from_attributes = True

# Complete Itinerary Schema with nested relationships
class GetItineraryResponse(BaseModel):
    id: int
    customerId: int
    name: str
    numberOfPersons: int
    createdAt: datetime
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    destinations: List[str] = Field(default_factory=list)
    
    # Relationships with nested data
    roomItems: List[GetItineraryRoomItemResponse] = Field(default_factory=list)
    scheduleItems: List[ScheduleItemResponse] = Field(default_factory=list)
    # rideBookings: List[RideBookingResponse] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class ItineraryItemsResponse(BaseModel):
    schedule_items: List[ScheduleItemResponse] = []
    room_items: List[RoomItemResponse] = []
    
    class Config:
        from_attributes = True
        
    
class DriverDetailResponse(BaseModel):
    id: int
    name: str
    username : str
    email: str
    phone: str
    address: Optional[str]
    carModel: str
    carNumber: str
    carType: str
    seatingCapacity: int
    status: str
    joinedDate: str
    totalCompletedRides: int
    
    
    

# Input schema for updating room dates
class RoomItemUpdate(BaseModel):
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Response schema for the updated room item with extended information
class UpdateItineraryRoomItemResponse(BaseModel):
    id: int
    itineraryId: int
    roomId: int
    startDate: datetime
    endDate: datetime
    createdAt: datetime
    hotelName: str
    roomName: str
    roomType: str
    city: str
    pricePerNight: float
    capacity: int
    isPaid: bool = False
    
    class Config:
        from_attributes = True
        
class RideBookingBase(BaseModel):
    pickupLocation: str
    dropoffLocation: str  # Note: frontend sends 'dropoffLocation'
    pickupDateTime: datetime  # Note: frontend sends 'pickupDateTime'
    numberOfPersons: Optional[int] = None

class RideBookingCreate(RideBookingBase):
    pass

class RideBookingResponse(BaseModel):
    id: int
    pickupLocation: str
    dropoffLocation: str
    pickupDateTime: datetime
    numberOfPersons: int
    price: float
    status: str
    driverName: str = "Pending..."
    
    class Config:
        orm_mode = True

# from pydantic import BaseModel, Field, EmailStr
# from typing import List, Optional, Dict, Any, Union
# from datetime import datetime
# from enum import Enum

# # Enum definitions
# class UserType(str, Enum):
#     customer = "customer" 
#     hotel = "hotel"
#     driver = "driver"
#     admin = "admin"

# class RideStatus(str, Enum):
#     pending = "pending"
#     confirmed = "confirmed"
#     completed = "completed" 
#     cancelled = "cancelled"

# class ItineraryStatus(str, Enum):
#     upcoming = "upcoming"
#     ongoing = "ongoing"
#     completed = "completed"
#     accepted = "accepted"

# # Base schemas - User
# class UserBase(BaseModel):
#     username: str
#     email: str
#     phone: str
#     name: str
#     address: str
#     userType: UserType

# class UserCreate(UserBase):
#     password: str

# class UserResponse(UserBase):
#     id: int
#     createdAt: datetime

#     class Config:
#         from_attributes = True

# # Base schemas - Customer
# class CustomerBase(BaseModel):
#     dob: Optional[datetime] = None  
#     gender: Optional[str] = None

# class CustomerCreate(CustomerBase):
#     userId: int

# class CustomerResponse(CustomerBase):
#     id: int
#     userId: int
#     createdAt: datetime

#     class Config:
#         from_attributes = True

# # Base schemas - Schedule Item
# class ScheduleItemBase(BaseModel):
#     startTime: datetime
#     endTime: datetime
#     location: str
#     description: Optional[str] = None

# class ScheduleItemCreate(ScheduleItemBase):
#     pass

class ScheduleItemUpdate(BaseModel):
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None

# class ScheduleItemResponse(ScheduleItemBase):
#     id: int
#     itinerary_id: int
#     createdAt: datetime

#     class Config:
#         from_attributes = True

# # Base schemas - Room Item
# class RoomItemBase(BaseModel):
#     startDate: datetime
#     endDate: datetime
#     roomId: int

# class RoomItemCreate(RoomItemBase):
#     pass

# class RoomItemUpdate(BaseModel):
#     startDate: Optional[datetime] = None
#     endDate: Optional[datetime] = None

# class RoomItemResponse(BaseModel):
#     id: int
#     itinerary_id: int
#     roomId: int
#     startDate: datetime
#     endDate: datetime
#     createdAt: datetime
#     # Additional fields from joined tables
#     hotelName: Optional[str] = None
#     roomName: Optional[str] = None
#     roomType: Optional[str] = None
#     city: Optional[str] = None
#     pricePerNight: Optional[float] = None
#     capacity: Optional[int] = None
#     isPaid: bool = False

#     class Config:
#         from_attributes = True

# # Base schemas - Ride Booking
# class RideBookingBase(BaseModel):
#     driverId: Optional[int] = None
#     pickupLocation: str
#     dropLocation: str
#     pickupTime: datetime
#     numberOfPersons: int
#     withDriverService: bool = False
#     type: str  # taxi, premium, shuttle
#     price: float

# class RideBookingCreate(RideBookingBase):
#     pass

# class RideBookingUpdate(BaseModel):
#     pickupLocation: Optional[str] = None
#     dropLocation: Optional[str] = None
#     pickupTime: Optional[datetime] = None
#     withDriverService: Optional[bool] = None
#     status: Optional[RideStatus] = None
#     type: Optional[str] = None

# class RideBookingResponse(RideBookingBase):
#     id: int
#     customerId: int
#     itineraryId: int
#     status: RideStatus
#     createdAt: datetime
#     dropTime: Optional[datetime] = None
#     driverName: Optional[str] = None
#     driverPhone: Optional[str] = None
#     vehicleInfo: Optional[str] = None
#     isReviewed: bool = False

#     class Config:
#         from_attributes = True

# # Base schemas - Itinerary
# class ItineraryBase(BaseModel):
#     name: str
#     numberOfPersons: int = Field(gt=0)
    
# class ItineraryCreate(ItineraryBase):
#     driverServiceRequested: bool = False

# class ItineraryUpdate(BaseModel):
#     name: Optional[str] = None
#     numberOfPersons: Optional[int] = None
#     status: Optional[ItineraryStatus] = None
#     driverServiceRequested: Optional[bool] = None

# class ItineraryResponse(ItineraryBase):
#     id: int
#     customerId: int
#     status: ItineraryStatus = ItineraryStatus.upcoming
#     createdAt: datetime
#     driverServiceRequested: bool = False
#     # Derived fields
#     startDate: Optional[datetime] = None
#     endDate: Optional[datetime] = None
#     destinations: List[str] = []

#     class Config:
#         from_attributes = True

# class ItineraryDetailResponse(ItineraryResponse):
#     scheduleItems: List[ScheduleItemResponse] = []
#     roomItems: List[RoomItemResponse] = []
#     rideBookings: List[RideBookingResponse] = []

#     class Config:
#         from_attributes = True

# # Combined response for items
# class ItineraryItemsResponse(BaseModel):
#     schedule_items: List[ScheduleItemResponse] = []
#     room_items: List[RoomItemResponse] = []
#     ride_bookings: List[RideBookingResponse] = []

#     class Config:
#         from_attributes = True

# # Review schemas
# class ReviewBase(BaseModel):
#     rating: float
#     description: str

# class HotelReviewCreate(ReviewBase):
#     hotelId: int

# class HotelReviewResponse(ReviewBase):
#     id: int
#     customerId: int
#     hotelId: int
#     createdAt: datetime
#     customerName: Optional[str] = None

#     class Config:
#         from_attributes = True

# Room schemas for selection
class CustomerRoomBase(BaseModel):
    type: str
    roomCapacity: int
    basePrice: float
    
class CustomerRoomResponse(CustomerRoomBase):
    id: int
    hotelId: int
    totalNumber: int
    # Joined fields
    hotelName: Optional[str] = None
    city: Optional[str] = None
    
    class Config:
        from_attributes = True

class CustomerAvailableRoomResponse(CustomerRoomResponse):
    image: Optional[str] = None
    amenities: List[str] = []
    availableRoomsList: List[int] = []
    
    class Config:
        from_attributes = True

# Request schema for booking a room
class RoomBookingRequest(BaseModel):
    room_item_id: int
    number_of_persons: int
    customer_id: int

# Response schema for successful booking
class RoomBookingResponse(BaseModel):
    booking_id: int
    room_item_id: int
    start_date: datetime
    end_date: datetime
    room_type: str
    hotel_name: str
    number_of_persons: int
    total_price: float
    message: str = "Booking successful"

# Error response schema
class ErrorResponse(BaseModel):
    detail: str