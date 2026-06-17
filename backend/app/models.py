from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), nullable=False)
    phone = Column(String(40), nullable=True)
    role = Column(String(30), nullable=False, index=True)  # patient, doctor, company_admin
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token_hash = Column(String(128), nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    owned_company = relationship("Company", back_populates="owner", uselist=False)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False, index=True)
    nip = Column(String(30), nullable=True, index=True)
    address = Column(String(255), nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    owner = relationship("User", back_populates="owned_company")
    doctors = relationship("DoctorProfile", back_populates="company")
    appointments = relationship("Appointment", back_populates="company")

class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    specialization = Column(String(160), nullable=True)
    license_number = Column(String(80), nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    user = relationship("User", back_populates="doctor_profile")
    company = relationship("Company", back_populates="doctors")
    services = relationship("Service", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    name = Column(String(140), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    price_cents = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    doctor = relationship("DoctorProfile", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    patient_name = Column(String(160), nullable=False)
    patient_email = Column(String(255), nullable=False, index=True)
    patient_phone = Column(String(40), nullable=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True, index=True)
    service_name = Column(String(140), nullable=False, default="Wizyta")
    starts_at = Column(DateTime(timezone=False), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=False), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="confirmed", index=True)
    notes = Column(Text, nullable=True)
    reminder_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    patient_user = relationship("User", foreign_keys=[patient_user_id])
    doctor = relationship("DoctorProfile", back_populates="appointments")
    company = relationship("Company", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
