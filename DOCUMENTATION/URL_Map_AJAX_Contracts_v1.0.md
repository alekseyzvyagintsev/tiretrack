# Карта URL и AJAX-контракты
## Проект «Обработка QR-кодов» — Django + Templates

Версия 1.0 — от 20 сентября 2026

---

## 1. Карта экранов

### 1.1. Дерево экранов и переходов

```
/login/                          — Страница входа
│
└──/ (dashboard)                — Главная (после авторизации)
   │
   ├──/upload/                  — Загрузка файла с кодами
   │  └──/upload/report/<id>/   — Отчёт о загрузке
   │
   ├──/documents/               — Список документов (с фильтрами)
   │  │
   │  ├──/documents/create/     — Создание документа (черновик)
   │  │  └──/documents/<id>/    — Редактирование / просмотр документа
   │  │     ├──/documents/<id>/codes/  — Экранное отображение кодов (AJAX-модал)
   │  │     └──/codes/<code_id>/        — Карточка кода (AJAX-модал)
   │  │
   │  └──/nomenclature/search/  — Поиск номенклатуры (AJAX)
   │
   └──/users/                   — Управление пользователями (только manager)
      ├──/users/create/         — Создание пользователя
      └──/users/<id>/edit/      — Редактирование пользователя
```

### 1.2. Матрица экранов по ролям

| Экран                    | Manager (своя площадка) | Manager (чужая площадка) | Storekeeper | Шаблон                    |
|--------------------------|:---:|:---:|:---:|---------------------------|
| Dashboard                | ✅ Полный | ✅ Полный | ✅ Полный | `dashboard.html`          |
| Загрузка кодов           | ✅ | ❌ | ✅ | `upload/form.html`        |
| Отчёт о загрузке         | ✅ | ❌ | ✅ | `upload/report.html`     |
| Список документов        | ✅ Все своей площадки | ✅ Только чтение чужих | ✅ Только свои | `documents/list.html`     |
| Создание документа       | ✅ | ❌ | ✅ | `documents/form.html`     |
| Редактирование документа | ✅ | ❌ Только чтение | ✅ Только свой | `documents/form.html`     |
| Экранное отображение кодов | ✅ | ✅ Только чтение | ✅ Только свой проведённый | `documents/codes_modal.html` |
| Карточка кода            | ✅ | ✅ Только чтение | ✅ | `codes/card_modal.html`  |
| Управление пользователями | ✅ | ❌ | ❌ | `users/list.html`         |

---

## 2. Таблица URL-маршрутов

### 2.1. Стандартные маршруты (form submit → redirect)

| #  | URL                              | Метод  | View                       | Шаблон                  | Права              | US     |
|----|----------------------------------|--------|----------------------------|-------------------------|--------------------|--------|
| R1 | `/login/`                        | GET/POST | `LoginView`              | `login.html`            | Аноним             | —      |
| R2 | `/logout/`                       | POST    | `LogoutView`              | —                       | Авторизованный      | —      |
| R3 | `/`                              | GET     | `DashboardView`           | `dashboard.html`        | Любой авторизов.   | US-25–28 |
| R4 | `/upload/`                       | GET/POST | `UploadFormView`         | `upload/form.html`      | manager, storekeeper | US-01 |
| R5 | `/upload/process/`               | POST   | `UploadProcessView`       | redirect → R6           | manager, storekeeper | US-01–09 |
| R6 | `/upload/report/<upload_id>/`    | GET    | `UploadReportView`        | `upload/report.html`    | manager, storekeeper | US-09 |
| R7 | `/documents/`                    | GET    | `DocumentListView`        | `documents/list.html`   | Любой авторизов.   | US-20 |
| R8 | `/documents/create/`             | GET    | `DocumentCreateView`      | `documents/form.html`   | manager, storekeeper | US-10 |
| R9 | `/documents/<doc_id>/`           | GET/POST | `DocumentDetailView`    | `documents/form.html`   | По правилам R11–R12 | US-10–20 |
| R10| `/documents/<doc_id>/save/`      | POST   | `DocumentSaveView`        | redirect → R9            | author или manager | US-11 |
| R11| `/documents/<doc_id>/post/`      | POST   | `DocumentPostView`        | redirect → R9            | author или manager | US-12–13 |
| R12| `/documents/<doc_id>/unpost/`    | POST   | `DocumentUnpostView`      | redirect → R9            | author или manager | US-14 |
| R13| `/documents/<doc_id>/delete/`    | POST   | `DocumentDeleteView`      | redirect → R7            | author или manager | US-15 |
| R14| `/documents/<doc_id>/cancel/`    | POST   | `DocumentCancelView`      | redirect → R7            | author              | US-10 |
| R15| `/users/`                        | GET    | `UserListView`            | `users/list.html`       | manager            | US-28 |
| R16| `/users/create/`                 | GET/POST | `UserCreateView`         | `users/form.html`       | manager            | US-28 |
| R17| `/users/<user_id>/edit/`         | GET/POST | `UserEditView`           | `users/form.html`       | manager            | US-28 |

