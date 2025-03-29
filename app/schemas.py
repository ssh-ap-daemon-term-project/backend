from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: str
    userType: str = "customer"  # default userType

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    phone: str
    userType: str

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