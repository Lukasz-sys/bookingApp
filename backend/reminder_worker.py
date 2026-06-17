from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from app.config import REMINDER_HOURS_BEFORE
from app.database import SessionLocal
from app.emailer import send_email
from app.models import Appointment

def send_due_reminders():
    db = SessionLocal()
    try:
        now = datetime.now()
        until = now + timedelta(hours=REMINDER_HOURS_BEFORE)
        appointments = db.query(Appointment).filter(Appointment.status == "confirmed", Appointment.reminder_sent.is_(False), Appointment.starts_at >= now, Appointment.starts_at <= until).all()
        for appointment in appointments:
            send_email(appointment.patient_email, "Przypomnienie o wizycie", f"Przypominamy o wizycie {appointment.starts_at:%Y-%m-%d %H:%M}.\nUsługa: {appointment.service_name}.\nLekarz: {appointment.doctor.user.full_name if appointment.doctor else 'Lekarz'}.")
            if appointment.doctor and appointment.doctor.user:
                send_email(appointment.doctor.user.email, "Przypomnienie: nadchodząca wizyta", f"Wizyta pacjenta {appointment.patient_name}: {appointment.starts_at:%Y-%m-%d %H:%M}.\nUsługa: {appointment.service_name}.")
            appointment.reminder_sent = True
        db.commit()
        print(f"Wysłano/przetworzono przypomnienia: {len(appointments)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Reminder worker uruchomiony. Sprawdza wizyty co 15 minut.")
    scheduler = BlockingScheduler()
    scheduler.add_job(send_due_reminders, "interval", minutes=15, next_run_time=datetime.now())
    scheduler.start()