### 2.2. AJAX-маршруты (возвращают JSON)

| #  | URL                                         | Метод | View                        | Возвращает | Права              | US     |
|----|---------------------------------------------|-------|-----------------------------|------------|--------------------|--------|
| A1 | `/nomenclature/search/`                    | GET   | `NomenclatureSearchView`   | JSON       | manager, storekeeper | US-10 |
| A2 | `/documents/<doc_id>/items/add/`            | POST  | `DocumentItemAddView`      | JSON       | author или manager | US-10,15 |
| A3 | `/documents/<doc_id>/items/<item_id>/update/` | POST | `DocumentItemUpdateView`  | JSON       | author или manager | US-11 |
| A4 | `/documents/<doc_id>/items/<item_id>/remove/` | POST | `DocumentItemRemoveView`  | JSON       | author или manager | US-11 |
| A5 | `/documents/<doc_id>/counters/`              | GET   | `DocumentCountersView`     | JSON       | author или manager | US-21 |
| A6 | `/documents/<doc_id>/codes/`                | GET   | `DocumentCodesView`        | JSON       | author, manager (свои/чужие — чтение) | US-22 |
| A7 | `/codes/<code_id>/`                         | GET   | `CodeCardView`             | JSON       | author, manager (свои/чужие — чтение) | US-23 |
| A8 | `/documents/<doc_id>/autosave/`              | POST  | `DocumentAutosaveView`    | JSON       | author              | US-16 |
| A9 | `/upload/status/<upload_id>/`               | GET   | `UploadStatusView`         | JSON       | manager, storekeeper | US-09 |

---

## 3. Контракты AJAX-endpoint-ов

### A1. Поиск номенклатуры

**URL:** `/nomenclature/search/`
**Метод:** `GET`
**US:** US-10 (добавление строки в документ)

**Параметры запроса:**

| Параметр | Тип    | Обязательный | Описание                    |
|----------|--------|:---:|-----------------------------|
| `q`      | string | ✅  | Строка поиска (≥ 2 символа)  |
| `warehouse_id` | int | ❌  | ID склада-источника (для фильтрации по наличию) |

**Успешный ответ (200):**

```json
{
  "results": [
    {
      "id": 42,
      "brand": "Pirelli",
      "model": "Cinturato P7",
      "size": "205/55 R15",
      "product_name": "Шина легковая Pirelli Cinturato P7 205/55 R15",
      "active_count": 17
    }
  ],
  "total": 1
}
```

**Поля ответа:**

