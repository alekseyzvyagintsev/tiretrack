# Архитектурная спецификация
## Проект «Обработка QR-кодов»

**Версия:** 1.0  
**Дата:** 20 сентября 2026  
**Статус:** Согласовано

---

## 1. Технологический стек

| Слой | Технология | Версия | Обоснование |
|------|------------|--------|-------------|
| Backend | Python + Django | Python ≥ 3.11, Django ≥ 4.2 LTS | Серверная логика, ORM, маршрутизация, шаблоны |
| Frontend | Django Templates + HTMX | HTMX ≥ 1.9 | Серверный рендеринг, AJAX без SPA-фреймворка |
| База данных | PostgreSQL | ≥ 14 | Реляционная БД, транзакции, `SELECT ... FOR UPDATE` для FIFO |
| Внешняя интеграция | `nechestniy_znak` | Реализовано | Библиотека запроса к «Честному знаку» |
| QR-рендеринг | `qrcode` (Python) | — | Генерация DataMatrix-изображения для карточки кода |
| CSS-фреймворк | Bootstrap 5 | — | Базовые стили, модальные окна, адаптив |
| WSGI-сервер | gunicorn | — | Продакшн-раздача |

### Что НЕ используется

- REST API / DRF — не требуется, нет внешних потребителей
- SPA-фреймворки (React, Vue) — избыточны для внутреннего складского инструмента
- WebSocket — загрузка файла обрабатывается через polling статуса
- Celery / Redis — загрузка синхронная в рамках одного HTTP-запроса (MVP)

---

## 2. Архитектурный паттерн

### 2.1. Общая схема

```
┌──────────────────────────────────────────────────┐
│                    Браузер                        │
│  Django Templates (HTML) + HTMX (AJAX-фрагменты) │
└──────────────────────┬───────────────────────────┘
                       │ HTTP (form submit / HTMX)
┌──────────────────────▼───────────────────────────┐
│              Django (views.py)                     │
│  ┌─────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ Формы   │ │ Модели   │ │ Бизнес-логика      │  │
│  │ (forms) │ │ (models) │ │ (services.py)      │  │
│  └─────────┘ └──────────┘ └────────────────────┘  │
└──────────────────────┬───────────────────────────┘
                       │ ORM / psycopg2
┌──────────────────────▼───────────────────────────┐
│              PostgreSQL                            │
└──────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│        nechestniy_znak (HTTP → Честный знак)       │
└──────────────────────────────────────────────────┘
```

### 2.2. Слои приложения

| Слой | Расположение | Ответственность |
|------|-------------|-----------------|
| **Presentation** | `views.py`, `templates/` | Приём HTTP-запросов, валидация форм, рендеринг шаблонов, возврат HTMX-фрагментов |
| **Service** | `services.py` | Бизнес-логика: проведение документа (FIFO, атомарность), загрузка кодов, нумерация, дедупликация |
| **Data** | `models.py` | ORM-модели, валидация на уровне БД (`unique_together`, `constraints`), миграции |
| **Integration** | `integrations/` | Обёртка над `nechestniy_znak`, изоляция внешнего API |

### 2.3. Принцип разделения

- **Views** не содержат бизнес-логику — вызывают методы `services.py`
- **Services** не знают про HTTP — работают с моделями и возвращают результат/ошибку
- **Models** описывают только данные и простые валидации (`clean()`)
- **Транзакции** (`@transaction.atomic`) — в `services.py`, не в views

---

## 3. Организация Django-приложений

### 3.1. Структура проекта

```
qr_project/
├── qr_project/           # Настройки Django (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                 # Пользователи, площадки, склады, поставщики
│   ├── models.py         # User, Platform, Warehouse, Supplier
│   ├── views.py
│   ├── admin.py
│   └── migrations/
├── nomenclature/         # Номенклатура и коды
│   ├── models.py         # TireNomenclature, TireCode
│   ├── services.py       # Загрузка, парсинг, дедупликация
│   ├── views.py
│   ├── admin.py
│   └── migrations/
├── documents/            # Документы списания/выкупа
│   ├── models.py         # Document, DocumentItem
│   ├── services.py       # Проведение, распроведение, нумерация
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   └── migrations/
├── integrations/         # Внешние интеграции
│   └── honest_sign.py    # Обёртка над nechestniy_znak
├── templates/            # Общие шаблоны
│   ├── base.html
│   ├── core/
│   ├── nomenclature/
│   └── documents/
└── static/
    ├── css/
    └── js/
        └── htmx.min.js
```

### 3.2. Назначение приложений

