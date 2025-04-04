from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, demo_protected, admin , hotel
# from .llmsql import LLMSQL
# from .config import settings
from .database import engine
from .import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],    # frontend URL
    allow_credentials=True,                     # allow cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include API routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(demo_protected.router, prefix="/api/protected", tags=["Protected"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(hotel.router, prefix="/api/hotel", tags=["Hotel"])
# app.include_router(llmsql_routes.router)

@app.get("/")
def root():
    return {"message": "Welcome to the FastAPI Backend"}
