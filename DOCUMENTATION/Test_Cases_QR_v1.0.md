# ТЕСТ-КЕЙСЫ ДЛЯ АВТОМАТИЗИРОВАННОГО ТЕСТИРОВАНИЯ
# Проект «Обработка QR-кодов» — v1.0
# Сгенерировано: 2026-09-20

---

## Соглашения

- **Модуль** — функциональная область (совпадает с Epic из User Stories)
- **Уровень**: UNIT / INTEGRATION / E2E
- **Тип**: POSITIVE (позитивный) / NEGATIVE (негативный) / BOUNDARY (граничный)
- **Приоритет**: P0 (критичный) / P1 (высокий) / P2 (средний)
- Все тесты предполагают чистую БД с миграциями, если не указано иное в предусловиях

### Тестовые данные (фикстуры)

```
PLATFORM_SOF_GRUZ   — Площадка «Софийская Груз»
PLATFORM_SOF_LEG    — Площадка «Софийская Легковой» (архитектура учитывает, но реализация отложена)

WAREHOUSE_MAIN_GRUZ — Основной склад, platform=PLATFORM_SOF_GRUZ, type='main'
WAREHOUSE_OH_GRUZ   — Склад ОХ, platform=PLATFORM_SOF_GRUZ, type='oh', supplier=SUPPLIER_1
WAREHOUSE_MAIN_LEG  — Основной склад, platform=PLATFORM_SOF_LEG, type='main'

SUPPLIER_1          — Поставщик «ООО Поставщик»

USER_MANAGER        — role='manager', platform=PLATFORM_SOF_GRUZ
USER_STOREKEEPER_1  — role='storekeeper', platform=PLATFORM_SOF_GRUZ
USER_STOREKEEPER_2  — role='storekeeper', platform=PLATFORM_SOF_LEG

NOMENCLATURE_1      — brand='Michelin', model='Primacy 4', size='205/55 R15', product_name='Шина Michelin Primacy 4 205/55 R15'
NOMENCLATURE_2      — brand='Pirelli', model='Cinturato', size='225/45 R17', product_name=null

CODE_1..CODE_5      — TireCode, nomenclature=NOMENCLATURE_1, warehouse=WAREHOUSE_MAIN_GRUZ, is_active=True, is_used=False
CODE_6..CODE_10     — TireCode, nomenclature=NOMENCLATURE_2, warehouse=WAREHOUSE_OH_GRUZ, is_active=True, is_used=False
```

---

## МОДУЛЬ 1. ЗАГРУЗКА КОДОВ

### TC-LOAD-001: Успешная загрузка новых кодов (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-1, BR-2, BR-3
**Предусловия:**
- Склад WAREHOUSE_MAIN_GRUZ существует
- Файл `codes_new.txt` содержит 3 строки с уникальными DataMatrix-кодами
- Библиотека nechestniy_znak возвращает валидный ответ с атрибутами brand, model, size для каждого кода
- В БД нет записей TireCode с такими значениями qr_code

**Шаги:**
1. POST /api/upload/ с файлом `codes_new.txt` и параметром `warehouse_id=WAREHOUSE_MAIN_GRUZ`
2. Проверить ответ сервера
3. Проверить состояние БД

**Ожидаемый результат:**
- HTTP 200, в отчёте: `created=3, duplicates=0, unrecognized=0, honest_sign_errors=0`
- В БД создано 3 записи TireCode с is_active=True, is_used=False
- Каждая запись привязана к WAREHOUSE_MAIN_GRUZ
- Для каждого кода создана номенклатура (если сочетание brand+model+size новое) или использована существующая
- Поле honest_sign_data заполнено полным ответом
- created_at заполнено текущей датой/временем
- Лог загрузки содержит 3 записи со статусом «created»

---

### TC-LOAD-002: Дедупликация — повторная загрузка существующего кода (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-3
**Предусловия:**
- В БД существует TireCode с qr_code='0104630027600011...'
- Файл содержит строку с этим же кодом + 2 новых кода

**Шаги:**
1. POST /api/upload/ с файлом, `warehouse_id=WAREHOUSE_MAIN_GRUZ`
2. Проверить отчёт и лог

**Ожидаемый результат:**
- HTTP 200, `created=2, duplicates=1, unrecognized=0, honest_sign_errors=0`
- Запрос в «Честный знак» для дубликата НЕ отправлялся (проверить по логу или mock-счётчику вызовов)
- Дубликат записан в список пропущенных со значением кода и причиной «duplicate»
- В БД количество записей TireCode увеличилось на 2 (не на 3)

---

### TC-LOAD-003: Дедупликация — код с любым статусом пропускается (BOUNDARY, INTEGRATION, P0)