| Приложение | Модели | Шаблоны | URL-префикс |
|-----------|--------|---------|-------------|
| `core` | User, Platform, Warehouse, Supplier | login, user_list, user_form | `/users/` |
| `nomenclature` | TireNomenclature, TireCode | upload_form, upload_report, code_card | `/codes/` |
| `documents` | Document, DocumentItem | doc_list, doc_form, doc_detail, code_display | `/documents/` |

---

## 4. Шаблоны и HTMX

### 4.1. Базовый шаблон

`base.html` — общий каркас: навбар, блоки `content`, `scripts`, `styles`. Bootstrap 5.

### 4.2. HTMX-паттерны

| Действие | HTMX-атрибут | Что возвращает view |
|----------|-------------|---------------------|
| Поиск номенклатуры | `hx-get="/codes/nomenclature/search/?q=..."` | HTML-фрагмент `<option>`-списка |
| Добавление строки | `hx-post="/documents/{id}/items/add/"` | HTML-фрагмент строки таблицы |
| Удаление строки | `hx-delete="/documents/{id}/items/{item_id}/"` | Пустой ответ + `hx-swap="delete"` |
| Счётчики кодов | `hx-get="/documents/{id}/counters/"` | HTML-фрагмент с числами |
| Экранное отображение | `hx-get="/documents/{id}/codes/"` | HTML-фрагмент модального окна |
| Карточка кода | `hx-get="/codes/{id}/card/"` | HTML-фрагмент модального окна |
| Автосохранение черновика | `hx-post="/documents/{id}/autosave/"` + `hx-trigger="mouseleave"` | JSON-ответ |

### 4.3. Принципы

- HTMX-запросы возвращают **HTML-фрагменты**, не JSON — рендеринг на сервере
- Сервер определяет тип ответа по заголовку `HX-Request: true` → отдаёт фрагмент, иначе — полную страницу
- Модальные окна — Bootstrap 5 `modal`, контент подгружается через HTMX
- CSRF-токен передаётся через `htmx` config (`hx-headers`)

---

## 5. База данных

### 5.1. СУБД

PostgreSQL — единственная БД. SQLite допустим только для локальной разработки.

### 5.2. Транзакции и блокировки

| Операция | Уровень изоляции | Блокировка | Обоснование |
|----------|-----------------|------------|-------------|
| Проведение документа | `SERIALIZABLE` (через `@transaction.atomic`) | `SELECT ... FOR UPDATE` на TireCode | FIFO + атомарность (БП 6) |
| Загрузка кодов | `READ COMMITTED` | `unique` на `qr_code` | Дедупликация на уровне БД (БП 3) |
| Присвоение номера | `READ COMMITTED` | `SELECT FOR UPDATE` на счётчике | Сквозная нумерация (БП 16) |

### 5.3. Индексы

| Модель | Поле/комбинация | Тип | Назначение |
|--------|----------------|-----|------------|
| TireCode | `qr_code` | Unique | Дедупликация |
| TireNomenclature | `(brand, model, size)` | Unique | Авто-создание номенклатуры |
| DocumentItem | `(document, nomenclature)` | Unique | Запрет дубликатов в документе |
| TireCode | `(nomenclature, warehouse, is_active, created_at)` | B-tree | FIFO-выборка при проведении |
| Document | `(source_platform, status)` | B-tree | Фильтрация списка документов |
| Document | `number` | Unique | Уникальность нумерации |

---

## 6. Аутентификация и авторизация

### 6.1. Аутентификация

Стандартная Django-аутентификация (`django.contrib.auth`). Расширенная модель User с полями `platform` и `role`.

### 6.2. Авторизация

Проверка прав — в `views.py` через декораторы / миксины:

| Роль | Декоратор | Права |
|------|-----------|-------|
| `manager` | `@role_required('manager')` | Все документы своей площадки (чтение + запись); чужие — только чтение |
| `storekeeper` | `@role_required('storekeeper')` | Только свои документы; списание с любой площадки |
| Аноним | — | Редирект на `/login/` |

Дополнительно — per-object проверка в `views.py`: сравнение `request.user.platform` с `document.source_platform` / `document.writeoff_platform`.

---

## 7. Загрузка файла — технические детали

### 7.1. Flow

```
POST /codes/upload/  (form: файл + warehouse_id)
  │
  ├── Создание UploadSession (status=processing)
  │
  ├── Для каждой строки файла:
  │   ├── TireCode.objects.filter(qr_code=line).exists() → пропуск (дубликат)
  │   ├── nechestniy_znak.get_info(line) → при ошибке: пропуск (ошибка ЧЗ)
  │   ├── parse_attributes(response) → при неполных: пропуск (нераспознанный)
  │   ├── TireNomenclature.get_or_create(brand, model, size)
  │   └── TireCode.create(...)
  │
  ├── Сохранение отчёта в UploadSession
  └── Redirect → /codes/upload/{session_id}/report/
```

