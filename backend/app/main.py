import os
from datetime import date, datetime, timedelta
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from .config import BUSINESS_END_HOUR, BUSINESS_START_HOUR, DEV_PRINT_EMAILS, FRONTEND_URL, SLOT_MINUTES
from .database import Base, engine, get_db
from .deps import get_current_user, get_optional_user, require_roles, require_verified_user
from .emailer import send_email
from .models import Appointment, Company, DoctorProfile, Service, User
from .schemas import AppointmentCreate, AppointmentOut, AppointmentUpdate, AvailabilitySlot, CompanyOut, DoctorOut, LoginRequest, RegisterRequest, RegisterResponse, ResendVerificationRequest, ServiceCreate, ServiceOut, TokenOut, UserOut
from .security import create_access_token, create_email_verification_token, hash_password, hash_token, verify_password
from .services import appointment_end, can_manage_appointment, can_view_appointment, create_slots, get_service_or_none, has_conflict

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Booking API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def find_frontend_dir() -> Path | None:
    """Znajduje katalog frontendu zarówno lokalnie, jak i w kontenerze Docker."""
    candidates: list[Path] = []

    env_dir = os.getenv("FRONTEND_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    current_file = Path(__file__).resolve()
    candidates.extend([
        current_file.parent / "static",          # Najpewniejsze: pliki w obrazie Docker przy backendzie
        current_file.parents[2] / "frontend",   # Docker: /app/frontend
        current_file.parents[1] / "frontend",   # awaryjnie: /app/backend/frontend
        Path.cwd() / "frontend",
        Path.cwd().parent / "frontend",
        Path("/app/backend/app/static"),
        Path("/app/frontend"),
    ])

    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    return None


FRONTEND_DIR = find_frontend_dir()
if FRONTEND_DIR:
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")


@app.get("/", include_in_schema=False)
def root():
    # Redirect zamiast FileResponse, bo index.html ma assety pod /static/*.
    return RedirectResponse(url="/static/index.html", status_code=307)


@app.get("/app", include_in_schema=False)
def app_page():
    return RedirectResponse(url="/static/index.html", status_code=307)


@app.get("/index.html", include_in_schema=False)
def index_page():
    return RedirectResponse(url="/static/index.html", status_code=307)


@app.get("/verify.html", include_in_schema=False)
def verify_page():
    return RedirectResponse(url="/static/verify.html", status_code=307)


@app.get("/debug/static", include_in_schema=False)
def debug_static():
    current_file = Path(__file__).resolve()
    checked = [
        os.getenv("FRONTEND_DIR"),
        str(current_file.parent / "static"),
        str(current_file.parents[2] / "frontend"),
        str(Path("/app/backend/app/static")),
        str(Path("/app/frontend")),
    ]
    return {
        "frontend_found": FRONTEND_DIR is not None,
        "frontend_dir": str(FRONTEND_DIR) if FRONTEND_DIR else None,
        "index_exists": bool(FRONTEND_DIR and (FRONTEND_DIR / "index.html").exists()),
        "checked_paths": checked,
        "cwd": str(Path.cwd()),
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "frontend": bool(FRONTEND_DIR)}

@app.get("/api/settings")
def app_settings():
    return {
        "business_start_hour": BUSINESS_START_HOUR,
        "business_end_hour": BUSINESS_END_HOUR,
        "slot_minutes": SLOT_MINUTES,
        "timezone_hint": "local server time",
    }

def verification_url(raw_token: str) -> str:
    return f"{FRONTEND_URL.rstrip('/')}/verify.html?token={raw_token}"

def send_verification_email(user: User, raw_token: str) -> bool:
    return send_email(user.email, "Weryfikacja adresu e-mail", f"Cześć {user.full_name},\n\nKliknij link, aby zweryfikować e-mail:\n{verification_url(raw_token)}\n\nLink jest ważny 48 godzin.")

def doctor_to_out(doctor: DoctorProfile) -> DoctorOut:
    return DoctorOut(id=doctor.id, user_id=doctor.user_id, full_name=doctor.user.full_name, email=doctor.user.email, phone=doctor.user.phone, specialization=doctor.specialization, license_number=doctor.license_number, bio=doctor.bio, company_id=doctor.company_id, company_name=doctor.company.name if doctor.company else None, is_email_verified=doctor.user.is_email_verified)

def appointment_to_out(appointment: Appointment) -> AppointmentOut:
    doctor_user = appointment.doctor.user if appointment.doctor else None
    return AppointmentOut(id=appointment.id, patient_user_id=appointment.patient_user_id, patient_name=appointment.patient_name, patient_email=appointment.patient_email, patient_phone=appointment.patient_phone, doctor_id=appointment.doctor_id, doctor_name=doctor_user.full_name if doctor_user else "Lekarz", doctor_specialization=appointment.doctor.specialization if appointment.doctor else None, company_id=appointment.company_id, company_name=appointment.company.name if appointment.company else None, service_id=appointment.service_id, service_name=appointment.service_name, starts_at=appointment.starts_at, ends_at=appointment.ends_at, status=appointment.status, notes=appointment.notes, reminder_sent=appointment.reminder_sent, created_at=appointment.created_at)

def appointment_query_for_user(db: Session, user: User):
    query = db.query(Appointment)
    if user.role == "doctor" and user.doctor_profile:
        return query.filter(Appointment.doctor_id == user.doctor_profile.id)
    if user.role == "company_admin" and user.owned_company:
        return query.filter(Appointment.company_id == user.owned_company.id)
    if user.role == "patient":
        return query.filter(or_(Appointment.patient_user_id == user.id, Appointment.patient_email == user.email))
    raise HTTPException(status_code=403, detail="Brak uprawnień do listy wizyt.")

def apply_appointment_filters(query, day: date | None, status_filter: str | None):
    if day:
        start = datetime.combine(day, datetime.min.time())
        query = query.filter(Appointment.starts_at >= start, Appointment.starts_at < start + timedelta(days=1))
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    return query.order_by(Appointment.starts_at.asc())

@app.post("/api/auth/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Konto z takim adresem e-mail już istnieje.")
    if payload.role == "company_admin" and not payload.company_name:
        raise HTTPException(status_code=400, detail="Dla firmy/placówki podaj nazwę firmy.")
    company = None
    if payload.role == "doctor" and payload.company_id:
        company = db.get(Company, payload.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Nie znaleziono firmy o podanym ID.")
    raw_token, token_hash, expires_at = create_email_verification_token()
    user = User(email=payload.email, password_hash=hash_password(payload.password), full_name=payload.full_name, phone=payload.phone, role=payload.role, email_verification_token_hash=token_hash, email_verification_expires_at=expires_at)
    db.add(user)
    db.flush()
    if payload.role == "company_admin":
        company = Company(name=payload.company_name or payload.full_name, nip=payload.company_nip, address=payload.company_address, owner_user_id=user.id)
        db.add(company)
    if payload.role == "doctor":
        doctor = DoctorProfile(user_id=user.id, company_id=company.id if company else payload.company_id, specialization=payload.specialization, license_number=payload.license_number, bio=payload.bio)
        db.add(doctor)
        db.flush()
        db.add(Service(doctor_id=doctor.id, name="Konsultacja", duration_minutes=SLOT_MINUTES))
    db.commit()
    db.refresh(user)
    send_verification_email(user, raw_token)
    return RegisterResponse(user=user, message="Konto utworzone. Sprawdź e-mail i kliknij link weryfikacyjny.", dev_verification_url=verification_url(raw_token) if DEV_PRINT_EMAILS else None)

@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Nieprawidłowy e-mail lub hasło.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto jest nieaktywne.")
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Najpierw zweryfikuj adres e-mail.")
    return TokenOut(access_token=create_access_token(user.id, user.role), user=user)

@app.get("/api/auth/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verification_token_hash == hash_token(token)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Nieprawidłowy token weryfikacyjny.")
    if user.email_verification_expires_at and user.email_verification_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token weryfikacyjny wygasł. Wyślij link ponownie.")
    user.is_email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.commit()
    return {"verified": True, "message": "Adres e-mail został zweryfikowany. Możesz się zalogować."}

@app.post("/api/auth/resend-verification")
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"message": "Jeżeli konto istnieje, wysłaliśmy link weryfikacyjny."}
    if user.is_email_verified:
        return {"message": "Ten adres e-mail jest już zweryfikowany."}
    raw_token, token_hash, expires_at = create_email_verification_token()
    user.email_verification_token_hash = token_hash
    user.email_verification_expires_at = expires_at
    db.commit()
    send_verification_email(user, raw_token)
    return {"message": "Jeżeli konto istnieje, wysłaliśmy link weryfikacyjny.", "dev_verification_url": verification_url(raw_token) if DEV_PRINT_EMAILS else None}

@app.get("/api/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@app.get("/api/companies", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).order_by(Company.name.asc()).all()

@app.get("/api/doctors", response_model=list[DoctorOut])
def list_doctors(company_id: int | None = None, specialization: str | None = None, db: Session = Depends(get_db)):
    query = db.query(DoctorProfile).join(User).filter(User.is_active.is_(True))
    if company_id:
        query = query.filter(DoctorProfile.company_id == company_id)
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))
    return [doctor_to_out(doctor) for doctor in query.order_by(User.full_name.asc()).all()]

