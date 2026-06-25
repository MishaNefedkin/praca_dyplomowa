# Architektura systemu

## Cel systemu

Construction CRM Analytics to aplikacja wspierająca firmę budowlaną w obsłudze zapytań klientów, przygotowywaniu ofert oraz analizie aktywności użytkowników na stronie publicznej.

## Warstwy aplikacji

```mermaid
flowchart LR
    User["Użytkownik strony publicznej"] --> Frontend["Frontend statyczny"]
    Admin["Pracownik firmy"] --> AdminPanel["Panel administracyjny"]
    Frontend --> API["FastAPI"]
    AdminPanel --> API
    API --> DB["PostgreSQL / SQLite"]
    API --> Migrations["Alembic"]
```

- `frontend/` - strona publiczna, formularz kontaktowy, tracking aktywności i panel administracyjny.
- `backend/app/routers/` - endpointy API podzielone według obszarów: auth, clients, inquiries, offers, tracking, analytics, consents.
- `backend/app/models.py` - modele SQLAlchemy opisujące tabele bazy danych.
- `backend/app/schemas.py` - schematy Pydantic walidujące dane wejściowe i wyjściowe.
- `migrations/` - migracje Alembic utrzymujące wersję schematu bazy danych.
- `scripts/entrypoint.sh` - entrypoint kontenera uruchamiający opcjonalnie migracje przed startem API.
- `tests/` - testy integracyjne API uruchamiane przez pytest.

## Model danych

Główne encje:

- `Client` - klient firmy, dane kontaktowe i powiązana sesja trackingowa.
- `Inquiry` - zapytanie ofertowe klienta.
- `Offer` - oferta handlowa powiązana z zapytaniem.
- `ActivityLog` - zdarzenie aktywności na stronie, np. odsłona, kliknięcie CTA, wysłanie formularza.
- `Consent` - zgoda klienta na kontakt i analitykę.
- `User` - użytkownik panelu administracyjnego z rolą.
- `AuditLog` - dziennik operacji pracowników na danych CRM i danych osobowych.

Relacje:

- klient może mieć wiele zapytań;
- zapytanie może mieć wiele ofert;
- klient może mieć wiele zgód i logów aktywności;
- logi anonimowej sesji są przypisywane do klienta po wysłaniu formularza.

## Role użytkowników

- `admin` - pełny dostęp, zarządzanie użytkownikami, anonimizacja i eksport danych klienta.
- `sales` - praca operacyjna z klientami, zapytaniami i ofertami.
- `manager` - dostęp podglądowy do danych, analityki, zgód i eksportu danych.

## Najważniejsze przepływy

### Formularz kontaktowy

1. Użytkownik odwiedza stronę publiczną.
2. Skrypt trackingowy tworzy `session_id` i zapisuje zdarzenia aktywności.
3. Użytkownik wysyła formularz z wymaganą zgodą.
4. Backend tworzy lub aktualizuje klienta, zapisuje zapytanie i zgodę.
5. Anonimowe logi z tej samej sesji są przypisywane do klienta.

### Obsługa oferty

1. Pracownik loguje się do panelu administracyjnego.
2. Przegląda klientów i zapytania.
3. Tworzy ofertę dla wybranego zapytania.
4. Jeśli oferta ma status `sent`, status zapytania zmienia się na `offer_sent`.

### Zarządzanie CRM

1. Pracownik z rolą `admin` lub `sales` tworzy i aktualizuje klientów, zapytania oraz oferty.
2. Rola `manager` korzysta z widoków odczytu, analityki, historii klienta i eksportu danych.
3. Każda istotna operacja administracyjna zapisuje wpis w `AuditLog`.

### Start kontenera i migracje

1. Docker uruchamia `scripts/entrypoint.sh`.
2. Jeśli `RUN_MIGRATIONS=true`, entrypoint wykonuje `alembic upgrade head`.
3. Następnie uruchamiany jest `uvicorn`.
4. W produkcji zalecane jest `AUTO_CREATE_TABLES=false`, aby schemat bazy był zarządzany wyłącznie migracjami.

### RODO

System obsługuje:

- zapis zgody klienta;
- anonimizację danych osobowych klienta;
- dezaktywację zgód po anonimizacji;
- eksport danych klienta wraz z zapytaniami, ofertami, zgodami i logami aktywności.
- audit log eksportów, anonimizacji i zmian wykonywanych przez pracowników.

## Kluczowe endpointy API

