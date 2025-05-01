from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, demo_protected, admin , hotel, llmsql_routes,travel_routes, customer, customer_itineraries, driver
# from .llmsql import LLMSQL
# from .config import settings
from .database import engine
from .import models


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://cruiseaide.netlify.app/"],    # frontend URL
    allow_credentials=True,                     # allow cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include API routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(demo_protected.router, prefix="/api/protected", tags=["Protected"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(hotel.router, prefix="/api/hotel", tags=["Hotel"])
app.include_router(llmsql_routes.router, prefix="/api/llmsql", tags=["LLMSQL"])
app.include_router(customer_itineraries.router, prefix="/api/customer_itineraries", tags=["Customer Itineraries"])
app.include_router(customer.router, prefix="/api/customer", tags=["Customer"])
app.include_router(travel_routes.router, prefix="/api/travel", tags=["Travel Planning"])
app.include_router(driver.router, prefix="/api/driver", tags=["Driver"])

# app.include_router(llmsql_routes.router)

@app.get("/")
def root():
    return {"message": "Welcome to the FastAPI Backend"}
