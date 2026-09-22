# ДИАГРАММЫ ПОСЛЕДОВАТЕЛЬНОСТЕЙ
# Проект «Обработка QR-кодов» — v1.0
# Сгенерировано: 2026-09-20

---

## Обзор

Четыре ключевых сценария:

| № | Сценарий | Бизнес-правила | Визуализация |
|---|----------|----------------|--------------|
| 1 | Загрузка файла с DataMatrix-кодами | BR-1, BR-2, BR-3, BR-14 | PNG |
| 2 | Проведение документа (атомарная транзакция) | BR-6, BR-7 | PNG |
| 3 | Распроведение / Пометка на удаление | BR-9, BR-10 | PNG |
| 4 | Списание с чужой площадки / Выкуп | BR-8, BR-13 | PNG |

---

## Диаграмма 1. Загрузка файла с DataMatrix-кодами

### Участники
- **Пользователь** (Кладовщик) — инициирует загрузку, выбирает склад
- **Система** (Upload API) — оркестрирует процесс загрузки
- **nechestniy_znak** — внешняя библиотека для запроса данных по коду
- **Парсер атрибутов** — извлекает brand, model, size из ответа
- **БД** (Django ORM) — хранилище TireCode, TireNomenclature, логов

### Текстовое описание (Mermaid)

```mermaid
sequenceDiagram
    actor U as Пользователь
    participant S as Система (Upload API)
    participant NZ as nechestniy_znak
    participant P as Парсер атрибутов
    participant DB as БД (Django ORM)

    U->>S: POST /api/upload/ (file, warehouse_id)
    
    loop для каждой строки файла
        S->>DB: SELECT TireCode WHERE qr_code = ?
        alt код найден (дубликат)
            DB-->>S: найден
            S->>S: лог: "duplicate", пропуск
            Note over S: запрос в Честный знак НЕ отправляется
        else код новый
            DB-->>S: не найден
            S->>NZ: запрос данных по коду
            alt успешный ответ
                NZ-->>S: honest_sign_data (JSON)
                S->>P: парсинг brand, model, size
                alt атрибуты полные
                    P-->>S: brand, model, size
                    S->>DB: SELECT TireNomenclature WHERE brand+model+size
                    alt новое сочетание
                        S->>DB: INSERT TireNomenclature (BR-1, BR-14)
                    end
                    S->>DB: INSERT TireCode (qr_code, nomenclature, warehouse, honest_sign_data)
                    S->>S: лог: "created"
                else атрибуты неполные
                    P-->>S: неполные / null
                    S->>S: лог: "unrecognized", пропуск (BR-2)
                end
            else ошибка Честного знака
                NZ-->>S: ошибка / исключение
                S->>S: лог: "honest_sign_error", пропуск (BR-2)
            end
        end
    end
    
    S-->>U: Отчёт: created=N, duplicates=M, unrecognized=K, hs_errors=L
    Note over S,U: + список пропущенных кодов со значениями и причинами
```

### Ключевые моменты
1. **Дедупликация (BR-3):** проверка по `qr_code` с unique-ограничением; повторный запрос в «Честный знак» не отправляется
2. **Авто-создание номенклатуры (BR-1):** при первом сочетании `brand + model + size`; неполные атрибуты → пропуск
3. **product_name (BR-14):** заполняется из ответа Честного знака при создании; fallback `brand + model + size`; не перезаписывается при повторной загрузке
4. **Процесс не прерывается** на ошибках — каждый код обрабатывается независимо

---

## Диаграмма 2. Проведение документа (атомарная транзакция)

### Участники
- **Пользователь** (Кладовщик) — инициирует проведение
- **Система** (Document API) — оркестрирует транзакцию
- **БД** (Django ORM) — TireCode, Document, счётчики
- **FIFO Selector** — выбор старейших кодов
- **Счётчики** — активные коды по позициям и складам

### Текстовое описание (Mermaid)

