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
        from_attributes = True


class ScheduleItemUpdate(BaseModel):
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None


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
class ItineraryRoomBookingRequest(BaseModel):
    room_item_id: int
    number_of_persons: int
    customer_id: int

# Response schema for successful booking
class ItineraryRoomBookingResponse(BaseModel):
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

class ItineraryBookingCancellationResponse(BaseModel):
    message: str
    booking_id: int

class CustomerHotelResponse(BaseModel):
    id: int
    name: str
    city: str
    address: str
    description: Optional[str] = None
    basePrice: Optional[float] = None
    rating: Optional[float] = None
    imageUrl: Optional[str] = None
    amenities: List[str] = []
    
    class Config:
        from_attributes = True

class HotelReviewResponse(BaseModel):
    id: int
    customerId: int
    customerName: str
    rating: float
    description: str
    createdAt: Optional[str] = None
    
    class Config:
        from_attributes = True

class CustomerHotelByIdRoomResponse(BaseModel):
    id: int
    type: str
    roomCapacity: int
    basePrice: float
    totalNumber: int
    availableRoomsList: List[int] = []
    
    class Config:
        from_attributes = True

class CustomerHotelByIdResponse(BaseModel):
    id: int
    name: str
    city: str
    address: str
    longitude: float
    latitude: float
    description: str
    basePrice: Optional[float] = None
    rating: Optional[float] = None
    imageUrl: Optional[str] = None
    # amenities: List[str] = []
    rooms: List[CustomerHotelByIdRoomResponse] = []
    reviews: List[HotelReviewResponse] = []
    
    class Config:
        from_attributes = True

# Add to schemas.py
class RoomBookingByRoomIdRequest(BaseModel):
    room_id: int
    start_date: datetime
    end_date: datetime
    number_of_persons: int

class RoomBookingByRoomIdResponse(BaseModel):
    booking_id: int
    room_id: int
    start_date: datetime
    end_date: datetime
    room_type: str
    hotel_name: str
    number_of_persons: int
    total_price: float

class BookingCancellationByBookingIdResponse(BaseModel):
    message: str
    booking_id: int

class CustomerBookingResponse(BaseModel):
    id: int
    hotelId: int
    hotelName: str
    roomName: str
    city: str
    startDate: datetime
    endDate: datetime
    guests: int
    totalPrice: float
    status: str
    image: Optional[str] = None

class CancelBookingResponse(BaseModel):
    message: str
    booking_id: int

class BookingReviewRequest(BaseModel):
    booking_id: int
    rating: int
    comment: str
    
    
class HotelRoom(BaseModel):
    id: int
    type: str
    basePrice: float
    roomCapacity: int
    image: Optional[str] = None

class HotelReviewDetail(BaseModel):
    id: int
    rating: int
    comment: str
    customerName: str
    date: str

class HotelStats(BaseModel):
    totalBookings: int
    occupancyRate: int

class HotelProfileResponse(BaseModel):
    id: int
    userId: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: str
    description: Optional[str] = None
    rating: Optional[float] = None
    totalRooms: int
    rooms: List[HotelRoom]
    reviews: List[HotelReviewDetail]
    stats: HotelStats
    amenities: List[str]

class HotelProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None

    
    
class DriverProfileResponse(BaseModel):
    id: int
    userId: int
    name: str
    email: str
    licenseNumber: Optional[str] = ""
    vehicleType: Optional[str] = ""
    vehicleModel: Optional[str] = ""
    vehicleYear: Optional[int] = 0
    vehiclePlate: Optional[str] = ""
    address: Optional[str] = ""
    phoneNumber: Optional[str] = ""
    isVerified: bool = False
    createdAt: datetime
    rating: float = 0.0
    totalTrips: int = 0
    
    class Config:
        from_attributes = True
        
class CustomerProfileResponse(BaseModel):
    id: int
    userId: int
    name: str
    email: str
    phoneNumber: Optional[str] = ""
    address: Optional[str] = ""
    dateOfBirth: Optional[datetime] = None
    preferences: Optional[Dict[str, Any]] = {}
    isVerified: bool = False
    createdAt: datetime
    totalTrips: int = 0
    activeItineraries: int = 0
    completedItineraries: int = 0
    
    class Config:
        from_attributes = True
        

class AdminProfileResponse(BaseModel):
    id: int
    userId: int
    name: str
    email: str
    phoneNumber: Optional[str] = ""
    position: Optional[str] = "Administrator"
    department: Optional[str] = "Operations"
    permissions: Optional[List[str]] = []
    isActive: bool = True
    createdAt: datetime
    lastLogin: Optional[datetime] = None
    
    # Statistics
    totalCustomers: int = 0
    totalDrivers: int = 0
    totalItineraries: int = 0
    totalHotels: int = 0
    
    class Config:
        from_attributes = True
        
        
        
        
        
        
        
