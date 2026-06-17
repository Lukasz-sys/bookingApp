import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "System rezerwacji wizyt")
APP_ENV = os.getenv("APP_ENV", "development")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/booking_db")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_IN_PRODUCTION")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000/static")
BUSINESS_START_HOUR = int(os.getenv("BUSINESS_START_HOUR", "9"))
BUSINESS_END_HOUR = int(os.getenv("BUSINESS_END_HOUR", "17"))
SLOT_MINUTES = int(os.getenv("SLOT_MINUTES", "30"))
REMINDER_HOURS_BEFORE = int(os.getenv("REMINDER_HOURS_BEFORE", "24"))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "tak"}
DEV_PRINT_EMAILS = os.getenv("DEV_PRINT_EMAILS", "true").lower() in {"1", "true", "yes", "tak"}
