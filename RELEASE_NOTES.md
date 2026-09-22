# Release Notes — TireTrack v2.0

**Дата релиза:** 2026-09-22  
**Версия:** v2.0 (TireCode, новые модели документов)

---

## 🎯 Обзор изменений

TireTrack v2.0 — масштабная миграция на новые модели данных с улучшенной системой складского документооборота.

### Ключевые нововведения:
- ✅ Новая модель `TireCode` вместо `Tire` (поддержка DataMatrix)
- ✅ Система документов с FIFO и atomic операциями
- ✅ Экранное отображение кодов документов
- ✅ Карточки кодов с генерацией DataMatrix
- ✅ Обновлённая интеграция с Честным Знаком (`infoFromDataMatrix`)
- ✅ 113 тестов (все проходят ✅)

---

## ⚠️ Breaking Changes

### 1. Удаление модели `WarehouseMovement`

**Было:**
```python
class WarehouseMovement(models.Model):
    document = FK
    tire = FK
    movement_type = CharField
```

**Стало:**
- Модель удалена
- История перемещений хранится в `TireCode.document`
- Для отслеживания используйте `document.tire_codes.all()`

### 2. Изменение модели `Tire` → `TireCode`

**Было:**
```python
class Tire(models.Model):
    qr_code = CharField
    brand = CharField
    model = CharField
    size = CharField
    # ... поля в модели
```

**Стало:**
```python
class TireCode(models.Model):
    qr_code = CharField(unique=True)
    nomenclature = FK(TireNomenclature)
    warehouse = FK(Warehouse)
    is_active = BooleanField
    is_used = BooleanField
    document = FK(Document, null=True)
    honest_sign_data = JSONField
```

**Миграция:**
- Данные перенесены через `0007_migrate_tire_to_tirecode.py`
- Старая модель `Tire` оставлена для обратной совместимости
- Используйте `TireCode.objects.filter(is_active=True)` для активных кодов

### 3. Изменение `DocumentItem` с M2M на FK

**Было:**
```python
class DocumentItem(models.Model):
    document = FK
    tires = M2M(Tire)
    product_name = CharField
```

**Стало:**
```python
class DocumentItem(models.Model):
    document = FK
    nomenclature = FK(TireNomenclature)
    quantity = IntegerField
    # tires привязываются через document.tire_codes
```

**Миграция:**
- `items` теперь хранят ссылку на номенклатуру
- Конкретные коды привязываются при проведении через FIFO

### 4. Изменение статусов документов

**Было:**
- `draft` — черновик
- `saved` — сохранён
- `posted` — проведён
- `deleted` — удалён

**Стало:**
- `draft` — черновик (номер не присвоен)
- `saved` — сохранён (номер присвоен, нельзя удалить)
- `posted` — проведён (коды использованы)
- `marked_deleted` — помечен на удаление

### 5. Обновление API Честного Знака

**Было:**
```python
crpt.get_product_info(qr_code)
```

**Стало:**
```python
crpt.infoFromDataMatrix(qr_code)
```

**Файл:** `integrations/honest_sign.py`

---

## 📦 Новые модели

### tires.models

#### `Platform`
Площадка для организации складов.
```python
class Platform(models.Model):
    name = CharField(unique=True)
    created_at = DateTimeField(auto_now_add=True)
```

#### `TireNomenclature`
Номенклатура шин (технические характеристики).
```python
class TireNomenclature(models.Model):
    brand = CharField(max_length=100)
    model = CharField(max_length=100)
    size = CharField(max_length=50)
    product_name = CharField(blank=True, null=True)
    
    class Meta:
        unique_together = ['brand', 'model', 'size']
```

#### `TireCode`
Конкретный код DataMatrix.
```python
class TireCode(models.Model):
    qr_code = CharField(unique=True)
    nomenclature = FK(TireNomenclature)
    warehouse = FK(Warehouse, null=True)
    supplier = FK(Supplier, null=True)
    is_active = BooleanField(default=True)
    is_used = BooleanField(default=False)
    document = FK(Document, null=True, blank=True)
    honest_sign_data = JSONField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    used_at = DateTimeField(null=True, blank=True)
```

**Методы:**
- `mark_used(document)` — пометить как использованный
- `unmark_used()` — снять пометку

### warehouse.models

#### `DocType`
Тип документа (списание/выкуп).
```python
class DocType(models.Model):
    code = CharField(unique=True)  # 'writeoff', 'buyout'
    name = CharField(max_length=100)
    prefix = CharField(max_length=10)  # 'СП', 'ВК'
    is_active = BooleanField(default=True)
```

