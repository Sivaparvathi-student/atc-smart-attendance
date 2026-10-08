from datetime import date, datetime
from pydantic import BaseModel, EmailStr


# USER SCHEMAS
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_approved: bool

    model_config = {"from_attributes": True}


# EVENT SCHEMAS
class EventCreate(BaseModel):
    event_name: str
    event_date: date
    secret_key: str


class EventResponse(BaseModel):
    id: int
    event_name: str
    event_date: date
    is_active: bool

    model_config = {"from_attributes": True}


# ATTENDEE SCHEMAS
class AttendeeCreate(BaseModel):
    student_email: EmailStr
    event_id: int
    student_roll_number: str
    student_name: str


class AttendeeResponse(BaseModel):
    student_email: EmailStr
    event_id: int
    student_roll_number: str
    student_name: str
    status: str
    qr_sent: bool

    model_config = {"from_attributes": True}


# TOKEN SCHEMA
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str