**Связанные правила:** BR-3
**Предусловия:**
- В БД существует TireCode с qr_code='X1', is_active=False, is_used=True (списан)

**Шаги:**
1. Загрузить файл со строкой 'X1' + 1 новым кодом

**Ожидаемый результат:**
- `created=1, duplicates=1`
- Код 'X1' пропущен как дубликат, несмотря на is_active=False и is_used=True
- Новый запрос в «Честный знак» для 'X1' не отправлялся

---

### TC-LOAD-004: Нераспознанный код — неполные атрибуты (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-1, BR-2
**Предусловия:**
- Файл содержит код 'BADCODE1'
- nechestniy_znak возвращает ответ без атрибута `size` (или size=null)
- Кода 'BADCODE1' нет в БД

**Шаги:**
1. Загрузить файл с кодом 'BADCODE1'

**Ожидаемый результат:**
- `created=0, unrecognized=1`
- TireCode для 'BADCODE1' не создан
- Номенклатура не создана
- В списке пропущенных: код='BADCODE1', причина='unrecognized' (или 'incomplete_attributes')
- Запрос в «Честный знак» был отправлен, но парсинг не дал полного набора атрибутов

---

### TC-LOAD-005: Ошибка «Честного знака» при запросе (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-2
**Предусловия:**
- Файл содержит код 'HSERROR1'
- nechestniy_znak бросает исключение / возвращает ошибку для 'HSERROR1'
- Кода 'HSERROR1' нет в БД

**Шаги:**
1. Загрузить файл с кодом 'HSERROR1'

**Ожидаемый результат:**
- `created=0, honest_sign_errors=1`
- TireCode для 'HSERROR1' не создан
- В списке пропущенных: код='HSERROR1', причина='honest_sign_error'
- Процесс загрузки продолжился (не упал на ошибке)

---

### TC-LOAD-006: Авто-создание номенклатуры при новом сочетании (POSITIVE, INTEGRATION, P1)

**Связанные правила:** BR-1, BR-14
**Предусловия:**
- В БД нет номенклатуры с brand='Continental', model='PremiumContact', size='215/50 R17'

**Шаги:**
1. Загрузить файл с кодом, для которого nechestniy_znak вернул brand='Continental', model='PremiumContact', size='215/50 R17', product_name='Continental PremiumContact 215/50 R17'

**Ожидаемый результат:**
- Создана TireNomenclature с brand='Continental', model='PremiumContact', size='215/50 R17'
- product_name = 'Continental PremiumContact 215/50 R17' (из ответа Честного знака)
- is_active=True
- TireCode привязан к созданной номенклатуре

---

### TC-LOAD-007: Использование существующей номенклатуры (POSITIVE, INTEGRATION, P1)

**Связанные правила:** BR-1
**Предусловия:**
- В БД существует номенклатура NOMENCLATURE_1 (brand='Michelin', model='Primacy 4', size='205/55 R15')
- Файл содержит 2 кода с теми же brand+model+size

**Шаги:**
1. Загрузить файл

**Ожидаемый результат:**
- Новая номенклатура НЕ создана
- Оба TireCode привязаны к NOMENCLATURE_1
- Количество номенклатур в БД не изменилось

---

### TC-LOAD-008: product_name fallback при отсутствии (POSITIVE, UNIT, P1)

**Связанные правила:** BR-14
**Предусловия:**
- nechestniy_znak возвращает ответ без product_name (null)

**Шаги:**
1. Загрузить код с brand='Bridgestone', model='Turanza', size='195/65 R15'

**Ожидаемый результат:**
- Создана номенклатура с product_name=null в БД (raw-значение)
- При отображении / сериализации product_name = 'Bridgestone Turanza 195/65 R15' (fallback)

---

### TC-LOAD-009: product_name не перезаписывается при повторной загрузке (BOUNDARY, INTEGRATION, P1)

**Связанные правила:** BR-14
**Предусловия:**
- Номенклатура существует с product_name='Оригинальное наименование'
- Файл содержит новый код с тем же brand+model+size, но nechestniy_znak возвращает другой product_name

**Шаги:**
1. Загрузить файл

**Ожидаемый результат:**
- TireCode создан и привязан к существующей номенклатуре
- product_name в номенклатуре остался 'Оригинальное наименование' (не перезаписан)

---

### TC-LOAD-010: Загрузка без выбора склада (NEGATIVE, INTEGRATION, P1)

**Предусловия:**
- Файл с валидными кодами

**Шаги:**
1. POST /api/upload/ без параметра warehouse_id

**Ожидаемый результат:**
- HTTP 400, сообщение об обязательном параметре warehouse_id
- В БД ничего не создано

