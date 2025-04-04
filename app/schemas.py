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
        orm_mode = True

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
        orm_mode = True

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
    availableNumber: List[int]
    bookedNumber: List[int]
    price: List[float]
    
    class Config:
        orm_mode = True
        
        
class MessageResponse(BaseModel):
    detail: str
    
    
class RoomListResponse(BaseModel):
    id: int
    total_no: int
    type: str
    room_capacity: int
    no_booked: List[int]
    no_available: List[int]
    price: List[float] 
    hotelfk: int

    class Config:
        orm_mode = True
        
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
        orm_mode = True