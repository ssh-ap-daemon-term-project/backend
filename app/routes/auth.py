from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session
from datetime import timedelta
from ..schemas import UserCreate, UserResponse, UserLogin
from ..models import User, Customer, Hotel, Driver, Admin
from ..database import SessionLocal
from ..security import hash_password, verify_password, create_access_token
from ..config import ACCESS_TOKEN_EXPIRE_MINUTES
from ..middleware import is_admin

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, response: Response, request: Request, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    existing_user = db.query(User).filter(User.phone == user.phone).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    try:
        hashed = hash_password(user.password)
        new_user = User(
            username=user.username,
            email=user.email,
            hashedPassword=hashed,
            phone=user.phone,
            userType=user.userType,
            name=user.name,
            address=user.address
        )
        db.add(new_user)
        db.flush()  # Flush to generate new_user.id without committing
        
        # Create corresponding user type entry
        if user.userType == "customer":
            if user.dob is None:
                raise HTTPException(status_code=400, detail="Date of birth is required")
            if user.gender is None:
                raise HTTPException(status_code=400, detail="Gender is required")
            customer = Customer(userId=new_user.id, dob=user.dob, gender=user.gender)
            db.add(customer)
    
        elif user.userType == "hotel":
            # Check if admin has made the request using is_admin middleware
            creator_user = is_admin(request)
            
            if user.city is None:
                raise HTTPException(status_code=400, detail="City is required")
            if user.latitude is None:
                raise HTTPException(status_code=400, detail="Latitude is required")
            if user.longitude is None:
                raise HTTPException(status_code=400, detail="Longitude is required")
            if user.rating is None:
                raise HTTPException(status_code=400, detail="Rating is required")
            if user.description is None:
                raise HTTPException(status_code=400, detail="Description is required")
            hotel = Hotel(userId=new_user.id, city=user.city, latitude=user.latitude, longitude=user.longitude, rating=user.rating, description=user.description)
            db.add(hotel)
    
        elif user.userType == "driver":
            # Check if admin has made the request using is_admin middleware
            creator_user = is_admin(request)
            if user.carModel is None:
                raise HTTPException(status_code=400, detail="Car model is required")
            if user.carNumber is None:
                raise HTTPException(status_code=400, detail="Car number is required")
            if user.carType is None:
                raise HTTPException(status_code=400, detail="Car type is required")
            if user.seatingCapacity is None:
                raise HTTPException(status_code=400, detail="Seating capacity is required")
            driver = Driver(
                userId=new_user.id,
                carModel=user.carModel,
                carNumber=user.carNumber,
                carType=user.carType,
                seatingCapacity=user.seatingCapacity
            )
            db.add(driver)
        else:
            raise HTTPException(status_code=400, detail="Invalid user type")
    
        db.commit()  # Commit once all operations succeed
        db.refresh(new_user)
        return new_user
        
    except Exception as e:
        db.rollback()  # Rollback in case of any error
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/signin", response_model=UserResponse)
def signin(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashedPassword):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": str(db_user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # Set the JWT as an HTTP-only cookie
    cookie_max_age = int(timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds())
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=cookie_max_age, samesite="None", secure=True, path="/")       # TODO: will turn to lax if possible
    return db_user

@router.get("/signout")
def signout(response: Response):
    # Clear the JWT cookie
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Successfully logged out"}