---

### TC-LOAD-011: Пустой файл (BOUNDARY, INTEGRATION, P2)

**Предусловия:**
- Файл `empty.txt` (0 байт или только пустые строки)

**Шаги:**
1. Загрузить пустой файл

**Ожидаемый результат:**
- HTTP 200, `created=0, duplicates=0, unrecognized=0, honest_sign_errors=0`
- Отчёт возвращён, список пропущенных пуст
- Ошибка не выброшена

---

### TC-LOAD-012: Смешанная загрузка — все типы результатов в одном файле (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-1, BR-2, BR-3
**Предусловия:**
- Файл содержит 10 строк:
  - 4 новых кода (валидные)
  - 2 существующих кода (дубликаты в БД)
  - 2 кода с ошибкой «Честного знака»
  - 2 кода с неполными атрибутами

**Шаги:**
1. Загрузить файл

**Ожидаемый результат:**
- `created=4, duplicates=2, unrecognized=2, honest_sign_errors=2`
- В БД +4 TireCode
- Список пропущенных содержит 6 записей с корректными значениями и причинами
- Лог содержит 10 записей

---

### TC-LOAD-013: Отчёт о загрузке — структура и полнота (POSITIVE, INTEGRATION, P1)

**Предусловия:**
- Любая загрузка с хотя бы 1 кодом каждого типа

**Шаги:**
1. Проверить структуру ответа

**Ожидаемый результат:**
- Ответ содержит 4 счётчика: created, duplicates, unrecognized, honest_sign_errors
- Ответ содержит массив `skipped` с объектами `{code: string, reason: string}`
- Сумма всех счётчиков = общему числу строк в файле

---

## МОДУЛЬ 2. СОЗДАНИЕ И РЕДАКТИРОВАНИЕ ДОКУМЕНТОВ

### TC-DOC-001: Создание документа списания — черновик (POSITIVE, INTEGRATION, P0)

**Предусловия:**
- Авторизован USER_STOREKEEPER_1

**Шаги:**
1. POST /api/documents/ {doc_type='writeoff', source_warehouse=WAREHOUSE_MAIN_GRUZ}
2. Не вызывать «Сохранить»

**Ожидаемый результат:**
- Документ создан в статусе 'draft'
- number = null (не присвоен)
- is_deleted=False
- source_platform = PLATFORM_SOF_GRUZ (площадка автора)
- writeoff_platform = PLATFORM_SOF_GRUZ (площадка склада-источника)
- target_warehouse = null (для списания)

---

### TC-DOC-002: Сохранение документа — присвоение номера (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-16
**Предусловия:**
- Существует документ в статусе 'draft' (тип 'writeoff', автор USER_STOREKEEPER_1)
- В БД нет документов списания за текущий год

**Шаги:**
1. PATCH /api/documents/{id}/ с action='save'
2. Проверить номер и статус

**Ожидаемый результат:**
- Статус = 'saved'
- number = 'СП-2026-000001' (первый документ списания за 2026 год)
- updated_at обновлено

---

### TC-DOC-003: Сквозная нумерация — второй документ (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-16
**Предусловия:**
- Существует 1 проведённый/сохранённый документ списания с номером 'СП-2026-000001'
- Создаётся новый документ списания

**Шаги:**
1. Сохранить новый документ списания

**Ожидаемый результат:**
- number = 'СП-2026-000002'

---

### TC-DOC-004: Независимая нумерация для списания и выкупа (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-16
**Предусловия:**
- Существуют документы: СП-2026-000001, СП-2026-000002, ВК-2026-000001

**Шаги:**
1. Создать и сохранить новый документ списания
2. Создать и сохранить новый документ выкупа

**Ожидаемый результат:**
- Списание: 'СП-2026-000003'
- Выкуп: 'ВК-2026-000002'
- Нумерация каждого типа независима

---

### TC-DOC-005: Сброс нумерации в начале года (BOUNDARY, UNIT, P1)

**Связанные правила:** BR-16
**Предусловия:**
- Последний документ списания 2026 года — 'СП-2026-000050'
- Дата создания нового документа — 1 января 2027 года (или мок даты)

**Шаги:**
1. Сохранить новый документ списания от 01.01.2027

**Ожидаемый результат:**
- number = 'СП-2027-000001'
- Счётчик сброшен

---

### TC-DOC-006: Формат номера — 6 знаков с нулями (BOUNDARY, UNIT, P2)

**Связанные правила:** BR-16

**Шаги:**
1. Сохранить документ с порядковым номером 5
2. Сохранить документ с порядковым номером 12345

