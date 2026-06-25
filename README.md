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

Szczegółowy opis architektury, ról, przepływów i głównych endpointów znajduje się w `docs/architecture.md`.

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
- obsługa zgód RODO i anonimizacji danych osobowych;
- CRUD klientów, zapytań i ofert w panelu administracyjnym;
- zarządzanie użytkownikami panelu przez rolę `admin`;
- paginacja list, wyszukiwanie klientów i filtrowanie zapytań, ofert, logów oraz zdarzeń;
- audit log operacji administracyjnych, eksportów danych i zmian CRM;
- testy automatyczne API.

## Konfiguracja

Najważniejsze zmienne środowiskowe znajdują się w `.env.example`:

- `DATABASE_URL` - adres bazy danych używany przez API i migracje;
- `SECRET_KEY` - klucz podpisywania tokenów JWT;
- `ADMIN_LOGIN`, `ADMIN_PASSWORD` - konto administratora tworzone przy starcie;
- `SEED_SAMPLE_DATA` - włącza lub wyłącza dane demonstracyjne;
- `CORS_ALLOWED_ORIGINS` - dozwolone originy dla zapytań przeglądarki;
- `APP_ENV` - tryb aplikacji; w `production` wymagane są niedomyślne sekrety;
- `RUN_MIGRATIONS` - uruchamia `alembic upgrade head` w entrypoincie kontenera przed startem API;
- `AUTO_CREATE_TABLES` - automatyczne tworzenie tabel przy starcie, wygodne tylko dla lokalnego demo.

W konfiguracji kontenerowej domyślnie używane są migracje (`RUN_MIGRATIONS=true`) i wyłączone automatyczne tworzenie tabel (`AUTO_CREATE_TABLES=false`). Dla środowiska produkcyjnego utrzymaj `AUTO_CREATE_TABLES=false`, ustaw `APP_ENV=production`, wyłącz dane demonstracyjne (`SEED_SAMPLE_DATA=false`) i użyj własnych sekretów.

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

## Kontrola jakości i CI

Lokalne uruchomienie lintu:

```bash
ruff check .
```

Repozytorium zawiera workflow GitHub Actions w `.github/workflows/ci.yml`, który uruchamia lint i testy przy pushu oraz pull requestach.

## Migracje bazy danych

Projekt zawiera migracje Alembic. Po ustawieniu `DATABASE_URL` można wykonać:

```bash
alembic upgrade head
```

Obraz Docker korzysta ze skryptu `scripts/entrypoint.sh`. Jeśli `RUN_MIGRATIONS=true`, entrypoint uruchamia `alembic upgrade head` przed komendą startową kontenera. Migracje są zalecanym sposobem utrzymywania schematu bazy danych. `AUTO_CREATE_TABLES=true` zostaje jako awaryjne ułatwienie dla lokalnych demonstracji bez migracji.

## Audit log

Operacje wykonywane przez użytkowników panelu, takie jak tworzenie i edycja klientów,
tworzenie ofert, anonimizacja oraz eksport danych klienta, są zapisywane w tabeli
`audit_logs`. Log można przeglądać w panelu administracyjnym oraz przez endpoint
`GET /audit/logs`, dostępny dla ról `admin` i `manager`.

## Przydatne parametry API

Listy administracyjne przyjmują parametry:

- `limit` - liczba rekordów, domyślnie `100`, maksymalnie `300`;
- `offset` - przesunięcie wyników;
- `q` - wyszukiwanie klientów po nazwie, emailu lub telefonie dla endpointu `/clients`;
- `status` - filtrowanie zapytań i ofert po statusie;
- `event_type`, `client_id` - filtrowanie logów aktywności `/tracking/logs`;
- `action`, `entity_type`, `actor_login` - filtrowanie dziennika `/audit/logs`.

## Zakres MVP

MVP obejmuje formularz kontaktowy, tracking, CRM, role użytkowników, zgody RODO, anonimizację, eksport danych JSON i audit log. Automatyczna wysyłka emaili, generowanie PDF ofert i integracje z zewnętrznymi systemami pozostają zakresem przyszłych rozszerzeń.