@app.get("/api/services", response_model=list[ServiceOut])
def list_services(doctor_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(Service).filter(Service.doctor_id == doctor_id, Service.is_active.is_(True)).order_by(Service.name.asc()).all()

@app.post("/api/services", response_model=ServiceOut, status_code=201)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("doctor", "company_admin"))):
    if user.role == "doctor":
        if not user.doctor_profile:
            raise HTTPException(status_code=400, detail="Brak profilu lekarza.")
        doctor_id = user.doctor_profile.id
        if payload.doctor_id and payload.doctor_id != doctor_id:
            raise HTTPException(status_code=403, detail="Lekarz może dodawać usługi tylko do własnego profilu.")
    else:
        if not user.owned_company:
            raise HTTPException(status_code=400, detail="Brak profilu firmy.")
        if not payload.doctor_id:
            raise HTTPException(status_code=400, detail="Firma musi podać doctor_id.")
        doctor = db.get(DoctorProfile, payload.doctor_id)
        if not doctor or doctor.company_id != user.owned_company.id:
            raise HTTPException(status_code=403, detail="Ten lekarz nie należy do Twojej firmy.")
        doctor_id = payload.doctor_id
    service = Service(doctor_id=doctor_id, name=payload.name, duration_minutes=payload.duration_minutes, price_cents=payload.price_cents)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