**Ожидаемый результат:**
- 'СП-2026-000005' (5 знаков дополняется нулями до 6)
- 'СП-2026-012345'

---

### TC-DOC-007: Добавление строки в документ (POSITIVE, INTEGRATION, P0)

**Предусловия:**
- Документ в статусе 'saved' или 'draft'
- Номенклатура NOMENCLATURE_1 существует

**Шаги:**
1. POST /api/documents/{id}/items/ {nomenclature_id=NOMENCLATURE_1, quantity=3}

**Ожидаемый результат:**
- Создана DocumentItem с quantity=3
- Документ содержит 1 строку

---

### TC-DOC-008: Дубликат номенклатуры в документе — автоувеличение количества (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-15
**Предусловия:**
- Документ содержит DocumentItem с nomenclature=NOMENCLATURE_1, quantity=2

**Шаги:**
1. POST /api/documents/{id}/items/ {nomenclature_id=NOMENCLATURE_1, quantity=1}

**Ожидаемый результат:**
- Новая DocumentItem НЕ создана
- quantity в существующей строке = 3 (2+1)
- Количество строк в документе не изменилось
- API возвращает информацию о том, что строка найдена и количество увеличено

---

### TC-DOC-009: Дубликат номенклатуры — подсветка существующей строки (POSITIVE, E2E, P1)

**Связанные правила:** BR-15
**Предусловия:**
- Документ содержит строку с NOMENCLATURE_1

**Шаги:**
1. Попытаться добавить NOMENCLATURE_1 через UI (выбрать из списка номенклатуры)

**Ожидаемый результат:**
- Существующая строка подсвечена (визуально)
- Новая строка не добавлена
- quantity увеличен на 1
- Диалог объединения НЕ показан

---

### TC-DOC-010: Добавление строки в проведённый документ — отказ (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-9
**Предусловия:**
- Документ в статусе 'posted'

**Шаги:**
1. POST /api/documents/{id}/items/ {nomenclature_id=NOMENCLATURE_1, quantity=1}

**Ожидаемый результат:**
- HTTP 403 или 409
- Сообщение: редактирование проведённого документа запрещено
- Состав документа не изменился

---

### TC-DOC-011: Сохранение черновика при разрыве соединения (POSITIVE, E2E, P1)

**Предусловия:**
- Документ в статусе 'draft', содержит 2 строки
- Симуляция разрыва WebSocket / HTTP-соединения

**Шаги:**
1. Заполнить документ (2 строки)
2. Имитировать разрыв соединения
3. Восстановить соединение

**Ожидаемый результат:**
- Данные не потеряны (восстановлены из автосохранения)
- Строки и количества сохранены
- Статус остался 'draft'

---

## МОДУЛЬ 3. ПРОВЕДЕНИЕ ДОКУМЕНТА

### TC-POST-001: Успешное проведение — достаточно кодов (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-6, BR-7
**Предусловия:**
- Документ 'saved', содержит 1 строку: NOMENCLATURE_1, quantity=3
- На складе WAREHOUSE_MAIN_GRUZ: 5 активных кодов NOMENCLATURE_1 (CODE_1..CODE_5, все is_active=True, is_used=False)

**Шаги:**
1. POST /api/documents/{id}/post/

**Ожидаемый результат:**
- HTTP 200, статус документа = 'posted'
- Выбраны 3 старейших кода по FIFO (CODE_1, CODE_2, CODE_3)
- Выбранные коды: is_used=True, is_active=False, document=текущий документ, used_at заполнено
- CODE_4, CODE_5 остались is_active=True, is_used=False
- posted_at заполнено
- Транзакция атомарна — все изменения применены или ни одно

---

### TC-POST-002: Проведение — нехватка кодов по строке (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-6
**Предусловия:**
- Документ 'saved', содержит 1 строку: NOMENCLATURE_1, quantity=10
- На складе: 3 активных кода NOMENCLATURE_1

**Шаги:**
1. POST /api/documents/{id}/post/

**Ожидаемый результат:**
- HTTP 409 (или 422), ошибка с указанием: номенклатура, запрошено=10, доступно=3
- Документ остался в статусе 'saved'
- Ни один код не изменил статус (is_active=True, is_used=False для всех)
- Счётчики не изменились

---

### TC-POST-003: Проведение — нехватка по одной из нескольких строк (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-6
**Предусловия:**
- Документ 'saved', 2 строки:
  - Строка 1: NOMENCLATURE_1, quantity=3 (доступно 5) ✅
  - Строка 2: NOMENCLATURE_2, quantity=7 (доступно 3) ❌

**Шаги:**
1. POST /api/documents/{id}/post/

