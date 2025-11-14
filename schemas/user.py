from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str 
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str 

class Token(BaseModel):
    access_token: str
    token_type: str

class GoogleLogin(BaseModel):
    google_id: str
    email: EmailStr
    first_name: str
    last_name: str
    avatar: Optional[str] = None