@app.get("/api/availability", response_model=list[AvailabilitySlot])
def get_availability(doctor_id: int = Query(...), day: date = Query(...), service_id: int | None = None, db: Session = Depends(get_db)):
    doctor = db.get(DoctorProfile, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Nie znaleziono lekarza.")
    service = get_service_or_none(db, service_id, doctor_id) if service_id else None
    return create_slots(day, db, doctor_id, service.duration_minutes if service else SLOT_MINUTES)

@app.post("/api/appointments", response_model=AppointmentOut, status_code=201)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), current_user: User | None = Depends(get_optional_user)):
    doctor = db.get(DoctorProfile, payload.doctor_id)
    if not doctor or not doctor.user.is_active:
        raise HTTPException(status_code=404, detail="Nie znaleziono lekarza.")
    service = get_service_or_none(db, payload.service_id, doctor.id) if payload.service_id else None
    duration = service.duration_minutes if service else SLOT_MINUTES
    starts_at = payload.starts_at.replace(second=0, microsecond=0, tzinfo=None)
    ends_at = appointment_end(starts_at, duration)
    if starts_at < datetime.now().replace(second=0, microsecond=0):
        raise HTTPException(status_code=400, detail="Nie można rezerwować terminu z przeszłości.")
    slots = create_slots(starts_at.date(), db, doctor.id, duration)
    if not any(slot["starts_at"] == starts_at and slot["available"] for slot in slots):
        raise HTTPException(status_code=409, detail="Ten termin jest niedostępny albo poza godzinami pracy.")
    if has_conflict(db, doctor.id, starts_at, ends_at):
        raise HTTPException(status_code=409, detail="Ten termin jest już zajęty.")
    appointment = Appointment(
        patient_user_id=current_user.id if current_user and current_user.role == "patient" else None,
        patient_name=payload.patient_name,
        patient_email=payload.patient_email,
        patient_phone=payload.patient_phone,
        doctor_id=doctor.id,
        company_id=doctor.company_id,
        service_id=service.id if service else None,
        service_name=service.name if service else (payload.service_name or "Wizyta"),
        starts_at=starts_at,
        ends_at=ends_at,
        notes=payload.notes,
        status="confirmed",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    send_email(appointment.patient_email, "Potwierdzenie rezerwacji wizyty", f"Cześć {appointment.patient_name},\n\nTwoja wizyta '{appointment.service_name}' została zarezerwowana na {appointment.starts_at:%Y-%m-%d %H:%M}.\nLekarz: {doctor.user.full_name}.\nPlacówka: {doctor.company.name if doctor.company else 'brak'}.")
    send_email(doctor.user.email, "Nowa rezerwacja wizyty", f"Masz nową wizytę {appointment.starts_at:%Y-%m-%d %H:%M}.\nPacjent: {appointment.patient_name}, {appointment.patient_email}.\nUsługa: {appointment.service_name}.")
    return appointment_to_out(appointment)

@app.get("/api/appointments", response_model=list[AppointmentOut])
def list_appointments(day: date | None = None, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_verified_user)):
    query = apply_appointment_filters(appointment_query_for_user(db, user), day, status)
    return [appointment_to_out(item) for item in query.all()]

