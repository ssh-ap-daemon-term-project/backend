from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import date

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
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    description: Optional[str] = None

class HotelResponse(HotelBase):
    id: int
    
    class Config:
        orm_mode = True