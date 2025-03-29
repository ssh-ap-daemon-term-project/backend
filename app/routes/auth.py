from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from ..schemas import UserCreate, UserResponse, UserLogin
from ..models import User
from ..database import SessionLocal
from ..security import hash_password, verify_password, create_access_token
from ..config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, response: Response, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed, phone=user.phone, userType=user.userType)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/signin", response_model=UserResponse)
def signin(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": str(db_user.id)}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # Set the JWT as an HTTP-only cookie
    cookie_max_age = int(timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds())
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=cookie_max_age, samesite="None", secure=True, path="/")       # TODO: will turn to lax if possible
    return db_user
