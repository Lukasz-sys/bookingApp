from sqlalchemy.orm import Session
from .config import SLOT_MINUTES
from .models import Company, DoctorProfile, Service, User
from .security import hash_password

DEMO_PASSWORD = "Demo12345!"

DEMO_COMPANY_EMAIL = "luxmed.demo@example.com"
DEMO_PATIENT_EMAIL = "jan.pacjent@example.com"

DEMO_DOCTORS = [
    {
        "email": "anna.kowalska@example.com",
        "full_name": "dr Anna Kowalska",
        "phone": "+48 500 100 101",
        "specialization": "Kardiolog",
        "license_number": "PWZ-100001",
        "bio": "Konsultacje kardiologiczne, profilaktyka chorób serca i kontrola EKG.",
        "services": [
            {"name": "Konsultacja kardiologiczna", "duration_minutes": 30, "price_cents": 22000},
            {"name": "EKG z opisem", "duration_minutes": 20, "price_cents": 12000},
        ],
    },
    {
        "email": "piotr.nowak@example.com",
        "full_name": "dr Piotr Nowak",
        "phone": "+48 500 100 102",
        "specialization": "Dermatolog",
        "license_number": "PWZ-100002",
        "bio": "Diagnostyka zmian skórnych, trądzik, alergie skórne i kontrola znamion.",
        "services": [
            {"name": "Konsultacja dermatologiczna", "duration_minutes": 30, "price_cents": 20000},
            {"name": "Kontrola znamion", "duration_minutes": 45, "price_cents": 26000},
        ],
    },
    {
        "email": "maria.zielinska@example.com",
        "full_name": "dr Maria Zielińska",
        "phone": "+48 500 100 103",
        "specialization": "Pediatra",
        "license_number": "PWZ-100003",
        "bio": "Wizyty dziecięce, infekcje sezonowe, bilanse zdrowia i konsultacje profilaktyczne.",
        "services": [
            {"name": "Konsultacja pediatryczna", "duration_minutes": 30, "price_cents": 18000},
            {"name": "Bilans zdrowia dziecka", "duration_minutes": 45, "price_cents": 24000},
        ],
    },
]

INDEPENDENT_DOCTOR = {
    "email": "tomasz.wisniewski@example.com",
    "full_name": "dr Tomasz Wiśniewski",
    "phone": "+48 500 100 104",
    "specialization": "Ortopeda",
    "license_number": "PWZ-100004",
    "bio": "Urazy sportowe, bóle kręgosłupa, konsultacje ortopedyczne i kwalifikacje do rehabilitacji.",
    "services": [
        {"name": "Konsultacja ortopedyczna", "duration_minutes": 30, "price_cents": 21000},
        {"name": "Kontrola po urazie", "duration_minutes": 30, "price_cents": 17000},
    ],
}


def _get_or_create_user(db: Session, *, email: str, full_name: str, role: str, phone: str | None = None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name=full_name,
        phone=phone,
        role=role,
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def _ensure_service(db: Session, doctor_id: int, name: str, duration_minutes: int | None = None, price_cents: int | None = None) -> Service:
    service = db.query(Service).filter(Service.doctor_id == doctor_id, Service.name == name).first()
    if service:
        service.duration_minutes = duration_minutes or service.duration_minutes or SLOT_MINUTES
        service.price_cents = price_cents
        service.is_active = True
        return service
    service = Service(
        doctor_id=doctor_id,
        name=name,
        duration_minutes=duration_minutes or SLOT_MINUTES,
        price_cents=price_cents,
        is_active=True,
    )
    db.add(service)
    return service


def _ensure_doctor(db: Session, data: dict, company: Company | None = None) -> DoctorProfile:
    user = _get_or_create_user(
        db,
        email=data["email"],
        full_name=data["full_name"],
        phone=data.get("phone"),
        role="doctor",
    )
    doctor = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
    if not doctor:
        doctor = DoctorProfile(user_id=user.id)
        db.add(doctor)
        db.flush()
    doctor.company_id = company.id if company else None
    doctor.specialization = data.get("specialization")
    doctor.license_number = data.get("license_number")
    doctor.bio = data.get("bio")
    for service in data.get("services", []):
        _ensure_service(db, doctor.id, service["name"], service.get("duration_minutes"), service.get("price_cents"))
    return doctor


def seed_demo_data(db: Session) -> None:
    """Dodaje przykładową placówkę, pacjenta i lekarzy. Funkcja jest idempotentna."""
    company_owner = _get_or_create_user(
        db,
        email=DEMO_COMPANY_EMAIL,
        full_name="Luxmed Demo — administrator",
        phone="+48 500 100 100",
        role="company_admin",
    )
    company = db.query(Company).filter(Company.owner_user_id == company_owner.id).first()
    if not company:
        company = Company(
            name="Luxmed Demo",
            nip="5250000000",
            address="ul. Zdrowa 1, 00-001 Warszawa",
            owner_user_id=company_owner.id,
        )
        db.add(company)
        db.flush()
    else:
        company.name = "Luxmed Demo"
        company.nip = company.nip or "5250000000"
        company.address = company.address or "ul. Zdrowa 1, 00-001 Warszawa"

    _get_or_create_user(
        db,
        email=DEMO_PATIENT_EMAIL,
        full_name="Jan Pacjent",
        phone="+48 500 200 200",
        role="patient",
    )

    for doctor_data in DEMO_DOCTORS:
        _ensure_doctor(db, doctor_data, company)
    _ensure_doctor(db, INDEPENDENT_DOCTOR, None)

    db.commit()
