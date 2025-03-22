from fastapi import Request, HTTPException, status
from .security import decode_access_token
from .database import SessionLocal
from .models import User

def is_auth(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload or payload.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID")
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def is_customer(request: Request):
    user = is_auth(request)
    if user.role != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as customer")
    return user

def is_hotel(request: Request):
    user = is_auth(request)
    if user.role != "hotel":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as hotel")
    return user

def is_driver(request: Request):
    user = is_auth(request)
    if user.role != "driver":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as driver")
    return user