| Metoda | Endpoint | Dostęp | Opis |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | publiczny | Logowanie i wydanie tokenu JWT |
| `GET` | `/auth/me` | zalogowany | Dane aktualnego użytkownika |
| `GET` | `/auth/users` | admin | Lista użytkowników panelu |
| `POST` | `/auth/users` | admin | Utworzenie użytkownika panelu |
| `PUT` | `/auth/users/{user_id}` | admin | Aktualizacja roli lub hasła użytkownika |
| `DELETE` | `/auth/users/{user_id}` | admin | Usunięcie użytkownika panelu |
| `GET` | `/clients` | admin, sales, manager | Lista klientów, paginacja i wyszukiwanie |
| `POST` | `/clients` | admin, sales | Utworzenie klienta |
| `GET` | `/clients/{client_id}` | admin, sales, manager | Szczegóły klienta |
| `PUT` | `/clients/{client_id}` | admin, sales | Aktualizacja klienta |
| `DELETE` | `/clients/{client_id}` | admin | Usunięcie klienta |
| `DELETE` | `/clients/{client_id}/anonymize` | admin | Anonimizacja klienta |
| `GET` | `/clients/{client_id}/export` | admin, manager | Eksport danych klienta |
| `GET` | `/clients/{client_id}/timeline` | admin, sales, manager | Historia klienta |
| `POST` | `/inquiries` | publiczny | Utworzenie zapytania z formularza |
| `GET` | `/inquiries` | admin, sales, manager | Lista zapytań |
| `POST` | `/inquiries/admin` | admin, sales | Utworzenie zapytania w panelu |
| `GET` | `/inquiries/{inquiry_id}` | admin, sales, manager | Szczegóły zapytania |
| `PUT` | `/inquiries/{inquiry_id}` | admin, sales | Aktualizacja zapytania |
| `DELETE` | `/inquiries/{inquiry_id}` | admin | Usunięcie zapytania |
| `POST` | `/offers` | admin, sales | Utworzenie oferty |
| `GET` | `/offers` | admin, sales, manager | Lista ofert |
| `GET` | `/offers/{offer_id}` | admin, sales, manager | Szczegóły oferty |
| `PUT` | `/offers/{offer_id}` | admin, sales | Aktualizacja oferty |
| `DELETE` | `/offers/{offer_id}` | admin | Usunięcie oferty |
| `GET` | `/analytics/kpi` | admin, manager | Wskaźniki KPI |
| `GET` | `/analytics/top-pages` | admin, manager | Najczęściej odwiedzane strony |
| `GET` | `/analytics/alerts` | admin, manager | Alerty operacyjne |
| `GET` | `/consents/client/{client_id}` | admin, manager | Zgody klienta |
| `PUT` | `/consents/{consent_id}` | admin, manager | Aktywacja lub dezaktywacja zgody |
| `POST` | `/tracking/event` | publiczny | Zapis zdarzenia trackingowego |
| `GET` | `/tracking/logs` | admin, manager | Lista logów aktywności |
| `GET` | `/audit/logs` | admin, manager | Lista operacji administracyjnych |

## Parametry list i filtrów

- `limit` i `offset` - paginacja list administracyjnych; limit domyślny to `100`, maksymalny `300`.
- `q` - wyszukiwanie klientów po nazwie, emailu lub telefonie w `/clients`.
- `status` - filtrowanie `/inquiries` oraz `/offers`.
- `event_type` i `client_id` - filtrowanie `/tracking/logs`.
- `action`, `entity_type`, `actor_login` - filtrowanie `/audit/logs`.

## Bezpieczeństwo

System stosuje:

- JWT dla panelu administracyjnego;
- role dostępu dla endpointów administracyjnych;
- limit nieudanych prób logowania;
- nagłówki bezpieczeństwa HTTP, w tym CSP, `X-Frame-Options`, `nosniff` i `Referrer-Policy`;
- walidację danych wejściowych przez Pydantic;
- ograniczenie rozmiaru danych trackingowych;
- escapowanie danych renderowanych w panelu administracyjnym.
- blokadę startu w trybie `production`, jeśli użyto domyślnych sekretów.

## Uruchamianie kontroli jakości

```bash
python -m pytest -q
ruff check .
```

## Ograniczenia MVP

System nie wysyła jeszcze automatycznych emaili do klientów, nie generuje PDF ofert i nie integruje się z zewnętrznym CRM/ERP. Eksport danych klienta jest dostępny jako odpowiedź JSON.