**Ожидаемый результат:**
- HTTP 409, ошибка с указанием строки 2: запрошено=7, доступно=3
- Документ остался в статусе 'saved'
- Атомарный откат: коды по строке 1 НЕ списаны (is_active=True, is_used=False)
- Все счётчики в исходном состоянии

---

### TC-POST-004: Проведение — FIFO по дате загрузки (POSITIVE, UNIT, P0)

**Связанные правила:** BR-7
**Предусловия:**
- 5 кодов NOMENCLATURE_1 на складе:
  - CODE_A: created_at=2026-09-15
  - CODE_B: created_at=2026-09-16
  - CODE_C: created_at=2026-09-16
  - CODE_D: created_at=2026-09-17
  - CODE_E: created_at=2026-09-18
- CODE_C.id < CODE_B.id (младший ID, но та же дата — для проверки inside-day FIFO)

**Шаги:**
1. Провести документ с quantity=3

**Ожидаемый результат:**
- Выбраны CODE_A (15.09), затем один из CODE_B/C (16.09, по ID — старший ID = более ранний)
- Порядок FIFO: дата загрузки → внутри дня по ID (меньший ID = раньше)

---

### TC-POST-005: Проведение — уменьшение счётчиков (POSITIVE, INTEGRATION, P0)

**Предусловия:**
- Счётчик активных кодов по NOMENCLATURE_1 на WAREHOUSE_MAIN_GRUZ = 5

**Шаги:**
1. Провести документ с quantity=3 по NOMENCLATURE_1

**Ожидаемый результат:**
- Счётчик = 2 после проведения
- Счётчик уменьшен ровно на quantity

---

### TC-POST-006: Проведение — выбор склада-источника списания (POSITIVE, INTEGRATION, P1)

**Связанные правила:** BR-13
**Предусловия:**
- Кладовщик USER_STOREKEEPER_1 (платформа PLATFORM_SOF_GRUZ) создаёт документ списания с source_warehouse=WAREHOUSE_MAIN_LEG (чужая площадка)

**Шаги:**
1. Создать документ с source_warehouse=WAREHOUSE_MAIN_LEG
2. Провести документ

**Ожидаемый результат:**
- writeoff_platform = PLATFORM_SOF_LEG (площадка склада-источника)
- source_platform = PLATFORM_SOF_GRUZ (площадка автора)
- Коды списаны со склада WAREHOUSE_MAIN_LEG
- Счётчик уменьшен у WAREHOUSE_MAIN_LEG

---

### TC-POST-007: Проведение уже проведённого документа (NEGATIVE, INTEGRATION, P1)

**Предусловия:**
- Документ в статусе 'posted'

**Шаги:**
1. POST /api/documents/{id}/post/

**Ожидаемый результат:**
- HTTP 409, сообщение: документ уже проведён
- Никаких изменений в данных

---

### TC-POST-008: Проведение документа в статусе 'draft' (NEGATIVE, INTEGRATION, P1)

**Предусловия:**
- Документ в статусе 'draft' (не сохранён)

**Шаги:**
1. POST /api/documents/{id}/post/

**Ожидаемый результат:**
- HTTP 409, сообщение: нельзя провести несохранённый документ
- (Альтернативно: система автоматически сохраняет, потом проводит — зависит от реализации. Если авто-сохранение — проверить, что номер присвоен)

---

## МОДУЛЬ 4. РАСПРОВЕДЕНИЕ И УДАЛЕНИЕ

### TC-UNPOST-001: Успешное распроведение (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-9
**Предусловия:**
- Документ 'posted', к нему привязаны 3 кода (is_used=True, is_active=False, document=текущий)

**Шаги:**
1. POST /api/documents/{id}/unpost/

**Ожидаемый результат:**
- Статус = 'saved'
- 3 кода: is_used=False, is_active=True, document=null, used_at=null
- Счётчики восстановлены (+3)
- posted_at = null (или сохранено в истории)

---

### TC-UNPOST-002: Распроведение — статус 'marked_deleted' невозможен напрямую (NEGATIVE, INTEGRATION, P1)

**Связанные правила:** BR-10
**Предусловия:**
- Документ в статусе 'posted'

**Шаги:**
1. POST /api/documents/{id}/mark_deleted/

**Ожидаемый результат:**
- Статус = 'marked_deleted'
- is_deleted = True
- Коды возвращены в активные (как при распроведении)
- Счётчики восстановлены
- (Это комбинированная операция: распроведение + пометка на удаление)

---

### TC-UNPOST-003: Распроведение документа не в статусе 'posted' (NEGATIVE, INTEGRATION, P1)

**Предусловия:**
- Документ в статусе 'saved'

**Шаги:**
1. POST /api/documents/{id}/unpost/

