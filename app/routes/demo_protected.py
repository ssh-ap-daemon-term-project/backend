from fastapi import APIRouter, Depends, Request
from ..middleware import is_auth, is_customer, is_hotel, is_driver

router = APIRouter()

@router.get("/all")
def all_users(request: Request, user=Depends(is_auth)):
    return {"message": f"Hello {user.username}, you are authenticated as {user.role}"}

@router.get("/customer")
def customer_route(request: Request, user=Depends(is_customer)):
    return {"message": f"Hello {user.username}, welcome customer!"}

@router.get("/hotel")
def hotel_route(request: Request, user=Depends(is_hotel)):
    return {"message": f"Hello {user.username}, welcome hotel owner!"}

@router.get("/driver")
def driver_route(request: Request, user=Depends(is_driver)):
    return {"message": f"Hello {user.username}, welcome driver!"}