| Поле           | Тип    | Описание                                   |
|----------------|--------|--------------------------------------------|
| `id`           | int    | ID номенклатуры (TireNomenclature.id)       |
| `brand`        | string | Производитель                              |
| `model`        | string | Модель                                     |
| `size`         | string | Размер                                     |
| `product_name` | string | Наименование или fallback (brand + model + size) |
| `active_count` | int    | Кол-во активных кодов на складе-источнике (если `warehouse_id` передан) |

**Ошибки:**

| Код | Условие              | Тело ответа                              |
|-----|----------------------|------------------------------------------|
| 400 | `q` короче 2 символов | `{"error": "Минимум 2 символа"}`         |
| 403 | Не авторизован       | `{"error": "Доступ запрещён"}`           |

**Логика поиска:** `brand__icontains` OR `model__icontains` OR `size__icontains` OR `product_name__icontains`. Только `is_active=True`. Лимит — 20 результатов.

---

### A2. Добавление строки в документ

**URL:** `/documents/<doc_id>/items/add/`
**Метод:** `POST`
**US:** US-10, US-15 (дубликаты номенклатуры)

**Тело запроса:**

```json
{
  "nomenclature_id": 42
}
```

**Успешный ответ — новая строка (201):**

```json
{
  "status": "created",
  "item": {
    "id": 101,
    "nomenclature_id": 42,
    "nomenclature_label": "Pirelli Cinturato P7 205/55 R15",
    "quantity": 1
  }
}
```

**Успешный ответ — дубликат (200, бизнес-правило 15):**

```json
{
  "status": "duplicate",
  "item": {
    "id": 57,
    "nomenclature_id": 42,
    "nomenclature_label": "Pirelli Cinturato P7 205/55 R15",
    "quantity": 3
  }
}
```

> При `status: "duplicate"` фронтенд подсвечивает существующую строку в таблице и обновляет в ней quantity.

**Ошибки:**

| Код | Условие                          | Тело ответа                                  |
|-----|----------------------------------|----------------------------------------------|
| 400 | `nomenclature_id` не передан     | `{"error": "Не указана номенклатура"}`       |
| 404 | Документ или номенклатура не найдена | `{"error": "Не найдено"}`                 |
| 403 | Нет прав на документ             | `{"error": "Доступ запрещён"}`               |
| 409 | Документ в статусе `posted`      | `{"error": "Документ проведён, редактирование запрещено"}` |

---

### A3. Обновление количества в строке

**URL:** `/documents/<doc_id>/items/<item_id>/update/`
**Метод:** `POST`
**US:** US-11

**Тело запроса:**

```json
{
  "quantity": 5
}
```

**Успешный ответ (200):**

```json
{
  "status": "updated",
  "item": {
    "id": 57,
    "nomenclature_id": 42,
    "quantity": 5
  }
}
```

**Ошибки:**

| Код | Условие                          | Тело ответа                                  |
|-----|----------------------------------|----------------------------------------------|
| 400 | `quantity` ≤ 0 или не число       | `{"error": "Количество должно быть ≥ 1"}`    |
| 409 | Документ в статусе `posted`      | `{"error": "Документ проведён, редактирование запрещено"}` |

---

### A4. Удаление строки из документа

**URL:** `/documents/<doc_id>/items/<item_id>/remove/`
**Метод:** `POST`
**US:** US-11

**Тело запроса:** — (пустое)

**Успешный ответ (200):**

```json
{
  "status": "removed",
  "item_id": 57
}
```

**Ошибки:**

| Код | Условие                          | Тело ответа                                  |
|-----|----------------------------------|----------------------------------------------|
| 404 | Строка не найдена                | `{"error": "Строка не найдена"}`             |
| 409 | Документ в статусе `posted`      | `{"error": "Документ проведён, редактирование запрещено"}` |

---

### A5. Получение счётчиков активных кодов

**URL:** `/documents/<doc_id>/counters/`
**Метод:** `GET`
**US:** US-21

**Параметры запроса:** нет (склад-источник берётся из документа)

**Успешный ответ (200):**