**Ожидаемый результат:**
- HTTP 409, сообщение: документ не проведён
- Изменений нет

---

### TC-UNPOST-004: Документ 'marked_deleted' — только просмотр (POSITIVE, INTEGRATION, P1)

**Связанные правила:** BR-10
**Предусловия:**
- Документ в статусе 'marked_deleted'

**Шаги:**
1. Попытаться добавить строку
2. Попытаться провести
3. Попытаться распровести
4. Получить детали документа (GET)

**Ожидаемый результат:**
- Действия 1–3: HTTP 403, операция запрещена
- Действие 4: HTTP 200, данные доступны для чтения

---

## МОДУЛЬ 5. ЭКРАННОЕ ОТОБРАЖЕНИЕ КОДОВ

### TC-DISPLAY-001: Коды доступны после проведения (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-5
**Предусловия:**
- Документ 'posted', к нему привязаны 3 кода

**Шаги:**
1. GET /api/documents/{id}/codes/

**Ожидаемый результат:**
- HTTP 200, массив из 3 объектов TireCode
- Каждый объект содержит: qr_code, nomenclature (brand, model, size, product_name), is_used=True

---

### TC-DISPLAY-002: Коды недоступны до проведения (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-5
**Предусловия:**
- Документ 'saved' (сохранён, но не проведён)

**Шаги:**
1. GET /api/documents/{id}/codes/

**Ожидаемый результат:**
- HTTP 403 или 404
- Сообщение: коды доступны только после проведения документа
- Массив кодов не возвращён

---

### TC-DISPLAY-003: Карточка кода — состав данных (POSITIVE, UNIT, P1)

**Предусловия:**
- TireCode: qr_code='01046300276...\n21...', nomenclature с brand='Michelin', model='Primacy 4', size='205/55 R15', product_name='Шина...'

**Шаги:**
1. GET /api/codes/{id}/

**Ожидаемый результат:**
- Возвращены: qr_code (в две строки), nomenclature.brand, nomenclature.model, nomenclature.size, nomenclature.product_name
- DataMatrix-код визуализируется (если есть рендеринг — проверить размер сопоставим со спичечным коробком)

---

## МОДУЛЬ 6. СЧЁТЧИКИ И ФИЛЬТРАЦИЯ

### TC-COUNT-001: Счётчики активных кодов по позиции и складу (POSITIVE, INTEGRATION, P0)

**Предусловия:**
- WAREHOUSE_MAIN_GRUZ: 5 активных кодов NOMENCLATURE_1, 3 активных кода NOMENCLATURE_2
- 2 кода NOMENCLATURE_1 — is_used=True (списаны)

**Шаги:**
1. GET /api/warehouses/{id}/counters/

**Ожидаемый результат:**
- NOMENCLATURE_1: active_count=5 (не 7 — списанные не учитываются)
- NOMENCLATURE_2: active_count=3

---

### TC-COUNT-002: Счётчик обновляется после проведения (POSITIVE, INTEGRATION, P0)

**Предусловия:**
- Счётчик NOMENCLATURE_1 на WAREHOUSE_MAIN_GRUZ = 5

**Шаги:**
1. Провести документ с quantity=2
2. GET /api/warehouses/{id}/counters/

**Ожидаемый результат:**
- Счётчик = 3

---

### TC-COUNT-003: Счётчик восстанавливается после распроведения (POSITIVE, INTEGRATION, P0)

**Предусловия:**
- Счётчик NOMENCLATURE_1 = 3 (после проведения на 2)

**Шаги:**
1. Распровести документ
2. GET /api/warehouses/{id}/counters/

**Ожидаемый результат:**
- Счётчик = 5 (восстановлен)

---

### TC-FILTER-001: Фильтрация документов по площадке-источнику (POSITIVE, INTEGRATION, P1)

**Предусловия:**
- 3 документа: 2 с source_platform=PLATFORM_SOF_GRUZ, 1 с source_platform=PLATFORM_SOF_LEG

**Шаги:**
1. GET /api/documents/?source_platform=PLATFORM_SOF_GRUZ

**Ожидаемый результат:**
- Возвращено 2 документа
- Все документы имеют source_platform=PLATFORM_SOF_GRUZ

---

### TC-FILTER-002: Фильтрация документов по площадке списания (POSITIVE, INTEGRATION, P1)

**Предусловия:**
- 3 документа: 2 с writeoff_platform=PLATFORM_SOF_GRUZ, 1 с writeoff_platform=PLATFORM_SOF_LEG

**Шаги:**
1. GET /api/documents/?writeoff_platform=PLATFORM_SOF_LEG

