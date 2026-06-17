# System rezerwacji wizyt — pełna wersja Docker

Stack:

- PostgreSQL 16
- FastAPI / Python 3.12
- Frontend HTML/CSS/JavaScript serwowany przez Nginx

## Uruchomienie Windows PowerShell


```powershell
docker rm -f booking_postgres booking_api booking_frontend 2>$null
docker compose down --remove-orphans -v
docker compose up --build --force-recreate -d
```

## Adresy

Frontend:

```text
http://localhost:8080
```

API:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

## Naprawa cache przeglądarki

Po aktualizacji paczki zrób twarde odświeżenie:

```text
Ctrl + F5
```

## Konta demo

Hasło do wszystkich kont:

```text
Demo12345!
```

```text
luxmed.demo@example.com        firma / placówka
jan.pacjent@example.com        pacjent
anna.kowalska@example.com      kardiolog
piotr.nowak@example.com        dermatolog
maria.zielinska@example.com    pediatra
tomasz.wisniewski@example.com  ortopeda
```

## Co jest w projekcie

- rejestracja i logowanie JWT,
- role: pacjent, lekarz, firma / placówka,
- weryfikacja e-mail po rejestracji,
- przykładowi lekarze i placówka Luxmed Demo,
- dostępne godziny wizyt,
- zarządzanie wizytami,
- przypomnienia e-mail,
- frontend i backend w Dockerze.

