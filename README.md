# TireTrack — Система управления шинами и QR-кодами

## Описание

TireTrack — полнофункциональная система управления грузовыми шинами с интеграцией "Честный Знак". Система поддерживает загрузку DataMatrix-кодов, складской документооборот и аналитику.

### Основные возможности

**Загрузка QR-кодов:**
- Импорт из файлов (.txt) и ручное введение
- Интеграция с Честным Знаком через `infoFromDataMatrix()`
- Автоматическое создание номенклатуры
- Отчёты о загрузке (создано, дубликаты, ошибки)

**Складской документооборот:**
- Документы списания (СП-ГГГГ-NNNNNN) и выкупа (ВК-ГГГГ-NNNNNN)
- Статусы: draft → saved → posted
- Проведение с FIFO (First In, First Out)
- Экранное отображение кодов документов
- Карточки кодов с DataMatrix

**Аналитика:**
- Дашборд с счётчиками кодов и документов
- Поиск номенклатуры через AJAX
- API для получения количества активных кодов

**Управление:**
- Роли: Manager (начальник), Storekeeper (кладовщик)
- Площадки (Platform) и склады
- Поставщики и номенклатура

## Технологии

- **Backend:** Django 4.2, Python 3.14
- **Database:** PostgreSQL
- **Task Queue:** Celery + Redis
- **Frontend:** HTMX, Bootstrap 5, Font Awesome
- **QR:** qrcode, Pillow, nechestniy_znak (Честный Знак)
- **Deployment:** Docker, Docker Compose

## Технологии

- Django 4.2
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- HTMX для динамических интерфейсов
- Docker и Docker Compose
- Bootstrap 5 для UI
- Font Awesome для иконок

## Структура проекта

```
tiretrack/
├── tiretrack/              # Основной проект Django
│   ├── settings.py          # Конфигурация
│   ├── urls.py             # URL маршруты
│   └── celery_worker.py    # Celery worker
├── users/                  # Пользователи (email-based auth)
│   ├── models.py          # User с platform и role
│   └── views.py           # Login, logout
├── tires/                  # Управление шинами
│   ├── models.py          # Platform, Warehouse, TireNomenclature, TireCode
│   ├── services.py        # UploadService для загрузки QR
│   ├── views.py           # CRUD шин, складов, поставщиков
│   └── utils.py           # search_tire_nomenclature()
├── warehouse/              # Складской документооборот
│   ├── models.py          # DocType, Document, DocumentItem
│   ├── services.py        # DocumentService (создание, проведение, FIFO)
│   ├── views.py           # CRUD документов, AJAX endpoints
│   └── forms.py           # Формы документов
├── qr_processing/          # Обработка QR-кодов
│   ├── views.py           # Импорт файлов
│   ├── services.py        # UploadReport
│   └── models.py          # FileImport, ExportBatch
├── integrations/           # Интеграции
│   └── honest_sign.py     # HonestSignClient (infoFromDataMatrix)
├── DOCUMENTATION/          # Документация
│   ├── User_Guide_v1.0.md # Руководство пользователя
│   ├── Work_Breakdown_v2.0.md
│   └── ...
├── templates/              # HTML templates
├── static/                 # CSS, JS
├── manage.py
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## Быстрый старт

### 1. Установка

```bash
git clone <repository-url>
cd tiretrack
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка

Создайте `.env` файл:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/tiretrack
REDIS_URL=redis://localhost:6379/0
USE_MOCK_HONEST_SIGN=True  # Для разработки без Честного Знака
```

### 3. Инициализация базы

```bash
python manage.py migrate
python manage.py seed_platform  # Создаёт тестовую площадку
python manage.py createsuperuser
```

### 4. Запуск

```bash
# Terminal 1 - Django server
python manage.py runserver

# Terminal 2 - Celery worker
celery -A tiretrack worker --loglevel=info
```

### 5. Доступ

- **Django:** http://localhost:8000/
- **Admin:** http://localhost:8000/admin/
- **Warehouse:** http://localhost:8000/warehouse/
- **QR Import:** http://localhost:8000/qr/imports/

## Документация

- 📖 [Руководство пользователя](DOCUMENTATION/User_Guide_v1.0.md) — полное руководство
- 📊 [Work Breakdown v2.0](DOCUMENTATION/Work_Breakdown_v2.0.md) — план миграции
- 🏗️ [Architecture Spec](DOCUMENTATION/Architecture_Spec_v1.0.md) — архитектура системы

## Тестирование

```bash
# Все тесты
python manage.py test