@app.get("/api/my/appointments", response_model=list[AppointmentOut])
def my_appointments(day: date | None = None, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_verified_user)):
    query = apply_appointment_filters(appointment_query_for_user(db, user), day, status)
    return [appointment_to_out(item) for item in query.all()]

@app.get("/api/doctor/appointments", response_model=list[AppointmentOut])
def doctor_appointments(day: date | None = None, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles("doctor"))):
    query = db.query(Appointment).filter(Appointment.doctor_id == user.doctor_profile.id)
    return [appointment_to_out(item) for item in apply_appointment_filters(query, day, status).all()]

@app.get("/api/company/appointments", response_model=list[AppointmentOut])
def company_appointments(day: date | None = None, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles("company_admin"))):
    if not user.owned_company:
        raise HTTPException(status_code=400, detail="Brak profilu firmy.")
    query = db.query(Appointment).filter(Appointment.company_id == user.owned_company.id)
    return [appointment_to_out(item) for item in apply_appointment_filters(query, day, status).all()]

@app.patch("/api/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, payload: AppointmentUpdate, db: Session = Depends(get_db), user: User = Depends(require_verified_user)):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Nie znaleziono wizyty.")
    if not can_view_appointment(user, appointment):
        raise HTTPException(status_code=403, detail="Brak uprawnień do tej wizyty.")
    data = payload.model_dump(exclude_unset=True)
    is_manager = can_manage_appointment(user, appointment)
    if user.role == "patient" and not is_manager:
        if set(data.keys()) - {"status"} or data.get("status") != "cancelled":
            raise HTTPException(status_code=403, detail="Pacjent może tylko anulować własną wizytę.")
    new_service = appointment.service
    if "service_id" in data and data["service_id"] is not None:
        if not is_manager:
            raise HTTPException(status_code=403, detail="Tylko lekarz lub firma może zmienić usługę.")
        new_service = get_service_or_none(db, data["service_id"], appointment.doctor_id)
        if not new_service:
            raise HTTPException(status_code=404, detail="Nie znaleziono usługi dla tego lekarza.")
        appointment.service_id = new_service.id
        appointment.service_name = new_service.name
        data.pop("service_id")
    if "starts_at" in data and data["starts_at"]:
        if not is_manager:
            raise HTTPException(status_code=403, detail="Tylko lekarz lub firma może zmienić termin.")
        new_start = data["starts_at"].replace(second=0, microsecond=0, tzinfo=None)
        new_end = appointment_end(new_start, new_service.duration_minutes if new_service else SLOT_MINUTES)
        if has_conflict(db, appointment.doctor_id, new_start, new_end, ignore_id=appointment.id):
            raise HTTPException(status_code=409, detail="Ten termin jest już zajęty.")
        appointment.starts_at = new_start
        appointment.ends_at = new_end
        appointment.reminder_sent = False
        data.pop("starts_at")
    for key, value in data.items():
        setattr(appointment, key, value)
    db.commit()
    db.refresh(appointment)
    return appointment_to_out(appointment)

@app.post("/api/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(require_verified_user)):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Nie znaleziono wizyty.")
    if not can_view_appointment(user, appointment):
        raise HTTPException(status_code=403, detail="Brak uprawnień do tej wizyty.")
    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    send_email(appointment.patient_email, "Wizyta została anulowana", f"Twoja wizyta {appointment.starts_at:%Y-%m-%d %H:%M} została anulowana.")
    if appointment.doctor and appointment.doctor.user:
        send_email(appointment.doctor.user.email, "Anulowano wizytę", f"Anulowano wizytę pacjenta {appointment.patient_name} z dnia {appointment.starts_at:%Y-%m-%d %H:%M}.")
    return appointment_to_out(appointment)

@app.delete("/api/appointments/{appointment_id}")
def delete_appointment(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(require_verified_user)):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Nie znaleziono wizyty.")
    if not can_manage_appointment(user, appointment):
        raise HTTPException(status_code=403, detail="Tylko lekarz lub firma może usunąć wizytę.")
    db.delete(appointment)
    db.commit()
    return {"deleted": True}