```json
{
  "document_id": 15,
  "source_warehouse_id": 3,
  "source_warehouse_name": "Софийская Груз — Основной",
  "counters": [
    {
      "nomenclature_id": 42,
      "nomenclature_label": "Pirelli Cinturato P7 205/55 R15",
      "active_count": 17,
      "requested_count": 5
    },
    {
      "nomenclature_id": 88,
      "nomenclature_label": "Michelin Primacy 4 225/45 R17",
      "active_count": 3,
      "requested_count": 5,
      "warning": "Недостаточно кодов"
    }
  ]
}
```

**Поля ответа:**

| Поле               | Тип | Описание                                            |
|--------------------|-----|----------------------------------------------------|
| `active_count`     | int | Кол-во активных кодов по номенклатуре на складе-источнике |
| `requested_count`  | int | Запрошенное количество в строке документа           |
| `warning`          | string | Опционально. `"Недостаточно кодов"` если `requested > active` |

**Логика:** `TireCode.objects.filter(warehouse=source_warehouse, nomenclature=item.nomenclature, is_active=True, is_used=False).count()`

---

### A6. Экранное отображение кодов

**URL:** `/documents/<doc_id>/codes/`
**Метод:** `GET`
**US:** US-22

**Параметры запроса:**

| Параметр | Тип | Обязательный | Описание                    |
|---------|-----|:---:|-----------------------------|
| `page`  | int | ❌  | Номер страницы (по умолч. 1) |

**Успешный ответ (200):**

```json
{
  "document_id": 15,
  "document_number": "СП-2026-000012",
  "codes": [
    {
      "id": 501,
      "qr_code": "0104620012345678
21 ABC123",
      "qr_code_lines": ["0104620012345678", "21 ABC123"],
      "nomenclature_label": "Pirelli Cinturato P7 205/55 R15",
      "nomenclature_id": 42,
      "used_at": "2026-09-20T14:30:00+03:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

**Ошибки:**

| Код | Условие                              | Тело ответа                                    |
|-----|--------------------------------------|------------------------------------------------|
| 403 | Нет прав                             | `{"error": "Доступ запрещён"}`                 |
| 409 | Документ не в статусе `posted`       | `{"error": "Коды доступны только после проведения документа"}` |

**Логика:** Только если `document.status == 'posted'`. Возвращает коды, где `TireCode.document == doc_id`. `qr_code` разбивается на строки по `\n` для отображения в две строки в карточке.

---

### A7. Карточка кода

**URL:** `/codes/<code_id>/`
**Метод:** `GET`
**US:** US-23

**Параметры запроса:** нет

**Успешный ответ (200):**

```json
{
  "id": 501,
  "qr_code": "0104620012345678
21 ABC123",
  "qr_code_lines": ["0104620012345678", "21 ABC123"],
  "nomenclature": {
    "id": 42,
    "brand": "Pirelli",
    "model": "Cinturato P7",
    "size": "205/55 R15",
    "product_name": "Шина легковая Pirelli Cinturato P7 205/55 R15"
  },
  "warehouse": {
    "id": 3,
    "name": "Софийская Груз — Основной"
  },
  "is_active": false,
  "is_used": true,
  "used_at": "2026-09-20T14:30:00+03:00",
  "created_at": "2026-09-15T09:00:00+03:00",
  "honest_sign_data": { "...": "..." }
}
```

**Ошибки:**

| Код | Условие              | Тело ответа                    |
|-----|----------------------|--------------------------------|
| 403 | Нет прав на код      | `{"error": "Доступ запрещён"}` |
| 404 | Код не найден        | `{"error": "Код не найден"}`   |

**Права доступа:**
- Manager: доступ к кодам своей площадки (чужие — только если код привязан к документу, который manager может читать)
- Storekeeper: доступ только к кодам своих документов

---

### A8. Автосохранение черновика

**URL:** `/documents/<doc_id>/autosave/`
**Метод:** `POST`
**US:** US-16

**Тело запроса:**

```json
{
  "items": [
    {"nomenclature_id": 42, "quantity": 5},
    {"nomenclature_id": 88, "quantity": 3}
  ]
}
```

**Успешный ответ (200):**

```json
{
  "status": "autosaved",
  "document_id": 15,
  "saved_at": "2026-09-20T14:25:00+03:00"
}
```

**Ошибки:**

| Код | Условие                          | Тело ответа                                  |
|-----|----------------------------------|----------------------------------------------|
| 403 | Не автор документа                | `{"error": "Доступ запрещён"}`               |
| 409 | Документ не в статусе `draft`/`saved` | `{"error": "Автосохранение недоступно"}` |

**Логика:** Работает только для `status in ('draft', 'saved')`. Перезаписывает состав строк документа (удаляет отсутствующие, обновляет количества, добавляет новые). Не меняет статус документа. Триггер: фронтенд отправляет при `beforeunload` или по таймеру (каждые 30 сек при наличии изменений).

---

### A9. Статус загрузки файла

**URL:** `/upload/status/<upload_id>/`
**Метод:** `GET`
**US:** US-09

**Параметры запроса:** нет

**Успешный ответ — в процессе (200):**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "total": 500,
    "processed": 342,
    "created": 310,
    "skipped_duplicate": 20,
    "skipped_unrecognized": 8,
    "skipped_honest_sign_error": 4
  }
}
```

