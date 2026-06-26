from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "construction_crm_analytics_report.pdf"
FONT_DIR = Path(
    "/Users/mykhailonefedkin/.cache/codex-runtimes/codex-primary-runtime/dependencies/"
    "native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype"
)


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSansMono", str(FONT_DIR / "DejaVuSansMono.ttf")))


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleCustom",
            parent=sample["Title"],
            fontName="DejaVuSans-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCustom",
            parent=sample["BodyText"],
            fontName="DejaVuSans",
            fontSize=11.5,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "Heading1Custom",
            parent=sample["Heading1"],
            fontName="DejaVuSans-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#111827"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "Heading2Custom",
            parent=sample["Heading2"],
            fontName="DejaVuSans-Bold",
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor("#374151"),
            spaceBefore=8,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=sample["BodyText"],
            fontName="DejaVuSans",
            fontSize=9.4,
            leading=13.2,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "SmallCustom",
            parent=sample["BodyText"],
            fontName="DejaVuSans",
            fontSize=8.2,
            leading=11.5,
            textColor=colors.HexColor("#4b5563"),
        ),
        "code": ParagraphStyle(
            "CodeCustom",
            parent=sample["Code"],
            fontName="DejaVuSansMono",
            fontSize=8.1,
            leading=10.8,
            textColor=colors.HexColor("#111827"),
            backColor=colors.HexColor("#f3f4f6"),
            borderPadding=5,
            spaceAfter=6,
        ),
        "table": ParagraphStyle(
            "TableCustom",
            parent=sample["BodyText"],
            fontName="DejaVuSans",
            fontSize=8.2,
            leading=10.8,
            textColor=colors.HexColor("#1f2937"),
        ),
        "table_head": ParagraphStyle(
            "TableHeadCustom",
            parent=sample["BodyText"],
            fontName="DejaVuSans-Bold",
            fontSize=8.3,
            leading=10.8,
            textColor=colors.white,
        ),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def bullet(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=8) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=14,
        bulletFontName="DejaVuSans",
        bulletFontSize=7,
        spaceAfter=6,
    )


