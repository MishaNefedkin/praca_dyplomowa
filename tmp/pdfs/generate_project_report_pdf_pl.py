from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from generate_project_report_pdf import bullet as base_bullet
from generate_project_report_pdf import p as base_p
from generate_project_report_pdf import register_fonts, styles
from generate_project_report_pdf import table as base_table


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "construction_crm_analytics_raport_pl.pdf"

REPLACEMENTS = [
    ("Wartosc", "Wartość"),
    ("zapytan", "zapytań"),
    ("zarzadzania", "zarządzania"),
    ("aktywnosci", "aktywności"),
    ("klientow", "klientów"),
    ("uzytkownikow", "użytkowników"),
    ("uzytkownik", "użytkownik"),
    ("uzytkownika", "użytkownika"),
    ("obsluga", "obsługa"),
    ("obslugi", "obsługi"),
    ("obsludze", "obsłudze"),
    ("obsluguje", "obsługuje"),
    ("obslugiwane", "obsługiwane"),
    ("Krotkie", "Krótkie"),
    ("przeplyw", "przepływ"),
    ("wejscia", "wejścia"),
    ("strone", "stronę"),
    ("strona", "strona"),
    ("role", "role"),
    ("zgod", "zgód"),
    ("anonimizacje", "anonimizację"),
    ("podstawowa", "podstawową"),
    ("analityke", "analitykę"),
    ("siez", "się"),
    ("sklada", "składa"),
    ("statycznego", "statycznego"),
    ("autoryzacje", "autoryzację"),
    ("operacje", "operacje"),
    ("dziennik", "dziennik"),
    ("sciezki", "ścieżki"),
    ("pelnej", "pełnej"),
    ("dzialu", "działu"),
    ("sprzedazy", "sprzedaży"),
    ("dostepu", "dostępu"),
    ("dzialan", "działań"),
    ("Dodanie funkcji", "Dodanie funkcji"),
    ("uruchomienia", "uruchomienia"),
    ("laczenie", "łączenie"),
    ("laczy", "łączy"),
    ("publiczna", "publiczna"),
    ("aplikacja", "aplikacja"),
    ("warstwe", "warstwę"),
    ("przez", "przez"),
    ("odpowiedzialnosc", "odpowiedzialność"),
    ("Modele", "Modele"),
    ("opisujace", "opisujące"),
    ("Schematy", "Schematy"),
    ("utrzymujace", "utrzymujące"),
    ("uruchamiane", "uruchamiane"),
    ("imie", "imię"),
    ("data utworzenia", "data utworzenia"),
    ("Zgoda klienta", "Zgoda klienta"),
    ("Uzytkownik", "Użytkownik"),
    ("Dziennik", "Dziennik"),
    ("Uprawnienia", "Uprawnienia"),
    ("Pelny", "Pełny"),
    ("dostep", "dostęp"),
    ("tworzenie", "tworzenie"),
    ("usunie", "usunię"),
    ("Praca operacyjna", "Praca operacyjna"),
    ("Dostep", "Dostęp"),
    ("odczytowy", "odczytowy"),
    ("Srodowisko", "Środowisko"),
    ("srodowisku", "środowisku"),
    ("Zrealizowane", "Zrealizowane"),
    ("glowna", "główna"),
    ("uslugi", "usługi"),
    ("Rejestrowanie", "Rejestrowanie"),
    ("odslon", "odsłon"),
    ("klikniec", "kliknięć"),
    ("wyslania", "wysłania"),
    ("czasie", "czasie"),
    ("wyszukiwanie", "wyszukiwanie"),
    ("podglad", "podgląd"),
    ("szczegolow", "szczegółów"),
    ("tworzyc", "tworzyć"),
    ("zmieniac", "zmieniać"),
    ("hasla", "hasła"),
    ("ochrona", "ochroną"),
    ("ostatniego administratora", "ostatniego administratora"),
    ("aktywowac", "aktywować"),
    ("dezaktywacja", "dezaktywacja"),
    ("danych osobowych", "danych osobowych"),
    ("Najwazniejsze", "Najważniejsze"),
    ("Bezpieczenstwo", "Bezpieczeństwo"),
    ("Autoryzacja", "Autoryzacja"),
    ("dostep", "dostęp"),
    ("oparty", "oparty"),
    ("Hasla", "Hasła"),
    ("przechowywane", "przechowywane"),
    ("nieudanych logowan", "nieudanych logowań"),
    ("zdarzen", "zdarzeń"),
    ("Naglowki", "Nagłówki"),
    ("Blokada", "Blokada"),
    ("domyslnymi", "domyślnymi"),
    ("sekretami", "sekretami"),
    ("ochrone", "ochronę"),
    ("Uruchomienie", "Uruchomienie"),
    ("mozna", "można"),
    ("uzywany", "używany"),
    ("moze", "może"),
    ("wykonac", "wykonać"),
    ("Dokumentacja", "Dokumentacja"),
    ("Testy", "Testy"),
    ("jakosci", "jakości"),
    ("pokrywaja", "pokrywają"),
    ("autoryzacje", "autoryzację"),
    ("Scenariusz", "Scenariusz"),
    ("prezentacji", "prezentacji"),
    ("promotorowi", "promotorowi"),
    ("Otworzyc", "Otworzyć"),
    ("pokazac", "pokazać"),
    ("Wyslac", "Wysłać"),
    ("zaznaczona", "zaznaczoną"),
    ("Zalogowac", "Zalogować"),
    ("Ograniczenia", "Ograniczenia"),
    ("dalszy rozwoj", "dalszy rozwój"),
    ("glowny", "główny"),
    ("czesc", "część"),
    ("zostala", "została"),
    ("rozszerzenia", "rozszerzenia"),
    ("powiadomienia", "powiadomienia"),
    ("Bardziej", "Bardziej"),
    ("rozbudowane", "rozbudowane"),
    ("wykresy", "wykresy"),
    ("okresowe", "okresowe"),
    ("pelniejsze", "pełniejsze"),
    ("zewnetrznymi", "zewnętrznymi"),
    ("Podsumowanie", "Podsumowanie"),
    ("implementacje", "implementację"),
    ("tez", "też"),
    ("zrozumienie", "zrozumienie"),
    ("pozyskanie", "pozyskanie"),
    ("przygotowanie", "przygotowanie"),
    ("kontrole", "kontrolę"),
    ("zachowania", "zachowania"),
    ("zaprezentowac", "zaprezentować"),
    ("baze", "bazę"),
    ("gotowa", "gotową"),
]


