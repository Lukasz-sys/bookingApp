from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session
from .config import BUSINESS_END_HOUR, BUSINESS_START_HOUR, SLOT_MINUTES
from .models import Appointment, DoctorProfile, Service, User

ACTIVE_APPOINTMENT_STATUSES = ("confirmed",)

def appointment_end(starts_at: datetime, duration_minutes: int | None = None) -> datetime:
    return starts_at + timedelta(minutes=duration_minutes or SLOT_MINUTES)

def has_conflict(db: Session, doctor_id: int, starts_at: datetime, ends_at: datetime, ignore_id: int | None = None) -> bool:
    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
    )
    if ignore_id:
        query = query.filter(Appointment.id != ignore_id)
    return db.query(query.exists()).scalar()

def create_slots(day: date, db: Session, doctor_id: int, duration_minutes: int | None = None) -> list[dict]:
    duration = duration_minutes or SLOT_MINUTES
    start = datetime.combine(day, time(hour=BUSINESS_START_HOUR))
    end = datetime.combine(day, time(hour=BUSINESS_END_HOUR))
    now = datetime.now().replace(second=0, microsecond=0)
    slots = []
    current = start
    while current + timedelta(minutes=duration) <= end:
        slot_end = current + timedelta(minutes=duration)
        slots.append({"starts_at": current, "ends_at": slot_end, "available": current >= now and not has_conflict(db, doctor_id, current, slot_end)})
        current += timedelta(minutes=SLOT_MINUTES)
    return slots

def get_service_or_none(db: Session, service_id: int | None, doctor_id: int) -> Service | None:
    if not service_id:
        return None
    return db.query(Service).filter(Service.id == service_id, Service.doctor_id == doctor_id, Service.is_active.is_(True)).first()

def can_manage_appointment(user: User, appointment: Appointment) -> bool:
    if user.role == "doctor" and user.doctor_profile:
        return appointment.doctor_id == user.doctor_profile.id
    if user.role == "company_admin" and user.owned_company:
        return appointment.company_id == user.owned_company.id
    return False

def can_view_appointment(user: User, appointment: Appointment) -> bool:
    if can_manage_appointment(user, appointment):
        return True
    if user.role == "patient":
        return appointment.patient_user_id == user.id or appointment.patient_email == user.email
    return False
