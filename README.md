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
docker compose up --build
```

Po starcie:

- strona publiczna: `http://localhost:8000/`
- panel administracyjny: `http://localhost:8000/admin`
- dokumentacja API: `http://localhost:8000/docs`

Domyślne konto administratora:

- login: `admin`
- hasło: `admin12345`

## Funkcje

- publiczna strona firmy budowlanej z formularzem kontaktowym;
- automatyczne śledzenie odsłon, kliknięć CTA, interakcji z formularzem i czasu na stronie;
- retroaktywne połączenie anonimowej sesji z klientem po wysłaniu formularza;
- CRM klientów, zapytań ofertowych i ofert handlowych;
- panel administracyjny z KPI, top stronami, alertami i logami aktywności;
- JWT, role `admin`, `sales`, `manager`;
- obsługa zgód RODO i anonimizacji danych osobowych.

## Lokalne uruchomienie bez Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Bez zmiennej `DATABASE_URL` aplikacja użyje lokalnego pliku SQLite `construction_crm.db`. W Docker Compose używany jest PostgreSQL.