```mermaid
sequenceDiagram
    actor U as Пользователь
    participant S as Система (Document API)
    participant DB as БД (Django ORM)
    participant FIFO as FIFO Selector
    participant C as Счётчики

    U->>S: POST /api/documents/{id}/post/
    S->>DB: BEGIN TRANSACTION
    
    loop для каждой строки документа
        S->>DB: SELECT COUNT(*) FROM TireCode<br/>WHERE nomenclature=X AND warehouse=Y<br/>AND is_active=True
        DB-->>S: available_count = N
        S->>S: проверка: quantity <= available_count?
    end
    
    alt по всем строкам достаточно кодов
        loop для каждой строки документа
            S->>FIFO: выбрать quantity старейших кодов
            Note over FIFO: сортировка: created_at ASC, затем id ASC
            FIFO-->>S: selected_codes []
            S->>DB: UPDATE TireCode SET is_used=True, is_active=False,<br/>document={id}, used_at=NOW()<br/>WHERE id IN (selected_codes)
        end
        S->>C: уменьшить счётчики по позициям и складам
        S->>DB: UPDATE Document SET status='posted', posted_at=NOW()
        S->>DB: COMMIT
        S-->>U: HTTP 200 — документ проведён
    else нехватка хотя бы по одной строке
        S->>DB: ROLLBACK
        Note over S,DB: атомарный откат: ни один код не списан,<br/>счётчики не изменены
        S-->>U: HTTP 409 — ошибка: позиция=X, запрошено=Q, доступно=N<br/>Документ остался в статусе "saved"
    end
```

### Ключевые моменты
1. **Атомарность (BR-6):** вся транзакция — единое целое. Либо все строки обработаны, либо ни одна
2. **FIFO (BR-7):** сортировка по `created_at` (дата загрузки), внутри дня — по `id` (автоинкремент, меньший ID = раньше)
3. **Без резерва (BR-6):** коды не блокируются заранее; конфликт обнаруживается при проведении; кто первым провёл — забрал коды
4. **При нехватке:** документ остаётся в `saved`, пользователь корректирует количество и повторяет

---

## Диаграмма 3. Распроведение / Пометка на удаление

### Участники
- **Пользователь** — инициирует операцию
- **Система** (Document API) — выполняет откат
- **БД** — TireCode, Document
- **Счётчики** — восстановление значений

### Текстовое описание (Mermaid)

```mermaid
sequenceDiagram
    actor U as Пользователь
    participant S as Система (Document API)
    participant DB as БД (Django ORM)
    participant C as Счётчики

    rect rgb(235, 245, 251)
    Note over U,C: Сценарий A: Распроведение
    U->>S: POST /api/documents/{id}/unpost/
    S->>DB: BEGIN TRANSACTION
    S->>DB: UPDATE TireCode SET is_used=False, is_active=True,<br/>document=null, used_at=null<br/>WHERE document={id}
    S->>C: восстановить счётчики (+quantity по каждой строке)
    S->>DB: UPDATE Document SET status='saved', posted_at=null
    S->>DB: COMMIT
    S-->>U: HTTP 200 — документ "saved", коды активны
    end

    rect rgb(253, 237, 236)
    Note over U,C: Сценарий B: Пометка на удаление (= распроведение + is_deleted)
    U->>S: POST /api/documents/{id}/mark_deleted/
    S->>DB: BEGIN TRANSACTION
    Note over S: Шаги 2-5 идентичны распроведению
    S->>DB: UPDATE TireCode SET is_used=False, is_active=True, document=null...
    S->>C: восстановить счётчики
    S->>DB: UPDATE Document SET status='marked_deleted', is_deleted=True
    S->>DB: COMMIT
    S-->>U: HTTP 200 — документ "marked_deleted", только просмотр
    end
```

