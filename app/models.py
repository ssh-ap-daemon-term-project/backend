from .database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Enum, TIMESTAMP, func, Text, Float, Boolean, ARRAY
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(100), nullable=False, unique=True, index=True)
    hashedPassword = Column(Text, nullable=False)  # Allow long hashes
    phone = Column(String(15), nullable=False, unique=True)  
    userType = Column(Enum("customer", "hotel", "driver", "admin", name="userTypes"), nullable=False, default="customer")
    createdAt = Column(TIMESTAMP, server_default=func.now())
    updatedAt = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", uselist=False, back_populates="user")
    hotel = relationship("Hotel", uselist=False, back_populates="user")
    driver = relationship("Driver", uselist=False, back_populates="user")
    admin = relationship("Admin", uselist=False, back_populates="user")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    dob = Column(Date)
    gender = Column(Enum("male", "female", "other", name="gender"))
    createdAt = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", uselist=False, back_populates="customer")
    bookings = relationship("RoomBooking", back_populates="customer")
    rideBookings = relationship("RideBooking", back_populates="customer")
    itineraries = relationship("Itinerary", back_populates="customer")

class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    rating = Column(Float, nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", uselist=False, back_populates="hotel")
    rooms = relationship("Room", back_populates="hotel")
    reviews = relationship("HotelReview", back_populates="hotel")

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    type = Column(Enum("basic", "luxury", "suite", name="room_types"), nullable=False)
    roomCapacity = Column(Integer, nullable=False)
    totalNumber = Column(Integer, nullable=False)
    availableNumber = Column(ARRAY(Integer), nullable=False)
    bookedNumber = Column(ARRAY(Integer), nullable=False)
    price = Column(ARRAY(Float), nullable=False)
    hotelId = Column(Integer, ForeignKey("hotels.id"), nullable=False)

    hotel = relationship("Hotel", uselist=False, back_populates="rooms")
    bookings = relationship("RoomBooking", back_populates="room")

class RoomBooking(Base):
    __tablename__ = "roomBookings"

    id = Column(Integer, primary_key=True)
    customerId = Column(Integer, ForeignKey("customers.id"), nullable=False)
    roomId = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    startDate = Column(DateTime, nullable=False)
    endDate = Column(DateTime, nullable=False)
    numberOfPersons = Column(Integer, nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    customer = relationship("Customer", uselist=False, back_populates="bookings")
    room = relationship("Room", uselist=False, back_populates="bookings")

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    carModel = Column(String(50), nullable=False)
    carNumber = Column(String(20), nullable=False)
    carType = Column(Enum("sedan", "suv", "hatchback", "luxury", name="carTypes"), nullable=False)
    seatingCapacity = Column(Integer, nullable=False)
    address = Column(String(200), nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", uselist=False, back_populates="driver")
    rideBookings = relationship("RideBooking", back_populates="driver")

class RideBooking(Base):
    __tablename__ = "rideBookings"

    id = Column(Integer, primary_key=True)
    customerId = Column(Integer, ForeignKey("customers.id"), nullable=False)
    driverId = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    
    pickupLocation = Column(String(100), nullable=False)
    dropLocation = Column(String(100), nullable=False)
    pickupTime = Column(DateTime, nullable=False)
    dropTime = Column(DateTime, nullable=False)
    numberOfPersons = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(Enum("pending", "confirmed", "completed", "cancelled", name="ride_status"), default="pending")
    createdAt = Column(TIMESTAMP, server_default=func.now())

    customer = relationship("Customer", back_populates="rideBookings")
    driver = relationship("Driver", back_populates="rideBookings")

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), unique=True, nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="admin")

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True)
    customerId = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(String(100), nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    customer = relationship("Customer", back_populates="itineraries")
    scheduleItems = relationship("ScheduleItem", back_populates="itinerary")

class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id = Column(Integer, primary_key=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"), nullable=False)
    startTime = Column(DateTime, nullable=False)
    endTime = Column(DateTime, nullable=False)
    location = Column(String(100), nullable=False)
    description = Column(String)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    itinerary = relationship("Itinerary", back_populates="scheduleItems")

class HotelReview(Base):
    __tablename__ = "hotel_reviews"

    id = Column(Integer, primary_key=True)
    customerId = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    hotelId = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now())

    customer = relationship("Customer")
    hotel = relationship("Hotel", back_populates="reviews")
