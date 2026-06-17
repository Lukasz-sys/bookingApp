from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

UserRole = Literal["patient", "doctor", "company_admin"]
AppointmentStatus = Literal["confirmed", "cancelled", "completed"]

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str
    is_email_verified: bool
    created_at: datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=40)
    role: UserRole = "patient"
    company_name: Optional[str] = Field(default=None, max_length=180)
    company_nip: Optional[str] = Field(default=None, max_length=30)
    company_address: Optional[str] = Field(default=None, max_length=255)
    specialization: Optional[str] = Field(default=None, max_length=160)
    license_number: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = None
    company_id: Optional[int] = None
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()

class RegisterResponse(BaseModel):
    user: UserOut
    message: str
    dev_verification_url: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    nip: Optional[str] = None
    address: Optional[str] = None
    owner_user_id: int
    created_at: datetime

class DoctorOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    bio: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    is_email_verified: bool

class ServiceCreate(BaseModel):
    doctor_id: Optional[int] = None
    name: str = Field(min_length=2, max_length=140)
    duration_minutes: int = Field(default=30, ge=10, le=240)
    price_cents: Optional[int] = Field(default=None, ge=0)

class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_id: int
    name: str
    duration_minutes: int
    price_cents: Optional[int] = None
    is_active: bool

class AppointmentCreate(BaseModel):
    doctor_id: int
    service_id: Optional[int] = None
    patient_name: str = Field(min_length=2, max_length=160)
    patient_email: EmailStr
    patient_phone: Optional[str] = Field(default=None, max_length=40)
    service_name: Optional[str] = Field(default=None, max_length=140)
    starts_at: datetime
    notes: Optional[str] = None
    @field_validator("patient_email")
    @classmethod
    def normalize_patient_email(cls, value: str) -> str:
        return value.lower().strip()

class AppointmentUpdate(BaseModel):
    patient_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    patient_email: Optional[EmailStr] = None
    patient_phone: Optional[str] = Field(default=None, max_length=40)
    service_id: Optional[int] = None
    service_name: Optional[str] = Field(default=None, max_length=140)
    starts_at: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None

class AppointmentOut(BaseModel):
    id: int
    patient_user_id: Optional[int] = None
    patient_name: str
    patient_email: EmailStr
    patient_phone: Optional[str] = None
    doctor_id: int
    doctor_name: str
    doctor_specialization: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    service_id: Optional[int] = None
    service_name: str
    starts_at: datetime
    ends_at: datetime
    status: str
    notes: Optional[str] = None
    reminder_sent: bool
    created_at: datetime

class AvailabilitySlot(BaseModel):
    starts_at: datetime
    ends_at: datetime
    available: bool
