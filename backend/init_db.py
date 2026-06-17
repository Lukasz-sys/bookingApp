import os
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.demo_data import DEMO_PASSWORD, seed_demo_data


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Połączenie z PostgreSQL działa.")
            return
        except OperationalError as exc:
            last_error = exc
            print(f"Czekam na PostgreSQL... próba {attempt}/{max_attempts}")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Nie udało się połączyć z PostgreSQL: {last_error}")


def should_reset_db() -> bool:
    value = os.getenv("RESET_DB_ON_START", "false").strip().lower()
    return value in {"1", "true", "yes", "tak"}


if __name__ == "__main__":
    wait_for_database()

    if should_reset_db():
        print("RESET_DB_ON_START=true — usuwam stare tabele demo i tworzę świeżą bazę.")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_demo_data(db)

    print("Baza danych została zainicjalizowana.")
    print("Dodano/odświeżono dane demo.")
    print("Hasło do kont demo:", DEMO_PASSWORD)
    print("Konta demo:")
    print("- luxmed.demo@example.com — firma / placówka")
    print("- jan.pacjent@example.com — pacjent")
    print("- anna.kowalska@example.com — lekarz")
    print("- piotr.nowak@example.com — lekarz")
    print("- maria.zielinska@example.com — lekarz")
    print("- tomasz.wisniewski@example.com — lekarz niezależny")