#### `Document`
Документ складского документооборота.
```python
class Document(models.Model):
    doc_type = FK(DocType)
    number = CharField(unique=True, null=True)  # 'СП-2026-000001'
    status = CharField(choices=['draft', 'saved', 'posted', 'marked_deleted'])
    author = FK(User)
    source_platform = FK(Platform)
    writeoff_platform = FK(Platform, null=True)
    source_warehouse = FK(Warehouse)
    target_warehouse = FK(Warehouse, null=True)
    is_deleted = BooleanField(default=False)
    posted_at = DateTimeField(null=True, blank=True)
```

**Методы:**
- `can_edit()` — можно ли редактировать
- `can_post()` — можно ли провести

#### `DocumentItem`
Позиция документа.
```python
class DocumentItem(models.Model):
    document = FK(Document)
    nomenclature = FK(TireNomenclature)
    quantity = IntegerField
    
    class Meta:
        unique_together = ['document', 'nomenclature']
```

---

## 🔧 Новые сервисы

### DocumentService

**warehouse/services.py**

```python
# Создание документа
document = DocumentService.create(
    user=request.user,
    doc_type=doc_type,
    source_warehouse=warehouse,
    target_warehouse=target_warehouse,
    notes='...'
)

# Сохранение черновика
document = DocumentService.save_draft(document)

# Добавление строки
item, is_duplicate = DocumentService.add_item(
    document,
    nomenclature,
    quantity=1
)

# Проведение (FIFO)
document = DocumentService.post_document(document)

# Распроведение
document = DocumentService.unpost_document(document)

# Пометка на удаление
document = DocumentService.mark_deleted(document)

# Удаление строки
DocumentService.delete_item(item)
```

### UploadService

**tires/services.py**

```python
service = UploadService(warehouse=warehouse, supplier=supplier)
report = service.upload(['QR001', 'QR002', 'QR003'])

# Отчёт
report.total_lines    # всего строк
report.created        # создано
report.duplicates     # дубликаты
report.unrecognized   # нераспознанные
report.honest_sign_errors  # ошибки ЧЗ
```

---

## 🎨 Новые экраны

### 1. Дашборд (`/warehouse/`)
- Счётчики кодов (всего, active, used)
- Счётчики документов (draft, saved, posted)
- Последние 5 документов

### 2. Экран кодов (`/warehouse/documents/<id>/codes/`)
- Пагинация (50 кодов на странице)
- Фильтр по номенклатуре
- Клик на код → карточка

### 3. Карточка кода (`/warehouse/codes/<id>/card/`)
- Генерация DataMatrix (PNG, base64)
- Информация о номенклатуре
- Статус кода

### 4. AJAX endpoints
- `nomenclature_search` — поиск по бренду/модели/размеру
- `document_add_item` — добавление строки
- `document_update_item` — обновление количества
- `document_delete_item` — удаление строки
- `document_autosave` — автосохранение
- `counters_api` — счётчики активных кодов

---

## 📊 Статистика тестов

| Приложение | Тестов | Статус |
|------------|--------|--------|
| warehouse.tests_document_service | 9 | ✅ |
| warehouse.tests_posting | 9 | ✅ |
| warehouse.tests_views | 15 | ✅ |
| warehouse.tests_ajax | 18 | ✅ |
| tires.tests | 20 | ✅ |
| qr_processing.tests | 11 | ✅ |
| qr_processing.tests_upload_service | 13 | ✅ |
| users.tests | 18 | ✅ |
| **ИТОГО** | **113** | **✅** |

---

## 🚀 Миграция с v1.0

### Шаг 1: Резервное копирование
```bash
pg_dump tiretrack > backup_v1.sql
```

### Шаг 2: Применение миграций
```bash
python manage.py migrate
```

### Шаг 3: Проверка данных
```bash
# Проверка TireCode
python manage.py shell
>>> from tires.models import TireCode
>>> TireCode.objects.count()
>>> TireCode.objects.filter(is_active=True).count()

# Проверка документов
>>> from warehouse.models import Document
>>> Document.objects.count()
```

### Шаг 4: Обновление кода
- Замените импорты `from tires.models import Tire` на `TireCode`
- Замените `tires = M2M` на `nomenclature = FK`
- Обновите вызовы API Честного Знака

### Шаг 5: Тестирование
```bash
python manage.py test
python manage.py check
```

---

## 🐛 Известные проблемы

Нет известных проблем в v2.0.

---

## 📝 Изменения в API

### HonestSignClient

**Было:**
```python
crpt.get_product_info(qr_code)
```

**Стало:**
```python
crpt.infoFromDataMatrix(qr_code)
```

**Файл:** `integrations/honest_sign.py`

---

## 🙏 Благодарности

Спасибо всем, кто тестировал и предоставлял фидбек!

---

**Версия:** v2.0  
**Дата:** 2026-09-22  
**Совместимость:** Python 3.14, Django 4.2, PostgreSQL
