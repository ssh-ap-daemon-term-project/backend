from pydantic import BaseModel, EmailStr

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

class Token(BaseModel):
    access_token: str
    token_type: str