# Тесты по приложениям
python manage.py test warehouse.tests_document_service
python manage.py test warehouse.tests_posting
python manage.py test warehouse.tests_views
python manage.py test warehouse.tests_ajax
python manage.py test tires.tests
python manage.py test qr_processing.tests
python manage.py test qr_processing.tests_upload_service

# Проверка проекта
python manage.py check
```

**Статистика тестов:** 113 тестов, все проходят ✅

## URL маршруты

### Warehouse (склад)

**Документы:**
- `GET /warehouse/` — Дашборд
- `GET /warehouse/documents/` — Список документов
- `GET /warehouse/documents/new/` — Создание документа
- `GET /warehouse/documents/<id>/` — Детальный просмотр
- `POST /warehouse/documents/<id>/save/` — Сохранение черновика
- `POST /warehouse/documents/<id>/post/` — Проведение
- `POST /warehouse/documents/<id>/unpost/` — Распроведение
- `POST /warehouse/documents/<id>/delete/` — Пометка на удаление
- `GET /warehouse/documents/<id>/codes/` — Экран кодов

**AJAX endpoints:**
- `GET /warehouse/api/nomenclature/search/` — Поиск номенклатуры
- `POST /warehouse/documents/<id>/add-item/` — Добавление строки
- `POST /warehouse/documents/<id>/items/<item_id>/update/` — Обновление количества
- `POST /warehouse/documents/<id>/items/<item_id>/delete/` — Удаление строки
- `POST /warehouse/documents/<id>/autosave/` — Автосохранение
- `GET /warehouse/api/counters-api/` — Счётчики активных кодов

**Карточки:**
- `GET /warehouse/codes/<code_id>/card/` — Карточка кода с DataMatrix

### Tires (управление шинами)
- `GET /tires/` — Список TireCode
- `GET /tires/search/` — Поиск номенклатуры
- `GET /tires/warehouses/` — Список складов
- `GET /tires/suppliers/` — Список поставщиков

### QR Processing
- `GET /qr/imports/` — Импорт QR-кодов
- `GET /qr/imports/report/<id>/` — Отчёт о загрузке
- `GET /qr/exports/` — Список экспортов

## Разработка

### Тесты

```bash
python manage.py test
```

**113 тестов по приложениям:**
- `warehouse.tests_document_service` — 9 тестов (создание, сохранение, проведение)
- `warehouse.tests_posting` — 9 тестов (FIFO, atomic, concurrent)
- `warehouse.tests_views` — 15 тестов (homepage, document_codes, code_card)
- `warehouse.tests_ajax` — 18 тестов (nomenclature_search, add_item, update_item)
- `tires.tests` — 20 тестов (TireNomenclature, TireCode)
- `qr_processing.tests` — 11 тестов (FileImport, ExportBatch)
- `qr_processing.tests_upload_service` — 13 тестов (UploadService, HonestSignClient)
- `users.tests` — 18 тестов (auth, views)

### Миграции

```bash
# Создание миграций
python manage.py makemigrations tires warehouse

# Применение
python manage.py migrate

# Проверка
python manage.py makemigrations --check
```

### Новые модели (v2.0)

**tires.models:**
- `Platform` — Площадка (unique name)
- `Warehouse` — Склад (с привязкой к площадке)
- `Supplier` — Поставщик
- `TireNomenclature` — Номенклатура (brand, model, size)
- `TireCode` — Код DataMatrix (qr_code, nomenclature, warehouse, document)

**warehouse.models:**
- `DocType` — Тип документа (writeoff/buyout, prefix)
- `Document` — Документ (doc_type, number, status, author)
- `DocumentItem` — Позиция документа (FK на nomenclature)

**users.models:**
- `User` — Пользователь (email-based, platform, role)

### Интеграция с Честным Знаком

```python
from integrations.honest_sign import HonestSignClient

client = HonestSignClient()
result = client.get_code_info("00000046209849Uon<TYfACyAJPHJ")
# result = {"brand": "...", "model": "...", "size": "..."}
```

Для разработки без Честного Знака:
```bash
export USE_MOCK_HONEST_SIGN=True
```

## Лицензия

MIT

## Автор и поддержка

**Разработчик**: Alexey Zvyagintsev
**Email**: alex0236889@gmail.com
**GitHub**: https://github.com/alekseyzvyagintsev/tiretrack

---

**Версия:** v2.0 (TireCode, новые модели документов)
**Дата:** 2026-09-22
**Тестов:** 113 ✅