**Ожидаемый результат:**
- Возвращен 1 документ
- Документ имеет writeoff_platform=PLATFORM_SOF_LEG

---

### TC-FILTER-003: Комбинированная фильтрация (POSITIVE, INTEGRATION, P2)

**Предусловия:**
- Документы с разными source_platform и writeoff_platform

**Шаги:**
1. GET /api/documents/?source_platform=PLATFORM_SOF_GRUZ&writeoff_platform=PLATFORM_SOF_LEG

**Ожидаемый результат:**
- Возвращены только документы, где source_platform=GRUZ AND writeoff_platform=LEG
- (Документы списания с чужой площадки)

---

## МОДУЛЬ 7. ПРАВА ДОСТУПА

### TC-AUTH-001: Кладовщик видит только свои документы (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-12
**Предусловия:**
- USER_STOREKEEPER_1 — 2 документа
- USER_STOREKEEPER_2 — 1 документ

**Шаги:**
1. GET /api/documents/ от имени USER_STOREKEEPER_1

**Ожидаемый результат:**
- Возвращено 2 документа (автор = USER_STOREKEEPER_1)
- Документ USER_STOREKEEPER_2 отсутствует

---

### TC-AUTH-002: Начальник видит все документы своей площадки (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-11
**Предусловия:**
- USER_MANAGER (platform=PLATFORM_SOF_GRUZ)
- 3 документа с source_platform=PLATFORM_SOF_GRUZ от разных кладовщиков
- 1 документ с source_platform=PLATFORM_SOF_LEG

**Шаги:**
1. GET /api/documents/ от имени USER_MANAGER

**Ожидаемый результат:**
- Возвращено 3 документа (все с source_platform=PLATFORM_SOF_GRUZ)
- Документ с PLATFORM_SOF_LE
- Документ с PLATFORM_SOF_LEG отсутствует

---

### TC-AUTH-003: Начальник — документы чужой площадки только для чтения (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-11
**Предусловия:**
- USER_MANAGER (platform=PLATFORM_SOF_GRUZ)
- Документ с source_platform=PLATFORM_SOF_LEG, статус 'saved'

**Шаги:**
1. GET /api/documents/{id}/ от имени USER_MANAGER
2. PATCH /api/documents/{id}/ от имени USER_MANAGER
3. POST /api/documents/{id}/post/ от имени USER_MANAGER

**Ожидаемый результат:**
- Шаг 1: HTTP 200, данные получены
- Шаг 2: HTTP 403, редактирование запрещено
- Шаг 3: HTTP 403, проведение запрещено

---

### TC-AUTH-004: Кладовщик — списание с чужой площадки (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-13
**Предусловия:**
- USER_STOREKEEPER_1 (platform=PLATFORM_SOF_GRUZ)
- WAREHOUSE_MAIN_LEG принадлежит PLATFORM_SOF_LEG
- На WAREHOUSE_MAIN_LEG есть 5 активных кодов NOMENCLATURE_1

**Шаги:**
1. Создать документ списания от USER_STOREKEEPER_1 с source_warehouse=WAREHOUSE_MAIN_LEG
2. Добавить строку: NOMENCLATURE_1, quantity=3
3. Провести документ

**Ожидаемый результат:**
- Документ создан, author=USER_STOREKEEPER_1
- source_platform=PLATFORM_SOF_GRUZ (площадка автора)
- writeoff_platform=PLATFORM_SOF_LEG (площадка склада-источника)
- Коды списаны со склада WAREHOUSE_MAIN_LEG
- Счётчик WAREHOUSE_MAIN_LEG уменьшен на 3

---

### TC-AUTH-005: Кладовщик не видит чужие документы (NEGATIVE, INTEGRATION, P0)

**Связанные правила:** BR-12
**Предусловия:**
- USER_STOREKEEPER_1
- Документ, автор=USER_STOREKEEPER_2

**Шаги:**
1. GET /api/documents/{id}/ от имени USER_STOREKEEPER_1

**Ожидаемый результат:**
- HTTP 404 (документ не найден) или 403 (доступ запрещён)
- Данные документа не возвращены

---

### TC-AUTH-006: Кладовщик не может редактировать чужие документы (NEGATIVE, INTEGRATION, P1)

**Связанные правила:** BR-12
**Предусловия:**
- Документ, автор=USER_STOREKEEPER_2, статус 'saved'

**Шаги:**
1. PATCH /api/documents/{id}/ от имени USER_STOREKEEPER_1

**Ожидаемый результат:**
- HTTP 403 или 404
- Документ не изменён

---

### TC-AUTH-007: Выкуп — target_warehouse заполняется (POSITIVE, INTEGRATION, P1)