def table(rows: list[list[str]], col_widths: list[float], s: dict[str, ParagraphStyle]) -> Table:
    data = []
    for row_index, row in enumerate(rows):
        style = s["table_head"] if row_index == 0 else s["table"]
        data.append([Paragraph(cell, style) for cell in row])
    result = Table(data, colWidths=col_widths, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return result


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("DejaVuSans", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(1.6 * cm, 1.0 * cm, "Construction CRM Analytics - отчет по проекту")
    canvas.drawRightString(A4[0] - 1.6 * cm, 1.0 * cm, f"Страница {doc.page}")
    canvas.restoreState()


def build_story() -> list:
    s = styles()
    story: list = []

    story.append(Spacer(1, 1.3 * cm))
    story.append(p("Construction CRM Analytics", s["title"]))
    story.append(
        p(
            "Веб-система для строительной компании: публичный сайт, сбор заявок, CRM-панель, "
            "аналитика активности клиентов, роли пользователей, RODO/GDPR и audit log.",
            s["subtitle"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        table(
            [
                ["Параметр", "Значение"],
                ["Тип проекта", "MVP веб-системы для управления клиентами строительной компании"],
                ["Backend", "Python, FastAPI, SQLAlchemy, Alembic, Pydantic, JWT"],
                ["Frontend", "HTML, CSS, JavaScript без фреймворка"],
                ["База данных", "PostgreSQL в Docker Compose, SQLite для локального режима и тестов"],
                ["Инфраструктура", "Docker, Docker Compose, GitHub Actions CI, Ruff, Pytest"],
            ],
            [4.0 * cm, 12.2 * cm],
            s,
        )
    )
    story.append(Spacer(1, 0.45 * cm))
    story.append(p("<b>Короткое польское резюме для промотора</b>", s["h2"]))
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

    story.append(p("1. Цель проекта", s["h1"]))
    story.append(
        p(
            "Цель проекта - создать практическую систему, которая помогает строительной компании "
            "управлять обращениями клиентов и анализировать активность пользователей на сайте. "
            "Проект объединяет публичную витрину компании, CRM для сотрудников и аналитический слой.",
            s["body"],
        )
    )
    story.append(
        bullet(
            [
                "Показать полный путь клиента: посещение сайта, tracking, отправка формы, создание заявки.",
                "Автоматизировать базовую работу отдела продаж с клиентами, заявками и офертами.",
                "Реализовать роли доступа и административный контроль действий сотрудников.",
                "Добавить функции RODO/GDPR: согласия, экспорт данных и анонимизация.",
                "Подготовить проект к запуску через Docker с миграциями базы данных.",
            ],
            s["body"],
        )
    )

    story.append(p("2. Архитектура", s["h1"]))
    story.append(
        p(
            "Система состоит из статического frontend, FastAPI backend и базы данных. Backend обслуживает "
            "REST API, авторизацию, CRM-операции, tracking, аналитику и audit log.",
            s["body"],
        )
    )
    story.append(
        p(
            "Поток данных: пользователь сайта -> tracking.js и форма контакта -> FastAPI API -> "
            "PostgreSQL/SQLite -> административная панель.",
            s["code"],
        )
    )
    story.append(
        table(
            [
                ["Слой", "Ответственность"],
                ["frontend/", "Публичный сайт, страницы услуг/проектов, tracking.js, admin panel"],
                ["backend/app/routers/", "Endpoint'ы API: auth, clients, inquiries, offers, tracking, analytics, consents, audit"],
                ["backend/app/models.py", "SQLAlchemy-модели таблиц базы данных"],
                ["backend/app/schemas.py", "Pydantic-схемы и валидация данных"],
                ["migrations/", "Alembic-миграции схемы базы данных"],
                ["tests/", "Интеграционные API-тесты"],
            ],
            [4.1 * cm, 12.1 * cm],
            s,
        )
    )

    story.append(p("3. Модель данных", s["h1"]))
    story.append(
        table(
            [
                ["Сущность", "Назначение"],
                ["Client", "Клиент компании: имя, email, телефон, session_id, дата создания"],
                ["Inquiry", "Заявка клиента со статусами new, in_progress, offer_sent, closed"],
                ["Offer", "Коммерческая оферта со статусами draft, sent, accepted, rejected"],
                ["ActivityLog", "События активности: page_view, page_leave, cta_click, form_interaction, form_submit"],
                ["Consent", "Согласие клиента на обработку данных и аналитику"],
                ["User", "Пользователь admin panel с ролью admin, sales или manager"],
                ["AuditLog", "Журнал действий сотрудников над CRM и персональными данными"],
            ],
            [4.0 * cm, 12.2 * cm],
            s,
        )
    )

    story.append(p("4. Роли пользователей", s["h1"]))
    story.append(
        table(
            [
                ["Роль", "Возможности"],
                [
                    "admin",
                    "Полный доступ: пользователи, клиенты, заявки, оферты, удаления, анонимизация, экспорт, audit log.",
                ],
                [
                    "sales",
                    "Операционная работа: создание и обновление клиентов, заявок и оферт, изменение статусов.",
                ],
                [
                    "manager",
                    "Просмотр CRM-данных, аналитики, audit log, согласий и экспортов без изменения CRM.",
                ],
            ],
            [3.0 * cm, 13.2 * cm],
            s,
        )
    )

    story.append(p("5. Реализованные функции", s["h1"]))
    features = [
        ("Публичный сайт", "Главная страница, услуги, проекты, форма контакта и согласие на обработку данных."),
        (
            "Tracking",
            "Система фиксирует просмотры страниц, клики CTA, взаимодействие с формой, отправку формы и время на странице.",
        ),
        (
            "CRM клиентов",
            "Просмотр, поиск, создание, редактирование, timeline, экспорт, анонимизация и удаление клиентов.",
        ),
        ("Заявки", "Список, фильтр по статусу, создание, изменение статуса, просмотр детали и удаление."),
        ("Оферты", "Список, фильтр по статусу, создание, изменение статуса, просмотр детали и удаление."),
        (
            "Пользователи",
            "Admin может создавать пользователей, менять роль/пароль и удалять пользователей с защитой последнего admin.",
        ),
        (
            "RODO/GDPR",
            "Согласия, активация/деактивация согласий, экспорт данных клиента и анонимизация персональных данных.",
        ),
        (
            "Audit log",
            "Запись действий: client.create/update/delete/export/anonymize, inquiry.*, offer.*, user.*, consent.update.",
        ),
        ("Аналитика", "KPI, top pages, activity за 24 часа, конверсия inquiry -> offer, alert'ы старых заявок."),
    ]
    for title, description in features:
        story.append(KeepTogether([p(title, s["h2"]), p(description, s["body"])]))

    story.append(PageBreak())
    story.append(p("6. API endpoint'ы", s["h1"]))
    story.append(
        table(
            [
                ["Группа", "Endpoint'ы"],
                ["Auth", "POST /auth/login; GET /auth/me; GET/POST /auth/users; PUT/DELETE /auth/users/{user_id}"],
                [
                    "Clients",
                    "GET/POST /clients; GET/PUT/DELETE /clients/{client_id}; DELETE /clients/{client_id}/anonymize; GET /clients/{client_id}/export; GET /clients/{client_id}/timeline",
                ],
                [
                    "Inquiries",
                    "GET/POST /inquiries; POST /inquiries/admin; GET/PUT/DELETE /inquiries/{inquiry_id}",
                ],
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

    story.append(p("7. Безопасность", s["h1"]))
    story.append(
        bullet(
            [
                "JWT-авторизация для административной панели.",
                "Ролевой доступ: admin, sales, manager.",
                "Хеширование паролей через bcrypt.",
                "Rate limiting для неудачных попыток логина и tracking-событий.",
                "Валидация входных данных через Pydantic.",
                "HTTP security headers: CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy.",
                "Запрет production-запуска с дефолтными секретами.",
                "Audit log операций с CRM и персональными данными.",
                "RODO/GDPR-функции: согласия, экспорт и анонимизация.",
            ],
            s["body"],
        )
    )

    story.append(p("8. Docker, миграции и запуск", s["h1"]))
    story.append(
        p(
            "Проект запускается через Docker Compose. В контейнерной конфигурации используется PostgreSQL. "
            "Перед стартом API entrypoint может выполнить Alembic-миграции.",
            s["body"],
        )
    )
    story.append(
        p(
            "cp .env.example .env\n"
            "docker compose up --build\n\n"
            "Public site: http://localhost:8000/\n"
            "Admin panel: http://localhost:8000/admin\n"
            "API docs: http://localhost:8000/docs",
            s["code"],
        )
    )
    story.append(
        bullet(
            [
                "RUN_MIGRATIONS=true запускает alembic upgrade head перед uvicorn.",
                "AUTO_CREATE_TABLES=false делает миграции главным способом управления схемой.",
                "SEED_SAMPLE_DATA можно отключить для production.",
            ],
            s["body"],
        )
    )

    story.append(p("9. Тестирование и качество", s["h1"]))
    story.append(
        p(
            "Автоматические тесты покрывают авторизацию, роли, CRM-операции, tracking, связывание session_id, "
            "audit log, анонимизацию, экспорт данных, поиск, пагинацию, управление пользователями и новые CRUD endpoint'ы.",
            s["body"],
        )
    )
    story.append(
        table(
            [
                ["Проверка", "Результат"],
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

    story.append(p("10. Сценарий демонстрации промотору", s["h1"]))
    story.append(
        bullet(
            [
                "Открыть публичный сайт и показать главную страницу, услуги, проекты и форму контакта.",
                "Отправить тестовую заявку с согласием на обработку данных.",
                "Войти в /admin как admin и показать dashboard с KPI, top pages и alert'ами.",
                "Открыть клиентов: найти созданного клиента, показать timeline, согласия и экспорт JSON.",
                "Показать заявки и оферты: фильтры, создание оферты и изменение статусов.",
                "Показать RODO/GDPR: деактивация согласия, экспорт данных, анонимизация клиента.",
                "Показать audit log, где видны административные операции.",
                "Открыть /docs и показать автоматически сгенерированную документацию FastAPI.",
            ],
            s["body"],
        )
    )

    story.append(p("11. Ограничения MVP и дальнейшее развитие", s["h1"]))
    story.append(
        p(
            "Проект является MVP: он закрывает основной бизнес-процесс, но оставляет часть функций как будущие расширения.",
            s["body"],
        )
    )
    story.append(
        bullet(
            [
                "Email-уведомления клиенту и менеджеру после отправки формы.",
                "Генерация PDF-оферт и печатных коммерческих документов.",
                "Более развитые графики аналитики и отчеты по периодам.",
                "Redis для production rate limiting в нескольких процессах/контейнерах.",
                "Refresh tokens, logout/revocation и расширенное управление сессиями.",
                "Frontend e2e-тесты административной панели.",
                "Интеграции с внешними CRM/ERP.",
            ],
            s["body"],
        )
    )

    story.append(p("12. Итог", s["h1"]))
    story.append(
        p(
            "Construction CRM Analytics демонстрирует не только разработку backend и frontend, но и понимание "
            "реального бизнес-процесса строительной компании: привлечение клиента, обработка заявки, подготовка "
            "оферты, контроль ролей, аналитика поведения, аудит операций и защита персональных данных. "
            "Проект можно показать как законченную базовую систему, готовую к дальнейшему развитию.",
            s["body"],
        )
    )

    return story


def main() -> None:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.55 * cm,
        title="Construction CRM Analytics - отчет по проекту",
        author="Codex",
    )
    doc.build(build_story(), onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
