from .database import Base
from sqlalchemy import Column, Integer, String

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    userType = Column(String, nullable=False, default="customer")  # userType: 'customer', 'hotel', 'driver', 'admin'