### 7.2. Ограничения MVP

- Синхронная обработка (в рамках HTTP-запроса)
- Файл — текстовый, по коду на строку
- Таймаут на запрос к «Честному знаку» — настраивается в `settings.py`
- Размер файла — без жёсткого лимита (MVP), но рекомендация ≤ 5000 строк

### 7.3. Отчёт о загрузке

Хранится в БД (модель `UploadSession` или в логе). Содержит:
- `total_lines` — всего строк
- `created` — создано кодов
- `duplicates` — пропущено дубликатов
- `unrecognized` — пропущено нераспознанных
- `honest_sign_errors` — пропущено по ошибке ЧЗ
- `details` — JSON-массив `{code, reason}` для пропущенных

---

## 8. Логирование

| Уровень | Что логируется | Куда |
|---------|---------------|------|
| `INFO` | Загрузка файла (старт, конец, сводка) | Django logging → файл |
| `WARNING` | Пропуск кода (дубликат / нераспознанный / ошибка ЧЗ) | Django logging → файл |
| `ERROR` | Ошибка транзакции при проведении | Django logging → файл + сообщение пользователю |
| `DEBUG` | Детали парсинга, FIFO-выборка | Django logging (только при `DEBUG=True`) |

---

## 9. Развёртывание

### 9.1. Окружения

| Окружение | БД | DEBUG | Назначение |
|-----------|-----|-------|------------|
| `dev` | SQLite или локальная PostgreSQL | True | Локальная разработка |
| `staging` | PostgreSQL | False | Тестирование перед продакшеном |
| `prod` | PostgreSQL | False | Рабочее окружение |

### 9.2. Prod-конфигурация

- WSGI: gunicorn (`--workers 3 --bind 0.0.0.0:8000`)
- Статика: `collectstatic` → nginx
- Миграции: `python manage.py migrate` при деплое
- Секреты: через переменные окружения (`.env`)

### 9.3. Переменные окружения (prod)

```
DEBUG=False
SECRET_KEY=<generate>
DATABASE_URL=postgres://user:pass@host:5432/qr_db
HONEST_SIGN_TIMEOUT=30
ALLOWED_HOSTS=...
```

---

## 10. Соглашения по коду

| Аспект | Конвенция |
|--------|-----------|
| Именование моделей | PascalCase, без префикса `Tire` в коде (только в артефактах для ясности) |
| Именование полей | snake_case |
| Именование URL | kebab-case, trailing slash |
| Именование шаблонов | snake_case, в подпапках по приложению |
| Сервисный слой | Методы в `services.py`, возвращают `ServiceResult` (data + errors) |
| Транзакции | `@transaction.atomic` в сервисном слое, не в views |
| Комментарии | На русском, только для нетривиальной бизнес-логики |

---

## 11. Соответствие артефактам

| Артефакт | Где учтён в архитектуре |
|----------|------------------------|
| Модели данных (Раздел 4) | `models.py` по приложениям (Раздел 3.1) |
| Бизнес-правила 1, 2, 3 | `nomenclature/services.py` — загрузка кодов |
| Бизнес-правило 6 | `documents/services.py` — `@transaction.atomic` + `FOR UPDATE` |
| Бизнес-правило 7 | `documents/services.py` — FIFO через `order_by('created_at', 'id')` |
| Бизнес-правило 15 | `documents/views.py` — AJAX endpoint добавления строки |
| Бизнес-правило 16 | `documents/services.py` — генерация номера при сохранении |
| Статусная модель (Раздел 3) | `documents/services.py` — переходы между статусами |
| URL-маршруты (Карта URL) | `urls.py` по приложениям |
| AJAX-контракты | HTMX-фрагменты (Раздел 4.2) |

---

## 12. Не вошедшее в MVP

| Отложено | Влияние на архитектуру |
|----------|----------------------|
| API-интеграция с 1С | Архитектура допускает добавление `api/` приложения с DRF в будущем |
| Печать кодов на А4 | Потребует `weasyprint` или `reportlab`, шаблон A4 |
| Вторая площадка «Софийская Легковой» | Модель `Platform` уже поддерживает множественность |
| Автоматический маппинг владелец → склад | Потребует справочник маппингов + периодический импорт |
| Celery для фоновой загрузки | Структура `services.py` готова к выносу в task |
