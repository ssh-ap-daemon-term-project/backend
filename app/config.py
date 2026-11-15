import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
DATABASE_URL = os.environ["DATABASE_URL"]
CSRF_SECRET = os.environ["CSRF_SECRET"]


class CsrfSettings(BaseModel):
    secret_key: str = CSRF_SECRET