**Связанные правила:** BR-8
**Предусловия:**
- USER_STOREKEEPER_1 (platform=PLATFORM_SOF_GRUZ)
- source_warehouse=WAREHOUSE_OH_GRUZ (склад ОХ)
- WAREHOUSE_MAIN_GRUZ — основной склад PLATFORM_SOF_GRUZ

**Шаги:**
1. Создать документ выкупа (doc_type='buyout') с source_warehouse=WAREHOUSE_OH_GRUZ
2. Сохранить и провести

**Ожидаемый результат:**
- target_warehouse=WAREHOUSE_MAIN_GRUZ (основной склад площадки автора)
- При проведении: коды перевязаны на WAREHOUSE_MAIN_GRUZ (локальная приписка)
- Повторный запрос в «Честный знак» НЕ отправлялся
- Счётчик WAREHOUSE_OH_GRUZ уменьшен
- Счётчик WAREHOUSE_MAIN_GRUZ увеличен (коды теперь активны на новом складе)

---

## МОДУЛЬ 8. КОНКУРЕНТНОСТЬ И ТРАНЗАКЦИИ

### TC-CONC-001: Конкурентное проведение — кто первым, тот забрал коды (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-6
**Предусловия:**
- 3 активных кода NOMENCLATURE_1 на складе
- Документ_А: quantity=2 (автор USER_STOREKEEPER_1)
- Документ_Б: quantity=2 (автор USER_STOREKEEPER_1 или другой)
- Оба в статусе 'saved'

**Шаги:**
1. Одновременно (в одной транзакции / параллельных запросах) провести оба документа

**Ожидаемый результат:**
- Один документ проведён успешно (HTTP 200)
- Второй — отклонён (HTTP 409: нехватка, доступно=1)
- Суммарно списано ровно 3 кода (не больше)
- Атомарность: ни один код не списан дважды

---

### TC-CONC-002: Откат транзакции при ошибке — данные консистентны (POSITIVE, INTEGRATION, P0)

**Связанные правила:** BR-6
**Предусловия:**
- Документ с 2 строками, вторая — нехватка

**Шаги:**
1. Провести документ
2. Проверить все коды, счётчики, статус документа

**Ожидаемый результат:**
- Документ: статус 'saved' (не изменился)
- Все коды: is_active=True, is_used=False (ни один не списан)
- Все счётчики: исходные значения
- posted_at=null

---

## СВОДНАЯ ТАБЛИЦА ПОКРЫТИЯ

| Модуль                  | Кол-во тестов | P0 | P1 | P2 |
|-------------------------|---------------|----|----|----| 
| Загрузка кодов           | 13            | 5  | 6  | 2  |
| Документы               | 11            | 4  | 6  | 1  |
| Проведение               | 8             | 5  | 3  | 0  |
| Распроведение/удаление  | 4             | 0  | 4  | 0  |
| Экранное отображение     | 3             | 2  | 1  | 0  |
| Счётчики и фильтрация    | 6             | 3  | 2  | 1  |
| Права доступа            | 7             | 5  | 2  | 0  |
| Конкурентность           | 2             | 2  | 0  | 0  |
| **ИТОГО**               | **54**        | **26** | **24** | **4** |

### Покрытие бизнес-правил

| BR  | Правило                        | Тест-кейсы                              |
|-----|--------------------------------|-----------------------------------------|
| 1   | Авто-создание номенклатуры      | TC-LOAD-001, 004, 006, 007, 012        |
| 2   | Нераспознанные коды              | TC-LOAD-004, 005, 012                   |
| 3   | Дедупликация                     | TC-LOAD-002, 003, 012                   |
| 4   | Маппинг владелец→склад           | TC-LOAD-010 (отсутствие склада)          |
| 5   | Экранное отображение             | TC-DISPLAY-001, 002                     |
| 6   | Параллельная работа              | TC-POST-001–003, TC-CONC-001, 002       |
| 7   | FIFO                            | TC-POST-001, 004                       |
| 8   | Выкуп                            | TC-AUTH-007                            |
| 9   | Редактирование проведённого      | TC-DOC-010, TC-UNPOST-001              |
| 10  | Помечен на удаление              | TC-UNPOST-002, 004                     |
| 11  | Начальник — чужие площадки       | TC-AUTH-002, 003                       |
| 12  | Кладовщик — чужие документы      | TC-AUTH-001, 005, 006                  |
| 13  | Списание с чужой площадки        | TC-POST-006, TC-AUTH-004               |
| 14  | product_name                    | TC-LOAD-006, 008, 009                  |
| 15  | Дубликаты номенклатуры           | TC-DOC-008, 009                        |
| 16  | Нумерация документов             | TC-DOC-002–006                         |