**Успешный ответ — завершено (200):**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": {
    "total": 500,
    "processed": 500,
    "created": 468,
    "skipped_duplicate": 20,
    "skipped_unrecognized": 8,
    "skipped_honest_sign_error": 4
  },
  "report_url": "/upload/report/550e8400-e29b-41d4-a716-446655440000"
}
```

**Ошибки:**

| Код | Условие            | Тело ответа                          |
|-----|--------------------|--------------------------------------|
| 404 | Сессия не найдена  | `{"error": "Сессия загрузки не найдена"}` |

**Логика:** Фронтенд опрашивает (polling) каждые 2 секунды. После `status: "completed"` — редирект на `report_url`.

---

## 4. Детализация стандартных маршрутов

### R4–R5. Загрузка файла с кодами

**R4: `/upload/` (GET)**
- Рендерит форму: выбор склада (select) + выбор файла (input file)
- Склады фильтруются по площадке пользователя
- Для storekeeper — только склады своей площадки
- Для manager — все склады своей площадки

**R5: `/upload/process/` (POST)**
- Принимает: `warehouse_id` (int), `file` (UploadedFile)
- Валидация: файл передан, warehouse_id принадлежит площадке пользователя
- Создаёт `UploadSession` (id, warehouse, user, status, timestamps)
- Запускает фоновую обработку (Celery task или sequential в view для MVP)
- Редирект на `/upload/report/<upload_id>/`
- Если обработка асинхронная — редирект на промежуточную страницу с polling A9

**R6: `/upload/report/<upload_id>/` (GET)**
- Рендерит `upload/report.html`
- Передаёт в контекст:
  - `summary`: {total, created, skipped_duplicate, skipped_unrecognized, skipped_honest_sign_error}
  - `skipped_codes`: список [{qr_code, reason, reason_label}]
  - `warehouse_name`

### R8–R9. Создание и редактирование документа

**R8: `/documents/create/` (GET)**
- Создаёт документ в статусе `draft` (без номера, без строк)
- Рендерит `documents/form.html` с пустой формой
- `doc_type` передаётся через query param: `?type=writeoff` или `?type=buyout`
- Поля, заполняемые автоматически:
  - `author` = request.user
  - `source_platform` = request.user.platform
  - `source_warehouse` = основной склад площадки пользователя (для списания — выбор, для выкупа — автоматически)
  - `writeoff_platform` = source_platform (по умолчанию, меняется при списании с чужой площадки)

**R9: `/documents/<doc_id>/` (GET)**
- Рендерит `documents/form.html`
- Передаёт в контекст:
  - `document` — объект документа со всеми полями
  - `items` — список строк с номенклатурой
  - `can_edit` — bool, зависит от статуса и прав
  - `can_post` — bool, статус `saved` + есть права
  - `can_unpost` — bool, статус `posted` + есть права
  - `can_delete` — bool, есть права
  - `can_view_codes` — bool, статус `posted` + есть права

**Кнопки по статусам (рендерятся в шаблоне):**

| Статус | Кнопки | AJAX-вызовы |
|--------|--------|------------|
| `draft` | «Добавить строку» (A1+A2), «Сохранить» (R10), «Отменить» (R14) | A8 (автосохранение) |
| `saved` | «Добавить строку» (A1+A2), «Сохранить» (R10), «Провести» (R11), «Пометить на удаление» (R13) | A3, A4 (редактирование строк) |
| `posted` | «Распровести» (R12), «Экранное отображение кодов» (A6) | A6, A7 |
| `marked_deleted` | Только просмотр | — |

### R10. `/documents/<doc_id>/save/` (POST)
- Присваивает номер (если `draft` → `saved`, бизнес-правило 16)
- Формат: СП-ГГГГ-NNNNNN или ВК-ГГГГ-NNNNNN
- Переписывает состав строк из POST-данных формы
- Редирект на R9

### R11. `/documents/<doc_id>/post/` (POST)
- Атомарная транзакция:
  1. Для каждой строки: проверка остатка активных кодов
  2. Если нехватка — возврат с ошибкой (HTTP 400 + сообщение)
  3. FIFO-выбор кодов → `is_used=True`, `is_active=False`, `document=doc`
  4. Обновление счётчиков
  5. `status='posted'`, `posted_at=now()`
- Успех — редирект на R9
- Ошибка — редирект на R9 с сообщением об ошибке (django.contrib.messages)

### R12. `/documents/<doc_id>/unpost/` (POST)
- Откат: `is_used=False`, `is_active=True`, `document=None`, `used_at=None`
- Восстановление счётчиков
- `status='saved'`, `posted_at=None`
- Редирект на R9

### R13. `/documents/<doc_id>/delete/` (POST)
- Если `posted` — сначала распроведение (как R12)
- `is_deleted=True`, `status='marked_deleted'`
- Редирект на R7

### R14. `/documents/<doc_id>/cancel/` (POST)
- Только для `draft`
- Удаляет документ (физически, т.к. номер не присвоен)
- Редирект на R7

### R7. `/documents/` (GET) — список с фильтрами

**Query параметры:**

| Параметр           | Тип | Описание                                      |
|--------------------|-----|-----------------------------------------------|
| `status`           | string | Фильтр по статусу: `saved`, `posted`, `marked_deleted` |
| `doc_type`         | string | Фильтр по типу: `writeoff`, `buyout`          |
| `source_platform`  | int  | Фильтр по площадке-источнику документа        |
| `writeoff_platform`| int  | Фильтр по площадке-источнику списания          |
| `page`             | int  | Пагинация (по умолчанию 1, 20 на страницу)     |

**Логика фильтрации по ролям:**
- **Manager:** видит документы своей `source_platform` + чужие `source_platform` (только чтение, без кнопок редактирования)
- **Storekeeper:** видит только документы, где `author == request.user`
- Фильтр `writeoff_platform` доступен всем — для поиска списаний с конкретной площадки

---

## 5. Оформление (CSRF, форматы, конвенции)

### CSRF-токен
Все POST-запросы (как form submit, так и AJAX) требуют CSRF-токен.
- Form submit: `{% csrf_token %}` в шаблоне
- AJAX: передача `X-CSRFToken` в заголовке (читается из cookie `csrftoken`)

### Content-Type
- Form submit: `application/x-www-form-urlencoded` или `multipart/form-data` (для файла)
- AJAX: `application/json` (тело) + `X-CSRFToken` заголовок

### Пагинация
Списки (документы, коды) пагинируются по 20 записей.
Параметр `page` в query string. В ответе AJAX — объект `pagination`.

### Ошибки в form submit
При ошибках в стандартных маршрутах (R10–R14) — редирект обратно на R9 с `django.contrib.messages` (error level).

### Ошибки в AJAX
Всегда JSON-ответ с полем `error` (string). HTTP-код соответствует типу ошибки.

---

## 6. Маппинг URL → User Stories

| US   | Описание                              | Маршруты              |
|------|---------------------------------------|-----------------------|
| US-01| Загрузка файла с кодами               | R4, R5                |
| US-02| Выбор склада перед загрузкой          | R4                    |
| US-03| Запрос в Честный знак                 | R5 (внутри view)      |
| US-04| Парсинг атрибутов                     | R5 (внутри view)      |
| US-05| Авто-создание номенклатуры            | R5 (внутри view)      |
| US-06| Дедупликация по значению кода         | R5 (внутри view)      |
| US-07| Логирование процесса загрузки         | R5 (внутри view)      |
| US-08| Хранение кодов с атрибутами           | R5 (внутри view)      |
| US-09| Отчёт по итогам загрузки             | R6, A9                |
| US-10| Создание документа                    | R8, A1, A2            |
| US-11| Добавление / редактирование строк     | R9, A3, A4            |
| US-12| Нумерация документов                  | R10                   |
| US-13| Проведение документа                  | R11                   |
| US-14| Распроведение                         | R12                   |
| US-15| Пометка на удаление                   | R13                   |
| US-16| Автосохранение черновика              | A8                    |
| US-17| Дубликаты номенклатуры в документе    | A2 (ответ duplicate)  |
| US-18| Отмена черновика                      | R14                   |
| US-19| Редактирование сохранённого           | R9, R10, A3, A4       |
| US-20| Фильтрация документов                 | R7                    |
| US-21| Счётчики активных кодов               | A5                    |
| US-22| Экранное отображение кодов            | A6                    |
| US-23| Карточка кода                         | A7                    |
| US-24| FIFO-выбор при проведении             | R11 (внутри view)     |
| US-25| Права начальника                      | Все R*, проверка в middleware/views |
| US-26| Права кладовщика                      | Все R*, проверка в middleware/views |
| US-27| Списание с чужой площадки             | R8, R11               |
| US-28| Управление пользователями             | R15, R16, R17         |

---

## 7. Маппинг URL → бизнес-правила

| БП | Правило                              | Где реализуется       |
|----|--------------------------------------|-----------------------|
| 1  | Авто-создание номенклатуры           | R5 (UploadProcessView) |
| 2  | Нераспознанные коды                  | R5, R6                |
| 3  | Дедупликация                         | R5 (UploadProcessView) |
| 4  | Маппинг владелец → склад (ручной)    | R4 (select склада)    |
| 5  | Экранное отображение (после провед.) | A6 (проверка status)  |
| 6  | Параллельная работа (атомарность)    | R11 (transaction.atomic) |
| 7  | FIFO                                 | R11 (ORDER BY created_at, id) |
| 8  | Выкуп (без перезапроса)              | R11 (перевязка warehouse) |
| 9  | Редактирование проведённого          | A2, A3, A4 (проверка status) |
| 10 | Помечен на удаление                  | R13                   |
| 11 | Начальник — чужие площадки (чтение)  | R7, R9 (can_edit=False) |
| 12 | Кладовщик — чужие документы          | R7, R9 (403)          |
| 13 | Списание с чужой площадки            | R8 (выбор склада-источника) |
| 14 | product_name (fallback)              | A1 (в ответе)         |
| 15 | Дубликаты номенклатуры               | A2 (status: duplicate) |
| 16 | Формат нумерации                     | R10 (генерация номера) |