def pl(text: str) -> str:
    for source, target in REPLACEMENTS:
        text = text.replace(source, target)
    return text


def p(text: str, style):
    return base_p(pl(text), style)


def bullet(items: list[str], style):
    return base_bullet([pl(item) for item in items], style)


def table(rows: list[list[str]], col_widths: list[float], s):
    return base_table([[pl(cell) for cell in row] for row in rows], col_widths, s)


def footer_pl(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("DejaVuSans", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(1.6 * cm, 1.0 * cm, "Construction CRM Analytics - raport projektu")
    canvas.drawRightString(21 * cm - 1.6 * cm, 1.0 * cm, f"Strona {doc.page}")
    canvas.restoreState()


def build_story() -> list:
    s = styles()
    story: list = []

    story.append(Spacer(1, 1.2 * cm))
    story.append(p("Construction CRM Analytics", s["title"]))
    story.append(
        p(
            "System internetowy dla firmy budowlanej: strona publiczna, zbieranie zapytan, panel CRM, "
            "analiza aktywnosci klientow, role uzytkownikow, obsluga RODO/GDPR oraz audit log.",
            s["subtitle"],
        )
    )
    story.append(Spacer(1, 0.35 * cm))
    story.append(
        table(
            [
                ["Parametr", "Wartosc"],
                ["Typ projektu", "MVP systemu webowego do zarzadzania klientami firmy budowlanej"],
                ["Backend", "Python, FastAPI, SQLAlchemy, Alembic, Pydantic, JWT"],
                ["Frontend", "HTML, CSS, JavaScript bez frameworka"],
                ["Baza danych", "PostgreSQL w Docker Compose, SQLite lokalnie i w testach"],
                ["Infrastruktura", "Docker, Docker Compose, GitHub Actions CI, Ruff, Pytest"],
            ],
            [4.0 * cm, 12.2 * cm],
            s,
        )
    )
    story.append(Spacer(1, 0.45 * cm))
    story.append(p("Krotkie streszczenie dla promotora", s["h2"]))
    story.append(
        p(
            "Projekt pokazuje kompletny przeplyw biznesowy: od wejscia uzytkownika na strone firmy "
            "budowlanej, przez tracking i formularz kontaktowy, az do obslugi klienta w panelu CRM. "
            "System zawiera role uzytkownikow, audit log, obsluge zgod RODO, anonimizacje danych, "
            "eksport danych klienta i podstawowa analityke.",
            s["body"],
        )
    )
    story.append(PageBreak())

    story.append(p("1. Cel projektu", s["h1"]))
    story.append(
        p(
            "Celem projektu jest stworzenie praktycznego systemu wspierajacego firme budowlana w obsludze "
            "klientow oraz analizie aktywnosci uzytkownikow na stronie internetowej. Aplikacja laczy publiczna "
            "strone firmy, panel CRM dla pracownikow oraz warstwe analityczna.",
            s["body"],
        )
    )
    story.append(
        bullet(
            [
                "Pokazanie pelnej sciezki klienta: wejscie na strone, tracking, formularz, utworzenie zapytania.",
                "Automatyzacja podstawowej pracy dzialu sprzedazy z klientami, zapytaniami i ofertami.",
                "Wdrozenie rol dostepu i kontroli dzialan administracyjnych.",
                "Dodanie funkcji RODO/GDPR: zgody, eksport danych i anonimizacja.",
                "Przygotowanie projektu do uruchomienia przez Docker z migracjami bazy danych.",
            ],
            s["body"],
        )
    )

    story.append(p("2. Architektura systemu", s["h1"]))
    story.append(
        p(
            "System sklada sie ze statycznego frontendu, backendu FastAPI oraz bazy danych. Backend obsluguje "
            "REST API, autoryzacje, operacje CRM, tracking, analityke oraz dziennik audytu.",
            s["body"],
        )
    )
    story.append(
        p(
            "Uzytkownik strony -> tracking.js i formularz kontaktowy -> FastAPI API -> PostgreSQL/SQLite -> panel administracyjny",
            s["code"],
        )
    )
    story.append(
        table(
            [
                ["Warstwa", "Odpowiedzialnosc"],
                ["frontend/", "Strona publiczna, strony uslug/projektow, tracking.js, panel administracyjny"],
                ["backend/app/routers/", "Endpointy API: auth, clients, inquiries, offers, tracking, analytics, consents, audit"],
                ["backend/app/models.py", "Modele SQLAlchemy opisujace tabele bazy danych"],
                ["backend/app/schemas.py", "Schematy Pydantic i walidacja danych"],
                ["migrations/", "Migracje Alembic utrzymujace schemat bazy danych"],
                ["tests/", "Testy integracyjne API uruchamiane przez Pytest"],
            ],
            [4.1 * cm, 12.1 * cm],
            s,
        )
    )

    story.append(p("3. Model danych", s["h1"]))
    story.append(
        table(
            [
                ["Encja", "Opis"],
                ["Client", "Klient firmy: imie/nazwa, email, telefon, session_id, data utworzenia"],
                ["Inquiry", "Zapytanie klienta ze statusami new, in_progress, offer_sent, closed"],
                ["Offer", "Oferta handlowa ze statusami draft, sent, accepted, rejected"],
                ["ActivityLog", "Zdarzenia aktywnosci: page_view, page_leave, cta_click, form_interaction, form_submit"],
                ["Consent", "Zgoda klienta na kontakt i analityke"],
                ["User", "Uzytkownik panelu administracyjnego z rola admin, sales albo manager"],
                ["AuditLog", "Dziennik operacji pracownikow na danych CRM i danych osobowych"],
            ],
            [4.0 * cm, 12.2 * cm],
            s,
        )
    )

    story.append(p("4. Role uzytkownikow", s["h1"]))
    story.append(
        table(
            [
                ["Rola", "Uprawnienia"],
                [
                    "admin",
                    "Pelny dostep: uzytkownicy, klienci, zapytania, oferty, usuwanie, anonimizacja, eksport, audit log.",
                ],
                [
                    "sales",
                    "Praca operacyjna: tworzenie i aktualizacja klientow, zapytan oraz ofert, zmiana statusow.",
                ],
                [
                    "manager",
                    "Dostep odczytowy do CRM, analityki, audit log, zgod i eksportow bez zmian danych CRM.",
                ],
            ],
            [3.0 * cm, 13.2 * cm],
            s,
        )
    )

    story.append(p("5. Zrealizowane funkcje", s["h1"]))
    features = [
        ("Strona publiczna", "Strona glowna, uslugi, projekty, formularz kontaktowy i zgoda na przetwarzanie danych."),
        ("Tracking", "Rejestrowanie odslon, klikniec CTA, interakcji z formularzem, wyslania formularza i czasu na stronie."),
        ("CRM klientow", "Lista, wyszukiwanie, tworzenie, edycja, timeline, eksport, anonimizacja i usuwanie klientow."),
        ("Zapytania", "Lista, filtrowanie po statusie, tworzenie, zmiana statusu, podglad szczegolow i usuwanie."),
        ("Oferty", "Lista, filtrowanie po statusie, tworzenie, zmiana statusu, podglad szczegolow i usuwanie."),
        (
            "Uzytkownicy",
            "Admin moze tworzyc uzytkownikow, zmieniac role/hasla i usuwac konta z ochrona ostatniego administratora.",
        ),
        (
            "RODO/GDPR",
            "Zgody, aktywacja/dezaktywacja zgod, eksport danych klienta i anonimizacja danych osobowych.",
        ),
        (
            "Audit log",
            "Zapisywanie operacji: client.create/update/delete/export/anonymize, inquiry.*, offer.*, user.*, consent.update.",
        ),
        ("Analityka", "KPI, top pages, aktywnosc z 24h, konwersja inquiry -> offer, alerty starych zapytan."),
    ]
    for title, description in features:
        story.append(p(title, s["h2"]))
        story.append(p(description, s["body"]))

    story.append(PageBreak())

    story.append(p("6. Najwazniejsze endpointy API", s["h1"]))
    story.append(
        table(
            [
                ["Grupa", "Endpointy"],
                ["Auth", "POST /auth/login; GET /auth/me; GET/POST /auth/users; PUT/DELETE /auth/users/{user_id}"],
                [
                    "Clients",
                    "GET/POST /clients; GET/PUT/DELETE /clients/{client_id}; DELETE /clients/{client_id}/anonymize; GET /clients/{client_id}/export; GET /clients/{client_id}/timeline",
                ],
                ["Inquiries", "GET/POST /inquiries; POST /inquiries/admin; GET/PUT/DELETE /inquiries/{inquiry_id}"],
                ["Offers", "GET/POST /offers; GET/PUT/DELETE /offers/{offer_id}"],
                ["Consents", "GET /consents/client/{client_id}; PUT /consents/{consent_id}"],
                ["Tracking", "POST /tracking/event; GET /tracking/logs"],
                ["Analytics", "GET /analytics/kpi; GET /analytics/top-pages; GET /analytics/alerts"],
                ["Audit", "GET /audit/logs"],
            ],
            [3.0 * cm, 13.2 * cm],
            s,
        )
    )

    story.append(p("7. Bezpieczenstwo", s["h1"]))
    story.append(
        bullet(
            [
                "Autoryzacja JWT dla panelu administracyjnego.",
                "Dostep oparty o role: admin, sales, manager.",
                "Hasla przechowywane jako hashe bcrypt.",
                "Rate limiting dla nieudanych logowan i zdarzen trackingowych.",
                "Walidacja danych przez Pydantic.",
                "Naglowki bezpieczenstwa: CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy.",
                "Blokada startu produkcyjnego z domyslnymi sekretami.",
                "Audit log operacji na danych CRM i danych osobowych.",
                "Funkcje RODO/GDPR: zgody, eksport i anonimizacja.",
            ],
            s["body"],
        )
    )

    story.append(p("8. Docker, migracje i uruchomienie", s["h1"]))
    story.append(
        p(
            "Projekt mozna uruchomic przez Docker Compose. W konfiguracji kontenerowej uzywany jest PostgreSQL. "
            "Przed startem API entrypoint moze wykonac migracje Alembic.",
            s["body"],
        )
    )
    story.append(
        p(
            "cp .env.example .env\n"
            "docker compose up --build\n\n"
            "Strona publiczna: http://localhost:8000/\n"
            "Panel admin: http://localhost:8000/admin\n"
            "Dokumentacja API: http://localhost:8000/docs",
            s["code"],
        )
    )
    story.append(
        bullet(
            [
                "RUN_MIGRATIONS=true uruchamia alembic upgrade head przed uvicorn.",
                "AUTO_CREATE_TABLES=false oznacza, ze schemat bazy jest zarzadzany migracjami.",
                "SEED_SAMPLE_DATA mozna wylaczyc w srodowisku produkcyjnym.",
            ],
            s["body"],
        )
    )

    story.append(p("9. Testy i kontrola jakosci", s["h1"]))
    story.append(
        p(
            "Testy automatyczne pokrywaja autoryzacje, role, operacje CRM, tracking, laczenie session_id z klientem, "
            "audit log, anonimizacje, eksport danych, wyszukiwanie, paginacje, zarzadzanie uzytkownikami oraz nowe endpointy CRUD.",
            s["body"],
        )
    )
    story.append(
        table(
            [
                ["Sprawdzenie", "Wynik"],
                ["pytest", "29 passed"],
                ["ruff check .", "passed"],
                ["node --check frontend/admin.js", "passed"],
                ["sh -n scripts/entrypoint.sh", "passed"],
                ["docker compose config", "passed"],
            ],
            [6.0 * cm, 10.2 * cm],
            s,
        )
    )

    story.append(p("10. Scenariusz prezentacji promotorowi", s["h1"]))
    story.append(
        bullet(
            [
                "Otworzyc strone publiczna i pokazac strone glowna, uslugi, projekty oraz formularz kontaktowy.",
                "Wyslac testowe zapytanie z zaznaczona zgoda na przetwarzanie danych.",
                "Zalogowac sie do /admin jako admin i pokazac dashboard z KPI, top pages i alertami.",
                "Otworzyc klientow: znalezc utworzonego klienta, pokazac timeline, zgody i eksport JSON.",
                "Pokazac zapytania i oferty: filtry, utworzenie oferty i zmiane statusow.",
                "Pokazac RODO/GDPR: dezaktywacje zgody, eksport danych i anonimizacje klienta.",
                "Pokazac audit log, w ktorym widac operacje administracyjne.",
                "Otworzyc /docs i pokazac automatycznie wygenerowana dokumentacje FastAPI.",
            ],
            s["body"],
        )
    )

    story.append(p("11. Ograniczenia MVP i dalszy rozwoj", s["h1"]))
    story.append(
        p(
            "Projekt jest MVP: realizuje glowny proces biznesowy, ale czesc funkcji zostala zaplanowana jako dalsze rozszerzenia.",
            s["body"],
        )
    )
    story.append(
        bullet(
            [
                "Automatyczne powiadomienia email do klienta i managera.",
                "Generowanie PDF ofert i dokumentow handlowych.",
                "Bardziej rozbudowane wykresy analityczne i raporty okresowe.",
                "Redis dla produkcyjnego rate limiting w wielu procesach/kontenerach.",
                "Refresh tokens, logout/revocation i pelniejsze zarzadzanie sesjami.",
                "Testy e2e panelu administracyjnego.",
                "Integracje z zewnetrznymi systemami CRM/ERP.",
            ],
            s["body"],
        )
    )

    story.append(p("12. Podsumowanie", s["h1"]))
    story.append(
        p(
            "Construction CRM Analytics pokazuje nie tylko implementacje backendu i frontendu, ale tez zrozumienie "
            "realnego procesu biznesowego firmy budowlanej: pozyskanie klienta, obsluge zapytania, przygotowanie oferty, "
            "kontrole rol, analityke zachowania, audit operacji i ochrone danych osobowych. Projekt mozna zaprezentowac "
            "jako kompletna baze systemu gotowa do dalszego rozwoju.",
            s["body"],
        )
    )
    return story


def main() -> None:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=(21 * cm, 29.7 * cm),
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.55 * cm,
        title="Construction CRM Analytics - raport po polsku",
        author="Codex",
    )
    doc.build(build_story(), onFirstPage=footer_pl, onLaterPages=footer_pl)
    print(OUTPUT)


if __name__ == "__main__":
    main()
