# Construction CRM Analytics

System internetowy wspomagający zarządzanie i analizę aktywności klientów firmy budowlanej.

## Struktura

```text
backend/app/
  main.py
  database.py
  models.py
  schemas.py
  auth.py
  routers/
  services/
frontend/
  index.html
  admin.html
  styles.css
  tracking.js
  admin.js
Dockerfile
docker-compose.yml
requirements.txt
```

## Uruchomienie przez Docker

```bash
cp .env.example .env
docker compose up --build
```

Po starcie:

- strona publiczna: `http://localhost:8000/`
- panel administracyjny: `http://localhost:8000/admin`
- dokumentacja API: `http://localhost:8000/docs`

Domyślne konto administratora:

- login: wartość `ADMIN_LOGIN` z pliku `.env`
- hasło: wartość `ADMIN_PASSWORD` z pliku `.env`

Przed uruchomieniem poza środowiskiem demonstracyjnym zmień wartości `SECRET_KEY`,
`POSTGRES_PASSWORD` i `ADMIN_PASSWORD` w pliku `.env`.

## Funkcje

- publiczna strona firmy budowlanej z formularzem kontaktowym;
- automatyczne śledzenie odsłon, kliknięć CTA, interakcji z formularzem i czasu na stronie;
- retroaktywne połączenie anonimowej sesji z klientem po wysłaniu formularza;
- CRM klientów, zapytań ofertowych i ofert handlowych;
- panel administracyjny z KPI, top stronami, alertami i logami aktywności;
- JWT, role `admin`, `sales`, `manager`;
- obsługa zgód RODO i anonimizacji danych osobowych.
- paginacja list oraz wyszukiwanie klientów;
- testy automatyczne API.

## Konfiguracja

Najważniejsze zmienne środowiskowe znajdują się w `.env.example`:

- `DATABASE_URL` - adres bazy danych używany przez API i migracje;
- `SECRET_KEY` - klucz podpisywania tokenów JWT;
- `ADMIN_LOGIN`, `ADMIN_PASSWORD` - konto administratora tworzone przy starcie;
- `SEED_SAMPLE_DATA` - włącza lub wyłącza dane demonstracyjne;
- `CORS_ALLOWED_ORIGINS` - dozwolone originy dla zapytań przeglądarki.

Role użytkowników:

- `admin` - zarządzanie użytkownikami, pełny dostęp, anonimizacja danych;
- `sales` - obsługa klientów, zapytań i ofert;
- `manager` - dostęp podglądowy do danych i analityki.

## Lokalne uruchomienie bez Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="change-this-local-secret"
export ADMIN_PASSWORD="change-this-admin-password"
uvicorn backend.app.main:app --reload
```

Bez zmiennej `DATABASE_URL` aplikacja użyje lokalnego pliku SQLite `construction_crm.db`. W Docker Compose używany jest PostgreSQL.

## Testy

```bash
python -m pytest -q
```

Testy używają osobnej bazy SQLite w katalogu tymczasowym systemu.

## Migracje bazy danych

Projekt zawiera migracje Alembic. Po ustawieniu `DATABASE_URL` można wykonać:

```bash
alembic upgrade head
```

Aplikacja nadal tworzy tabele automatycznie przy starcie, co ułatwia lokalne demo, ale migracje są zalecanym sposobem utrzymywania schematu bazy danych.

## Przydatne parametry API

Listy administracyjne przyjmują parametry:

- `limit` - liczba rekordów, domyślnie `100`, maksymalnie `300`;
- `offset` - przesunięcie wyników;
- `q` - wyszukiwanie klientów po nazwie, emailu lub telefonie dla endpointu `/clients`;
- `status` - filtrowanie zapytań i ofert po statusie.