### Ключевые моменты
1. **Редактирование проведённого (BR-9):** запрещено. Для изменений — распроведение в `saved`
2. **Помечен на удаление (BR-10):** это **распроведение + `is_deleted=true`** — комбинированная операция
3. **Откат:** коды возвращаются в активные (`is_active=True, is_used=False`), `document=null`, `used_at=null`
4. **Счётчики** восстанавливаются на `quantity` по каждой строке документа
5. **Статус `marked_deleted`:** только просмотр, любые изменения запрещены

---

## Диаграмма 4. Списание с чужой площадки / Выкуп

### Участники
- **Кладовщик** (Площадка А) — создаёт документ
- **Система** (Document API) — оркестрация
- **БД** — TireCode, Document, склады
- **Площадка Б** (склад-источник) — откуда списываются коды
- **Площадка А** (склад-получатель) — только для выкупа

### Текстовое описание (Mermaid)

```mermaid
sequenceDiagram
    actor K as Кладовщик (Площадка А)
    participant S as Система (Document API)
    participant DB as БД (TireCode, Document)
    participant PB as Площадка Б (склад-источник)
    participant PA as Площадка А (склад-получатель)

    rect rgb(235, 245, 251)
    Note over K,DB: Фаза 1: Создание документа
    K->>S: Создать документ списания/выкупа<br/>source_warehouse = склад Площадки Б
    S->>DB: source_platform = Площадка А (автор)<br/>writeoff_platform = Площадка Б (склад-источник)
    Note over S: Для выкупа: target_warehouse = основной склад Площадки А
    S-->>K: Документ создан (status=draft)
    end

    rect rgb(234, 250, 241)
    Note over K,PA: Фаза 2: Сохранение и проведение
    K->>S: Сохранить (присвоить номер)
    K->>S: Добавить строку: Nomenclature + quantity
    K->>S: Провести документ
    S->>DB: BEGIN TRANSACTION
    S->>PB: Проверить остаток активных кодов
    PB-->>S: доступно N кодов
    
    alt doc_type = writeoff (списание)
        S->>DB: UPDATE TireCode SET is_used=True, is_active=False
        S->>PB: счётчик Площадки Б: -quantity
        S->>DB: UPDATE Document SET status='posted'
        S->>DB: COMMIT
        S-->>K: HTTP 200 — коды списаны
    else doc_type = buyout (выкуп)
        S->>DB: UPDATE TireCode SET warehouse=склад А
        Note over S,DB: локальная приписка, БЕЗ перезапроса "Честного знака" (BR-8)
        S->>PA: счётчик Площадки А: +quantity
        S->>PB: счётчик Площадки Б: -quantity
        S->>DB: UPDATE Document SET status='posted'
        S->>DB: COMMIT
        S-->>K: HTTP 200 — коды перевязаны на склад А
    end
    end
```

### Ключевые моменты
1. **Списание с чужой площадки (BR-13):** разрешено; документ на имя создавшего кладовщика; счётчик уменьшается у площадки-источника списания
2. **Поля документа:** `source_platform` = площадка автора (А), `writeoff_platform` = площадка склада-источника (Б) — они различаются
3. **Выкуп (BR-8):** приписка меняется локально (`warehouse` обновляется), без перезапроса «Честного знака»
4. **При выкупе** `target_warehouse` = основной склад площадки автора; коды остаются активными, но на новом складе
5. **При списании** `target_warehouse` = null; коды помечаются `is_used=True, is_active=False`

---

## Приложение: матрица сценариев и тест-кейсов

| Сценарий | Тест-кейсы |
|----------|-----------|
| Загрузка QR-кодов | TC-LOAD-001 … TC-LOAD-013 |
| Проведение документа | TC-POST-001 … TC-POST-008, TC-CONC-001, TC-CONC-002 |
| Распроведение / удаление | TC-UNPOST-001 … TC-UNPOST-004 |
| Списание с чужой площадки | TC-POST-006, TC-AUTH-004, TC-AUTH-007 |
