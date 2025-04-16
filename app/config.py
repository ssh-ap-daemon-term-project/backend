import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "bb3911aacc0a1c464b78b7aa8790abf325b14be2e1a16fbf409d61a649575f85")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
CSRF_SECRET = os.getenv("CSRF_SECRET", "fe9a624eb8ffc525af8fdd821f7363f6bb3e9475980cb8cf88c69dc947dc2f9a")

# Example CSRF settings (to be used with a CSRF package later)
class CsrfSettings(BaseModel):
    secret_key: str = CSRF_SECRET
